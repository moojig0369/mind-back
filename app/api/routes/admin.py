"""
/api/admin — хэрэглэгч удирдлага, LLM тохиргоо, статистик.
Зөвхөн admin эрхтэй хэрэглэгч хандах боломжтой.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from app.services.auth_service import get_admin_user
from app.db.supabase import get_admin_client

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Request schemas ───────────────────────────────────────────────────────────

class InviteUserRequest(BaseModel):
    email: EmailStr


# ── Хэрэглэгч ────────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(admin: dict = Depends(get_admin_user)):
    """Бүх хэрэглэгчдийн жагсаалт."""
    db = get_admin_client()
    result = (
        db.table("users")
        .select("id, email, display_name, created_at")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


@router.post("/users/invite")
async def invite_user(
    req: InviteUserRequest,
    admin: dict = Depends(get_admin_user),
):
    """Шинэ хэрэглэгчид урилга илгээх."""
    db = get_admin_client()
    result = db.auth.admin.invite_user_by_email(req.email)
    return {"message": f"{req.email} руу урилга илгээлээ"}


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    admin: dict = Depends(get_admin_user),
):
    """Хэрэглэгчийг бүрмөсөн устгах."""
    get_admin_client().auth.admin.delete_user(user_id)


# ── LLM ──────────────────────────────────────────────────────────────────────

@router.get("/llm/config")
async def get_llm_config(admin: dict = Depends(get_admin_user)):
    """Одоогийн LLM тохиргоо."""
    from app.core.settings import get_settings
    s = get_settings()
    return {
        "model": s.llm_model,
        "temperature": s.llm_temperature,
        "max_tokens": s.llm_max_tokens,
        "base_url": s.llm_base_url,
    }


@router.post("/llm/test")
async def test_llm_connection(admin: dict = Depends(get_admin_user)):
    """LLM холболт шалгах."""
    from app.services.llm_service import get_llm_service
    try:
        result = await get_llm_service().analyze_entry(
            surface="Өнөөдөр их ядарлаа.",
            inner="Амрахыг хүсч байна.",
            meaning="Тогтворгүй байдал мэдрэгдэж байна.",
        )
        return {"status": "ok", "hawkins_level": result.hawkins.level}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Статистик ─────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(admin: dict = Depends(get_admin_user)):
    """Ерөнхий тоон мэдээлэл."""
    db = get_admin_client()
    users = db.table("users").select("id", count="exact").execute()
    entries = db.table("journal_entries").select("id", count="exact").execute()
    insights = db.table("deep_insights").select("id", count="exact").execute()
    return {
        "total_users": users.count,
        "total_entries": entries.count,
        "total_deep_insights": insights.count,
    }
