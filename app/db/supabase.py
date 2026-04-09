"""
Supabase client factory.
- anon_client  : RLS дагасан хэрэглэгчийн хүсэлт
- admin_client : service role (worker, admin)
"""

from functools import lru_cache
from supabase import create_client, Client
from app.core.settings import get_settings

_settings = get_settings()


@lru_cache()
def get_anon_client() -> Client:
    return create_client(
        _settings.supabase_url,
        _settings.supabase_anon_key,
    )


@lru_cache()
def get_admin_client() -> Client:
    return create_client(
        _settings.supabase_url,
        _settings.supabase_service_role_key,
    )
