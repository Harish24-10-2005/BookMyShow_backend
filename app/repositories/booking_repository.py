from __future__ import annotations

from datetime import datetime
from typing import List, Optional
import uuid
from app.db import get_supabase_client
from app.models.schemas import BookingResponse, Seat, BookingHistoryItem
from app.models.entities import SeatStatus


class BookingRepository:
    """Repository for booking operations with Supabase."""
    
    def __init__(self):
        self._client = get_supabase_client()
    
    def create_booking(self, user_id: Optional[str], show_id: str, seats: List[Seat], 
                       total_amount: float, status: str = "pending") -> BookingResponse:
        """Create a new booking."""
        if not self._client:
            raise ValueError("Database not configured")
        
        booking_id = str(uuid.uuid4())
        
        # Insert booking
        booking_data = {
            "id": booking_id,
            "show_id": show_id,
            "status": status,
            "total_amount": total_amount,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Only add user_id if provided and not "anonymous"
        if user_id and user_id != "anonymous":
            booking_data["user_id"] = user_id
        
        self._client.table("bookings").insert(booking_data).execute()
        
        # Insert booking items
        booking_items = []
        for seat in seats:
            booking_items.append({
                "booking_id": booking_id,
                "seat_id": seat.id,
                "price": seat.price
            })
        
        if booking_items:
            self._client.table("booking_items").insert(booking_items).execute()
        
        return BookingResponse(
            show_id=show_id,
            booking_id=booking_id,
            status=status,
            total_amount=total_amount,
            seats=seats
        )
    
    def get_booking(self, booking_id: str) -> Optional[BookingResponse]:
        """Get booking by ID."""
        if not self._client:
            return None
        
        response = self._client.table("bookings").select("*").eq("id", booking_id).single().execute()
        
        if not response.data:
            return None
        
        booking = response.data
        
        # Get booking items
        items_resp = self._client.table("booking_items").select("*").eq("booking_id", booking_id).execute()
        
        seats = []
        for item in items_resp.data:
            # Parse seat_id
            seat_id_parts = item["seat_id"].split("-")
            section = seat_id_parts[0] if seat_id_parts else "gold"
            row_letter = seat_id_parts[1][0] if len(seat_id_parts) > 1 and seat_id_parts[1] else "A"
            seat_number = seat_id_parts[1][1:] if len(seat_id_parts) > 1 and len(seat_id_parts[1]) > 1 else "1"
            
            seats.append(Seat(
                id=item["seat_id"],
                section=section,
                row=row_letter,
                number=seat_number,
                status=SeatStatus.booked,
                price=float(item["price"])
            ))
        
        return BookingResponse(
            show_id=str(booking["show_id"]),
            booking_id=str(booking["id"]),
            status=booking["status"],
            total_amount=float(booking["total_amount"]),
            seats=seats
        )
    
    def update_status(self, booking_id: str, status: str, payment_ref: Optional[str] = None) -> Optional[BookingResponse]:
        """Update booking status."""
        if not self._client:
            return None
        
        update_data = {"status": status}
        if payment_ref:
            update_data["payment_ref"] = payment_ref
        
        self._client.table("bookings").update(update_data).eq("id", booking_id).execute()
        
        return self.get_booking(booking_id)
    
    def get_user_bookings(self, user_id: Optional[str] = None) -> List[BookingHistoryItem]:
        """Get booking history for a user or all bookings."""
        if not self._client:
            return []
        
        query = self._client.table("bookings").select("*").order("created_at", desc=True)
        
        if user_id:
            query = query.eq("user_id", user_id)
        
        response = query.limit(50).execute()
        
        history = []
        for booking in response.data:
            # Get seat IDs for this booking
            items_resp = self._client.table("booking_items").select("seat_id").eq("booking_id", booking["id"]).execute()
            seat_ids = [item["seat_id"] for item in items_resp.data]
            
            created_at = booking.get("created_at", datetime.utcnow().isoformat())
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            
            history.append(BookingHistoryItem(
                booking_id=str(booking["id"]),
                show_id=str(booking["show_id"]),
                status=booking["status"],
                total_amount=float(booking["total_amount"]),
                created_at=created_at,
                seats=seat_ids
            ))
        
        return history
    
    def create_payment(self, booking_id: str, amount: float, status: str = "pending", 
                      provider: str = "mock", txn_ref: Optional[str] = None) -> dict:
        """Create a payment record."""
        if not self._client:
            raise ValueError("Database not configured")
        
        payment_id = str(uuid.uuid4())
        
        self._client.table("payments").insert({
            "id": payment_id,
            "booking_id": booking_id,
            "status": status,
            "amount": amount,
            "provider": provider,
            "txn_ref": txn_ref or str(uuid.uuid4())
        }).execute()
        
        return {
            "id": payment_id,
            "booking_id": booking_id,
            "status": status,
            "amount": amount
        }
    
    def update_payment_status(self, booking_id: str, status: str) -> None:
        """Update payment status for a booking."""
        if not self._client:
            return
        
        self._client.table("payments").update({
            "status": status
        }).eq("booking_id", booking_id).execute()
