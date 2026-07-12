from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
import uuid

from app.database import SessionLocal, engine, Base
from app.dependencies import get_password_hash
from app import models

def seed_db():
    print("Re-initializing tables...")
    with engine.connect() as connection:
        # Disable foreign key checks temporarily to drop/create circular tables
        connection.execute(text("PRAGMA foreign_keys = OFF"))
        Base.metadata.drop_all(bind=connection)
        Base.metadata.create_all(bind=connection)
        connection.commit()
    
    db: Session = SessionLocal()
    try:
        print("Seeding database...")
        
        # 1. Create Departments
        print("Creating departments...")
        dept_eng = models.Department(name="Engineering", status="Active")
        dept_fac = models.Department(name="Facilities", status="Active")
        dept_fo = models.Department(name="Field Ops", status="Active")
        db.add_all([dept_eng, dept_fac, dept_fo])
        db.commit()
        
        # Field Ops East is inactive, parent is Field Ops
        dept_foe = models.Department(name="Field Ops (east)", parent_department_id=dept_fo.id, status="Inactive")
        db.add(dept_foe)
        db.commit()
        
        # 2. Create Users
        print("Creating users...")
        pw_hash = get_password_hash("password123")
        
        u_admin = models.User(name="Admin User", email="admin@company.com", hashed_password=pw_hash, role="admin", status="Active")
        u_manager = models.User(name="Asset Manager", email="manager@company.com", hashed_password=pw_hash, role="asset_manager", status="Active")
        
        # Department heads
        u_aditi = models.User(name="Aditi Rao", email="aditi@company.com", hashed_password=pw_hash, role="department_head", status="Active", department_id=dept_eng.id)
        u_rohan = models.User(name="Rohan Mehta", email="rohan@company.com", hashed_password=pw_hash, role="department_head", status="Active", department_id=dept_fac.id)
        u_sana = models.User(name="Sana Iqbal", email="sana@company.com", hashed_password=pw_hash, role="department_head", status="Active", department_id=dept_foe.id)
        
        # Employees
        u_priya = models.User(name="Priya Shah", email="priya@company.com", hashed_password=pw_hash, role="employee", status="Active", department_id=dept_eng.id)
        u_raj = models.User(name="Raj Patel", email="raj@company.com", hashed_password=pw_hash, role="employee", status="Active", department_id=dept_eng.id)
        u_arjun = models.User(name="Arjun Nair", email="arjun@company.com", hashed_password=pw_hash, role="employee", status="Active", department_id=dept_fac.id)
        
        db.add_all([u_admin, u_manager, u_aditi, u_rohan, u_sana, u_priya, u_raj, u_arjun])
        db.commit()
        
        # Update department heads
        dept_eng.head_id = u_aditi.id
        dept_fac.head_id = u_rohan.id
        dept_foe.head_id = u_sana.id
        db.commit()
        
        # 3. Create Categories
        print("Creating categories...")
        cat_elec = models.Category(
            name="Electronics",
            category_specific_fields=[
                {"name": "warranty_months", "type": "int", "required": False},
                {"name": "manufacturer", "type": "string", "required": True}
            ]
        )
        cat_furn = models.Category(
            name="Furniture",
            category_specific_fields=[
                {"name": "material", "type": "string", "required": False}
            ]
        )
        cat_veh = models.Category(
            name="Vehicles",
            category_specific_fields=[
                {"name": "license_plate", "type": "string", "required": True},
                {"name": "fuel_type", "type": "string", "required": False}
            ]
        )
        db.add_all([cat_elec, cat_furn, cat_veh])
        db.commit()
        
        # 4. Create Assets
        print("Creating assets...")
        # Dell Laptop AF-0012
        a_dell12 = models.Asset(
            name="Dell Laptop", asset_tag="AF-0012", serial_number="SN-DELL-12001",
            qr_code=f"ASSETFLOW:AF-0012:{uuid.uuid4().hex[:8]}",
            category_id=cat_elec.id, status="Allocated", condition="Good",
            location="Bengaluru", acquisition_cost=1200.00,
            acquisition_date=date(2026, 3, 12), is_shared=False,
            current_holder_id=u_priya.id, department_id=dept_eng.id
        )
        # Dell Laptop AF-0114
        a_dell14 = models.Asset(
            name="Dell Laptop", asset_tag="AF-0114", serial_number="SN-DELL-14002",
            qr_code=f"ASSETFLOW:AF-0114:{uuid.uuid4().hex[:8]}",
            category_id=cat_elec.id, status="Allocated", condition="Good",
            location="Bengaluru", acquisition_cost=1200.00,
            acquisition_date=date(2026, 1, 1), is_shared=False,
            current_holder_id=u_priya.id, department_id=dept_eng.id
        )
        # Projector AF-0062
        a_proj = models.Asset(
            name="Projector", asset_tag="AF-0062", serial_number="SN-PROJ-6209",
            qr_code=f"ASSETFLOW:AF-0062:{uuid.uuid4().hex[:8]}",
            category_id=cat_elec.id, status="Under Maintenance", condition="Damaged",
            location="HQ floor 2", acquisition_cost=800.00,
            acquisition_date=date(2026, 6, 10), is_shared=False
        )
        # Office Chair AF-0201
        a_chair = models.Asset(
            name="Office chair", asset_tag="AF-0201", serial_number="SN-CHAIR-201",
            qr_code=f"ASSETFLOW:AF-0201:{uuid.uuid4().hex[:8]}",
            category_id=cat_furn.id, status="Available", condition="Good",
            location="Warehouse", acquisition_cost=150.00,
            acquisition_date=date(2026, 1, 15), is_shared=False
        )
        # Conference Room B2 (Shared Asset)
        a_room = models.Asset(
            name="Conference Room B2", asset_tag="AF-9901", serial_number="ROOM-B2-HQ",
            qr_code=f"ASSETFLOW:AF-9901:{uuid.uuid4().hex[:8]}",
            category_id=cat_elec.id, status="Available", condition="Good",
            location="HQ floor 1", acquisition_cost=0.00,
            acquisition_date=date(2026, 1, 1), is_shared=True
        )
        # Pool Car 1 (Shared Asset)
        a_car = models.Asset(
            name="Pool Car 1", asset_tag="AF-9902", serial_number="VEH-CAR-01",
            qr_code=f"ASSETFLOW:AF-9902:{uuid.uuid4().hex[:8]}",
            category_id=cat_veh.id, status="Available", condition="Good",
            location="Parking", acquisition_cost=25000.00,
            acquisition_date=date(2026, 2, 10), is_shared=True
        )
        # AC Unit AF-0003
        a_ac = models.Asset(
            name="AC Unit", asset_tag="AF-0003", serial_number="SN-AC-003",
            qr_code=f"ASSETFLOW:AF-0003:{uuid.uuid4().hex[:8]}",
            category_id=cat_elec.id, status="Under Maintenance", condition="Damaged",
            location="Server Room", acquisition_cost=2500.00,
            acquisition_date=date(2026, 2, 20), is_shared=False
        )
        # Forklift AF-0078
        a_fork = models.Asset(
            name="Forklift", asset_tag="AF-0078", serial_number="SN-FORK-078",
            qr_code=f"ASSETFLOW:AF-0078:{uuid.uuid4().hex[:8]}",
            category_id=cat_veh.id, status="Under Maintenance", condition="Damaged",
            location="Yard", acquisition_cost=15000.00,
            acquisition_date=date(2026, 4, 5), is_shared=False
        )
        # Printer AF-0897
        a_print = models.Asset(
            name="Printer", asset_tag="AF-0897", serial_number="SN-PRINT-897",
            qr_code=f"ASSETFLOW:AF-0897:{uuid.uuid4().hex[:8]}",
            category_id=cat_elec.id, status="Under Maintenance", condition="Damaged",
            location="Copy Room", acquisition_cost=500.00,
            acquisition_date=date(2025, 9, 18), is_shared=False
        )
        # Office Chair 2 AF-0873
        a_chair2 = models.Asset(
            name="Office chair 2", asset_tag="AF-0873", serial_number="SN-CHAIR-873",
            qr_code=f"ASSETFLOW:AF-0873:{uuid.uuid4().hex[:8]}",
            category_id=cat_furn.id, status="Available", condition="Good",
            location="HR Dept", acquisition_cost=150.00,
            acquisition_date=date(2026, 1, 2), is_shared=False
        )
        
        # Dell Laptop AF-003
        a_dell03 = models.Asset(
            name="Dell laptop", asset_tag="AF-003", serial_number="SN-DELL-00301",
            qr_code=f"ASSETFLOW:AF-003:{uuid.uuid4().hex[:8]}",
            category_id=cat_elec.id, status="Allocated", condition="Good",
            location="Desk E12", acquisition_cost=1200.00,
            acquisition_date=date(2026, 2, 1), is_shared=False,
            current_holder_id=u_priya.id, department_id=dept_eng.id
        )
        # Office Chair AF-9921
        a_chair9921 = models.Asset(
            name="Office chair", asset_tag="AF-9921", serial_number="SN-CHAIR-9921",
            qr_code=f"ASSETFLOW:AF-9921:{uuid.uuid4().hex[:8]}",
            category_id=cat_furn.id, status="Allocated", condition="Good",
            location="Desk E14", acquisition_cost=150.00,
            acquisition_date=date(2026, 1, 15), is_shared=False,
            current_holder_id=u_priya.id, department_id=dept_eng.id
        )
        # Monitor AF-9838
        a_monitor9838 = models.Asset(
            name="Monitor", asset_tag="AF-9838", serial_number="SN-MON-9838",
            qr_code=f"ASSETFLOW:AF-9838:{uuid.uuid4().hex[:8]}",
            category_id=cat_elec.id, status="Allocated", condition="Good",
            location="Desk E15", acquisition_cost=300.00,
            acquisition_date=date(2026, 2, 10), is_shared=False,
            current_holder_id=u_priya.id, department_id=dept_eng.id
        )
        # Van AF-343
        a_van343 = models.Asset(
            name="Van", asset_tag="AF-343", serial_number="VEH-VAN-343",
            qr_code=f"ASSETFLOW:AF-343:{uuid.uuid4().hex[:8]}",
            category_id=cat_veh.id, status="Available", condition="Good",
            location="Parking", acquisition_cost=30000.00,
            acquisition_date=date(2026, 1, 10), is_shared=True
        )
        # Projector AF-335
        a_proj335 = models.Asset(
            name="Projector", asset_tag="AF-335", serial_number="SN-PROJ-335",
            qr_code=f"ASSETFLOW:AF-335:{uuid.uuid4().hex[:8]}",
            category_id=cat_elec.id, status="Available", condition="Good",
            location="Conference Room B2", acquisition_cost=800.00,
            acquisition_date=date(2026, 2, 15), is_shared=True
        )
        # Camera AF-0301 (unused 60+ days)
        a_camera0301 = models.Asset(
            name="Camera", asset_tag="AF-0301", serial_number="SN-CAM-0301",
            qr_code=f"ASSETFLOW:AF-0301:{uuid.uuid4().hex[:8]}",
            category_id=cat_elec.id, status="Available", condition="Good",
            location="Warehouse", acquisition_cost=500.00,
            acquisition_date=date.today() - timedelta(days=62), is_shared=False
        )
        # Chair AF-0410 (unused 45 days)
        a_chair0410 = models.Asset(
            name="Chair", asset_tag="AF-0410", serial_number="SN-CHAIR-0410",
            qr_code=f"ASSETFLOW:AF-0410:{uuid.uuid4().hex[:8]}",
            category_id=cat_furn.id, status="Available", condition="Good",
            location="Warehouse", acquisition_cost=150.00,
            acquisition_date=date.today() - timedelta(days=46), is_shared=False
        )
        # Forklift AF-0087 (service due in 5 days, condition Damaged)
        a_fork0087 = models.Asset(
            name="Forklift", asset_tag="AF-0087", serial_number="SN-FORK-0087",
            qr_code=f"ASSETFLOW:AF-0087:{uuid.uuid4().hex[:8]}",
            category_id=cat_veh.id, status="Under Maintenance", condition="Damaged",
            location="Yard", acquisition_cost=18000.00,
            acquisition_date=date.today() - timedelta(days=120), is_shared=False
        )
        # Laptop AF-0020 (4 years old: nearing retirement)
        a_laptop0020 = models.Asset(
            name="Laptop", asset_tag="AF-0020", serial_number="SN-LAP-0020",
            qr_code=f"ASSETFLOW:AF-0020:{uuid.uuid4().hex[:8]}",
            category_id=cat_elec.id, status="Allocated", condition="Good",
            location="Bengaluru", acquisition_cost=1200.00,
            acquisition_date=date.today() - timedelta(days=365 * 4), is_shared=False,
            current_holder_id=u_priya.id, department_id=dept_eng.id
        )
        
        db.add_all([
            a_dell12, a_dell14, a_proj, a_chair, a_room, a_car, a_ac, a_fork, a_print, a_chair2,
            a_dell03, a_chair9921, a_monitor9838, a_van343, a_proj335, a_camera0301, a_chair0410, a_fork0087, a_laptop0020
        ])
        db.commit()
        
        # 5. Create Allocation History
        print("Creating allocation history...")
        # AF-0012
        hist12 = models.AllocationHistory(
            asset_id=a_dell12.id, employee_id=u_priya.id, department_id=dept_eng.id,
            allocated_at=date(2026, 3, 12), expected_return_date=date(2026, 12, 31)
        )
        
        # AF-0114 previous allocation returned
        hist14_prev = models.AllocationHistory(
            asset_id=a_dell14.id, employee_id=u_arjun.id, department_id=dept_fac.id,
            allocated_at=date(2025, 12, 1), returned_at=date(2026, 1, 4),
            return_condition="Good", check_in_notes="Returned by Arjun Nair - condition: good"
        )
        # AF-0114 current active allocation (overdue by a few days for testing, e.g. expected July 5, today is July 12)
        hist14_curr = models.AllocationHistory(
            asset_id=a_dell14.id, employee_id=u_priya.id, department_id=dept_eng.id,
            allocated_at=date(2026, 3, 12), expected_return_date=date(2026, 7, 5)
        )
        db.add_all([hist12, hist14_prev, hist14_curr])
        db.commit()
        
        # 6. Create Resource Bookings
        print("Creating bookings...")
        # 34 bookings for Conference Room B2 (AF-9901)
        for i in range(34):
            b = models.Booking(
                asset_id=a_room.id,
                booked_by_id=u_aditi.id if i % 2 == 0 else u_priya.id,
                start_time=datetime.utcnow() - timedelta(days=i, hours=2),
                end_time=datetime.utcnow() - timedelta(days=i, hours=1),
                status="Completed"
            )
            db.add(b)

        # 21 bookings for Van (AF-343)
        for i in range(21):
            b = models.Booking(
                asset_id=a_van343.id,
                booked_by_id=u_arjun.id if i % 2 == 0 else u_priya.id,
                start_time=datetime.utcnow() - timedelta(days=i, hours=4),
                end_time=datetime.utcnow() - timedelta(days=i, hours=3),
                status="Completed"
            )
            db.add(b)

        # 18 bookings for Projector (AF-335)
        for i in range(18):
            b = models.Booking(
                asset_id=a_proj335.id,
                booked_by_id=u_raj.id if i % 2 == 0 else u_priya.id,
                start_time=datetime.utcnow() - timedelta(days=i, hours=6),
                end_time=datetime.utcnow() - timedelta(days=i, hours=5),
                status="Completed"
            )
            db.add(b)
        db.commit()

        # 7. Create Maintenance Requests
        print("Creating maintenance requests...")
        m_proj = models.MaintenanceRequest(
            asset_id=a_proj.id, reporter_id=u_priya.id,
            description="Projector bulb not turning on", priority="High",
            status="Pending", created_at=datetime(2026, 7, 10, 10, 0, 0)
        )
        m_ac = models.MaintenanceRequest(
            asset_id=a_ac.id, reporter_id=u_raj.id,
            description="ac unit noisy compressor", priority="Medium",
            status="Approved", created_at=datetime(2026, 7, 8, 14, 30, 0)
        )
        m_fork = models.MaintenanceRequest(
            asset_id=a_fork.id, reporter_id=u_arjun.id,
            description="Forklift - regular servicing needed", priority="High",
            status="Technician Assigned", technician_name="R Varma",
            created_at=datetime(2026, 7, 7, 11, 15, 0)
        )
        m_print = models.MaintenanceRequest(
            asset_id=a_print.id, reporter_id=u_raj.id,
            description="Printer Jam - parts ordered", priority="Low",
            status="In Progress", technician_name="Internal IT Support",
            created_at=datetime(2026, 7, 6, 9, 45, 0)
        )
        m_chair2 = models.MaintenanceRequest(
            asset_id=a_chair2.id, reporter_id=u_arjun.id,
            description="Chair repair - loose bolts", priority="Low",
            status="Resolved", technician_name="Rohan Mehta",
            resolution_notes="Tightened all bolts and verified load capacity.",
            created_at=datetime(2026, 7, 5, 10, 0, 0),
            updated_at=datetime(2026, 7, 7, 16, 0, 0)
        )
        db.add_all([m_proj, m_ac, m_fork, m_print, m_chair2])
        db.commit()

        # 7.5 Create Audit Cycles and Records
        print("Creating audit cycle...")
        audit_cycle = models.AuditCycle(
            name="Q3 audit: Engineering dept - 1-15 jul",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 15),
            scope_type="department",
            scope_value="Engineering",
            status="Active"
        )
        db.add(audit_cycle)
        db.commit()

        # Assign auditors
        assign_aditi = models.AuditAssignment(audit_cycle_id=audit_cycle.id, auditor_id=u_aditi.id)
        assign_sana = models.AuditAssignment(audit_cycle_id=audit_cycle.id, auditor_id=u_sana.id)
        db.add_all([assign_aditi, assign_sana])
        db.commit()

        # Seed records with statuses matching Screen 8:
        # - AF-003 Dell laptop: Verified
        # - AF-9921 Office chair: Missing
        # - AF-9838 Monitor: Damaged
        rec_dell03 = models.AuditRecord(
            audit_cycle_id=audit_cycle.id,
            asset_id=a_dell03.id,
            auditor_id=u_aditi.id,
            verification_status="Verified",
            notes="Verified at desk",
            audited_at=datetime(2026, 7, 12, 10, 0, 0)
        )
        rec_chair9921 = models.AuditRecord(
            audit_cycle_id=audit_cycle.id,
            asset_id=a_chair9921.id,
            auditor_id=u_aditi.id,
            verification_status="Missing",
            notes="Not at expected desk",
            audited_at=datetime(2026, 7, 12, 10, 30, 0)
        )
        rec_monitor9838 = models.AuditRecord(
            audit_cycle_id=audit_cycle.id,
            asset_id=a_monitor9838.id,
            auditor_id=u_sana.id,
            verification_status="Damaged",
            notes="Cracked bezel",
            audited_at=datetime(2026, 7, 12, 11, 0, 0)
        )
        db.add_all([rec_dell03, rec_chair9921, rec_monitor9838])
        db.commit()

        # 8. Create some Notifications
        print("Creating notifications...")
        # Seed the notifications for all users to ensure anyone logged in can view them
        for u in [u_admin, u_manager, u_aditi, u_rohan, u_sana, u_priya, u_raj, u_arjun]:
            notifs = [
                models.Notification(
                    user_id=u.id,
                    type="Asset Assigned",
                    title="Laptop Assigned",
                    message="Laptop AF-0014 assigned to Priya shah",
                    created_at=datetime.utcnow() - timedelta(minutes=2)
                ),
                models.Notification(
                    user_id=u.id,
                    type="Maintenance request approved",
                    title="Maintenance Approved",
                    message="Maintenance request AF-0055 approved",
                    created_at=datetime.utcnow() - timedelta(minutes=18)
                ),
                models.Notification(
                    user_id=u.id,
                    type="Booking confirmed",
                    title="Booking Confirmed",
                    message="Booking confirmed : Room B2 : 2:00 to 3:00 PM",
                    created_at=datetime.utcnow() - timedelta(hours=1)
                ),
                models.Notification(
                    user_id=u.id,
                    type="Transfer approved",
                    title="Transfer Approved",
                    message="Transfer approved : AF-0033 to facilities dept",
                    created_at=datetime.utcnow() - timedelta(hours=3)
                ),
                models.Notification(
                    user_id=u.id,
                    type="Overdue return",
                    title="Overdue Return Alert",
                    message="Overdue return : AF-0021 was due 3 days ago",
                    created_at=datetime.utcnow() - timedelta(days=1)
                ),
                models.Notification(
                    user_id=u.id,
                    type="audit discrepancy flagged",
                    title="Audit Discrepancy Flagged",
                    message="audit discrepancy flagged : AF-0088 damaged",
                    created_at=datetime.utcnow() - timedelta(days=2)
                )
            ]
            db.add_all(notifs)
        db.commit()
        
        # 9. Log some initial activities
        print("Creating activity logs...")
        log1 = models.ActivityLog(actor_id=u_manager.id, action="CREATE_ASSET", details="Registered new Dell Laptop AF-0012", created_at=datetime.utcnow() - timedelta(days=10))
        log2 = models.ActivityLog(actor_id=u_manager.id, action="ALLOCATE_ASSET", details="Allocated Laptop AF-0012 to Priya Shah", created_at=datetime.utcnow() - timedelta(days=10))
        log3 = models.ActivityLog(actor_id=u_priya.id, action="CREATE_BOOKING", details="Booked Conference Room B2 for Tuesday July 7", created_at=datetime.utcnow() - timedelta(days=5))
        log4 = models.ActivityLog(actor_id=u_priya.id, action="RAISE_MAINTENANCE", details="Raised maintenance request for Projector AF-0062", created_at=datetime.utcnow() - timedelta(days=2))
        db.add_all([log1, log2, log3, log4])
        db.commit()
        
        print("Database seeded successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
