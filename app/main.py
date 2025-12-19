from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import public, admin
from app.db import is_supabase_enabled, get_supabase_client

settings = get_settings()


def seed_database_if_empty():
    """Seed the Supabase database with initial data if empty."""
    if not is_supabase_enabled():
        print("Supabase not enabled, skipping database seeding")
        return
    
    client = get_supabase_client()
    if not client:
        return
    
    try:
        existing_movies = client.table("movies").select("id").limit(1).execute()
        if existing_movies.data:
            print("Database already has movies, skipping seeding")
            return
        
        print("Seeding database with initial data...")
        
        # Seed cities
        cities = [
            {"id": str(uuid.uuid4()), "name": "Bengaluru", "state": "KA", "country": "IN"},
            {"id": str(uuid.uuid4()), "name": "Mumbai", "state": "MH", "country": "IN"},
            {"id": str(uuid.uuid4()), "name": "Delhi", "state": "DL", "country": "IN"},
        ]
        client.table("cities").insert(cities).execute()
        
        # Seed venues
        venues = [
            {"id": str(uuid.uuid4()), "city_id": cities[0]["id"], "name": "Orion Mall Cinemas", "address": "Brigade Gateway, Rajajinagar"},
            {"id": str(uuid.uuid4()), "city_id": cities[0]["id"], "name": "Phoenix Marketcity", "address": "Whitefield Main Road"},
            {"id": str(uuid.uuid4()), "city_id": cities[1]["id"], "name": "PVR Icon", "address": "Andheri West"},
            {"id": str(uuid.uuid4()), "city_id": cities[1]["id"], "name": "INOX Megaplex", "address": "Malad Infinity"},
            {"id": str(uuid.uuid4()), "city_id": cities[2]["id"], "name": "PVR Select City", "address": "Saket District Centre"},
        ]
        client.table("venues").insert(venues).execute()
        
        screens = []
        for venue in venues:
            for i in range(1, 4):
                screens.append({
                    "id": str(uuid.uuid4()),
                    "venue_id": venue["id"],
                    "name": f"Screen {i}",
                })
        client.table("screens").insert(screens).execute()
        
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
                "description": "A stand-up comedian's journey to nationwide fame.",
                "language": "English",
                "genre": "Comedy",
                "duration_min": 108,
                "poster_url": "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=400",
                "rating": 7.2,
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Shadow Detective",
                "description": "A noir thriller solving a 30-year-old cold case.",
                "language": "Hindi",
                "genre": "Thriller",
                "duration_min": 140,
                "poster_url": "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=400",
                "rating": 8.6,
            },
        ]
        client.table("movies").insert(movies).execute()
        
        # Seed shows
        now = datetime.utcnow()
        shows = []
        formats = ["2D", "3D", "IMAX"]
        
        for movie in movies:
            for screen in screens[:6]:
                for hour_offset in [1, 4]:
                    starts_at = now + timedelta(hours=hour_offset + (len(shows) % 5))
                    shows.append({
                        "id": str(uuid.uuid4()),
                        "movie_id": movie["id"],
                        "screen_id": screen["id"],
                        "starts_at": starts_at.isoformat(),
                        "ends_at": (starts_at + timedelta(minutes=movie["duration_min"])).isoformat(),
                        "base_price": 200 + ((len(shows) % 4) * 50),
                        "language": movie["language"],
                        "format": formats[len(shows) % 3]
                    })
        
        client.table("shows").insert(shows).execute()
        
        print(f"Database seeded: {len(cities)} cities, {len(venues)} venues, {len(screens)} screens, {len(movies)} movies, {len(shows)} shows")
        
    except Exception as e:
        print(f"Warning: Failed to seed database: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed database if empty
    seed_database_if_empty()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://.*",  # Allow all http/https origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public.router)
app.include_router(admin.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "BookMyShow backend running"}
