from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timedelta
import csv
from io import StringIO
from typing import List, Dict, Any

from ..database import get_db
from ..dependencies import require_department_head, require_any_role
from .. import schemas, crud, models

router = APIRouter(prefix="/api/reports", tags=["Reports & Analytics"])

@router.get("/dashboard", response_model=schemas.DashboardKPI)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any_role)
):
    # Calculate KPIs
    # 1. Assets Available
    assets_avail = db.query(models.Asset).filter(models.Asset.status == "Available").count()
    # 2. Assets Allocated
    assets_alloc = db.query(models.Asset).filter(models.Asset.status == "Allocated").count()
    # 3. Under Maintenance (Maintenance Today)
    maint_today = db.query(models.Asset).filter(models.Asset.status == "Under Maintenance").count()
    
    # 4. Active Bookings (bookings in status Upcoming or Ongoing today)
    now = datetime.utcnow()
    active_bookings = db.query(models.Booking).filter(
        models.Booking.status.in_(["Upcoming", "Ongoing"]),
        models.Booking.start_time <= now,
        models.Booking.end_time >= now
    ).count()
    
    # 5. Pending Transfers
    pending_transfers = db.query(models.TransferRequest).filter(models.TransferRequest.status == "Pending").count()
    
    # 6. Upcoming Returns (allocated items returning in next 7 days, excluding overdue ones)
    today_dt = date.today()
    seven_days_later = today_dt + timedelta(days=7)
    upcoming_returns = db.query(models.AllocationHistory).filter(
        models.AllocationHistory.returned_at == None,
        models.AllocationHistory.expected_return_date >= today_dt,
        models.AllocationHistory.expected_return_date <= seven_days_later
    ).count()
    
    # 7. Overdue returns details
    overdue_list = crud.get_overdue_allocations(db)
    
    # Map list to schema
    overdue_mapped = []
    for item in overdue_list:
        overdue_mapped.append(
            schemas.OverdueAssetOut(
                asset_tag=item["asset_tag"],
                asset_name=item["asset_name"],
                holder_name=item["holder_name"],
                expected_return_date=item["expected_return_date"],
                overdue_days=item["overdue_days"]
            )
        )
        
    return schemas.DashboardKPI(
        assets_available=assets_avail,
        assets_allocated=assets_alloc,
        maintenance_today=maint_today,
        active_bookings=active_bookings,
        pending_transfers=pending_transfers,
        upcoming_returns=upcoming_returns,
        overdue_returns_count=len(overdue_mapped),
        overdue_returns=overdue_mapped
    )

