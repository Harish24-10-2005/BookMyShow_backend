from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List

from app.models.schemas import BookingHistoryItem, BookingRequest, BookingResponse, MockPaymentRequest, Seat
from app.services.lock_manager import InMemoryLockManager
from app.services.seats import SeatService
from app.models.entities import SeatStatus


class BookingService:
    def __init__(self, lock_manager: InMemoryLockManager, seat_service: SeatService) -> None:
        self.lock_manager = lock_manager
        self.seat_service = seat_service
        self._bookings: Dict[str, BookingResponse] = {}

    def lock_seats(self, show_id: str, seat_ids: List[str]) -> tuple[str, List[Seat], datetime]:
        seats = self.seat_service.list_seats(show_id)
        seat_map = {s.id: s for s in seats}
        missing = [s for s in seat_ids if s not in seat_map]
        if missing:
            raise ValueError(f"Seats not found: {missing}")
        lock_id, expires_at = self.lock_manager.lock(show_id, seat_ids)
        # Return copies marked as locked so caller sees locked state without mutating store
        locked_seats = [Seat(**{**seat_map[s].model_dump(), "status": SeatStatus.locked}) for s in seat_ids]
        return lock_id, locked_seats, expires_at

    def create_booking(self, payload: BookingRequest) -> BookingResponse:
        show_id = payload.show_id
        seats = self.seat_service.list_seats(show_id)
        seat_map = {s.id: s for s in seats}
        for seat_id in payload.seats:
            if not self.lock_manager.is_locked(show_id, seat_id, payload.lock_id):
                raise ValueError(f"Seat not locked by this request: {seat_id}")
            if seat_map[seat_id].status == "booked":
                raise ValueError(f"Seat already booked: {seat_id}")
        total_amount = sum(seat_map[s].price for s in payload.seats)
        booking_id = str(uuid.uuid4())
        response = BookingResponse(
            show_id=show_id,
            booking_id=booking_id,
            status="pending",
            total_amount=total_amount,
            seats=[seat_map[s] for s in payload.seats],
        )
        self._bookings[booking_id] = response
        return response

    def mock_payment(self, request: MockPaymentRequest) -> BookingResponse:
        booking = self._bookings.get(request.booking_id)
        if not booking:
            raise ValueError("Booking not found")
        if request.outcome == "success":
            booking.status = "confirmed"
            self.seat_service.mark_booked(booking.show_id, [s.id for s in booking.seats])
            # Release any lock linked to these seats (best-effort)
            for lock_id, meta in list(self.lock_manager._lock_id_to_meta.items()):
                if meta["show_id"] == booking.show_id and all(seat_id in meta["seats"] for seat_id in [s.id for s in booking.seats]):
                    self.lock_manager.release_by_lock_id(lock_id)
        else:
            booking.status = "failed"
            self.seat_service.release(booking.show_id, [s.id for s in booking.seats])
        return booking

    def booking_history(self, user_id: str | None = None) -> List[BookingHistoryItem]:
        history: List[BookingHistoryItem] = []
        for booking in self._bookings.values():
            history.append(
                BookingHistoryItem(
                    booking_id=booking.booking_id,
                    show_id=booking.show_id,
                    status=booking.status,
                    total_amount=booking.total_amount,
                    created_at=datetime.utcnow(),
                    seats=[s.id for s in booking.seats],
                )
            )
        return history
