# MindSteps — Journal Graph System

> FastAPI · Clean Architecture · PostgreSQL · Redis Queue (RQ) · AI-Powered Insights

---

## 🏗 Architecture Overview

This project follows **Clean Architecture** principles to ensure separation of concerns, testability, and maintainability.

### Key Architectural Decisions

1.  **Separation of Concerns**: Controllers (API routes) are strictly separated from Domain logic.
2.  **Repository Pattern**: Business logic depends on interfaces, not concrete database implementations.
3.  **Schema Separation**: 
    -   **API Schemas**: Pydantic models for request/response validation.
    -   **Domain Models**: Pure Python dataclasses/entities for business rules.
4.  **Async Worker**: Uses **Redis Queue (RQ)** for background tasks (graph calculations, AI processing).
5.  **Database**: PostgreSQL with async drivers (`asyncpg`).

### Layer Structure

```
┌─────────────────────────────────────────────────────────┐
│                      API Layer                          │
│  (Controllers, Pydantic Schemas, Routes)                │
└───────────────────────┬─────────────────────────────────┘
                        │ Depends on Interfaces
┌───────────────────────▼─────────────────────────────────┐
│                    Domain Layer                         │
│  (Entities, Value Objects, Business Logic, Interfaces)  │
└───────────────────────┬─────────────────────────────────┘
                        │ Implements
┌───────────────────────▼─────────────────────────────────┐
│                Infrastructure Layer                     │
│  (DB Repositories, External Services, Workers/RQ)       │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Technologies

| Layer | Technology |
|---|---|
| **API** | FastAPI + Uvicorn |
| **Database** | PostgreSQL (Supabase or self-hosted) |
| **Queue / Worker** | Redis + RQ |
| **AI/LLM** | OpenAI-compatible (supports Qwen3, GPT-4) |
| **Containerization** | Docker Compose |
| **Testing** | Pytest + Asyncio |

---

## 📦 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/munkhjargal333/MindSteps.git
cd MindSteps/v2back

# 2. Setup configuration
cp .env.example .env
nano .env   # Update SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, REDIS_URL, LLM_API_KEY

# 3. Start all services (API, Worker, Redis)
docker compose up --build

# API:    http://localhost:8000/docs
# Worker: Starts automatically
```

**Optional: RQ Dashboard**
```bash
docker compose --profile dev up
# → http://localhost:9181
```

### Option 2: Manual Setup

```bash
# 1. Create virtual environment
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Setup configuration
cp .env.example .env

# 3. Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# 4. Run API
uvicorn app.main:app --reload
# → http://localhost:8000/docs

# 5. Run Worker (separate terminal)
python worker.py
```

---

## ⚙️ Configuration (.env)

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/journal_db
# OR Supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM (OpenAI or Qwen3)
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o

# Security
SECRET_KEY=your-secret-key
CORS_ORIGINS=["http://localhost:3000"]
```

> ⚠️ **Never commit `.env` to git**. Ensure it's in `.gitignore`.

### Switching to Qwen3

Only change 2 lines in `.env` — no code changes needed:

```env
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3-235b-a22b
LLM_API_KEY=<Alibaba Cloud key>
```

---

## 🧪 Testing

We use `pytest` for comprehensive unit and integration testing.

### Run All Tests
```bash
pytest
```

### Run Specific Test Suites
```bash
# Domain Logic Tests
pytest tests/test_journal_domain.py

# Graph Structure & Algorithm Tests
pytest tests/test_graph_structure.py

# Repository Interface Tests
pytest tests/test_repository_interface.py
```

### CI/CD
GitHub Actions automatically runs tests and linting on every push and pull request. See `.github/workflows/ci.yml` for details.

---

## 📂 Project Structure

```
.
├── app/
│   ├── api/                # Controllers, Routes, API Schemas
│   │   ├── routes/
│   │   └── schemas/
│   ├── core/               # Config, Security, Exceptions, Middleware
│   ├── domains/            # Business Logic, Entities, Interfaces
│   │   ├── models/         # Domain entities
│   │   ├── services/       # Business logic
│   │   └── repositories/   # Interface definitions
│   ├── infrastructure/     # DB Models, Repositories, External Services
│   │   ├── database/
│   │   ├── repositories/   # Concrete implementations
│   │   └── external/       # LLM, Email, etc.
│   ├── workers/            # RQ Job definitions
│   └── main.py             # App Entry Point
├── tests/                  # Unit & Integration Tests
├── worker.py               # RQ Worker Entry Point
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🔌 API Endpoints

