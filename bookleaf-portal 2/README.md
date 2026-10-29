# BookLeaf Author Support & Communication Portal

Two portals (author + admin) on one REST API, with AI-assisted ticket classification, priority scoring and reply drafting.

**Stack:** FastAPI · SQLAlchemy · PostgreSQL · React (Vite) · Claude Haiku · polling for near-real-time updates.

## Run locally

```bash
# 1. Database
docker compose up -d

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # set JWT_SECRET and ANTHROPIC_API_KEY
# put the provided dataset at backend/data/bookleaf_sample_data.json
python -m scripts.seed          # use --reset to wipe and reseed
uvicorn app.main:app --reload   # API on :8000, Swagger on /docs

# 3. Frontend (new terminal)
cd frontend
cp .env.example .env
npm install && npm run dev      # http://localhost:5173
```

**Demo logins** (created by the seed): admin `admin@bookleaf.com` / `Admin@123`; every author uses their dataset email with `Author@123`.

Tests: `cd backend && pytest -m "not live"` (offline, SQLite). Live AI checks against the 7 sample queries: `ANTHROPIC_API_KEY=... pytest -m live`.

## Deploy
- **API + Postgres:** Render/Railway. Start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set `DATABASE_URL`, `JWT_SECRET`, `ANTHROPIC_API_KEY`, `CORS_ORIGINS` (your frontend URL). Run `python -m scripts.seed` once.
- **Frontend:** Vercel with root `frontend/`, env `VITE_API_URL=<api url>`. `vercel.json` handles SPA routing.
- Keep the repo **private** (assignment is confidential); `.gitignore` already excludes `.env` and the dataset.

## Architecture
```
backend/app
  core/       config (env vars), security (bcrypt + JWT), errors (uniform error shape)
  routers/    auth, books, tickets (author), admin: thin HTTP layer
  services/   ticket serialisation + background AI job
  ai/         client (provider wrapper), prompts, knowledge_base, service (use-cases)
  models.py   SQLAlchemy schema        deps.py   auth + role dependencies
```
Key decisions:
- **Ticket flow never depends on AI.** `POST /tickets` saves and returns; classification runs as a background task.
- **AI values are stored separately** (`ai_category`, `ai_priority`) from final values, with `*_overridden` flags, so overrides are traceable and an AI result arriving late never clobbers an admin's choice.
- **RBAC:** role is read from the DB, never the token. Author queries are always scoped to `user.author.id`; other authors' tickets return 404, not 403.
- **Internal notes** are `ticket_messages.is_internal=true` and filtered out in the author serializer, which also omits priority and AI fields.
- **Queue order:** unresolved first, then Critical → Low, then oldest first. Unresolved tickets older than 48h get a ⚠ in the age column.
- **Real-time:** 5s polling, paused while the tab is hidden. Simple, proxy-friendly, and enough for this load. Next step would be SSE.

## AI integration
**Model:** Claude Haiku. Low cost per ticket, fast, reliable at strict JSON and tone instructions. The provider sits behind `ai/client.py`, so switching to OpenAI means one new class. Model name is configurable (`ANTHROPIC_MODEL`).

**Prompts**
- *Classify + prioritise* (one call): short system prompt with the six categories, explicit priority rules (ISBN errors always ≥ High, 6+ months unpaid = Critical), three examples, JSON-only output validated against the allowed values.
- *Draft reply:* system prompt = BookLeaf tone guidelines + hard rules (no invented facts, use real numbers, 48h timelines, clear next step) + knowledge base. User message = this ticket, this book's actual figures, whether bank details are linked, the current royalty cycle and payout deadline (computed from the 45-day rule), and the last 4 public messages.

**Cost control**
- Classification sends only subject + description (truncated) and caps output at 120 tokens. No knowledge base.
- Drafts include only the KB sections relevant to the ticket's category (`knowledge_base.py`), not the whole KB.
- Only the one relevant book is sent, never the author's catalogue or full ticket history.
- Drafts are generated on demand when an admin opens a ticket, then cached on the ticket. Re-calling needs an explicit "Regenerate".
- The static system prompt is marked for provider-side prompt caching.

**Graceful degradation**
- Any AI failure (no key, timeout, 429, outage, bad JSON) raises one `LLMError`. The SDK retries 429/5xx twice with backoff, with a 20s timeout.
- Classification failure → ticket still saved; a keyword heuristic assigns category/priority, `ai_status="failed"`, queue shows an "AI offline" badge, and admins get a "Retry AI" button.
- Draft failure → `503 AI_UNAVAILABLE`; the reply box stays usable for manual writing.

**Security:** the API key is read from env vars on the server only and never reaches the frontend.

## API
Interactive docs at `/docs` (Swagger) and `/openapi.json`. Errors always look like `{"error": {"code", "message", "details?"}}`. All routes except login need `Authorization: Bearer <token>`.

| Method | Path | Role | Purpose |
|---|---|---|---|
| POST | /api/auth/login | public | Email/password → JWT |
| GET | /api/auth/me | any | Current user |
| GET | /api/books | author | Own books |
| POST | /api/tickets | author | Create ticket (`book_id` null = general) |
| GET | /api/tickets | author | Own tickets with public replies |
| GET | /api/tickets/{id} | author | One own ticket |
| GET | /api/admin/tickets | admin | Queue; filters `status, category, priority, assigned, date_from, date_to, limit, offset` |
| GET | /api/admin/tickets/{id} | admin | Detail incl. internal notes + AI metadata |
| GET | /api/admin/tickets/{id}/context | admin | Book + bank-link facts |
| PATCH | /api/admin/tickets/{id} | admin | Status, category/priority override, `assignee: me\|unassigned` |
| POST | /api/admin/tickets/{id}/reply | admin | Send reply visible to author |
| POST | /api/admin/tickets/{id}/notes | admin | Internal note |
| POST | /api/admin/tickets/{id}/draft | admin | AI draft (cached; `?regenerate=true`) |
| POST | /api/admin/tickets/{id}/reclassify | admin | Retry AI classification |
| GET | /api/health | public | Liveness + whether AI is configured |

## Known limitations / next steps
- Tables created with `create_all`; use Alembic migrations in production.
- Classification runs in-process via FastAPI background tasks; a real queue (Celery/RQ) would survive restarts and smooth rate limits.
- Polling instead of SSE/WebSockets; no email notifications; file attachments are UI-only.
- Authors cannot reply back on a ticket (not in scope); no audit log of admin actions.
- Money stored as `Numeric` but shown as ₹ only; no multi-currency for US authors.
- The seed reads dataset keys by alias (`scripts/seed.py` → `FIELD_ALIASES`) and keeps unmapped fields (print partner, platforms, last payout date) in `books.extra`, which the AI draft prompt receives. Bank-link status is not in the dataset, so it is stored as *unknown* and drafts say so instead of guessing.
- Next: vector search if the KB grows, evaluation set for classification accuracy, rate limiting on login.
