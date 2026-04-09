from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class EntryCreateRequest(BaseModel):
    surface_text: str = Field(..., min_length=1, max_length=5000)
    inner_reaction_text: str = Field(..., min_length=1, max_length=5000)
    meaning_text: str = Field(..., min_length=1, max_length=5000)
    # False бол текстийг DB-д хадгалахгүй, зөвхөн шинжилгээ хийнэ
    save_text: bool = True


class EntryResponse(BaseModel):
    id: UUID
    user_id: UUID
    surface_text: str | None
    inner_reaction_text: str | None
    meaning_text: str | None
    is_encrypted: bool
    is_text_saved: bool
    entry_index: int
    created_at: datetime


class EntryCreateResponse(BaseModel):
    entry_id: str
    status: str
    message: str
    ws_channel: str


class PaginatedEntryResponse(BaseModel):
    items: list[EntryResponse]
    total: int
    page: int
    page_size: int
