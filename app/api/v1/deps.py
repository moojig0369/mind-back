"""
API Dependencies - Dependency Injection Layer
Provides shared dependencies for API routes.
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from supabase import Client

from app.infrastructure.supabase_client import get_admin_client, get_user_client
from app.infrastructure.repositories.journal_repo import JournalRepository
from app.domains.journal.service import JournalService
from app.infrastructure.ai.client import LLMClient


# ── Database Dependencies ─────────────────────────────────────────────────────

def get_db() -> Generator[Client, None, None]:
    """Get Supabase admin client for database operations."""
    db = get_admin_client()
    try:
        yield db
    finally:
        pass  # Supabase client doesn't need explicit cleanup


# ── Authentication Dependencies ───────────────────────────────────────────────

async def get_current_user(
    authorization: str = Depends(lambda: None),
) -> dict:
    """
    Get current authenticated user from Supabase Auth.
    Expects: Authorization: Bearer <jwt_token>
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or invalid",
        )
    
    token = authorization.replace("Bearer ", "")
    
    try:
        supabase = get_user_client(token=token)
        user_response = supabase.auth.get_user()
        
        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        
        return {
            "id": str(user_response.user.id),
            "email": user_response.user.email,
            "role": "user",
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )


# ── Service Dependencies ──────────────────────────────────────────────────────

def get_journal_service() -> JournalService:
    """Get JournalService with repository and LLM client."""
    db = get_admin_client()
    repo = JournalRepository(db)
    llm_client = LLMClient()
    return JournalService(repo, llm_client)


def get_llm_client() -> LLMClient:
    """Get LLM client for AI operations."""
    return LLMClient()
