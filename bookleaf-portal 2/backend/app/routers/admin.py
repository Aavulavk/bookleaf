from datetime import date, datetime, time, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, select
from sqlalchemy.orm import Session

from ..ai import service as ai
from ..ai.client import LLMError
from ..constants import Category, Priority, Status
from ..core.errors import AppError
from ..db import get_db
from ..deps import require_admin
from ..models import Ticket, TicketMessage, User, utcnow
from ..schemas import AdminBookContext, AdminTicketOut, AdminTicketPatch, DraftOut, NoteIn, ReplyIn
from ..services.tickets import classify_in_session, serialize_admin

router = APIRouter(prefix="/api/admin", tags=["Admin"])

_PRIORITY_RANK = case({"Critical": 0, "High": 1, "Medium": 2, "Low": 3}, value=Ticket.priority, else_=4)
_DONE_LAST = case((Ticket.status.in_(["Resolved", "Closed"]), 1), else_=0)


def _get(db: Session, ticket_id: int) -> Ticket:
    t = db.get(Ticket, ticket_id)
    if t is None:
        raise AppError(404, "TICKET_NOT_FOUND", "Ticket not found.")
    return t


@router.get("/tickets", response_model=list[AdminTicketOut])
def ticket_queue(
    status: Optional[Status] = None,
    category: Optional[Category] = None,
    priority: Optional[Priority] = None,
    assigned: Optional[str] = Query(default=None, pattern="^(me|unassigned)$"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Unresolved first, then Critical -> Low, then oldest first, so urgent + stale tickets sit on top."""
    q = select(Ticket)
    if status:
        q = q.where(Ticket.status == status)
    if category:
        q = q.where(Ticket.category == category)
    if priority:
        q = q.where(Ticket.priority == priority)
    if assigned == "me":
        q = q.where(Ticket.assigned_to_id == admin.id)
    elif assigned == "unassigned":
        q = q.where(Ticket.assigned_to_id.is_(None))
    if date_from:
        q = q.where(Ticket.created_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        q = q.where(Ticket.created_at <= datetime.combine(date_to, time.max, tzinfo=timezone.utc))
    q = q.order_by(_DONE_LAST, _PRIORITY_RANK, Ticket.created_at.asc()).limit(limit).offset(offset)
    return [serialize_admin(t, with_messages=False) for t in db.scalars(q).all()]


@router.get("/tickets/{ticket_id}", response_model=AdminTicketOut)
def ticket_detail(ticket_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return serialize_admin(_get(db, ticket_id))


@router.get("/tickets/{ticket_id}/context", response_model=AdminBookContext)
def ticket_context(ticket_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Book + account facts shown beside the thread so the admin can verify the draft."""
    t = _get(db, ticket_id)
    return {"book": t.book, "bank_linked": t.author.bank_linked}


@router.patch("/tickets/{ticket_id}", response_model=AdminTicketOut)
def update_ticket(ticket_id: int, payload: AdminTicketPatch, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    t = _get(db, ticket_id)
    if payload.status:
        t.status = payload.status
    if payload.category:
        t.category = payload.category
        t.category_overridden = payload.category != t.ai_category
    if payload.priority:
        t.priority = payload.priority
        t.priority_overridden = payload.priority != t.ai_priority
    if payload.assignee == "me":
        t.assigned_to_id = admin.id
    elif payload.assignee == "unassigned":
        t.assigned_to_id = None
    t.updated_at = utcnow()
    db.commit()
    db.refresh(t)
    return serialize_admin(t)


@router.post("/tickets/{ticket_id}/notes", response_model=AdminTicketOut, status_code=201)
def add_note(ticket_id: int, payload: NoteIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Internal notes are flagged is_internal and filtered out of every author response."""
    t = _get(db, ticket_id)
    db.add(TicketMessage(ticket_id=t.id, sender_id=admin.id, sender_role="admin", body=payload.body.strip(), is_internal=True))
    t.updated_at = utcnow()
    db.commit()
    db.refresh(t)
    return serialize_admin(t)


@router.post("/tickets/{ticket_id}/reply", response_model=AdminTicketOut, status_code=201)
def reply(ticket_id: int, payload: ReplyIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    t = _get(db, ticket_id)
    if t.status == "Closed":
        raise AppError(409, "TICKET_CLOSED", "Reopen the ticket before replying.")
    db.add(TicketMessage(ticket_id=t.id, sender_id=admin.id, sender_role="admin", body=payload.body.strip(), is_internal=False))
    t.status = payload.status or ("In Progress" if t.status == "Open" else t.status)
    if t.assigned_to_id is None:
        t.assigned_to_id = admin.id
    t.updated_at = utcnow()
    db.commit()
    db.refresh(t)
    return serialize_admin(t)


@router.post("/tickets/{ticket_id}/draft", response_model=DraftOut)
def ai_draft(ticket_id: int, regenerate: bool = False, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Generated on demand and cached on the ticket; the model is only called again when asked to regenerate."""
    t = _get(db, ticket_id)
    if t.ai_draft and not regenerate:
        return {"draft": t.ai_draft, "cached": True}
    try:
        t.ai_draft = ai.generate_draft(t, t.book, t.author)
    except LLMError:
        raise AppError(503, "AI_UNAVAILABLE", "AI drafting is unavailable right now. You can write the reply manually.")
    db.commit()
    return {"draft": t.ai_draft, "cached": False}


@router.post("/tickets/{ticket_id}/reclassify", response_model=AdminTicketOut)
def reclassify(ticket_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    """'Retry AI' button: re-run classification (never overwrites admin overrides)."""
    t = _get(db, ticket_id)
    classify_in_session(db, t)
    db.refresh(t)
    return serialize_admin(t)
