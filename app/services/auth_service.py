"""
AuthService — Supabase JWT токен баталгаажуулалт.
FastAPI Depends()-д ашиглагдана.
"""

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.settings import get_settings
from app.db.supabase import get_admin_client

_settings = get_settings()
_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """
    Supabase /auth/v1/user endpoint-д токенийг шалгана.
    Буцаах утга: {"id": str, "email": str, "role": str}
    """
    token = credentials.credentials
    user_data = await _fetch_supabase_user(token)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Нэвтрэлт хүчингүй байна",
        )

    return {
        "id": user_data["id"],
        "email": user_data["email"],
        "role": user_data.get("role", "authenticated"),
    }


async def get_admin_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Admin эрх шалгана."""
    supabase = get_admin_client()
    result = (
        supabase.table("users")
        .select("id")
        .eq("id", current_user["id"])
        .eq("role", "admin")
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin эрх шаардлагатай",
        )
    return current_user


async def _fetch_supabase_user(token: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{_settings.supabase_url}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": _settings.supabase_anon_key,
            },
        )
    if response.status_code != 200:
        return None
    return response.json()
