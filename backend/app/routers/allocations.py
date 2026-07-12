from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..dependencies import require_asset_manager, require_department_head, require_any_role, get_current_user
from .. import schemas, crud, models

router = APIRouter(prefix="/api/allocations", tags=["Asset Allocation & Transfers"])

@router.post("/allocate/{asset_id}", response_model=schemas.AssetOut)
def allocate_asset_to_holder(
    asset_id: int,
    alloc_in: schemas.AssetAllocate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_asset_manager)
):
    db_asset = crud.get_asset_by_id(db, asset_id)
    if not db_asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    # --- CONFLICT RULE (Double Allocation Block) ---
    if db_asset.status != "Available":
        holder_name = "Unknown"
        dept_name = "Unknown"
        
        if db_asset.current_holder:
            holder_name = db_asset.current_holder.name
            if db_asset.current_holder.department:
                dept_name = db_asset.current_holder.department.name
        elif db_asset.department:
            holder_name = "Department-wide"
            dept_name = db_asset.department.name
            
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Already Allocated to {holder_name} ({dept_name}). Direct re-allocation is blocked - submit a transfer request below."
        )
        
    # Verify target employee if specified
    if alloc_in.employee_id:
        target_emp = crud.get_user_by_id(db, alloc_in.employee_id)
        if not target_emp:
            raise HTTPException(status_code=400, detail="Target employee not found")
        # Auto-fill department from employee if not specified
        if not alloc_in.department_id:
            alloc_in.department_id = target_emp.department_id

    # Verify target department if specified
    if alloc_in.department_id:
        dept = db.query(models.Department).filter(models.Department.id == alloc_in.department_id).first()
        if not dept:
            raise HTTPException(status_code=400, detail="Target department not found")
            
    updated_asset = crud.allocate_asset(db, asset_id, alloc_in, actor_id=current_user.id)
    
    holder_name = updated_asset.current_holder.name if updated_asset.current_holder else None
    dept_name = updated_asset.department.name if updated_asset.department else None
    return schemas.AssetOut(
        id=updated_asset.id,
        name=updated_asset.name,
        asset_tag=updated_asset.asset_tag,
        serial_number=updated_asset.serial_number,
        qr_code=updated_asset.qr_code,
        category_id=updated_asset.category_id,
        category_name=updated_asset.category.name,
        status=updated_asset.status,
        condition=updated_asset.condition,
        location=updated_asset.location,
        acquisition_cost=updated_asset.acquisition_cost,
        acquisition_date=updated_asset.acquisition_date,
        is_shared=updated_asset.is_shared,
        current_holder_id=updated_asset.current_holder_id,
        current_holder_name=holder_name,
        department_id=updated_asset.department_id,
        department_name=dept_name
    )

@router.post("/return/{asset_id}", response_model=schemas.AssetOut)
def return_allocated_asset(
    asset_id: int,
    return_in: schemas.AssetReturn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_asset_manager)
):
    db_asset = crud.get_asset_by_id(db, asset_id)
    if not db_asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if db_asset.status != "Allocated":
        raise HTTPException(status_code=400, detail="Asset is not currently allocated")
        
    updated_asset = crud.return_asset(db, asset_id, return_in, actor_id=current_user.id)
    
    holder_name = updated_asset.current_holder.name if updated_asset.current_holder else None
    dept_name = updated_asset.department.name if updated_asset.department else None
    return schemas.AssetOut(
        id=updated_asset.id,
        name=updated_asset.name,
        asset_tag=updated_asset.asset_tag,
        serial_number=updated_asset.serial_number,
        qr_code=updated_asset.qr_code,
        category_id=updated_asset.category_id,
        category_name=updated_asset.category.name,
        status=updated_asset.status,
        condition=updated_asset.condition,
        location=updated_asset.location,
        acquisition_cost=updated_asset.acquisition_cost,
        acquisition_date=updated_asset.acquisition_date,
        is_shared=updated_asset.is_shared,
        current_holder_id=updated_asset.current_holder_id,
        current_holder_name=holder_name,
        department_id=updated_asset.department_id,
        department_name=dept_name
    )

