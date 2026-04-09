# MindSteps — Тэмдэглэлийн системийн Backend

> FastAPI · Supabase · Redis Queue · OpenAI / Qwen3

---

## Технологийн стек

| Давхарга | Технологи |
|---|---|
| API | FastAPI + Uvicorn |
| Баазын удирдлага | Supabase (PostgreSQL) |
| Дараалал / Worker | Redis + RQ |
| LLM | OpenAI-тэй нийцтэй (Qwen3 дэмжинэ) |
| Орчин | Docker Compose |

---

## Хурдан эхлүүлэх

### Docker-оор (зөвлөмж)

```bash
# 1. Repo clone хий
git clone https://github.com/munkhjargal333/MindSteps.git
cd MindSteps/v2back

# 2. Тохиргоо үүсгэх
cp .env.example .env
nano .env   # SUPABASE_URL, SUPABASE_ANON_KEY, LLM_API_KEY оруул

# 3. Асаах
docker compose up --build

# API:    http://localhost:8000/docs
# Worker: автоматаар эхэлнэ
```

RQ dashboard (optional):
```bash
docker compose --profile dev up
# → http://localhost:9181
```

### Гараар эхлүүлэх

```bash
# 1. Орчин үүсгэх
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Тохиргоо
cp .env.example .env

# 3. Redis
docker run -d -p 6379:6379 redis:7-alpine

# 4. API
uvicorn app.main:app --reload
# → http://localhost:8000/docs

# 5. Worker (шинэ terminal)
python worker.py
```

---

## Тохиргоо (.env)

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o

REDIS_URL=redis://localhost:6379
```

> ⚠️ `.env` файлыг **хэзээ ч** git-д оруулж болохгүй. `.gitignore`-д байгааг шалга.

---

## Qwen3 руу шилжих

Зөвхөн `.env`-д 2 мөр солино — кодонд хүрэхгүй:

```env
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3-235b-a22b
LLM_API_KEY=<Alibaba Cloud key>
```

---

## Файлын бүтэц

```
app/
├── core/
│   ├── settings.py         ← Бүх тохиргоо (.env уншина)
│   └── middleware.py       ← Rate limiting
├── db/
│   ├── supabase.py         ← Client factory (anon + admin)
│   └── redis_client.py     ← Redis + Queue factory
├── schemas/
│   ├── entry.py            ← Тэмдэглэлийн схем
│   ├── analysis.py         ← LLM шинжилгээний схем
│   └── graph.py            ← ValueGraph схем
├── services/
│   ├── auth_service.py     ← Supabase JWT баталгаажуулалт
│   ├── llm_service.py      ← OpenAI / Qwen3 шинжилгээ
│   └── journal_service.py  ← CRUD + ValueGraph логик
├── workers/
│   └── jobs.py             ← RQ Worker jobs
├── api/routes/
│   ├── entries.py          ← /api/entries
│   ├── graph.py            ← /api/graph, /api/insights
│   ├── admin.py            ← /api/admin
│   └── websocket.py        ← /ws/{channel}
└── main.py                 ← FastAPI app, router холболт
```

---

## API Endpoints

### Тэмдэглэл
| Method | URL | Тайлбар |
|---|---|---|
| `GET` | `/health` | Redis + Supabase шалгах |
| `GET` | `/api/entries` | Тэмдэглэлийн жагсаалт |
| `POST` | `/api/entries` | Тэмдэглэл үүсгэх → queue |
| `GET` | `/api/entries/{id}` | Дэлгэрэнгүй харах |
| `DELETE` | `/api/entries/{id}` | Устгах |

### Шинжилгээ
| Method | URL | Тайлбар |
|---|---|---|
| `GET` | `/api/graph` | Үнэт зүйлсийн граф |
| `GET` | `/api/insights/deep` | Deep Insight жагсаалт |
| `GET` | `/api/insights/seed/{id}` | Seed Insight |
| `GET` | `/api/stats/emotions` | Сэтгэл хөдлөлийн статистик |
| `WS` | `/ws/{channel}` | Бодит цагийн мэдэгдэл |

### Админ
| Method | URL | Тайлбар |
|---|---|---|
| `GET` | `/api/admin/stats` | Статистик |
| `GET` | `/api/admin/users` | Хэрэглэгчид |
| `POST` | `/api/admin/users/invite` | Урилга илгээх |
| `POST` | `/api/admin/llm/test` | LLM шалгах |

---

## Архитектурын зарчмууд

| Зарчим | Хэрэгжилт |
|---|---|
| **SRP** | Схем, сервис, route, worker тус бүр нэг үүрэгтэй |
| **DRY** | DB client factory — нэг газраас авна |
| **KISS** | Route-д зөвхөн HTTP логик, бизнес логик service-д |
| **OCP** | LLM загвар солиход зөвхөн `.env` өөрчилнө |

---

## Орчны шаардлага

- Python 3.12+
- Docker & Docker Compose
- Redis 7+
- Supabase project

---

## Лиценз

MIT# mind-back