### Health Check
| Method | URL | Description |
|---|---|---|
| `GET` | `/health` | Check Redis + Database connectivity |

### Journal Entries
| Method | URL | Description |
|---|---|---|
| `GET` | `/api/entries` | List journal entries |
| `POST` | `/api/entries` | Create entry → queued for processing |
| `GET` | `/api/entries/{id}` | Get entry details |
| `DELETE` | `/api/entries/{id}` | Delete entry |

### Graph & Insights
| Method | URL | Description |
|---|---|---|
| `GET` | `/api/graph` | Get value graph structure |
| `GET` | `/api/insights/deep` | List deep insights |
| `GET` | `/api/insights/seed/{id}` | Get seed insight |
| `GET` | `/api/stats/emotions` | Emotion statistics |
| `WS` | `/ws/{channel}` | Real-time notifications |

### Admin
| Method | URL | Description |
|---|---|---|
| `GET` | `/api/admin/stats` | System statistics |
| `GET` | `/api/admin/users` | User management |
| `POST` | `/api/admin/users/invite` | Send invitation |
| `POST` | `/api/admin/llm/test` | Test LLM connection |

---

## 🏛 Architecture Principles

| Principle | Implementation |
|---|---|
| **SRP** (Single Responsibility) | Schemas, services, routes, workers each have one responsibility |
| **DRY** (Don't Repeat Yourself) | DB client factory — single source of truth |
| **KISS** (Keep It Simple) | Routes handle HTTP only; business logic in services |
| **OCP** (Open/Closed) | LLM model switching via `.env` only — no code changes |
| **DIP** (Dependency Inversion) | Domain depends on abstractions, not concrete implementations |

---

## 🖥 Requirements

- Python 3.9+
- Docker & Docker Compose (optional but recommended)
- Redis 7+
- PostgreSQL 13+ (or Supabase project)

---

## 📄 License

MIT License

---

## 📊 Current Status (as of April 2025)

### Development Phase
**Active Development** - Core architecture implemented, domain logic in progress

### Completed Components
✅ **Clean Architecture Foundation**
- Full separation of API, Domain, and Infrastructure layers
- Repository pattern with interface-based design
- Dependency injection structure

✅ **Core Domains Implemented**
- Journal domain with entity and service layer
- Graph domain for value relationships
- Insight domain for AI-generated insights
- Pattern domain for behavior analysis
- Auth domain for authentication

✅ **Infrastructure**
- PostgreSQL database with async support
- Redis Queue (RQ) for background jobs
- Supabase client integration
- LLM integration (OpenAI + Qwen3 compatible)

✅ **Testing Framework**
- Pytest configuration with async support
- Domain logic tests (`test_journal_domain.py`)
- Graph structure tests (`test_graph_structure.py`)
- Repository interface tests (`test_repository_interface.py`)

### Technology Stack
| Component | Technology | Version |
|---|---|---|
| **Framework** | FastAPI | 0.115.0 |
| **Validation** | Pydantic | 2.8.2 |
| **Database** | PostgreSQL (asyncpg) | - |
| **Queue** | Redis + RQ | 5.0.8 / 1.16.2 |
| **LLM Client** | OpenAI SDK | 1.51.0 |
| **External DB** | Supabase | 2.7.4 |
| **Testing** | Pytest | - |

### Code Statistics
- **Application Files**: 44 Python modules
- **Test Files**: 4 test suites
- **Architecture Layers**: 3 (API, Domain, Infrastructure)
- **Domain Modules**: 6 (auth, graph, insight, journal, pattern)

### In Progress / Next Steps
🔄 **API Endpoints** - Expanding v1 routes
🔄 **Worker Tasks** - Background job implementation
🔄 **Migration Scripts** - Database schema evolution (v4, v5 UML alignment)
🔄 **Docker Configuration** - Multi-service orchestration

### Known Features
- Async worker processing for graph calculations and AI insights
- Multi-LLM support (switch between GPT-4, Qwen3 via `.env` only)
- Real-time notifications via WebSocket
- Clean separation allowing easy testing and maintenance
- CI/CD ready with GitHub Actions support

### Requirements to Run
- Python 3.9+
- Redis 7+
- PostgreSQL 13+ or Supabase account
- Docker & Docker Compose (recommended)
