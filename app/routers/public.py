from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from typing import Optional

from app.models.schemas import (
    BookingRequest,
    BookingResponse,
    City,
    HealthResponse,
    LockSeatsRequest,
    LockSeatsResponse,
    MockPaymentRequest,
    Movie,
    Show,
    ShowSeatsResponse,
    Venue,
    BookingHistoryItem,
)
from app.db import is_supabase_enabled, get_supabase_client
from app.services.lock_manager import apply_lock_state_to_seats
from app.config import get_settings
from app.dependencies import (
    city_repo, venue_repo, movie_repo, show_repo, seat_repo, booking_repo,
    catalog_service, lock_manager, seat_service, booking_service
)

router = APIRouter()

# Settings
settings = get_settings()


def _is_connectivity_error(exc: Exception) -> bool:
    """Return True when request failed because Supabase was unreachable."""
    if isinstance(exc, httpx.ConnectError):
        return True
    return "Device or resource busy" in str(exc)


def get_user_id_from_token(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Extract user ID from JWT token."""
    if not authorization:
        return None
    
    if authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        
        # Try to get user from Supabase
        client = get_supabase_client()
        if client:
            try:
                user_response = client.auth.get_user(token)
                if user_response and user_response.user:
                    return user_response.user.id
            except Exception as e:
                print(f"Error verifying token: {e}")
                pass
                
        # If we can't verify, return None rather than "anonymous" which breaks UUID validation
        return None
    return None


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok", 
        service="bookmyshow-backend",
    )


@router.get("/cities", response_model=list[City])
def list_cities() -> list[City]:
    if is_supabase_enabled():
        try:
            return city_repo.list_all()
        except Exception as exc:
            if not _is_connectivity_error(exc):
                raise
            print(f"Supabase unavailable for /cities, falling back to in-memory catalog: {exc}")
    return catalog_service.list_cities()


@router.get("/movies", response_model=list[Movie])
def list_movies(city_id: str | None = Query(None), q: str | None = Query(None)) -> list[Movie]:
    if is_supabase_enabled():
        try:
            return movie_repo.list_all(q=q)
        except Exception as exc:
            if not _is_connectivity_error(exc):
                raise
            print(f"Supabase unavailable for /movies, falling back to in-memory catalog: {exc}")
    return catalog_service.list_movies(city_id=city_id, q=q)


@router.get("/venues", response_model=list[Venue])
def list_venues(city_id: str | None = Query(None)) -> list[Venue]:
    if is_supabase_enabled():
        try:
            return venue_repo.list_all(city_id=city_id)
        except Exception as exc:
            if not _is_connectivity_error(exc):
                raise
            print(f"Supabase unavailable for /venues, falling back to in-memory catalog: {exc}")
    return catalog_service.list_venues(city_id=city_id)


@router.get("/shows", response_model=list[Show])
def list_shows(movie_id: str | None = Query(None), venue_id: str | None = Query(None)) -> list[Show]:
    if is_supabase_enabled():
        try:
            return show_repo.list_all(movie_id=movie_id, venue_id=venue_id)
        except Exception as exc:
            if not _is_connectivity_error(exc):
                raise
            print(f"Supabase unavailable for /shows, falling back to in-memory catalog: {exc}")
    return catalog_service.list_shows(movie_id=movie_id, venue_id=venue_id)


@router.get("/shows/{show_id}/seats", response_model=ShowSeatsResponse)
def get_seats(show_id: str) -> ShowSeatsResponse:
    if is_supabase_enabled():
        seats = seat_repo.get_seats_for_show(show_id)
        if not seats:
            raise HTTPException(status_code=404, detail="Show not found or no seats available")
        return ShowSeatsResponse(show_id=show_id, seats=seats)
    
    # Fallback to in-memory
    lock_manager.purge_expired()
    seats = seat_service.list_seats(show_id)
    if seats == []:
        raise HTTPException(status_code=404, detail="Show not found")
    seats_with_locks = apply_lock_state_to_seats(show_id, seats, lock_manager)
    return ShowSeatsResponse(show_id=show_id, seats=seats_with_locks)


@router.post("/shows/{show_id}/lock", response_model=LockSeatsResponse)
def lock_seats(
    show_id: str, 
    payload: LockSeatsRequest,
    authorization: Optional[str] = Header(None)
) -> LockSeatsResponse:
    user_id = get_user_id_from_token(authorization)
    
    if is_supabase_enabled():
        try:
            lock_id, expires_at, locked_seats = seat_repo.lock_seats(show_id, payload.seats, user_id)
            return LockSeatsResponse(lock_id=lock_id, expires_at=expires_at, seats=locked_seats)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    
    # Fallback to in-memory
    try:
        lock_id, locked_seats, expires_at = booking_service.lock_seats(show_id, payload.seats)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return LockSeatsResponse(lock_id=lock_id, expires_at=expires_at, seats=locked_seats)


@router.post("/bookings", response_model=BookingResponse)
def create_booking(
    payload: BookingRequest,
    authorization: Optional[str] = Header(None)
) -> BookingResponse:
    user_id = get_user_id_from_token(authorization)
    
    if is_supabase_enabled():
        try:
            # Get seat prices
            seats = seat_repo.get_seats_for_show(payload.show_id)
            seat_map = {s.id: s for s in seats}
            
            # Validate seats are locked
            selected_seats = []
            for seat_id in payload.seats:
                if seat_id not in seat_map:
                    raise ValueError(f"Seat not found: {seat_id}")
                seat = seat_map[seat_id]
                if seat.status.value == "booked":
                    raise ValueError(f"Seat already booked: {seat_id}")
                selected_seats.append(seat)
            
            total_amount = sum(s.price for s in selected_seats)
            
            # Create booking
            booking = booking_repo.create_booking(
                user_id=user_id,
                show_id=payload.show_id,
                seats=selected_seats,
                total_amount=total_amount,
                status="pending"
            )
            
            return booking
            
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    
    # Fallback to in-memory
    try:
        booking = booking_service.create_booking(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return booking


@router.post("/payments/mock", response_model=BookingResponse)
def mock_payment(
    payload: MockPaymentRequest,
    authorization: Optional[str] = Header(None)
) -> BookingResponse:
    if is_supabase_enabled():
        try:
            # Get booking
            booking = booking_repo.get_booking(payload.booking_id)
            if not booking:
                raise ValueError("Booking not found")
            
            if payload.outcome == "success":
                # Mark seats as booked
                seat_ids = [s.id for s in booking.seats]
                seat_repo.book_seats(booking.show_id, seat_ids, payload.booking_id)
                
                # Update booking status
                booking = booking_repo.update_status(payload.booking_id, "confirmed")
                
                # Create payment record
                booking_repo.create_payment(
                    booking_id=payload.booking_id,
                    amount=booking.total_amount,
                    status="success",
                    provider="mock"
                )
            else:
                # Payment failed - release seats
                seat_ids = [s.id for s in booking.seats]
                seat_repo.release_seats(booking.show_id, seat_ids)
                
                # Update booking status
                booking = booking_repo.update_status(payload.booking_id, "failed")
                
                # Create failed payment record
                booking_repo.create_payment(
                    booking_id=payload.booking_id,
                    amount=booking.total_amount,
                    status="failed",
                    provider="mock"
                )
            
            return booking
            
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    
    # Fallback to in-memory
    try:
        return booking_service.mock_payment(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/bookings/history", response_model=list[BookingHistoryItem])
def history(authorization: Optional[str] = Header(None)) -> list[BookingHistoryItem]:
    user_id = get_user_id_from_token(authorization)
    
    if is_supabase_enabled():
        return booking_repo.get_user_bookings(user_id)
    
    # Fallback to in-memory - return all bookings for demo
    return booking_service.booking_history()
