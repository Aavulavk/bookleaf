"""Ticket serialisation and the background AI classification job."""
import logging

from sqlalchemy.orm import Session

from ..ai import service as ai
from ..ai.client import LLMError
from ..db import SessionLocal
from ..models import Ticket, utcnow

log = logging.getLogger(__name__)


def _messages(t: Ticket, include_internal: bool) -> list[dict]:
    return [
        {"id": m.id, "sender_role": m.sender_role, "body": m.body, "is_internal": m.is_internal, "created_at": m.created_at}
        for m in t.messages
        if include_internal or not m.is_internal
    ]


def serialize_author(t: Ticket) -> dict:
    """What an author may see: no internal notes, no AI/priority metadata."""
    return {
        "id": t.id, "subject": t.subject, "description": t.description, "status": t.status,
        "category": t.category, "book_id": t.book_id, "book_title": t.book.title if t.book else None,
        "created_at": t.created_at, "updated_at": t.updated_at, "messages": _messages(t, False),
    }


def serialize_admin(t: Ticket, with_messages: bool = True) -> dict:
    return {
        "id": t.id, "subject": t.subject, "description": t.description, "status": t.status,
        "category": t.category, "priority": t.priority,
        "category_overridden": t.category_overridden, "priority_overridden": t.priority_overridden,
        "ai_category": t.ai_category, "ai_priority": t.ai_priority, "ai_reason": t.ai_reason,
        "ai_status": t.ai_status, "has_draft": bool(t.ai_draft),
        "book_id": t.book_id, "book_title": t.book.title if t.book else None,
        "author": {"id": t.author.id, "name": t.author.name, "email": t.author.user.email},
        "assigned_to": {"id": t.assignee.id, "name": t.assignee.name} if t.assignee else None,
        "created_at": t.created_at, "updated_at": t.updated_at,
        "messages": _messages(t, True) if with_messages else [],
    }


def apply_classification(t: Ticket, result: dict, *, from_ai: bool) -> None:
    """Never overwrite a value an admin already overrode."""
    if from_ai:
        t.ai_category, t.ai_priority, t.ai_reason, t.ai_status = result["category"], result["priority"], result["reason"], "done"
    else:
        t.ai_category = t.ai_priority = None
        t.ai_reason, t.ai_status = result["reason"], "failed"
    if not t.category_overridden:
        t.category = result["category"]
    if not t.priority_overridden:
        t.priority = result["priority"]
    t.updated_at = utcnow()


def classify_in_session(db: Session, t: Ticket) -> None:
    try:
        result = ai.classify(t.subject, t.description, t.book.title if t.book else None)
        apply_classification(t, result, from_ai=True)
    except LLMError as exc:
        log.warning("AI classification failed for ticket %s: %s", t.id, exc)
        apply_classification(t, ai.heuristic_classify(t.subject, t.description), from_ai=False)
    db.commit()


def run_classification(ticket_id: int) -> None:
    """Runs after the HTTP response is sent, so the author never waits on the AI."""
    with SessionLocal() as db:
        t = db.get(Ticket, ticket_id)
        if t is not None:
            classify_in_session(db, t)
