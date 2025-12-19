from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from .entities import SeatStatus


class City(BaseModel):
    id: str
    name: str
    state: str | None = None
    country: str | None = None


class Movie(BaseModel):
    id: str
    title: str
    description: str
    language: str
    genre: str
    duration_min: int
    poster_url: str | None = None
    rating: float | None = None


class MovieCreate(BaseModel):
    title: str
    description: str | None = None
    language: str = "English"
    genre: str = "Drama"
    duration_min: int = 120
    poster_url: str | None = None
    rating: float | None = None


class Venue(BaseModel):
    id: str
    city_id: str
    name: str
    address: str


class Show(BaseModel):
    id: str
    movie_id: str
    venue_id: str
    screen_id: str
    starts_at: datetime
    ends_at: datetime
    base_price: float
    language: str
    format: str


class ShowCreate(BaseModel):
    movie_id: str
    venue_id: str
    screen_id: str = "Screen 1"
    starts_at: datetime
    base_price: float = 250.0
    language: str = "English"
    format: str = "2D"


class Seat(BaseModel):
    id: str
    section: str
    row: str
    number: str
    status: SeatStatus
    price: float
    lock_expires_at: Optional[datetime] = None
    booking_id: Optional[str] = None


class ShowSeatsResponse(BaseModel):
    show_id: str
    seats: List[Seat]


class LockSeatsRequest(BaseModel):
    seats: List[str] = Field(..., description="Seat IDs to lock")


class LockSeatsResponse(BaseModel):
    lock_id: str
    expires_at: datetime
    seats: List[Seat]


class BookingRequest(BaseModel):
    show_id: str
    seats: List[str]
    lock_id: str


class BookingResponse(BaseModel):
    show_id: str
    booking_id: str
    status: str
    total_amount: float
    seats: List[Seat]


class MockPaymentRequest(BaseModel):
    booking_id: str
    outcome: str = Field("success", pattern="^(success|fail)$")


class BookingHistoryItem(BaseModel):
    booking_id: str
    show_id: str
    status: str
    total_amount: float
    created_at: datetime
    seats: List[str]


class HealthResponse(BaseModel):
    status: str
    service: str
