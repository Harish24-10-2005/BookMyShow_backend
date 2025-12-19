from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Header, Depends

from app.models.schemas import Movie, MovieCreate, City, Venue, Show, ShowCreate
from app.db import is_supabase_enabled, get_supabase_client
from app.dependencies import movie_repo, show_repo, catalog_service, seat_service
from app.config import get_settings

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if settings.admin_api_key:
        if not x_admin_key or x_admin_key != settings.admin_api_key:
            raise HTTPException(status_code=401, detail="Invalid admin key")


@router.post("/movies", response_model=Movie)
def add_movie(payload: MovieCreate, _: None = Depends(require_admin)) -> Movie:
    if not payload.title:
        raise HTTPException(status_code=400, detail="Title is required")
    
    if is_supabase_enabled():
        try:
            return movie_repo.create(payload)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create movie: {str(e)}")
    
    # Fallback to in-memory
    movie = Movie(
        id=f"m_{uuid.uuid4().hex[:8]}",
        title=payload.title,
        description=payload.description or "",
        language=payload.language,
        genre=payload.genre,
        duration_min=payload.duration_min,
        poster_url=payload.poster_url,
        rating=payload.rating,
    )
    return catalog_service.add_movie(movie)


@router.post("/shows", response_model=Show)
def add_show(payload: ShowCreate, _: None = Depends(require_admin)) -> Show:
    # Calculate ends_at
    duration_min = 120
    if is_supabase_enabled():
        movie = movie_repo.get_by_id(payload.movie_id)
        if movie:
            duration_min = movie.duration_min
            
        # Resolve screen_id if it's a placeholder or we need to find one for the venue
        client = get_supabase_client()
        # Check if screen_id exists or is valid
        # If payload.screen_id is "Screen 1" (default), try to find a screen for the venue
        if payload.screen_id == "Screen 1":
             resp = client.table("screens").select("id").eq("venue_id", payload.venue_id).limit(1).execute()
             if resp.data:
                 payload.screen_id = resp.data[0]["id"]
             else:
                 # Create a screen if none exists? Or fail?
                 # Let's create one for simplicity or fail
                 raise HTTPException(status_code=400, detail="No screens found for this venue")
        
    else:
        movies = catalog_service.list_movies()
        movie = next((m for m in movies if m.id == payload.movie_id), None)
        if movie:
            duration_min = movie.duration_min
            
    ends_at = payload.starts_at + timedelta(minutes=duration_min)
    
    if is_supabase_enabled():
        try:
            return show_repo.create(
                movie_id=payload.movie_id,
                screen_id=payload.screen_id,
                starts_at=payload.starts_at,
                ends_at=ends_at,
                base_price=payload.base_price,
                language=payload.language,
                format=payload.format
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create show: {str(e)}")
            
    # Fallback to in-memory
    show = Show(
        id=f"s_{uuid.uuid4().hex[:8]}",
        movie_id=payload.movie_id,
        venue_id=payload.venue_id,
        screen_id=payload.screen_id,
        starts_at=payload.starts_at,
        ends_at=ends_at,
        base_price=payload.base_price,
        language=payload.language,
        format=payload.format,
    )
    catalog_service.add_show(show)
    seat_service.seed_show(show.id, show.base_price)
    return show


@router.post("/seed")
def seed_database(_: None = Depends(require_admin), force: bool = False) -> dict:
    """Seed the database with initial test data."""
    if not is_supabase_enabled():
        return {"status": "skipped", "message": "Supabase not enabled, using in-memory data"}
    
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=500, detail="Database not available")
    
    try:
        # Check if data already exists
        existing_movies = client.table("movies").select("id").limit(1).execute()
        if existing_movies.data and not force:
            return {"status": "skipped", "message": "Database already has movies"}
        
        # If force, delete existing data
        if force:
            client.table("bookings").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            client.table("show_seats").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            client.table("shows").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            client.table("screens").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            client.table("movies").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            client.table("venues").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            client.table("cities").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        
        # Seed cities
        cities = [
            {"id": str(uuid.uuid4()), "name": "Bengaluru", "state": "KA", "country": "IN"},
            {"id": str(uuid.uuid4()), "name": "Mumbai", "state": "MH", "country": "IN"},
            {"id": str(uuid.uuid4()), "name": "Delhi", "state": "DL", "country": "IN"},
        ]
        client.table("cities").insert(cities).execute()
        
        # Seed venues (linked to cities)
        venues = [
            {"id": str(uuid.uuid4()), "city_id": cities[0]["id"], "name": "Orion Mall Cinemas", "address": "Brigade Gateway, Rajajinagar"},
            {"id": str(uuid.uuid4()), "city_id": cities[0]["id"], "name": "Phoenix Marketcity", "address": "Whitefield Main Road"},
            {"id": str(uuid.uuid4()), "city_id": cities[1]["id"], "name": "PVR Icon", "address": "Andheri West"},
            {"id": str(uuid.uuid4()), "city_id": cities[1]["id"], "name": "INOX Megaplex", "address": "Malad Infinity"},
            {"id": str(uuid.uuid4()), "city_id": cities[2]["id"], "name": "PVR Select City", "address": "Saket District Centre"},
        ]
        client.table("venues").insert(venues).execute()
        
        # Seed screens (linked to venues)
        screens = []
        for venue in venues:
            for i in range(1, 4):  # 3 screens per venue
                screens.append({
                    "id": str(uuid.uuid4()),
                    "venue_id": venue["id"],
                    "name": f"Screen {i}",
                })
        client.table("screens").insert(screens).execute()
        
        # Seed movies
        movies = [
            {
                "id": str(uuid.uuid4()),
                "title": "Galactic Odyssey",
                "description": "An epic sci-fi adventure spanning multiple galaxies.",
                "language": "English",
                "genre": "Sci-Fi",
                "duration_min": 132,
                "poster_url": "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?w=400",
                "rating": 8.4,
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Monsoon Raga",
                "description": "A heartwarming musical drama set during the monsoon season.",
                "language": "Hindi",
                "genre": "Drama",
                "duration_min": 148,
                "poster_url": "https://images.unsplash.com/photo-1485846234645-a62644f84728?w=400",
                "rating": 7.8,
            },
            {
                "id": str(uuid.uuid4()),
                "title": "The Last Heist",
                "description": "A retired thief is pulled back for one final job.",
                "language": "English",
                "genre": "Action",
                "duration_min": 125,
                "poster_url": "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=400",
                "rating": 8.1,
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Laughing Matters",
                "description": "A stand-up comedian's journey from small-town clubs to fame.",
                "language": "English",
                "genre": "Comedy",
                "duration_min": 108,
                "poster_url": "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=400",
                "rating": 7.2,
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Shadow Detective",
                "description": "A noir thriller following a detective solving a cold case.",
                "language": "Hindi",
                "genre": "Thriller",
                "duration_min": 140,
                "poster_url": "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=400",
                "rating": 8.6,
            },
        ]
        client.table("movies").insert(movies).execute()
        
        # Seed shows (linking movies to screens with different times)
        now = datetime.utcnow()
        shows = []
        show_times = [1, 4, 7, 10]  # Hours from now
        formats = ["2D", "3D", "IMAX"]
        
        for movie in movies:
            for screen in screens[:6]:  # Use first 6 screens
                for i, hour_offset in enumerate(show_times[:2]):  # 2 shows per movie per screen
                    starts_at = now + timedelta(hours=hour_offset + (len(shows) % 3))
                    shows.append({
                        "id": str(uuid.uuid4()),
                        "movie_id": movie["id"],
                        "screen_id": screen["id"],
                        "starts_at": starts_at.isoformat(),
                        "ends_at": (starts_at + timedelta(minutes=movie["duration_min"])).isoformat(),
                        "base_price": 200 + (i * 50),
                        "language": movie["language"],
                        "format": formats[len(shows) % 3]
                    })
        
        client.table("shows").insert(shows).execute()
        
        return {
            "status": "success",
            "message": "Database seeded successfully",
            "counts": {
                "cities": len(cities),
                "venues": len(venues),
                "screens": len(screens),
                "movies": len(movies),
                "shows": len(shows)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to seed database: {str(e)}")
