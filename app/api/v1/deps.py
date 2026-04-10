"""
API Dependencies - Dependency Injection Layer
Provides shared dependencies for API routes.
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from supabase import Client

from app.infrastructure.supabase_client import get_admin_client
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
