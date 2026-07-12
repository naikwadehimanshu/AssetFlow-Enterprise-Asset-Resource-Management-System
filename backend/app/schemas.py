from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Any, Dict
from datetime import date, datetime

# --- Token & Authentication ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
    user_id: Optional[int] = None


# --- Department Schemas ---
class DepartmentBase(BaseModel):
    name: str
    parent_department_id: Optional[int] = None
    status: Optional[str] = "Active"

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    head_id: Optional[int] = None
    parent_department_id: Optional[int] = None
    status: Optional[str] = None

class DepartmentOut(DepartmentBase):
    id: int
    head_id: Optional[int] = None
    head_name: Optional[str] = None

    class Config:
        from_attributes = True
        orm_mode = True


# --- User & Employee Directory ---
class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: Optional[str] = "employee"
    status: Optional[str] = "Active"
    department_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    department_id: Optional[int] = None

class UserPromote(BaseModel):
    role: str  # admin, asset_manager, department_head, employee
    department_id: Optional[int] = None
    status: Optional[str] = None

class UserOut(UserBase):
    id: int
    department_name: Optional[str] = None

    class Config:
        from_attributes = True
        orm_mode = True


# --- Category Schemas ---
class CategoryBase(BaseModel):
    name: str
    category_specific_fields: Optional[List[Dict[str, Any]]] = None  # e.g., [{"name": "warranty_months", "type": "int", "required": false}]

class CategoryCreate(CategoryBase):
    pass

class CategoryOut(CategoryBase):
    id: int

    class Config:
        from_attributes = True
        orm_mode = True


# --- Asset Schemas ---
class AssetBase(BaseModel):
    name: str
    serial_number: str
    category_id: int
    condition: Optional[str] = "Good"
    location: str
    acquisition_cost: Optional[float] = 0.0
    acquisition_date: date
    is_shared: Optional[bool] = False

class AssetCreate(AssetBase):
    pass

class AssetUpdate(BaseModel):
    name: Optional[str] = None
    serial_number: Optional[str] = None
    condition: Optional[str] = None
    location: Optional[str] = None
    acquisition_cost: Optional[float] = None
    acquisition_date: Optional[date] = None
    is_shared: Optional[bool] = None
    status: Optional[str] = None
    department_id: Optional[int] = None
    current_holder_id: Optional[int] = None

class AssetOut(AssetBase):
    id: int
    asset_tag: str
    qr_code: str
    status: str
    current_holder_id: Optional[int] = None
    current_holder_name: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    category_name: Optional[str] = None

    class Config:
        from_attributes = True
        orm_mode = True


# --- Allocation & Transfer Schemas ---
class AssetAllocate(BaseModel):
    employee_id: Optional[int] = None
    department_id: Optional[int] = None
    expected_return_date: Optional[date] = None

class AssetReturn(BaseModel):
    return_condition: str
    check_in_notes: Optional[str] = None

class TransferRequestCreate(BaseModel):
    to_employee_id: int
    reason: str

class TransferRequestOut(BaseModel):
    id: int
    asset_id: int
    asset_tag: str
    asset_name: str
    from_employee_id: int
    from_employee_name: str
    to_employee_id: int
    to_employee_name: str
    reason: str
    status: str
    approved_by_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True


# --- Booking Schemas ---
class BookingCreate(BaseModel):
    asset_id: int
    start_time: datetime
    end_time: datetime

class BookingOut(BaseModel):
    id: int
    asset_id: int
    asset_name: str
    asset_tag: str
    booked_by_id: int
    booked_by_name: str
    start_time: datetime
    end_time: datetime
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True


# --- Maintenance Schemas ---
class MaintenanceCreate(BaseModel):
    asset_id: int
    description: str
    priority: Optional[str] = "Medium"  # Low, Medium, High, Critical
    photo_url: Optional[str] = None

class MaintenanceStatusUpdate(BaseModel):
    status: str  # Pending, Approved, Rejected, Technician Assigned, In Progress, Resolved
    technician_name: Optional[str] = None
    resolution_notes: Optional[str] = None

class MaintenanceOut(BaseModel):
    id: int
    asset_id: int
    asset_tag: str
    asset_name: str
    reporter_id: int
    reporter_name: str
    description: str
    priority: str
    status: str
    technician_name: Optional[str] = None
    resolution_notes: Optional[str] = None
    photo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True


# --- Audit Schemas ---
class AuditCycleCreate(BaseModel):
    name: str
    start_date: date
    end_date: date
    scope_type: str  # department, location, overall
    scope_value: Optional[str] = None  # Specific department name or location name
    auditor_ids: List[int]

class AuditCycleOut(BaseModel):
    id: int
    name: str
    start_date: date
    end_date: date
    scope_type: str
    scope_value: Optional[str] = None
    status: str
    auditor_names: List[str] = []

    class Config:
        from_attributes = True
        orm_mode = True

class AuditRecordOut(BaseModel):
    id: int
    audit_cycle_id: int
    asset_id: int
    asset_tag: str
    asset_name: str
    asset_location: str
    expected_holder_name: Optional[str] = None
    verification_status: str
    notes: Optional[str] = None
    auditor_id: Optional[int] = None
    auditor_name: Optional[str] = None
    audited_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        orm_mode = True

class AuditRecordUpdate(BaseModel):
    verification_status: str  # Verified, Missing, Damaged
    notes: Optional[str] = None


# --- Notification & Logs ---
class NotificationOut(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True

class ActivityLogOut(BaseModel):
    id: int
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
    action: str
    details: str
    created_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True


# --- Dashboard KPI Schemas ---
class OverdueAssetOut(BaseModel):
    asset_tag: str
    asset_name: str
    holder_name: str
    expected_return_date: date
    overdue_days: int

class DashboardKPI(BaseModel):
    assets_available: int
    assets_allocated: int
    maintenance_today: int
    active_bookings: int
    pending_transfers: int
    upcoming_returns: int
    overdue_returns_count: int
    overdue_returns: List[OverdueAssetOut] = []
