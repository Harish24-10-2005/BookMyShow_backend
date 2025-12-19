from __future__ import annotations

from typing import List, Optional
from app.db import get_supabase_client, is_supabase_enabled
from app.models.schemas import City


class CityRepository:
    """Repository for city operations."""
    
    def __init__(self):
        self._client = get_supabase_client()
    
    def list_all(self) -> List[City]:
        """Get all cities."""
        if not self._client:
            return []
        
        response = self._client.table("cities").select("*").execute()
        return [City(
            id=str(row["id"]),
            name=row["name"],
            state=row.get("state"),
            country=row.get("country")
        ) for row in response.data]
    
    def get_by_id(self, city_id: str) -> Optional[City]:
        """Get city by ID."""
        if not self._client:
            return None
        
        response = self._client.table("cities").select("*").eq("id", city_id).single().execute()
        if response.data:
            row = response.data
            return City(
                id=str(row["id"]),
                name=row["name"],
                state=row.get("state"),
                country=row.get("country")
            )
        return None
    
    def create(self, name: str, state: Optional[str] = None, country: Optional[str] = None) -> City:
        """Create a new city."""
        if not self._client:
            raise ValueError("Database not configured")
        
        response = self._client.table("cities").insert({
            "name": name,
            "state": state,
            "country": country
        }).execute()
        
        row = response.data[0]
        return City(
            id=str(row["id"]),
            name=row["name"],
            state=row.get("state"),
            country=row.get("country")
        )
