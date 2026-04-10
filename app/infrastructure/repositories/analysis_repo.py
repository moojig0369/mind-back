from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
import uuid

from app.infrastructure.models import PsychometricAnalysisDB, ValueNodeDB, ValueNodeMaslowTrackerDB


class AnalysisRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_analysis(
        self,
        user_id: str,
        entry_id: str,
        hawkins_level: int,
        hawkins_label_en: str,
        hawkins_label_mn: str,
        plutchik_emotions: List[str],
        maslow_categories: List[str],
        ewma_score: float,
        trend: str,
        raw_response: str
    ) -> PsychometricAnalysisDB:
        """Шинэ шинжилгээний үр дүнг үүсгэнэ."""
        analysis = PsychometricAnalysisDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            entry_id=entry_id,
            hawkins_level=hawkins_level,
            hawkins_label_en=hawkins_label_en,
            hawkins_label_mn=hawkins_label_mn,
            plutchik_emotions=plutchik_emotions,
            maslow_categories=maslow_categories,
            ewma_score=ewma_score,
            trend=trend,
            raw_response=raw_response,
            created_at=datetime.utcnow(),
            is_processed=False
        )
        self.db.add(analysis)
        await self.db.flush()
        return analysis

    async def get_analysis(self, analysis_id: str) -> Optional[PsychometricAnalysisDB]:
        """ID-ээр шинжилгээг олно."""
        result = await self.db.execute(
            select(PsychometricAnalysisDB).where(PsychometricAnalysisDB.id == analysis_id)
        )
        return result.scalar_one_or_none()

    async def mark_as_processed(self, analysis_id: str):
        """Шинжилгээг 'processed' төлөвт шилжүүлнэ."""
        result = await self.db.execute(
            select(PsychometricAnalysisDB).where(PsychometricAnalysisDB.id == analysis_id)
        )
        analysis = result.scalar_one_or_none()
        if analysis:
            analysis.is_processed = True
            analysis.processed_at = datetime.utcnow()
            await self.db.flush()

    async def get_user_ewma(self, user_id: str, limit: int = 50) -> Optional[float]:
        """Хэрэглэгчийн сүүлийн EWMA утгуудыг авна."""
        result = await self.db.execute(
            select(PsychometricAnalysisDB.ewma_score)
            .where(PsychometricAnalysisDB.user_id == user_id)
            .order_by(PsychometricAnalysisDB.created_at.desc())
            .limit(limit)
        )
        scores = result.scalars().all()
        return scores[0] if scores else None

    async def count_user_entries(self, user_id: str) -> int:
        """Хэрэглэгчийн нийт бичлэгийн тоог авна."""
        result = await self.db.execute(
            select(func.count(PsychometricAnalysisDB.id))
            .where(PsychometricAnalysisDB.user_id == user_id)
        )
        return result.scalar() or 0

    async def update_value_node_maslow(self, node_id: str, maslow_code: str):
        """ValueNode-ын Maslow кодыг шинэчилнэ."""
        result = await self.db.execute(
            select(ValueNodeDB).where(ValueNodeDB.id == node_id)
        )
        node = result.scalar_one_or_none()
        if node:
            node.maslow_code = maslow_code
            await self.db.flush()

    async def create_maslow_tracker(
        self,
        node_id: str,
        maslow_code: str,
        confidence: float
    ):
        """Maslow tracker бичлэг үүсгэнэ."""
        tracker = ValueNodeMaslowTrackerDB(
            id=str(uuid.uuid4()),
            node_id=node_id,
            maslow_code=maslow_code,
            confidence=confidence,
            created_at=datetime.utcnow()
        )
        self.db.add(tracker)
        await self.db.flush()
