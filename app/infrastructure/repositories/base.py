"""Base repository with common CRUD operations."""
from typing import TypeVar, Generic, Optional, List, Type, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from app.infrastructure.database import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """Generic base repository for CRUD operations."""
    
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db
    
    async def get_by_id(self, id: Any) -> Optional[ModelType]:
        """Get single record by ID."""
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all records with pagination."""
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())
    
    async def create(self, data: dict[str, Any]) -> ModelType:
        """Create new record."""
        obj = self.model(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj
    
    async def update(self, id: Any, data: dict[str, Any]) -> Optional[ModelType]:
        """Update existing record."""
        obj = await self.get_by_id(id)
        if not obj:
            return None
        
        for field, value in data.items():
            if hasattr(obj, field):
                setattr(obj, field, value)
        
        await self.db.flush()
        await self.db.refresh(obj)
        return obj
    
    async def delete(self, id: Any) -> bool:
        """Delete record by ID."""
        result = await self.db.execute(delete(self.model).where(self.model.id == id))
        await self.db.flush()
        return result.rowcount > 0
    
    async def count(self) -> int:
        """Count total records."""
        result = await self.db.execute(select(func.count()).select_from(self.model))
        return result.scalar_one() or 0
