# DDD Архитектурт Шилжих Хөтөлбөр

## 1. Шинэ Фолдер Бүтэц

```
app/
├── main.py                      # FastAPI app initialization
├── config.py                    # Configuration settings
├── core/                        # Core utilities (security, logging, exceptions)
│   ├── security.py
│   ├── logging.py
│   └── exceptions.py
├── infrastructure/              # Infrastructure layer (DB, AI, external services)
│   ├── database.py
│   ├── repositories/            # Repository pattern implementation
│   │   ├── base.py
│   │   ├── journal_repo.py     ✅ DONE
│   │   ├── analysis_repo.py
│   │   └── graph_repo.py
│   └── ai/                      # AI/LLM logic
│       ├── client.py
│       ├── prompts.py
│       └── embeddings.py
├── domains/                     # Domain layer (business logic)
│   ├── auth/
│   │   ├── entities.py
│   │   ├── schemas.py
│   │   └── service.py
│   ├── journal/                 ✅ DONE
│   │   ├── entities.py         # Domain entities (JournalEntry, SeedInsight)
│   │   ├── schemas.py          # API schemas (Request/Response)
│   │   └── service.py          # Business logic
│   ├── insight/
│   │   ├── entities.py
│   │   ├── schemas.py
│   │   ├── pipeline.py
│   │   └── service.py
│   └── graph/
│       ├── entities.py
│       ├── schemas.py
│       └── service.py
├── api/                         # API layer (controllers/routes)
│   ├── v1/
│   │   ├── deps.py             ✅ DONE - Dependencies
│   │   ├── router.py
│   │   ├── journal_routes.py   ✅ DONE
│   │   ├── insight_routes.py
│   │   └── graph_routes.py
│   └── deps.py
└── workers/                     # Background jobs
    ├── celery_app.py
    └── tasks.py
```

## 2. Шилжүүлэх Үе Шатууд

### Phase 1: ✅已完成 - Journal Domain
- [x] `domains/journal/entities.py` - Domain entities
- [x] `domains/journal/schemas.py` - API schemas
- [x] `domains/journal/service.py` - Business logic
- [x] `infrastructure/repositories/journal_repo.py` - Repository
- [x] `api/v1/journal_routes.py` - API routes
- [x] `api/v1/deps.py` - Dependencies

### Phase 2: Insight Domain (Next)
- [ ] Move `services/llm_service.py` → `domains/insight/service.py`
- [ ] Create `domains/insight/pipeline.py` for AI workflow
- [ ] Create `infrastructure/repositories/analysis_repo.py`
- [ ] Move psychometric analysis logic to domain

### Phase 3: Graph Domain
- [ ] Move `services/graph_builder.py` → `domains/graph/service.py`
- [ ] Create `domains/graph/entities.py` (ValueNode, ValueEdge)
- [ ] Create `infrastructure/repositories/graph_repo.py`

### Phase 4: Auth Domain (Supabase Integration)
- [ ] Move `services/auth_service.py` → `domains/auth/service.py`
- [ ] Create `domains/auth/entities.py` (User)
- [ ] Update Supabase auth integration

### Phase 5: Cleanup
- [ ] Remove old `/services` folder
- [ ] Remove old `/schemas` folder
- [ ] Update all imports in `main.py`
- [ ] Update worker imports

## 3. Гол Өөрчлөлтүүд

### Old Structure → New Structure

| Old Location | New Location | Status |
|-------------|-------------|--------|
| `schemas/entry.py` | `domains/journal/schemas.py` | ✅ Migrated |
| `services/journal_service.py` | `domains/journal/service.py` | ✅ Migrated |
| N/A | `infrastructure/repositories/journal_repo.py` | ✅ Created |
| `api/routes/entries.py` | `api/v1/journal_routes.py` | ✅ Migrated |
| `services/auth_service.py` | `domains/auth/service.py` | ⏳ Pending |
| `services/llm_service.py` | `domains/insight/service.py` | ⏳ Pending |
| `services/graph_builder.py` | `domains/graph/service.py` | ⏳ Pending |

## 4. Ашиглалтын Жишээ

### Journal Entry Creation Flow

```python
# 1. API Route receives request
POST /api/v1/entries/
{
  "surface_text": "...",
  "inner_reaction_text": "...",
  "meaning_text": "..."
}

# 2. Route delegates to service
service.create_entry(user_id, data)

# 3. Service uses repository
repo.insert(payload)

# 4. Generate seed insight (sync)
seed = await service.generate_seed_insight(...)

# 5. Queue full analysis (async)
background_tasks.add_task(_enqueue_analysis, ...)
```

## 5. Давуу Талууд

✅ **Separation of Concerns**: API, Domain, Infrastructure тусгаарлагдсан
✅ **Testability**: Repository pattern mock хийхэд хялбар
✅ **Scalability**: 10k-100k users дэмжих боломжтой
✅ **Maintainability**: Код ойлгоход хялбар, өөрчлөлт оруулахад аюулгүй
✅ **Supabase Auth**: JWT token ашиглан authentication

## 6. Дараагийн Алхам

1. Run tests to verify journal domain works
2. Migrate insight domain (LLM/AI logic)
3. Migrate graph domain (value graphs)
4. Remove old folders
5. Deploy and monitor
