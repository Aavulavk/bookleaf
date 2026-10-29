from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.errors import register_error_handlers
from .db import Base, engine
from .routers import admin, auth, books, tickets


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)  # swap for Alembic migrations in production
    yield


app = FastAPI(title="BookLeaf Author Support Portal", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)
for r in (auth.router, books.router, tickets.router, admin.router):
    app.include_router(r)


@app.get("/api/health", tags=["Meta"])
def health():
    return {"status": "ok", "ai_configured": bool(settings.anthropic_api_key)}
