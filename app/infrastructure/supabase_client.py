"""
Supabase client management.
Infrastructure layer for Supabase operations (PostgreSQL + Auth).
"""

from typing import Optional
from supabase import create_client, Client
from app.core.settings import get_settings


class SupabaseClient:
    """Supabase connection manager."""
    
    def __init__(self):
        self._admin_client: Optional[Client] = None
        self._anon_client: Optional[Client] = None
    
    def init(self, supabase_url: str, supabase_key: str, supabase_anon_key: str):
        """Initialize Supabase clients."""
        # Admin client (service role key) - for server-side operations
        self._admin_client = create_client(supabase_url, supabase_key)
        
        # Anon client (anon key) - for public/read-only operations
        self._anon_client = create_client(supabase_url, supabase_anon_key)
    
    @property
    def admin_client(self) -> Client:
        if self._admin_client is None:
            raise RuntimeError("Supabase admin client not initialized")
        return self._admin_client
    
    @property
    def anon_client(self) -> Client:
        if self._anon_client is None:
            raise RuntimeError("Supabase anon client not initialized")
        return self._anon_client


# Global Supabase instance
_supabase_client = SupabaseClient()


def get_admin_client() -> Client:
    """Get Supabase admin client (service role)."""
    return _supabase_client.admin_client


def get_anon_client() -> Client:
    """Get Supabase anon client."""
    return _supabase_client.anon_client


def get_user_client(token: str) -> Client:
    """Get Supabase client with user token for authenticated operations."""
    settings = get_settings()
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    # Set the user's auth token
    client.auth.set_session(token)
    return client


def init_supabase(supabase_url: str, supabase_key: str, supabase_anon_key: str):
    """Initialize Supabase connections from settings."""
    _supabase_client.init(supabase_url, supabase_key, supabase_anon_key)
