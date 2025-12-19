from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple, Dict
import uuid
from app.db import get_supabase_client
from app.models.schemas import Seat
from app.models.entities import SeatStatus


class SeatRepository:
    """Repository for seat operations with Supabase."""
    
    def __init__(self, lock_ttl_seconds: int = 300):
        self._client = get_supabase_client()
        self._lock_ttl = lock_ttl_seconds
    
    def get_seats_for_show(self, show_id: str) -> List[Seat]:
        """Get all seats for a show."""
        if not self._client:
            return []
        
        # Check if seats exist for this show
        response = self._client.table("show_seats").select("*").eq("show_id", show_id).execute()
        
        if not response.data:
            # Initialize seats for this show if they don't exist
            self._initialize_seats_for_show(show_id)
            response = self._client.table("show_seats").select("*").eq("show_id", show_id).execute()
        
        # Pre-fetch pricing info to avoid N+1 queries
        pricing_map: Dict[str, float] = {}
        base_price = 250.0
        
        try:
            # Get explicit pricing
            pricing_resp = self._client.table("show_pricing").select("section, price").eq("show_id", show_id).execute()
            if pricing_resp.data:
                for p in pricing_resp.data:
                    pricing_map[p["section"]] = float(p["price"])
            
            # Get base price
            show_resp = self._client.table("shows").select("base_price").eq("id", show_id).single().execute()
            if show_resp.data:
                base_price = float(show_resp.data["base_price"])
        except Exception as e:
            print(f"Error fetching pricing: {e}")
            pass

        now = datetime.now(timezone.utc)
        seats = []
        
        for row in response.data:
            status = SeatStatus(row["status"])
            lock_expires = None
            
            if row.get("lock_expires_at"):
                lock_expires = datetime.fromisoformat(row["lock_expires_at"].replace("Z", "+00:00"))
                # Auto-release expired locks
                if status == SeatStatus.locked and lock_expires < now:
                    status = SeatStatus.available
                    self._release_expired_lock(row["id"])
            
            # Parse seat_id to get row and number (format: section-RowNumber e.g., "gold-A1")
            seat_id_parts = row["seat_id"].split("-")
            if len(seat_id_parts) == 2:
                row_letter = seat_id_parts[1][0] if seat_id_parts[1] else "A"
                seat_number = seat_id_parts[1][1:] if len(seat_id_parts[1]) > 1 else "1"
            else:
                row_letter = "A"
                seat_number = "1"
            
            # Get price from map or calculate
            section = row["section"]
            if section in pricing_map:
                price = pricing_map[section]
            else:
                multipliers = {"gold": 1.0, "silver": 0.8, "bronze": 0.6}
                price = base_price * multipliers.get(section.lower(), 1.0)
            
            seats.append(Seat(
                id=row["seat_id"],
                section=row["section"],
                row=row_letter,
                number=seat_number,
                status=status,
                price=price,
                lock_expires_at=lock_expires if status == SeatStatus.locked else None,
                booking_id=row.get("booking_id")
            ))
        
        return seats
    
    def _get_seat_price(self, show_id: str, section: str) -> float:
        """Get price for a seat based on show and section."""
        if not self._client:
            return 250.0
        
        # Try to get price from show_pricing
        response = self._client.table("show_pricing").select("price").eq("show_id", show_id).eq("section", section).execute()
        
        if response.data:
            return float(response.data[0]["price"])
        
        # Fall back to base_price from show
        show_resp = self._client.table("shows").select("base_price").eq("id", show_id).single().execute()
        base_price = float(show_resp.data["base_price"]) if show_resp.data else 250.0
        
        # Apply section multipliers
        multipliers = {"gold": 1.0, "silver": 0.8, "bronze": 0.6}
        return base_price * multipliers.get(section.lower(), 1.0)
    
    def _initialize_seats_for_show(self, show_id: str) -> None:
        """Initialize seats for a show if they don't exist."""
        if not self._client:
            return
        
        sections = [("gold", 4, 10), ("silver", 4, 10), ("bronze", 4, 10)]
        seats_to_insert = []
        
        for section, num_rows, seats_per_row in sections:
            for row_idx in range(num_rows):
                row_letter = chr(ord("A") + row_idx)
                for seat_num in range(1, seats_per_row + 1):
                    seat_id = f"{section}-{row_letter}{seat_num}"
                    seats_to_insert.append({
                        "show_id": show_id,
                        "seat_id": seat_id,
                        "section": section,
                        "status": "available"
                    })
        
        if seats_to_insert:
            self._client.table("show_seats").insert(seats_to_insert).execute()
    
    def _release_expired_lock(self, seat_db_id: str) -> None:
        """Release an expired lock."""
        if not self._client:
            return
        
        self._client.table("show_seats").update({
            "status": "available",
            "lock_expires_at": None
        }).eq("id", seat_db_id).execute()
    
    def lock_seats(self, show_id: str, seat_ids: List[str], user_id: Optional[str] = None) -> Tuple[str, datetime, List[Seat]]:
        """Lock seats for booking. Returns (lock_id, expires_at, locked_seats)."""
        if not self._client:
            raise ValueError("Database not configured")
        
        lock_id = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self._lock_ttl)
        now = datetime.now(timezone.utc)
        
        # Check if seats are available
        for seat_id in seat_ids:
            response = self._client.table("show_seats").select("*").eq("show_id", show_id).eq("seat_id", seat_id).single().execute()
            
            if not response.data:
                raise ValueError(f"Seat not found: {seat_id}")
            
            seat_data = response.data
            status = seat_data["status"]
            lock_expires = seat_data.get("lock_expires_at")
            
            # Check if seat is available or lock expired
            if status == "booked":
                raise ValueError(f"Seat already booked: {seat_id}")
            
            if status == "locked":
                if lock_expires:
                    lock_expires_dt = datetime.fromisoformat(lock_expires.replace("Z", "+00:00"))
                    if lock_expires_dt > now:
                        raise ValueError(f"Seat already locked: {seat_id}")
        
        # Lock all seats
        locked_seats = []
        for seat_id in seat_ids:
            self._client.table("show_seats").update({
                "status": "locked",
                "lock_expires_at": expires_at.isoformat()
            }).eq("show_id", show_id).eq("seat_id", seat_id).execute()
            
            # Get updated seat data
            response = self._client.table("show_seats").select("*").eq("show_id", show_id).eq("seat_id", seat_id).single().execute()
            row = response.data
            
            seat_id_parts = row["seat_id"].split("-")
            row_letter = seat_id_parts[1][0] if len(seat_id_parts) > 1 and seat_id_parts[1] else "A"
            seat_number = seat_id_parts[1][1:] if len(seat_id_parts) > 1 and len(seat_id_parts[1]) > 1 else "1"
            price = self._get_seat_price(show_id, row["section"])
            
            locked_seats.append(Seat(
                id=row["seat_id"],
                section=row["section"],
                row=row_letter,
                number=seat_number,
                status=SeatStatus.locked,
                price=price,
                lock_expires_at=expires_at
            ))
        
        # Store lock_id mapping (we'll use this for validation during booking)
        # Store in a simple way by updating the seats with a reference
        # In production, you'd have a separate locks table
        
        return lock_id, expires_at, locked_seats
    
    def book_seats(self, show_id: str, seat_ids: List[str], booking_id: str) -> List[Seat]:
        """Mark seats as booked."""
        if not self._client:
            raise ValueError("Database not configured")
        
        booked_seats = []
        
        for seat_id in seat_ids:
            self._client.table("show_seats").update({
                "status": "booked",
                "booking_id": booking_id,
                "lock_expires_at": None
            }).eq("show_id", show_id).eq("seat_id", seat_id).execute()
            
            response = self._client.table("show_seats").select("*").eq("show_id", show_id).eq("seat_id", seat_id).single().execute()
            row = response.data
            
            seat_id_parts = row["seat_id"].split("-")
            row_letter = seat_id_parts[1][0] if len(seat_id_parts) > 1 and seat_id_parts[1] else "A"
            seat_number = seat_id_parts[1][1:] if len(seat_id_parts) > 1 and len(seat_id_parts[1]) > 1 else "1"
            price = self._get_seat_price(show_id, row["section"])
            
            booked_seats.append(Seat(
                id=row["seat_id"],
                section=row["section"],
                row=row_letter,
                number=seat_number,
                status=SeatStatus.booked,
                price=price,
                booking_id=booking_id
            ))
        
        return booked_seats
    
    def release_seats(self, show_id: str, seat_ids: List[str]) -> None:
        """Release locked seats back to available."""
        if not self._client:
            return
        
        for seat_id in seat_ids:
            self._client.table("show_seats").update({
                "status": "available",
                "lock_expires_at": None,
                "booking_id": None
            }).eq("show_id", show_id).eq("seat_id", seat_id).execute()
