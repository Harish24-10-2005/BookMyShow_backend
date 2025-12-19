from __future__ import annotations

from typing import Optional
from supabase import create_client, Client
from app.config import get_settings

_client: Optional[Client] = None
_client_initialized: bool = False
_supabase_enabled: Optional[bool] = None


def get_supabase_client() -> Optional[Client]:
    """Get Supabase client singleton."""
    global _client, _client_initialized
    
    if _client_initialized:
        return _client
    
    settings = get_settings()
    
    # Check if properly configured (not placeholder values)
    if not settings.supabase_url:
        print("Warning: Supabase URL not configured. Using in-memory storage.")
        _client_initialized = True
        return None
    
    # Require service_role key for backend operations (bypasses RLS)
    if not settings.supabase_service_role_key or settings.supabase_service_role_key == "service_role" or len(settings.supabase_service_role_key) < 50:
        print("Warning: Supabase service_role key not configured. Using in-memory storage.")
        print("To use Supabase:")
        print("  1. Go to Supabase Dashboard > Project Settings > API")
        print("  2. Copy the 'service_role' key (NOT the anon key)")
        print("  3. Set BMS_SUPABASE_SERVICE_ROLE_KEY in backend/.env")
        _client_initialized = True
        return None
    
    try:
        _client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
        print(f"Supabase client initialized successfully for {settings.supabase_url}")
        _client_initialized = True
        return _client
    except Exception as e:
        print(f"Warning: Failed to initialize Supabase client: {e}. Using in-memory storage.")
        _client_initialized = True
        return None


def is_supabase_enabled() -> bool:
    """Check if Supabase is configured and working."""
    global _supabase_enabled
    
    if _supabase_enabled is not None:
        return _supabase_enabled
    
    _supabase_enabled = get_supabase_client() is not None
    return _supabase_enabled