@router.post("/transfer-request/{asset_id}", response_model=schemas.TransferRequestOut)
def request_asset_transfer(
    asset_id: int,
    req_in: schemas.TransferRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any_role)
):
    # Retrieve asset
    db_asset = crud.get_asset_by_id(db, asset_id)
    if not db_asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if db_asset.status != "Allocated":
        raise HTTPException(status_code=400, detail="Asset is not currently allocated. You can allocate it directly.")
        
    # Check if target employee exists
    target = crud.get_user_by_id(db, req_in.to_employee_id)
    if not target:
        raise HTTPException(status_code=400, detail="Target employee not found")
        
    # Prevent transfer to the same person
    if db_asset.current_holder_id == req_in.to_employee_id:
        raise HTTPException(status_code=400, detail="Asset is already allocated to this employee")

    req = crud.create_transfer_request(db, asset_id, current_user.id, req_in)
    if not req:
        raise HTTPException(status_code=500, detail="Failed to create transfer request")
        
    return schemas.TransferRequestOut(
        id=req.id,
        asset_id=req.asset_id,
        asset_tag=req.asset.asset_tag,
        asset_name=req.asset.name,
        from_employee_id=req.from_employee_id,
        from_employee_name=req.from_employee.name,
        to_employee_id=req.to_employee_id,
        to_employee_name=req.to_employee.name,
        reason=req.reason,
        status=req.status,
        approved_by_id=req.approved_by_id,
        created_at=req.created_at
    )

@router.get("/transfers", response_model=List[schemas.TransferRequestOut])
def list_transfer_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any_role)
):
    reqs = crud.get_transfer_requests(db)
    res = []
    for req in reqs:
        res.append(
            schemas.TransferRequestOut(
                id=req.id,
                asset_id=req.asset_id,
                asset_tag=req.asset.asset_tag,
                asset_name=req.asset.name,
                from_employee_id=req.from_employee_id,
                from_employee_name=req.from_employee.name,
                to_employee_id=req.to_employee_id,
                to_employee_name=req.to_employee.name,
                reason=req.reason,
                status=req.status,
                approved_by_id=req.approved_by_id,
                created_at=req.created_at
            )
        )
    return res

@router.put("/transfers/{id}/approve", response_model=schemas.TransferRequestOut)
def approve_transfer(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_department_head)
):
    req = db.query(models.TransferRequest).filter(models.TransferRequest.id == id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Transfer request not found")
    if req.status != "Pending":
        raise HTTPException(status_code=400, detail="Transfer request is already processed")
        
    # Department Head Specific Security:
    # They can only approve if they belong to the same department as BOTH from and to employees
    if current_user.role == "department_head":
        if not (current_user.department_id == req.from_employee.department_id == req.to_employee.department_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Department Heads can only approve transfer requests where both the current holder and the recipient belong to their own department. Please contact an Asset Manager or Admin."
            )
            
    approved_req = crud.approve_transfer_request(db, id, current_user.id)
    return schemas.TransferRequestOut(
        id=approved_req.id,
        asset_id=approved_req.asset_id,
        asset_tag=approved_req.asset.asset_tag,
        asset_name=approved_req.asset.name,
        from_employee_id=approved_req.from_employee_id,
        from_employee_name=approved_req.from_employee.name,
        to_employee_id=approved_req.to_employee_id,
        to_employee_name=approved_req.to_employee.name,
        reason=approved_req.reason,
        status=approved_req.status,
        approved_by_id=approved_req.approved_by_id,
        created_at=approved_req.created_at
    )

@router.put("/transfers/{id}/reject", response_model=schemas.TransferRequestOut)
def reject_transfer(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_department_head)
):
    req = db.query(models.TransferRequest).filter(models.TransferRequest.id == id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Transfer request not found")
    if req.status != "Pending":
        raise HTTPException(status_code=400, detail="Transfer request is already processed")
        
    # Department Head Specific Security
    if current_user.role == "department_head":
        if not (current_user.department_id == req.from_employee.department_id == req.to_employee.department_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Department Heads can only reject transfer requests within their own department."
            )
            
    rejected_req = crud.reject_transfer_request(db, id, current_user.id)
    return schemas.TransferRequestOut(
        id=rejected_req.id,
        asset_id=rejected_req.asset_id,
        asset_tag=rejected_req.asset.asset_tag,
        asset_name=rejected_req.asset.name,
        from_employee_id=rejected_req.from_employee_id,
        from_employee_name=rejected_req.from_employee.name,
        to_employee_id=rejected_req.to_employee_id,
        to_employee_name=rejected_req.to_employee.name,
        reason=rejected_req.reason,
        status=rejected_req.status,
        approved_by_id=rejected_req.approved_by_id,
        created_at=rejected_req.created_at
    )
