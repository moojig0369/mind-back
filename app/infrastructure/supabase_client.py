"""
Supabase client management.
Infrastructure layer for Supabase operations (PostgreSQL).
Demo mode - no authentication required.
"""

from typing import Optional
from supabase import create_client, Client
from app.core.settings import get_settings


class SupabaseClient:
    """Supabase connection manager."""
    
    def __init__(self):
        self._admin_client: Optional[Client] = None
    
    def init(self, supabase_url: str, supabase_key: str, supabase_anon_key: str):
        """Initialize Supabase clients."""
        # Admin client (service role key) - for server-side operations
        self._admin_client = create_client(supabase_url, supabase_key)
    
    @property
    def admin_client(self) -> Client:
        if self._admin_client is None:
            raise RuntimeError("Supabase admin client not initialized")
        return self._admin_client


# Global Supabase instance
_supabase_client = SupabaseClient()


def get_admin_client() -> Client:
    """Get Supabase admin client (service role)."""
    return _supabase_client.admin_client


def init_supabase(supabase_url: str, supabase_key: str, supabase_anon_key: str):
    """Initialize Supabase connections from settings."""
    _supabase_client.init(supabase_url, supabase_key, supabase_anon_key)
