from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from ..database import get_db
from ..dependencies import require_any_role, get_current_user
from .. import schemas, crud, models

router = APIRouter(prefix="/api/bookings", tags=["Resource Bookings"])

@router.get("", response_model=List[schemas.BookingOut])
def list_bookings(
    asset_id: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any_role)
):
    bookings = crud.get_bookings(db, asset_id=asset_id, start=start_time, end=end_time)
    res = []
    for b in bookings:
        res.append(
            schemas.BookingOut(
                id=b.id,
                asset_id=b.asset_id,
                asset_name=b.resource.name,
                asset_tag=b.resource.asset_tag,
                booked_by_id=b.booked_by_id,
                booked_by_name=b.booked_by.name,
                start_time=b.start_time,
                end_time=b.end_time,
                status=b.status,
                created_at=b.created_at
            )
        )
    return res

@router.post("", response_model=schemas.BookingOut, status_code=status.HTTP_201_CREATED)
def book_shared_resource(
    book_in: schemas.BookingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any_role)
):
    db_asset = crud.get_asset_by_id(db, book_in.asset_id)
    if not db_asset:
        raise HTTPException(status_code=404, detail="Resource not found")
        
    # Check if resource is actually shared/bookable
    if not db_asset.is_shared:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset '{db_asset.asset_tag}' ({db_asset.name}) is not registered as a shared bookable resource."
        )
        
    # Validate start/end times
    if book_in.start_time >= book_in.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start time must be before end time."
        )
        
    if book_in.start_time < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot book slots in the past."
        )
        
    # --- OVERLAP VALIDATION ---
    has_overlap = crud.check_booking_overlap(db, book_in.asset_id, book_in.start_time, book_in.end_time)
    if has_overlap:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Time slot overlaps with an existing booking for resource '{db_asset.name}'."
        )
        
    booking = crud.create_booking(db, book_in, actor_id=current_user.id)
    
    return schemas.BookingOut(
        id=booking.id,
        asset_id=booking.asset_id,
        asset_name=db_asset.name,
        asset_tag=db_asset.asset_tag,
        booked_by_id=booking.booked_by_id,
        booked_by_name=current_user.name,
        start_time=booking.start_time,
        end_time=booking.end_time,
        status=booking.status,
        created_at=booking.created_at
    )

@router.put("/{id}/cancel", response_model=schemas.BookingOut)
def cancel_existing_booking(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_any_role)
):
    booking = db.query(models.Booking).filter(models.Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    # Check authorization: Only the employee who booked it, or an Asset Manager/Admin can cancel
    if current_user.role not in ["admin", "asset_manager"] and booking.booked_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to cancel this booking."
        )
        
    if booking.status in ["Completed", "Cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Booking is already {booking.status.lower()}."
        )
        
    cancelled = crud.cancel_booking(db, id, actor_id=current_user.id)
    return schemas.BookingOut(
        id=cancelled.id,
        asset_id=cancelled.asset_id,
        asset_name=cancelled.resource.name,
        asset_tag=cancelled.resource.asset_tag,
        booked_by_id=cancelled.booked_by_id,
        booked_by_name=cancelled.booked_by.name,
        start_time=cancelled.start_time,
        end_time=cancelled.end_time,
        status=cancelled.status,
        created_at=cancelled.created_at
    )
