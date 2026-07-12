from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..dependencies import require_asset_manager, require_any_role, get_current_user
from .. import schemas, crud, models

router = APIRouter(prefix="/api/notifications", tags=["Notifications & Activity Logs"])

@router.get("", response_model=List[schemas.NotificationOut])
def get_user_notifications(
    filter_type: Optional[str] = "All",  # All, Alerts, Approvals, Bookings
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any_role)
):
    query = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id
    )
    
    if filter_type and filter_type.lower() != "all":
        f = filter_type.lower()
        if f == "alerts":
            query = query.filter(
                models.Notification.type.in_([
                    "Overdue Return", "Audit Discrepancy", "Overdue return", "audit discrepancy flagged"
                ])
            )
        elif f == "approvals":
            query = query.filter(
                models.Notification.type.in_([
                    "Transfer Request", "Transfer Approved", "Transfer Rejected", 
                    "Maintenance Update", "Maintenance request approved", "Transfer approved"
                ])
            )
        elif f == "bookings":
            query = query.filter(
                models.Notification.type.in_([
                    "Booking Confirmation", "Booking Cancelled", "Booking confirmed", "Booking cancelled"
                ])
            )
            
    notifs = query.order_by(models.Notification.created_at.desc()).all()
    return notifs

@router.put("/{id}/read", response_model=schemas.NotificationOut)
def mark_notification_as_read(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any_role)
):
    notif = db.query(models.Notification).filter(
        models.Notification.id == id,
        models.Notification.user_id == current_user.id
    ).first()
    
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif

@router.get("/activities", response_model=List[schemas.ActivityLogOut])
def view_system_activities(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_asset_manager)
):
    logs = db.query(models.ActivityLog).order_by(models.ActivityLog.created_at.desc()).all()
    res = []
    for l in logs:
        actor_name = l.actor.name if l.actor else "System / Deleted User"
        res.append(
            schemas.ActivityLogOut(
                id=l.id,
                actor_id=l.actor_id,
                actor_name=actor_name,
                action=l.action,
                details=l.details,
                created_at=l.created_at
            )
        )
    return res
