from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from datetime import datetime, date
import uuid

from . import models, schemas, dependencies

# --- Helper: Activity Logging & Notifications ---
def create_activity_log(db: Session, actor_id: int, action: str, details: str) -> models.ActivityLog:
    db_log = models.ActivityLog(actor_id=actor_id, action=action, details=details)
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

def create_notification(db: Session, user_id: int, type_: str, title: str, message: str) -> models.Notification:
    db_notif = models.Notification(user_id=user_id, type=type_, title=title, message=message)
    db.add(db_notif)
    db.commit()
    db.refresh(db_notif)
    return db_notif


# --- User CRUD ---
def get_user_by_email(db: Session, email: str) -> models.User:
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_id(db: Session, user_id: int) -> models.User:
    return db.query(models.User).filter(models.User.id == user_id).first()

def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    hashed_pw = dependencies.get_password_hash(user_in.password)
    db_user = models.User(
        name=user_in.name,
        email=user_in.email,
        hashed_password=hashed_pw,
        role=user_in.role or "employee",
        status=user_in.status or "Active",
        department_id=user_in.department_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Log activity
    create_activity_log(db, db_user.id, "USER_SIGNUP", f"User {db_user.email} signed up as employee.")
    return db_user

def get_users(db: Session, skip: int = 0, limit: int = 100, role: str = None, dept_id: int = None) -> list[models.User]:
    query = db.query(models.User)
    if role:
        query = query.filter(models.User.role == role)
    if dept_id:
        query = query.filter(models.User.department_id == dept_id)
    return query.offset(skip).limit(limit).all()

def promote_user_role(db: Session, admin_id: int, target_user_id: int, promote_in: schemas.UserPromote) -> models.User:
    db_user = get_user_by_id(db, target_user_id)
    if not db_user:
        return None
        
    old_role = db_user.role
    old_dept_id = db_user.department_id
    old_status = db_user.status
    
    db_user.role = promote_in.role
    if promote_in.department_id is not None:
        db_user.department_id = promote_in.department_id
    if promote_in.status is not None:
        db_user.status = promote_in.status
        
    db.commit()
    db.refresh(db_user)
    
    # If they are promoted to head of department, update that department's head_id automatically
    if promote_in.role == "department_head" and db_user.department_id:
        dept = db.query(models.Department).filter(models.Department.id == db_user.department_id).first()
        if dept:
            dept.head_id = db_user.id
            db.commit()
            
    create_activity_log(
        db, admin_id, "USER_PROMOTE", 
        f"Promoted {db_user.email} from {old_role} (Dept: {old_dept_id}) to {db_user.role} (Dept: {db_user.department_id}). Status: {db_user.status}"
    )
    create_notification(
        db, db_user.id, "Role Update", "Role Promotion / Status Update",
        f"Your account role was updated to {db_user.role} and your department was set to {db_user.department_id}."
    )
    return db_user


# --- Department CRUD ---
def get_departments(db: Session) -> list[models.Department]:
    return db.query(models.Department).all()

def create_department(db: Session, dept_in: schemas.DepartmentCreate, actor_id: int) -> models.Department:
    db_dept = models.Department(
        name=dept_in.name,
        parent_department_id=dept_in.parent_department_id,
        status=dept_in.status or "Active"
    )
    db.add(db_dept)
    db.commit()
    db.refresh(db_dept)
    create_activity_log(db, actor_id, "CREATE_DEPARTMENT", f"Created department {db_dept.name}")
    return db_dept

def update_department(db: Session, dept_id: int, dept_in: schemas.DepartmentUpdate, actor_id: int) -> models.Department:
    db_dept = db.query(models.Department).filter(models.Department.id == dept_id).first()
    if not db_dept:
        return None
    
    if dept_in.name is not None:
        db_dept.name = dept_in.name
    if dept_in.head_id is not None:
        db_dept.head_id = dept_in.head_id
    if dept_in.parent_department_id is not None:
        # Prevent self-referencing hierarchy
        if dept_in.parent_department_id != dept_id:
            db_dept.parent_department_id = dept_in.parent_department_id
    if dept_in.status is not None:
        db_dept.status = dept_in.status
        
    db.commit()
    db.refresh(db_dept)
    create_activity_log(db, actor_id, "UPDATE_DEPARTMENT", f"Updated department {db_dept.name}")
    return db_dept


# --- Category CRUD ---
def get_categories(db: Session) -> list[models.Category]:
    return db.query(models.Category).all()

def create_category(db: Session, cat_in: schemas.CategoryCreate, actor_id: int) -> models.Category:
    db_cat = models.Category(
        name=cat_in.name,
        category_specific_fields=cat_in.category_specific_fields
    )
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    create_activity_log(db, actor_id, "CREATE_CATEGORY", f"Created asset category {db_cat.name}")
    return db_cat


# --- Asset CRUD ---
def generate_asset_tag(db: Session) -> str:
    # Query asset tags to find the highest number
    tags = db.query(models.Asset.asset_tag).filter(models.Asset.asset_tag.like("AF-%")).all()
    max_num = 0
    for tag_tuple in tags:
        tag_str = tag_tuple[0]
        try:
            num = int(tag_str.split("-")[1])
            if num > max_num:
                max_num = num
        except (IndexError, ValueError):
            continue
    next_num = max_num + 1
    return f"AF-{next_num:04d}"

def get_assets(db: Session, search: str = None, category_id: int = None, status: str = None, department_id: int = None, location: str = None) -> list[models.Asset]:
    query = db.query(models.Asset)
    if search:
        query = query.filter(
            or_(
                models.Asset.name.icontains(search),
                models.Asset.asset_tag.icontains(search),
                models.Asset.serial_number.icontains(search)
            )
        )
    if category_id:
        query = query.filter(models.Asset.category_id == category_id)
    if status:
        query = query.filter(models.Asset.status == status)
    if department_id:
        query = query.filter(models.Asset.department_id == department_id)
    if location:
        query = query.filter(models.Asset.location.icontains(location))
    return query.all()

def get_asset_by_id(db: Session, asset_id: int) -> models.Asset:
    return db.query(models.Asset).filter(models.Asset.id == asset_id).first()

def get_asset_by_tag(db: Session, asset_tag: str) -> models.Asset:
    return db.query(models.Asset).filter(models.Asset.asset_tag == asset_tag).first()

def create_asset(db: Session, asset_in: schemas.AssetCreate, actor_id: int) -> models.Asset:
    tag = generate_asset_tag(db)
    qr = f"ASSETFLOW:{tag}:{uuid.uuid4().hex[:8]}"
    db_asset = models.Asset(
        name=asset_in.name,
        asset_tag=tag,
        serial_number=asset_in.serial_number,
        qr_code=qr,
        category_id=asset_in.category_id,
        status="Available",
        condition=asset_in.condition or "Good",
        location=asset_in.location,
        acquisition_cost=asset_in.acquisition_cost or 0.0,
        acquisition_date=asset_in.acquisition_date,
        is_shared=asset_in.is_shared or False
    )
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    create_activity_log(db, actor_id, "CREATE_ASSET", f"Registered asset {db_asset.asset_tag} ({db_asset.name})")
    return db_asset

def update_asset(db: Session, asset_id: int, asset_in: schemas.AssetUpdate, actor_id: int) -> models.Asset:
    db_asset = get_asset_by_id(db, asset_id)
    if not db_asset:
        return None
        
    for field, val in asset_in.dict(exclude_unset=True).items():
        setattr(db_asset, field, val)
        
    db.commit()
    db.refresh(db_asset)
    create_activity_log(db, actor_id, "UPDATE_ASSET", f"Updated asset details for {db_asset.asset_tag}")
    return db_asset


# --- Allocation & Transfer CRUD ---
def allocate_asset(db: Session, asset_id: int, alloc_in: schemas.AssetAllocate, actor_id: int) -> models.Asset:
    db_asset = get_asset_by_id(db, asset_id)
    if not db_asset:
        return None
        
    # Set the holder and department
    db_asset.current_holder_id = alloc_in.employee_id
    db_asset.department_id = alloc_in.department_id
    db_asset.status = "Allocated"
    
    # Create allocation history entry
    history = models.AllocationHistory(
        asset_id=asset_id,
        employee_id=alloc_in.employee_id,
        department_id=alloc_in.department_id,
        allocated_at=date.today(),
        expected_return_date=alloc_in.expected_return_date
    )
    db.add(history)
    db.commit()
    db.refresh(db_asset)
    
    # Activity Log
    holder_str = f"User ID {alloc_in.employee_id}" if alloc_in.employee_id else f"Department ID {alloc_in.department_id}"
    create_activity_log(db, actor_id, "ALLOCATE_ASSET", f"Allocated asset {db_asset.asset_tag} to {holder_str}")
    
    # Notify target if user
    if alloc_in.employee_id:
        create_notification(
            db, alloc_in.employee_id, "Asset Assigned", "New Asset Allocated",
            f"Asset {db_asset.name} ({db_asset.asset_tag}) has been allocated to you. Expected return date: {alloc_in.expected_return_date or 'N/A'}"
        )
    return db_asset

def return_asset(db: Session, asset_id: int, return_in: schemas.AssetReturn, actor_id: int) -> models.Asset:
    db_asset = get_asset_by_id(db, asset_id)
    if not db_asset:
        return None
        
    old_holder_id = db_asset.current_holder_id
    
    # Update active history record
    history = db.query(models.AllocationHistory).filter(
        and_(
            models.AllocationHistory.asset_id == asset_id,
            models.AllocationHistory.returned_at == None
        )
    ).order_by(models.AllocationHistory.allocated_at.desc()).first()
    
    if history:
        history.returned_at = date.today()
        history.return_condition = return_in.return_condition
        history.check_in_notes = return_in.check_in_notes
    
    # Reset asset status
    db_asset.current_holder_id = None
    db_asset.status = "Available"
    db_asset.condition = return_in.return_condition
    
    db.commit()
    db.refresh(db_asset)
    
    create_activity_log(db, actor_id, "RETURN_ASSET", f"Asset {db_asset.asset_tag} returned by user ID {old_holder_id or 'N/A'}. Condition: {return_in.return_condition}")
    
    if old_holder_id:
        create_notification(
            db, old_holder_id, "Asset Returned", "Asset Return Confirmed",
            f"Your return of asset {db_asset.name} ({db_asset.asset_tag}) has been processed. Status: Available."
        )
    return db_asset

def create_transfer_request(db: Session, asset_id: int, requester_id: int, request_in: schemas.TransferRequestCreate) -> models.TransferRequest:
    # Fetch who currently holds it
    db_asset = get_asset_by_id(db, asset_id)
    if not db_asset or not db_asset.current_holder_id:
        return None
        
    db_request = models.TransferRequest(
        asset_id=asset_id,
        from_employee_id=db_asset.current_holder_id,
        to_employee_id=request_in.to_employee_id,
        reason=request_in.reason,
        status="Pending"
    )
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    
    create_activity_log(
        db, requester_id, "TRANSFER_REQUEST", 
        f"Requested transfer of {db_asset.asset_tag} from User {db_asset.current_holder_id} to User {request_in.to_employee_id}"
    )
    
    # Notify current holder and managers/department head
    create_notification(
        db, db_asset.current_holder_id, "Transfer Request", "Asset Transfer Initiated",
        f"A request has been made to transfer your allocated asset {db_asset.name} ({db_asset.asset_tag}) to another employee. Reason: {request_in.reason}"
    )
    return db_request

def get_transfer_requests(db: Session) -> list[models.TransferRequest]:
    return db.query(models.TransferRequest).all()

def approve_transfer_request(db: Session, request_id: int, approver_id: int) -> models.TransferRequest:
    req = db.query(models.TransferRequest).filter(models.TransferRequest.id == request_id).first()
    if not req or req.status != "Pending":
        return None
        
    # Update request
    req.status = "Approved"
    req.approved_by_id = approver_id
    
    # Perform the re-allocation
    db_asset = get_asset_by_id(db, req.asset_id)
    
    # 1. Close current allocation history entry
    hist = db.query(models.AllocationHistory).filter(
        and_(
            models.AllocationHistory.asset_id == req.asset_id,
            models.AllocationHistory.returned_at == None
        )
    ).first()
    if hist:
        hist.returned_at = date.today()
        hist.return_condition = db_asset.condition
        hist.check_in_notes = f"Transferred to User ID {req.to_employee_id} via Transfer Request #{req.id}"
        
    # 2. Update asset holder
    to_user = get_user_by_id(db, req.to_employee_id)
    db_asset.current_holder_id = req.to_employee_id
    db_asset.department_id = to_user.department_id if to_user else None
    db_asset.status = "Allocated"
    
    # 3. Create new allocation history
    new_hist = models.AllocationHistory(
        asset_id=req.asset_id,
        employee_id=req.to_employee_id,
        department_id=to_user.department_id if to_user else None,
        allocated_at=date.today()
    )
    db.add(new_hist)
    db.commit()
    db.refresh(req)
    
    create_activity_log(
        db, approver_id, "APPROVE_TRANSFER", 
        f"Approved transfer request #{req.id} for {db_asset.asset_tag} to User ID {req.to_employee_id}"
    )
    
    # Notify old holder, new holder, and requester
    create_notification(
        db, req.from_employee_id, "Transfer Approved", "Asset Transferred",
        f"Asset {db_asset.name} ({db_asset.asset_tag}) has been successfully transferred to another employee."
    )
    create_notification(
        db, req.to_employee_id, "Asset Assigned", "Asset Received via Transfer",
        f"Asset {db_asset.name} ({db_asset.asset_tag}) has been transferred to you."
    )
    
    return req

def reject_transfer_request(db: Session, request_id: int, rejecter_id: int) -> models.TransferRequest:
    req = db.query(models.TransferRequest).filter(models.TransferRequest.id == request_id).first()
    if not req or req.status != "Pending":
        return None
        
    req.status = "Rejected"
    req.approved_by_id = rejecter_id
    db.commit()
    db.refresh(req)
    
    create_activity_log(db, rejecter_id, "REJECT_TRANSFER", f"Rejected transfer request #{req.id}")
    
    create_notification(
        db, req.to_employee_id, "Transfer Rejected", "Transfer Request Denied",
        f"Your request to receive asset ID {req.asset_id} was rejected by management."
    )
    return req

def get_overdue_allocations(db: Session) -> list[dict]:
    today = date.today()
    overdue = db.query(models.AllocationHistory).filter(
        and_(
            models.AllocationHistory.returned_at == None,
            models.AllocationHistory.expected_return_date < today
        )
    ).all()
    
    results = []
    for o in overdue:
        holder_name = o.employee.name if o.employee else (o.department.name if o.department else "Unknown")
        delta = today - o.expected_return_date
        results.append({
            "asset_tag": o.asset.asset_tag,
            "asset_name": o.asset.name,
            "holder_name": holder_name,
            "expected_return_date": o.expected_return_date,
            "overdue_days": delta.days
        })
    return results


# --- Resource Booking CRUD ---
def check_booking_overlap(db: Session, asset_id: int, start: datetime, end: datetime) -> bool:
    # Overlap conditions: Start_existing < End_new AND End_existing > Start_new AND status != Cancelled
    overlap = db.query(models.Booking).filter(
        and_(
            models.Booking.asset_id == asset_id,
            models.Booking.status.in_(["Upcoming", "Ongoing"]),
            models.Booking.start_time < end,
            models.Booking.end_time > start
        )
    ).first()
    return overlap is not None

def create_booking(db: Session, book_in: schemas.BookingCreate, actor_id: int) -> models.Booking:
    db_booking = models.Booking(
        asset_id=book_in.asset_id,
        booked_by_id=actor_id,
        start_time=book_in.start_time,
        end_time=book_in.end_time,
        status="Upcoming"
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    
    asset = get_asset_by_id(db, book_in.asset_id)
    create_activity_log(db, actor_id, "CREATE_BOOKING", f"Booked shared resource {asset.asset_tag} from {book_in.start_time} to {book_in.end_time}")
    create_notification(
        db, actor_id, "Booking Confirmation", "Resource Booked Successfully",
        f"Your booking for {asset.name} ({asset.asset_tag}) on {book_in.start_time.strftime('%Y-%m-%d %H:%M')} is confirmed."
    )
    return db_booking

def get_bookings(db: Session, asset_id: int = None, start: datetime = None, end: datetime = None) -> list[models.Booking]:
    query = db.query(models.Booking)
    if asset_id:
        query = query.filter(models.Booking.asset_id == asset_id)
    if start:
        query = query.filter(models.Booking.end_time >= start)
    if end:
        query = query.filter(models.Booking.start_time <= end)
    return query.all()

def cancel_booking(db: Session, booking_id: int, actor_id: int) -> models.Booking:
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        return None
    booking.status = "Cancelled"
    db.commit()
    db.refresh(booking)
    
    create_activity_log(db, actor_id, "CANCEL_BOOKING", f"Cancelled booking #{booking.id}")
    create_notification(
        db, booking.booked_by_id, "Booking Cancelled", "Resource Booking Cancelled",
        f"Your booking for resource ID {booking.asset_id} has been cancelled."
    )
    return booking


# --- Maintenance CRUD ---
def create_maintenance_request(db: Session, maint_in: schemas.MaintenanceCreate, reporter_id: int) -> models.MaintenanceRequest:
    db_maint = models.MaintenanceRequest(
        asset_id=maint_in.asset_id,
        reporter_id=reporter_id,
        description=maint_in.description,
        priority=maint_in.priority or "Medium",
        photo_url=maint_in.photo_url,
        status="Pending"
    )
    db.add(db_maint)
    db.commit()
    db.refresh(db_maint)
    
    asset = get_asset_by_id(db, maint_in.asset_id)
    create_activity_log(db, reporter_id, "RAISE_MAINTENANCE", f"Raised maintenance request #{db_maint.id} for {asset.asset_tag}")
    return db_maint

def get_maintenance_requests(db: Session) -> list[models.MaintenanceRequest]:
    return db.query(models.MaintenanceRequest).all()

def update_maintenance_status(db: Session, maint_id: int, maint_in: schemas.MaintenanceStatusUpdate, actor_id: int) -> models.MaintenanceRequest:
    db_maint = db.query(models.MaintenanceRequest).filter(models.MaintenanceRequest.id == maint_id).first()
    if not db_maint:
        return None
        
    old_status = db_maint.status
    db_maint.status = maint_in.status
    if maint_in.technician_name is not None:
        db_maint.technician_name = maint_in.technician_name
    if maint_in.resolution_notes is not None:
        db_maint.resolution_notes = maint_in.resolution_notes
        
    db_asset = get_asset_by_id(db, db_maint.asset_id)
    
    # State transition effects:
    # 1. On Approval, move asset to 'Under Maintenance'
    if old_status == "Pending" and maint_in.status == "Approved":
        db_asset.status = "Under Maintenance"
    # 2. On Resolution, move asset back to 'Available'
    elif maint_in.status == "Resolved":
        db_asset.status = "Available"
        db_asset.condition = "Good" # Reverts to good upon fix
        
    db.commit()
    db.refresh(db_maint)
    
    create_activity_log(
        db, actor_id, "UPDATE_MAINTENANCE", 
        f"Updated maintenance request #{db_maint.id} status from {old_status} to {db_maint.status}"
    )
    create_notification(
        db, db_maint.reporter_id, "Maintenance Update", f"Maintenance Request #{db_maint.id} {db_maint.status}",
        f"Your maintenance request for asset {db_asset.name} has been updated to: {db_maint.status}."
    )
    return db_maint


# --- Audit CRUD ---
def create_audit_cycle(db: Session, audit_in: schemas.AuditCycleCreate, actor_id: int) -> models.AuditCycle:
    # Create cycle
    db_cycle = models.AuditCycle(
        name=audit_in.name,
        start_date=audit_in.start_date,
        end_date=audit_in.end_date,
        scope_type=audit_in.scope_type,
        scope_value=audit_in.scope_value,
        status="Active"
    )
    db.add(db_cycle)
    db.commit()
    db.refresh(db_cycle)
    
    # Add auditor assignments
    for a_id in audit_in.auditor_ids:
        assignment = models.AuditAssignment(
            audit_cycle_id=db_cycle.id,
            auditor_id=a_id
        )
        db.add(assignment)
        
    # Automatically query and populate Audit Records for all assets in scope
    query = db.query(models.Asset)
    if audit_in.scope_type == "department":
        dept = db.query(models.Department).filter(models.Department.name == audit_in.scope_value).first()
        if dept:
            query = query.filter(models.Asset.department_id == dept.id)
    elif audit_in.scope_type == "location":
        query = query.filter(models.Asset.location.icontains(audit_in.scope_value))
        
    assets = query.all()
    for asset in assets:
        record = models.AuditRecord(
            audit_cycle_id=db_cycle.id,
            asset_id=asset.id,
            verification_status="Pending"
        )
        db.add(record)
        
    db.commit()
    
    create_activity_log(db, actor_id, "CREATE_AUDIT_CYCLE", f"Created audit cycle '{db_cycle.name}', assigned {len(assets)} assets for verification.")
    
    # Notify auditors
    for a_id in audit_in.auditor_ids:
        create_notification(
            db, a_id, "Audit Assignment", "New Audit Cycle Assigned",
            f"You have been assigned as an auditor for cycle '{db_cycle.name}'. Date range: {db_cycle.start_date} to {db_cycle.end_date}."
        )
        
    return db_cycle

def get_audit_cycles(db: Session) -> list[models.AuditCycle]:
    return db.query(models.AuditCycle).all()

def get_audit_records(db: Session, cycle_id: int) -> list[models.AuditRecord]:
    return db.query(models.AuditRecord).filter(models.AuditRecord.audit_cycle_id == cycle_id).all()

def update_audit_record(db: Session, record_id: int, update_in: schemas.AuditRecordUpdate, auditor_id: int) -> models.AuditRecord:
    rec = db.query(models.AuditRecord).filter(models.AuditRecord.id == record_id).first()
    if not rec:
        return None
        
    rec.verification_status = update_in.verification_status
    rec.notes = update_in.notes
    rec.auditor_id = auditor_id
    rec.audited_at = datetime.utcnow()
    db.commit()
    db.refresh(rec)
    
    # If damaged or missing, create immediate activity log warning
    if update_in.verification_status in ["Missing", "Damaged"]:
        create_activity_log(
            db, auditor_id, "AUDIT_DISCREPANCY", 
            f"Audit Alert: Asset {rec.asset.asset_tag} was marked as '{update_in.verification_status}' during Audit Cycle #{rec.audit_cycle_id}."
        )
    return rec

def close_audit_cycle(db: Session, cycle_id: int, actor_id: int) -> models.AuditCycle:
    cycle = db.query(models.AuditCycle).filter(models.AuditCycle.id == cycle_id).first()
    if not cycle or cycle.status == "Closed":
        return None
        
    cycle.status = "Closed"
    
    # Auto-update asset statuses based on audit results
    records = get_audit_records(db, cycle_id)
    missing_count = 0
    damaged_count = 0
    
    for r in records:
        if r.verification_status == "Missing":
            r.asset.status = "Lost"
            missing_count += 1
        elif r.verification_status == "Damaged":
            r.asset.condition = "Damaged"
            damaged_count += 1
            
    db.commit()
    db.refresh(cycle)
    
    create_activity_log(
        db, actor_id, "CLOSE_AUDIT_CYCLE", 
        f"Closed audit cycle '{cycle.name}'. Automatically marked {missing_count} assets as Lost and updated {damaged_count} assets as Damaged."
    )
    
    # Notify all managers
    managers = db.query(models.User).filter(models.User.role.in_(["admin", "asset_manager"])).all()
    for m in managers:
        create_notification(
            db, m.id, "Audit Discrepancy", "Audit Cycle Closed with Discrepancies",
            f"Audit cycle '{cycle.name}' has been closed. Results: {missing_count} assets marked Lost, {damaged_count} assets marked Damaged."
        )
        
    return cycle
