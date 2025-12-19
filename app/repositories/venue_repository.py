from __future__ import annotations

from typing import List, Optional
from app.db import get_supabase_client
from app.models.schemas import Venue


class VenueRepository:
    """Repository for venue operations."""
    
    def __init__(self):
        self._client = get_supabase_client()
    
    def list_all(self, city_id: Optional[str] = None) -> List[Venue]:
        """Get all venues, optionally filtered by city."""
        if not self._client:
            return []
        
        query = self._client.table("venues").select("*")
        if city_id:
            query = query.eq("city_id", city_id)
        
        response = query.execute()
        return [Venue(
            id=str(row["id"]),
            city_id=str(row["city_id"]),
            name=row["name"],
            address=row.get("address", "")
        ) for row in response.data]
    
    def get_by_id(self, venue_id: str) -> Optional[Venue]:
        """Get venue by ID."""
        if not self._client:
            return None
        
        response = self._client.table("venues").select("*").eq("id", venue_id).single().execute()
        if response.data:
            row = response.data
            return Venue(
                id=str(row["id"]),
                city_id=str(row["city_id"]),
                name=row["name"],
                address=row.get("address", "")
            )
        return None
    
    def create(self, city_id: str, name: str, address: str) -> Venue:
        """Create a new venue."""
        if not self._client:
            raise ValueError("Database not configured")
        
        response = self._client.table("venues").insert({
            "city_id": city_id,
            "name": name,
            "address": address
        }).execute()
        
        row = response.data[0]
        return Venue(
            id=str(row["id"]),
            city_id=str(row["city_id"]),
            name=row["name"],
            address=row.get("address", "")
        )
