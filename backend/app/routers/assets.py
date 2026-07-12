from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from ..database import get_db
from ..dependencies import require_asset_manager, require_any_role
from .. import schemas, crud, models

router = APIRouter(prefix="/api/assets", tags=["Assets"])

@router.get("", response_model=List[schemas.AssetOut])
def search_and_list_assets(
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    department_id: Optional[int] = None,
    location: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any_role)
):
    assets = crud.get_assets(
        db, search=search, category_id=category_id, status=status, 
        department_id=department_id, location=location
    )
    result = []
    for a in assets:
        holder_name = a.current_holder.name if a.current_holder else None
        dept_name = a.department.name if a.department else None
        result.append(
            schemas.AssetOut(
                id=a.id,
                name=a.name,
                asset_tag=a.asset_tag,
                serial_number=a.serial_number,
                qr_code=a.qr_code,
                category_id=a.category_id,
                category_name=a.category.name,
                status=a.status,
                condition=a.condition,
                location=a.location,
                acquisition_cost=a.acquisition_cost,
                acquisition_date=a.acquisition_date,
                is_shared=a.is_shared,
                current_holder_id=a.current_holder_id,
                current_holder_name=holder_name,
                department_id=a.department_id,
                department_name=dept_name
            )
        )
    return result

@router.post("", response_model=schemas.AssetOut, status_code=status.HTTP_201_CREATED)
def register_new_asset(
    asset_in: schemas.AssetCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_asset_manager)
):
    a = crud.create_asset(db, asset_in, actor_id=current_user.id)
    return schemas.AssetOut(
        id=a.id,
        name=a.name,
        asset_tag=a.asset_tag,
        serial_number=a.serial_number,
        qr_code=a.qr_code,
        category_id=a.category_id,
        category_name=a.category.name,
        status=a.status,
        condition=a.condition,
        location=a.location,
        acquisition_cost=a.acquisition_cost,
        acquisition_date=a.acquisition_date,
        is_shared=a.is_shared,
        current_holder_id=a.current_holder_id,
        current_holder_name=None,
        department_id=a.department_id,
        department_name=None
    )

@router.get("/{id}", response_model=Dict[str, Any])
def get_asset_details_with_history(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any_role)
):
    a = crud.get_asset_by_id(db, id)
    if not a:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    holder_name = a.current_holder.name if a.current_holder else None
    dept_name = a.department.name if a.department else None
    
    # Format allocation history
    alloc_history_list = []
    for hist in a.allocation_history:
        alloc_history_list.append({
            "id": hist.id,
            "allocated_at": hist.allocated_at,
            "expected_return_date": hist.expected_return_date,
            "returned_at": hist.returned_at,
            "return_condition": hist.return_condition,
            "check_in_notes": hist.check_in_notes,
            "employee_name": hist.employee.name if hist.employee else None,
            "department_name": hist.department.name if hist.department else None
        })
        
    # Format maintenance history
    maint_history_list = []
    for maint in a.maintenance_requests:
        maint_history_list.append({
            "id": maint.id,
            "description": maint.description,
            "priority": maint.priority,
            "status": maint.status,
            "technician_name": maint.technician_name,
            "resolution_notes": maint.resolution_notes,
            "created_at": maint.created_at,
            "updated_at": maint.updated_at,
            "reporter_name": maint.reporter.name if maint.reporter else None
        })
        
    # Sort histories by date descending
    alloc_history_list.sort(key=lambda x: x["allocated_at"], reverse=True)
    maint_history_list.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "asset": {
            "id": a.id,
            "name": a.name,
            "asset_tag": a.asset_tag,
            "serial_number": a.serial_number,
            "qr_code": a.qr_code,
            "category_id": a.category_id,
            "category_name": a.category.name,
            "status": a.status,
            "condition": a.condition,
            "location": a.location,
            "acquisition_cost": a.acquisition_cost,
            "acquisition_date": a.acquisition_date,
            "is_shared": a.is_shared,
            "current_holder_id": a.current_holder_id,
            "current_holder_name": holder_name,
            "department_id": a.department_id,
            "department_name": dept_name
        },
        "allocation_history": alloc_history_list,
        "maintenance_history": maint_history_list
    }

@router.put("/{id}", response_model=schemas.AssetOut)
def update_existing_asset(
    id: int,
    asset_in: schemas.AssetUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_asset_manager)
):
    a = crud.update_asset(db, id, asset_in, actor_id=current_user.id)
    if not a:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    holder_name = a.current_holder.name if a.current_holder else None
    dept_name = a.department.name if a.department else None
    return schemas.AssetOut(
        id=a.id,
        name=a.name,
        asset_tag=a.asset_tag,
        serial_number=a.serial_number,
        qr_code=a.qr_code,
        category_id=a.category_id,
        category_name=a.category.name,
        status=a.status,
        condition=a.condition,
        location=a.location,
        acquisition_cost=a.acquisition_cost,
        acquisition_date=a.acquisition_date,
        is_shared=a.is_shared,
        current_holder_id=a.current_holder_id,
        current_holder_name=holder_name,
        department_id=a.department_id,
        department_name=dept_name
    )
