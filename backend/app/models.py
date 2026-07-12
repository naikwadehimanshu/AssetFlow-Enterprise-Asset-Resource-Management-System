from sqlalchemy import Column, Integer, String, Boolean, Float, Date, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="employee")  # admin, asset_manager, department_head, employee
    status = Column(String, default="Active")   # Active, Inactive
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    department = relationship("Department", foreign_keys=[department_id], back_populates="members")
    headed_departments = relationship("Department", foreign_keys="Department.head_id", back_populates="head")
    allocations = relationship("Asset", foreign_keys="Asset.current_holder_id", back_populates="current_holder")
    allocation_history = relationship("AllocationHistory", back_populates="employee")
    sent_transfers = relationship("TransferRequest", foreign_keys="TransferRequest.from_employee_id", back_populates="from_employee")
    received_transfers = relationship("TransferRequest", foreign_keys="TransferRequest.to_employee_id", back_populates="to_employee")
    approved_transfers = relationship("TransferRequest", foreign_keys="TransferRequest.approved_by_id", back_populates="approved_by")
    bookings = relationship("Booking", back_populates="booked_by")
    reported_maintenance = relationship("MaintenanceRequest", back_populates="reporter")
    audit_assignments = relationship("AuditAssignment", back_populates="auditor")
    audits_logged = relationship("AuditRecord", back_populates="auditor")
    notifications = relationship("Notification", back_populates="user")
    activities = relationship("ActivityLog", back_populates="actor")


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    head_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    parent_department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    status = Column(String, default="Active")   # Active, Inactive

    # Relationships
    head = relationship("User", foreign_keys=[head_id], back_populates="headed_departments")
    members = relationship("User", foreign_keys=[User.department_id], back_populates="department")
    parent_department = relationship("Department", remote_side=[id], backref="sub_departments")
    assets = relationship("Asset", back_populates="department")
    allocation_history = relationship("AllocationHistory", back_populates="department")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    category_specific_fields = Column(JSON, nullable=True)  # List of dicts representing custom fields, e.g. [{"name": "warranty_period", "type": "int"}]

    # Relationships
    assets = relationship("Asset", back_populates="category")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    asset_tag = Column(String, unique=True, index=True, nullable=False)  # e.g. AF-0001
    serial_number = Column(String, unique=True, index=True, nullable=False)
    qr_code = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String, default="Available")  # Available, Allocated, Reserved, Under Maintenance, Lost, Retired, Disposed
    condition = Column(String, default="Good")    # New, Good, Fair, Damaged, Broken
    location = Column(String, nullable=False)     # Bengaluru, HQ Floor 2, Warehouse, etc.
    acquisition_cost = Column(Float, default=0.0)
    acquisition_date = Column(Date, nullable=False)
    is_shared = Column(Boolean, default=False)
    current_holder_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    category = relationship("Category", back_populates="assets")
    current_holder = relationship("User", foreign_keys=[current_holder_id], back_populates="allocations")
    department = relationship("Department", back_populates="assets")
    allocation_history = relationship("AllocationHistory", back_populates="asset", cascade="all, delete-orphan")
    transfer_requests = relationship("TransferRequest", back_populates="asset", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="resource", cascade="all, delete-orphan")
    maintenance_requests = relationship("MaintenanceRequest", back_populates="asset", cascade="all, delete-orphan")
    audit_records = relationship("AuditRecord", back_populates="asset", cascade="all, delete-orphan")


class AllocationHistory(Base):
    __tablename__ = "allocation_history"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    allocated_at = Column(Date, default=datetime.utcnow, nullable=False)
    expected_return_date = Column(Date, nullable=True)
    returned_at = Column(Date, nullable=True)
    return_condition = Column(String, nullable=True)
    check_in_notes = Column(String, nullable=True)

    # Relationships
    asset = relationship("Asset", back_populates="allocation_history")
    employee = relationship("User", back_populates="allocation_history")
    department = relationship("Department", back_populates="allocation_history")


class TransferRequest(Base):
    __tablename__ = "transfer_requests"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    from_employee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    to_employee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reason = Column(String, nullable=False)
    status = Column(String, default="Pending")  # Pending, Approved, Rejected
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    asset = relationship("Asset", back_populates="transfer_requests")
    from_employee = relationship("User", foreign_keys=[from_employee_id], back_populates="sent_transfers")
    to_employee = relationship("User", foreign_keys=[to_employee_id], back_populates="received_transfers")
    approved_by = relationship("User", foreign_keys=[approved_by_id], back_populates="approved_transfers")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    booked_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String, default="Upcoming")  # Upcoming, Ongoing, Completed, Cancelled
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    resource = relationship("Asset", back_populates="bookings")
    booked_by = relationship("User", back_populates="bookings")


class MaintenanceRequest(Base):
    __tablename__ = "maintenance_requests"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    description = Column(String, nullable=False)
    priority = Column(String, default="Medium")  # Low, Medium, High, Critical
    status = Column(String, default="Pending")  # Pending, Approved, Rejected, Technician Assigned, In Progress, Resolved
    technician_name = Column(String, nullable=True)
    resolution_notes = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    asset = relationship("Asset", back_populates="maintenance_requests")
    reporter = relationship("User", back_populates="reported_maintenance")


class AuditCycle(Base):
    __tablename__ = "audit_cycles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    scope_type = Column(String, nullable=False)  # department, location, overall
    scope_value = Column(String, nullable=True)  # department name or location name
    status = Column(String, default="Active")    # Active, Closed

    # Relationships
    assignments = relationship("AuditAssignment", back_populates="audit_cycle", cascade="all, delete-orphan")
    records = relationship("AuditRecord", back_populates="audit_cycle", cascade="all, delete-orphan")


class AuditAssignment(Base):
    __tablename__ = "audit_assignments"

    id = Column(Integer, primary_key=True, index=True)
    audit_cycle_id = Column(Integer, ForeignKey("audit_cycles.id", ondelete="CASCADE"), nullable=False)
    auditor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    audit_cycle = relationship("AuditCycle", back_populates="assignments")
    auditor = relationship("User", back_populates="audit_assignments")


class AuditRecord(Base):
    __tablename__ = "audit_records"

    id = Column(Integer, primary_key=True, index=True)
    audit_cycle_id = Column(Integer, ForeignKey("audit_cycles.id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    auditor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verification_status = Column(String, default="Pending")  # Pending, Verified, Missing, Damaged
    notes = Column(String, nullable=True)
    audited_at = Column(DateTime, nullable=True)

    # Relationships
    audit_cycle = relationship("AuditCycle", back_populates="records")
    asset = relationship("Asset", back_populates="audit_records")
    auditor = relationship("User", back_populates="audits_logged")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)  # Asset Assigned, Maintenance Update, Booking Confirmation, Transfer Request, Overdue Return, Audit Discrepancy
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="notifications")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String, nullable=False)  # e.g., CREATE_ASSET, ALLOCATE_ASSET, APPROVE_MAINTENANCE
    details = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    actor = relationship("User", back_populates="activities")
