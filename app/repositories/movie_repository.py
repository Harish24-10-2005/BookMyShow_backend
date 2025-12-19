from __future__ import annotations

from typing import List, Optional
from app.db import get_supabase_client
from app.models.schemas import Movie, MovieCreate


class MovieRepository:
    """Repository for movie operations."""
    
    def __init__(self):
        self._client = get_supabase_client()
    
    def list_all(self, q: Optional[str] = None) -> List[Movie]:
        """Get all movies, optionally filtered by search query."""
        if not self._client:
            return []
        
        query = self._client.table("movies").select("*")
        
        response = query.execute()
        movies = []
        for row in response.data:
            # Filter by search query if provided
            if q and q.lower() not in row["title"].lower():
                continue
            movies.append(Movie(
                id=str(row["id"]),
                title=row["title"],
                description=row.get("description", ""),
                language=row.get("language", "English"),
                genre=row.get("genre", ""),
                duration_min=row.get("duration_min", 120),
                poster_url=row.get("poster_url"),
                rating=row.get("rating")
            ))
        return movies
    
    def get_by_id(self, movie_id: str) -> Optional[Movie]:
        """Get movie by ID."""
        if not self._client:
            return None
        
        response = self._client.table("movies").select("*").eq("id", movie_id).single().execute()
        if response.data:
            row = response.data
            return Movie(
                id=str(row["id"]),
                title=row["title"],
                description=row.get("description", ""),
                language=row.get("language", "English"),
                genre=row.get("genre", ""),
                duration_min=row.get("duration_min", 120),
                poster_url=row.get("poster_url"),
                rating=row.get("rating")
            )
        return None
    
    def create(self, movie: MovieCreate) -> Movie:
        """Create a new movie."""
        if not self._client:
            raise ValueError("Database not configured")
        
        response = self._client.table("movies").insert({
            "title": movie.title,
            "description": movie.description,
            "language": movie.language,
            "genre": movie.genre,
            "duration_min": movie.duration_min,
            "poster_url": movie.poster_url,
            "rating": movie.rating
        }).execute()
        
        row = response.data[0]
        return Movie(
            id=str(row["id"]),
            title=row["title"],
            description=row.get("description", ""),
            language=row.get("language", "English"),
            genre=row.get("genre", ""),
            duration_min=row.get("duration_min", 120),
            poster_url=row.get("poster_url"),
            rating=row.get("rating")
        )
