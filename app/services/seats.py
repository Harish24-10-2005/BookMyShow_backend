from __future__ import annotations

from typing import Dict, List

from app.models.entities import SeatStatus
from app.models.schemas import Seat


class SeatService:
    """Provides seat layout and status mutations in-memory."""

    def __init__(self) -> None:
        self._seats_by_show: Dict[str, Dict[str, Seat]] = {}

    def seed_show(self, show_id: str, base_price: float) -> None:
        if show_id in self._seats_by_show:
            return
        seat_map: Dict[str, Seat] = {}
        sections = [
            ("gold", 1.0),
            ("silver", 0.8),
            ("bronze", 0.6),
        ]
        for section, multiplier in sections:
            for row_idx in range(1, 5):
                row_label = chr(ord("A") + row_idx - 1)
                for seat_num in range(1, 11):
                    seat_id = f"{section}-{row_label}{seat_num}"
                    seat_map[seat_id] = Seat(
                        id=seat_id,
                        section=section,
                        row=row_label,
                        number=str(seat_num),
                        status=SeatStatus.available,
                        price=round(base_price * multiplier, 2),
                    )
        self._seats_by_show[show_id] = seat_map

    def list_seats(self, show_id: str) -> List[Seat]:
        seat_map = self._seats_by_show.get(show_id)
        if not seat_map:
            return []
        return list(seat_map.values())

    def mark_locked(self, show_id: str, seat_ids: List[str]) -> List[Seat]:
        seat_map = self._seats_by_show[show_id]
        updated = []
        for seat_id in seat_ids:
            seat = seat_map[seat_id]
            if seat.status != SeatStatus.available:
                raise ValueError(f"Seat not available: {seat_id}")
            seat.status = SeatStatus.locked
            updated.append(seat)
        return updated

    def mark_booked(self, show_id: str, seat_ids: List[str]) -> None:
        seat_map = self._seats_by_show[show_id]
        for seat_id in seat_ids:
            seat = seat_map[seat_id]
            if seat.status == SeatStatus.booked:
                raise ValueError(f"Seat already booked: {seat_id}")
            seat.status = SeatStatus.booked

    def release(self, show_id: str, seat_ids: List[str]) -> None:
        seat_map = self._seats_by_show.get(show_id, {})
        for seat_id in seat_ids:
            seat = seat_map.get(seat_id)
            if seat:
                seat.status = SeatStatus.available
