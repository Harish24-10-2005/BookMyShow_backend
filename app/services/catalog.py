from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from app.models.schemas import City, Movie, Show, Venue


class CatalogService:
    """In-memory catalog with seed data. Replace with Supabase-backed repo for production."""

    def __init__(self) -> None:
        now = datetime.utcnow()
        self.cities = [
            City(id="c_blr", name="Bengaluru", state="KA", country="IN"),
            City(id="c_mum", name="Mumbai", state="MH", country="IN"),
            City(id="c_del", name="Delhi", state="DL", country="IN"),
        ]
        self.movies = [
            Movie(
                id="m_1",
                title="Galactic Odyssey",
                description="An epic sci-fi adventure spanning multiple galaxies. Follow Captain Maya as she leads humanity's first interstellar mission.",
                language="English",
                genre="Sci-Fi",
                duration_min=132,
                poster_url="https://images.unsplash.com/photo-1462331940025-496dfbfc7564?w=400",
                rating=8.4,
            ),
            Movie(
                id="m_2",
                title="Monsoon Raga",
                description="A heartwarming musical drama set during the monsoon season in Mumbai. Love, music, and family come together.",
                language="Hindi",
                genre="Drama",
                duration_min=148,
                poster_url="https://images.unsplash.com/photo-1485846234645-a62644f84728?w=400",
                rating=7.8,
            ),
            Movie(
                id="m_3",
                title="The Last Heist",
                description="A retired thief is pulled back for one final job. Action-packed thriller with unexpected twists.",
                language="English",
                genre="Action",
                duration_min=125,
                poster_url="https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=400",
                rating=8.1,
            ),
            Movie(
                id="m_4",
                title="Laughing Matters",
                description="A stand-up comedian's journey from small-town clubs to nationwide fame. Hilarious and heartfelt.",
                language="English",
                genre="Comedy",
                duration_min=108,
                poster_url="https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=400",
                rating=7.2,
            ),
            Movie(
                id="m_5",
                title="Shadow Detective",
                description="A noir thriller following a detective solving a 30-year-old cold case that hits close to home.",
                language="Hindi",
                genre="Thriller",
                duration_min=140,
                poster_url="https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=400",
                rating=8.6,
            ),
        ]
        self.venues = [
            Venue(id="v_1", city_id="c_blr", name="Orion Mall Cinemas", address="Brigade Gateway, Rajajinagar"),
            Venue(id="v_2", city_id="c_blr", name="Phoenix Marketcity", address="Whitefield Main Road"),
            Venue(id="v_3", city_id="c_mum", name="PVR Icon", address="Andheri West"),
            Venue(id="v_4", city_id="c_mum", name="INOX Megaplex", address="Malad Infinity"),
            Venue(id="v_5", city_id="c_del", name="PVR Select City", address="Saket District Centre"),
        ]
        self.shows: List[Show] = []
        start_time = now + timedelta(hours=1)
        
        # Create multiple shows for each movie at different venues
        show_id = 1
        for movie in self.movies:
            for venue in self.venues[:3]:  # First 3 venues
                for hour_offset in [0, 3, 6]:  # Multiple showtimes
                    self.shows.append(
                        Show(
                            id=f"s_{show_id}",
                            movie_id=movie.id,
                            venue_id=venue.id,
                            screen_id=f"scr_{(show_id % 4) + 1}",
                            starts_at=start_time + timedelta(hours=hour_offset + (show_id % 5)),
                            ends_at=start_time + timedelta(hours=hour_offset + (show_id % 5) + 2),
                            base_price=200 + ((show_id % 4) * 50),
                            language=movie.language,
                            format="IMAX" if show_id % 3 == 0 else "2D",
                        )
                    )
                    show_id += 1

    def list_cities(self) -> List[City]:
        return self.cities

    def list_movies(self, city_id: str | None = None, q: str | None = None) -> List[Movie]:
        movies = self.movies
        if q:
            q_lower = q.lower()
            movies = [m for m in movies if q_lower in m.title.lower() or q_lower in m.genre.lower()]
        return movies

    def list_venues(self, city_id: str | None = None) -> List[Venue]:
        if city_id:
            return [v for v in self.venues if v.city_id == city_id]
        return self.venues

    def list_shows(self, movie_id: str | None = None, venue_id: str | None = None) -> List[Show]:
        shows = self.shows
        if movie_id:
            shows = [s for s in shows if s.movie_id == movie_id]
        if venue_id:
            shows = [s for s in shows if s.venue_id == venue_id]
        return shows

    def get_show(self, show_id: str) -> Show | None:
        return next((s for s in self.shows if s.id == show_id), None)

    def add_movie(self, movie: Movie) -> Movie:
        self.movies.append(movie)
        return movie

    def add_show(self, show: Show) -> Show:
        self.shows.append(show)
        return show
