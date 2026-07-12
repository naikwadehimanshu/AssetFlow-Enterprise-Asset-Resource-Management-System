from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..dependencies import require_asset_manager, require_any_role, get_current_user
from .. import schemas, crud, models

router = APIRouter(prefix="/api/maintenance", tags=["Maintenance Management"])

@router.get("", response_model=List[schemas.MaintenanceOut])
def list_maintenance_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any_role)
):
    reqs = crud.get_maintenance_requests(db)
    res = []
    for r in reqs:
        res.append(
            schemas.MaintenanceOut(
                id=r.id,
                asset_id=r.asset_id,
                asset_tag=r.asset.asset_tag,
                asset_name=r.asset.name,
                reporter_id=r.reporter_id,
                reporter_name=r.reporter.name,
                description=r.description,
                priority=r.priority,
                status=r.status,
                technician_name=r.technician_name,
                resolution_notes=r.resolution_notes,
                photo_url=r.photo_url,
                created_at=r.created_at,
                updated_at=r.updated_at
            )
        )
    return res

@router.post("", response_model=schemas.MaintenanceOut, status_code=status.HTTP_201_CREATED)
def raise_maintenance_request(
    maint_in: schemas.MaintenanceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any_role)
):
    db_asset = crud.get_asset_by_id(db, maint_in.asset_id)
    if not db_asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    m = crud.create_maintenance_request(db, maint_in, reporter_id=current_user.id)
    return schemas.MaintenanceOut(
        id=m.id,
        asset_id=m.asset_id,
        asset_tag=db_asset.asset_tag,
        asset_name=db_asset.name,
        reporter_id=m.reporter_id,
        reporter_name=current_user.name,
        description=m.description,
        priority=m.priority,
        status=m.status,
        technician_name=m.technician_name,
        resolution_notes=m.resolution_notes,
        photo_url=m.photo_url,
        created_at=m.created_at,
        updated_at=m.updated_at
    )

@router.put("/{id}/status", response_model=schemas.MaintenanceOut)
def update_maintenance_request_status(
    id: int,
    status_in: schemas.MaintenanceStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_asset_manager)
):
    # Verify status transition is valid
    valid_statuses = ["Pending", "Approved", "Rejected", "Technician Assigned", "In Progress", "Resolved"]
    if status_in.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid maintenance status. Must be one of {valid_statuses}."
        )
        
    m = crud.update_maintenance_status(db, id, status_in, actor_id=current_user.id)
    if not m:
        raise HTTPException(status_code=404, detail="Maintenance request not found")
        
    return schemas.MaintenanceOut(
        id=m.id,
        asset_id=m.asset_id,
        asset_tag=m.asset.asset_tag,
        asset_name=m.asset.name,
        reporter_id=m.reporter_id,
        reporter_name=m.reporter.name,
        description=m.description,
        priority=m.priority,
        status=m.status,
        technician_name=m.technician_name,
        resolution_notes=m.resolution_notes,
        photo_url=m.photo_url,
        created_at=m.created_at,
        updated_at=m.updated_at
    )
