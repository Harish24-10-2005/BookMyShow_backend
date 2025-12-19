from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class SeatStatus(str, Enum):
    available = "available"
    locked = "locked"
    booked = "booked"


@dataclass
class Seat:
    id: str
    section: str
    row: str
    number: str
    status: SeatStatus
    price: float
    lock_expires_at: Optional[datetime] = None
    booking_id: Optional[str] = None


@dataclass
class Show:
    id: str
    movie_id: str
    venue_id: str
    screen_id: str
    starts_at: datetime
    ends_at: datetime
    base_price: float
    language: str
    format: str


@dataclass
class Booking:
    id: str
    user_id: str
    show_id: str
    status: str
    total_amount: float
    created_at: datetime


@dataclass
class BookingItem:
    id: str
    booking_id: str
    seat_id: str
    price: float