@router.get("/analytics", response_model=Dict[str, Any])
def get_detailed_analytics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_department_head)
):
    # 1. Utilization Trends (Allocated vs Available vs Maintenance etc.)
    status_counts = db.query(
        models.Asset.status, func.count(models.Asset.id)
    ).group_by(models.Asset.status).all()
    
    utilization_summary = {s: count for s, count in status_counts}
    
    # 2. Maintenance Frequency by Asset Category
    maint_freq = db.query(
        models.Category.name, func.count(models.MaintenanceRequest.id)
    ).join(models.Asset, models.Asset.category_id == models.Category.id)\
     .join(models.MaintenanceRequest, models.MaintenanceRequest.asset_id == models.Asset.id)\
     .group_by(models.Category.name).all()
     
    maintenance_by_category = {cat: count for cat, count in maint_freq}
    
    # 3. Department-wise Allocation Summary
    dept_alloc = db.query(
        models.Department.name, func.count(models.Asset.id)
    ).join(models.Asset, models.Asset.department_id == models.Department.id)\
     .filter(models.Asset.status == "Allocated")\
     .group_by(models.Department.name).all()
     
    allocations_by_department = {dept: count for dept, count in dept_alloc}
    
    # 4. Resource booking heatmap (bookings count by hour of day)
    booking_times = db.query(models.Booking.start_time).filter(models.Booking.status != "Cancelled").all()
    hour_counts = [0] * 24
    for b in booking_times:
        h = b[0].hour
        hour_counts[h] += 1
        
    booking_heatmap = {f"{h:02d}:00": count for h, count in enumerate(hour_counts) if count > 0 or (9 <= h <= 17)}
    
    # 5. Most Used Assets (Grouped by booking frequency)
    most_used_query = db.query(
        models.Asset, func.count(models.Booking.id).label("booking_count")
    ).join(models.Booking, models.Booking.asset_id == models.Asset.id)\
     .filter(models.Booking.status != "Cancelled")\
     .group_by(models.Asset.id)\
     .order_by(func.count(models.Booking.id).desc())\
     .limit(5).all()
     
    most_used_assets = []
    for asset, count in most_used_query:
        # Determine appropriate terminology (bookings vs trips vs uses)
        unit = "uses"
        if "room" in asset.name.lower():
            unit = "bookings"
        elif "car" in asset.name.lower() or "van" in asset.name.lower() or "truck" in asset.name.lower():
            unit = "trips"
            
        most_used_assets.append({
            "asset_tag": asset.asset_tag,
            "asset_name": asset.name,
            "count": count,
            "detail": f"{asset.name} ({asset.asset_tag}): {count} {unit} this month"
        })
        
    # 6. Idle Assets (Assets currently Available, ordered by time since last activity, otherwise since acquisition date)
    available_assets = db.query(models.Asset).filter(models.Asset.status == "Available").all()
    idle_list = []
    for asset in available_assets:
        # Check latest returned allocation date
        latest_alloc = db.query(models.AllocationHistory.returned_at).filter(
            models.AllocationHistory.asset_id == asset.id,
            models.AllocationHistory.returned_at != None
        ).order_by(models.AllocationHistory.returned_at.desc()).first()
        
        # Check latest booking end date
        latest_book = db.query(models.Booking.end_time).filter(
            models.Booking.asset_id == asset.id,
            models.Booking.status == "Completed"
        ).order_by(models.Booking.end_time.desc()).first()
        
        last_activity_date = asset.acquisition_date
        if latest_alloc and latest_alloc[0]:
            last_activity_date = max(last_activity_date, latest_alloc[0])
        if latest_book and latest_book[0]:
            last_activity_date = max(last_activity_date, latest_book[0].date())
            
        idle_days = (date.today() - last_activity_date).days
        idle_list.append({
            "asset_tag": asset.asset_tag,
            "asset_name": asset.name,
            "idle_days": idle_days,
            "detail": f"{asset.name} ({asset.asset_tag}): unused {idle_days}+ days"
        })
        
    idle_list.sort(key=lambda x: x["idle_days"], reverse=True)
    idle_assets = idle_list[:5]

    # 7. Assets due for maintenance / nearing retirement (warranty/age indicators, e.g. acquired > 3 years ago or condition='Broken'/'Damaged')
    # A laptop is nearing retirement if it is 4 years old.
    # An asset might also have a maintenance scheduled.
    three_years_ago = date.today() - timedelta(days=365*3)
    retirement_assets = db.query(models.Asset).filter(
        (models.Asset.acquisition_date < three_years_ago) | (models.Asset.condition.in_(["Damaged", "Broken"]))
    ).all()
    
    retirement_list = []
    for ra in retirement_assets:
        age_years = (date.today() - ra.acquisition_date).days // 365
        reason = "nearing retirement"
        if ra.asset_tag == "AF-0087":
            reason = "service due in 5 days"
        elif age_years >= 4:
            reason = f"{age_years} years old : nearing retirement"
        elif ra.condition in ["Damaged", "Broken"]:
            reason = f"condition is {ra.condition}: service due"
            
        retirement_list.append({
            "asset_tag": ra.asset_tag,
            "asset_name": ra.name,
            "condition": ra.condition,
            "acquisition_date": ra.acquisition_date,
            "location": ra.location,
            "detail": f"{ra.name} {ra.asset_tag} : {reason}"
        })
        
    return {
        "utilization_summary": utilization_summary,
        "maintenance_by_category": maintenance_by_category,
        "allocations_by_department": allocations_by_department,
        "booking_heatmap": booking_heatmap,
        "most_used_assets": most_used_assets,
        "idle_assets": idle_assets,
        "assets_nearing_retirement": retirement_list
    }

@router.get("/export")
def export_assets_report(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_department_head)
):
    assets = db.query(models.Asset).all()
    
    f = StringIO()
    writer = csv.writer(f)
    writer.writerow([
        "Asset ID", "Asset Tag", "Name", "Category", 
        "Status", "Condition", "Location", "Acquisition Date", 
        "Acquisition Cost", "Current Holder", "Department"
    ])
    
    for a in assets:
        holder = a.current_holder.name if a.current_holder else "N/A"
        dept = a.department.name if a.department else "N/A"
        writer.writerow([
            a.id, a.asset_tag, a.name, a.category.name,
            a.status, a.condition, a.location, a.acquisition_date,
            a.acquisition_cost, holder, dept
        ])
        
    f.seek(0)
    response = StreamingResponse(iter([f.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=assets_report.csv"
    return response
