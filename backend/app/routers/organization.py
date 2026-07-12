from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..dependencies import require_admin, require_any_role, get_current_user
from .. import schemas, crud, models

router = APIRouter(prefix="/api/org", tags=["Organization Setup"])

# --- Department Endpoints ---
@router.get("/departments", response_model=List[schemas.DepartmentOut])
def list_departments(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any_role)
):
    departments = crud.get_departments(db)
    result = []
    for d in departments:
        head_name = d.head.name if d.head else None
        result.append(
            schemas.DepartmentOut(
                id=d.id,
                name=d.name,
                head_id=d.head_id,
                head_name=head_name,
                parent_department_id=d.parent_department_id,
                status=d.status
            )
        )
    return result

@router.post("/departments", response_model=schemas.DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_new_department(
    dept_in: schemas.DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    dept = crud.create_department(db, dept_in, actor_id=current_user.id)
    return schemas.DepartmentOut(
        id=dept.id,
        name=dept.name,
        head_id=dept.head_id,
        head_name=None,
        parent_department_id=dept.parent_department_id,
        status=dept.status
    )

@router.put("/departments/{id}", response_model=schemas.DepartmentOut)
def update_department_details(
    id: int,
    dept_in: schemas.DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    dept = crud.update_department(db, id, dept_in, actor_id=current_user.id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
        
    head_name = dept.head.name if dept.head else None
    return schemas.DepartmentOut(
        id=dept.id,
        name=dept.name,
        head_id=dept.head_id,
        head_name=head_name,
        parent_department_id=dept.parent_department_id,
        status=dept.status
    )


# --- Category Endpoints ---
@router.get("/categories", response_model=List[schemas.CategoryOut])
def list_categories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any_role)
):
    return crud.get_categories(db)

@router.post("/categories", response_model=schemas.CategoryOut, status_code=status.HTTP_201_CREATED)
def create_new_category(
    cat_in: schemas.CategoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    return crud.create_category(db, cat_in, actor_id=current_user.id)


# --- Employee Endpoints (Tab C) ---
@router.get("/employees", response_model=List[schemas.UserOut])
def list_employees(
    department_id: Optional[int] = None,
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any_role)
):
    users = crud.get_users(db, role=role, dept_id=department_id)
    result = []
    for u in users:
        dept_name = u.department.name if u.department else None
        result.append(
            schemas.UserOut(
                id=u.id,
                name=u.name,
                email=u.email,
                role=u.role,
                status=u.status,
                department_id=u.department_id,
                department_name=dept_name
            )
        )
    return result

@router.put("/employees/{id}/role", response_model=schemas.UserOut)
def promote_employee_role(
    id: int,
    promote_in: schemas.UserPromote,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    updated_user = crud.promote_user_role(db, admin_id=current_user.id, target_user_id=id, promote_in=promote_in)
    if not updated_user:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    dept_name = updated_user.department.name if updated_user.department else None
    return schemas.UserOut(
        id=updated_user.id,
        name=updated_user.name,
        email=updated_user.email,
        role=updated_user.role,
        status=updated_user.status,
        department_id=updated_user.department_id,
        department_name=dept_name
    )
