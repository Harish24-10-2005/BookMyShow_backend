from app.services.catalog import CatalogService
from app.services.seats import SeatService
from app.services.bookings import BookingService
from app.services.lock_manager import InMemoryLockManager
from app.repositories import (
    CityRepository,
    VenueRepository,
    MovieRepository,
    ShowRepository,
    SeatRepository,
    BookingRepository,
)
from app.config import get_settings
from app.db import is_supabase_enabled

settings = get_settings()

# Repositories
city_repo = CityRepository()
venue_repo = VenueRepository()
movie_repo = MovieRepository()
show_repo = ShowRepository()
seat_repo = SeatRepository(lock_ttl_seconds=settings.lock_ttl_seconds)
booking_repo = BookingRepository()

# In-memory Services
catalog_service = CatalogService()
lock_manager = InMemoryLockManager(ttl_seconds=settings.lock_ttl_seconds)
seat_service = SeatService()
booking_service = BookingService(lock_manager, seat_service)

# Seed seats for initial shows
if not is_supabase_enabled():
    for show in catalog_service.shows:
        seat_service.seed_show(show.id, show.base_price)
