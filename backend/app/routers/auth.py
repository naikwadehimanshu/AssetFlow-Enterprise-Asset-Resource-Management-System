from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional

from ..database import get_db
from ..dependencies import verify_password, create_access_token, get_current_user
from .. import schemas, crud, models

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/signup", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def signup(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user_in.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    return crud.create_user(db=db, user_in=user_in)

@router.post("/login", response_model=schemas.Token)
def login(
    login_data: Optional[schemas.UserLogin] = None,
    form_data: Optional[OAuth2PasswordRequestForm] = Depends(None),
    db: Session = Depends(get_db)
):
    # Support both JSON payload login and OAuth2 Form data login
    email = None
    password = None

    if form_data:
        email = form_data.username
        password = form_data.password
    elif login_data:
        email = login_data.email
        password = login_data.password
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login credentials must be provided either as JSON or form data."
        )

    user = crud.get_user_by_email(db, email=email)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if user.status != "Active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive. Please contact the administrator."
        )

    # Generate token
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "user_id": user.id}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.UserOut)
def get_current_user_profile(current_user: models.User = Depends(get_current_user)):
    # Prepare UserOut including department name
    dept_name = current_user.department.name if current_user.department else None
    
    out = schemas.UserOut(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        status=current_user.status,
        department_id=current_user.department_id,
        department_name=dept_name
    )
    return out
