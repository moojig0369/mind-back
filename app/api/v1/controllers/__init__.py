"""API Controllers package."""

from app.api.v1.controllers.journal_controller import router as journal_router

__all__ = ["journal_router"]
