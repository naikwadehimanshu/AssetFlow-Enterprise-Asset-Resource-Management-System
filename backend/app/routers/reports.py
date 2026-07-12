from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timedelta
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
    # 1. Utilization Trends (Allocated vs Available vs Maintenance)
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
    
    # 5. Assets nearing retirement (warranty/age indicators, e.g. acquired > 3 years ago or condition='Broken'/'Damaged')
    three_years_ago = date.today() - timedelta(days=365*3)
    retirement_assets = db.query(models.Asset).filter(
        (models.Asset.acquisition_date < three_years_ago) | (models.Asset.condition.in_(["Damaged", "Broken"]))
    ).all()
    
    retirement_list = []
    for ra in retirement_assets:
        retirement_list.append({
            "asset_tag": ra.asset_tag,
            "asset_name": ra.name,
            "condition": ra.condition,
            "acquisition_date": ra.acquisition_date,
            "location": ra.location
        })
        
    return {
        "utilization_summary": utilization_summary,
        "maintenance_by_category": maintenance_by_category,
        "allocations_by_department": allocations_by_department,
        "booking_heatmap": booking_heatmap,
        "assets_nearing_retirement": retirement_list
    }
