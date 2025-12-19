from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from app.db import get_supabase_client
from app.models.schemas import Show


class ShowRepository:
    """Repository for show operations."""
    
    def __init__(self):
        self._client = get_supabase_client()
    
    def list_all(self, movie_id: Optional[str] = None, venue_id: Optional[str] = None) -> List[Show]:
        """Get all shows, optionally filtered by movie or venue."""
        if not self._client:
            return []
        
        # Join with screens to get venue_id
        query = self._client.table("shows").select("*, screens!inner(venue_id)")
        
        if movie_id:
            query = query.eq("movie_id", movie_id)
        
        response = query.execute()
        shows = []
        
        for row in response.data:
            screen_data = row.get("screens", {})
            row_venue_id = screen_data.get("venue_id") if screen_data else None
            
            # Filter by venue_id if provided
            if venue_id and str(row_venue_id) != venue_id:
                continue
            
            shows.append(Show(
                id=str(row["id"]),
                movie_id=str(row["movie_id"]),
                venue_id=str(row_venue_id) if row_venue_id else "",
                screen_id=str(row["screen_id"]),
                starts_at=datetime.fromisoformat(row["starts_at"].replace("Z", "+00:00")),
                ends_at=datetime.fromisoformat(row["ends_at"].replace("Z", "+00:00")),
                base_price=float(row["base_price"]),
                language=row.get("language", ""),
                format=row.get("format", "2D")
            ))
        
        return shows
    
    def get_by_id(self, show_id: str) -> Optional[Show]:
        """Get show by ID."""
        if not self._client:
            return None
        
        response = self._client.table("shows").select("*, screens!inner(venue_id)").eq("id", show_id).single().execute()
        if response.data:
            row = response.data
            screen_data = row.get("screens", {})
            venue_id = screen_data.get("venue_id") if screen_data else None
            
            return Show(
                id=str(row["id"]),
                movie_id=str(row["movie_id"]),
                venue_id=str(venue_id) if venue_id else "",
                screen_id=str(row["screen_id"]),
                starts_at=datetime.fromisoformat(row["starts_at"].replace("Z", "+00:00")),
                ends_at=datetime.fromisoformat(row["ends_at"].replace("Z", "+00:00")),
                base_price=float(row["base_price"]),
                language=row.get("language", ""),
                format=row.get("format", "2D")
            )
        return None
    
    def create(self, movie_id: str, screen_id: str, starts_at: datetime, 
               ends_at: datetime, base_price: float, language: str = "", format: str = "2D") -> Show:
        """Create a new show."""
        if not self._client:
            raise ValueError("Database not configured")
        
        response = self._client.table("shows").insert({
            "movie_id": movie_id,
            "screen_id": screen_id,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "base_price": base_price,
            "language": language,
            "format": format
        }).execute()
        
        row = response.data[0]
        
        # Get venue_id from screen
        screen_resp = self._client.table("screens").select("venue_id").eq("id", screen_id).single().execute()
        venue_id = screen_resp.data.get("venue_id") if screen_resp.data else ""
        
        return Show(
            id=str(row["id"]),
            movie_id=str(row["movie_id"]),
            venue_id=str(venue_id),
            screen_id=str(row["screen_id"]),
            starts_at=datetime.fromisoformat(row["starts_at"].replace("Z", "+00:00")),
            ends_at=datetime.fromisoformat(row["ends_at"].replace("Z", "+00:00")),
            base_price=float(row["base_price"]),
            language=row.get("language", ""),
            format=row.get("format", "2D")
        )
