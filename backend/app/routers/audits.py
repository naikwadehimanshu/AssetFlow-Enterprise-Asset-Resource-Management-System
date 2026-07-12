from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from ..database import get_db
from ..dependencies import require_admin, require_any_role, get_current_user
from .. import schemas, crud, models

router = APIRouter(prefix="/api/audits", tags=["Asset Audits"])

@router.post("/cycles", response_model=schemas.AuditCycleOut, status_code=status.HTTP_201_CREATED)
def create_audit_cycle(
    audit_in: schemas.AuditCycleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    cycle = crud.create_audit_cycle(db, audit_in, actor_id=current_user.id)
    auditor_names = [a.auditor.name for a in cycle.assignments]
    return schemas.AuditCycleOut(
        id=cycle.id,
        name=cycle.name,
        start_date=cycle.start_date,
        end_date=cycle.end_date,
        scope_type=cycle.scope_type,
        scope_value=cycle.scope_value,
        status=cycle.status,
        auditor_names=auditor_names
    )

@router.get("/cycles", response_model=List[schemas.AuditCycleOut])
def list_audit_cycles(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any_role)
):
    cycles = crud.get_audit_cycles(db)
    res = []
    for c in cycles:
        auditor_names = [a.auditor.name for a in c.assignments]
        res.append(
            schemas.AuditCycleOut(
                id=c.id,
                name=c.name,
                start_date=c.start_date,
                end_date=c.end_date,
                scope_type=c.scope_type,
                scope_value=c.scope_value,
                status=c.status,
                auditor_names=auditor_names
            )
        )
    return res

@router.get("/cycles/{id}/records", response_model=List[schemas.AuditRecordOut])
def get_audit_cycle_records(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any_role)
):
    cycle = db.query(models.AuditCycle).filter(models.AuditCycle.id == id).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Audit cycle not found")
        
    records = crud.get_audit_records(db, id)
    res = []
    for r in records:
        holder_name = r.asset.current_holder.name if r.asset.current_holder else None
        auditor_name = r.auditor.name if r.auditor else None
        res.append(
            schemas.AuditRecordOut(
                id=r.id,
                audit_cycle_id=r.audit_cycle_id,
                asset_id=r.asset_id,
                asset_tag=r.asset.asset_tag,
                asset_name=r.asset.name,
                asset_location=r.asset.location,
                expected_holder_name=holder_name,
                verification_status=r.verification_status,
                notes=r.notes,
                auditor_id=r.auditor_id,
                auditor_name=auditor_name,
                audited_at=r.audited_at
            )
        )
    return res

@router.put("/records/{record_id}", response_model=schemas.AuditRecordOut)
def verify_audit_record(
    record_id: int,
    record_update: schemas.AuditRecordUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any_role)
):
    rec = db.query(models.AuditRecord).filter(models.AuditRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Audit record not found")
        
    # Check if cycle is active
    if rec.audit_cycle.status == "Closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update records in a closed audit cycle."
        )
        
    # Verify authorization: Only assigned auditors, an Asset Manager, or Admin can log audit status
    assigned_auditors = [a.auditor_id for a in rec.audit_cycle.assignments]
    if current_user.role not in ["admin", "asset_manager"] and current_user.id not in assigned_auditors:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned as an auditor for this cycle."
        )
        
    updated_rec = crud.update_audit_record(db, record_id, record_update, auditor_id=current_user.id)
    holder_name = updated_rec.asset.current_holder.name if updated_rec.asset.current_holder else None
    
    return schemas.AuditRecordOut(
        id=updated_rec.id,
        audit_cycle_id=updated_rec.audit_cycle_id,
        asset_id=updated_rec.asset_id,
        asset_tag=updated_rec.asset.asset_tag,
        asset_name=updated_rec.asset.name,
        asset_location=updated_rec.asset.location,
        expected_holder_name=holder_name,
        verification_status=updated_rec.verification_status,
        notes=updated_rec.notes,
        auditor_id=updated_rec.auditor_id,
        auditor_name=current_user.name,
        audited_at=updated_rec.audited_at
    )

@router.post("/cycles/{id}/close", response_model=schemas.AuditCycleOut)
def close_audit_cycle(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    cycle = db.query(models.AuditCycle).filter(models.AuditCycle.id == id).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Audit cycle not found")
    if cycle.status == "Closed":
        raise HTTPException(status_code=400, detail="Audit cycle is already closed")
        
    # Verify that all records have been audited (status is not Pending)
    pending_records = db.query(models.AuditRecord).filter(
        models.AuditRecord.audit_cycle_id == id,
        models.AuditRecord.verification_status == "Pending"
    ).count()
    
    if pending_records > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot close audit cycle. There are still {pending_records} pending asset verifications. All items must be marked Verified, Missing, or Damaged."
        )
        
    closed_cycle = crud.close_audit_cycle(db, id, actor_id=current_user.id)
    auditor_names = [a.auditor.name for a in closed_cycle.assignments]
    return schemas.AuditCycleOut(
        id=closed_cycle.id,
        name=closed_cycle.name,
        start_date=closed_cycle.start_date,
        end_date=closed_cycle.end_date,
        scope_type=closed_cycle.scope_type,
        scope_value=closed_cycle.scope_value,
        status=closed_cycle.status,
        auditor_names=auditor_names
    )
