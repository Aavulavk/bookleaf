"""AI use-cases: classification + priority (one cheap call) and draft replies (on demand)."""
import json
import re
from datetime import date, datetime, timedelta, timezone

from ..constants import CATEGORIES, PRIORITIES
from ..models import Author, Book, Ticket
from .client import LLMError, get_client
from .prompts import CLASSIFY_SYSTEM, classify_user, draft_system

# ---------- Classification ----------


def _parse_json(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise LLMError("Model did not return JSON")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise LLMError("Model returned malformed JSON") from exc
    if data.get("category") not in CATEGORIES or data.get("priority") not in PRIORITIES:
        raise LLMError("Model returned an unknown category or priority")
    return {
        "category": data["category"],
        "priority": data["priority"],
        "reason": str(data.get("reason", ""))[:300],
    }


def classify(subject: str, description: str, book_title: str | None = None) -> dict:
    """Small prompt, no knowledge base, tiny output cap: pennies per thousand tickets."""
    raw = get_client().complete(CLASSIFY_SYSTEM, classify_user(subject, description, book_title), max_tokens=120)
    return _parse_json(raw)


_KEYWORDS = [
    ("ISBN & Metadata Issues", ("isbn", "barcode", "wrong book", "duplicate")),
    ("Royalty & Payments", ("royalt", "payout", "payment", "paid", "bank", "earning")),
    ("Printing & Quality", ("print", "blurry", "binding", "misprint", "quality", "reprint", "damaged")),
    ("Distribution & Availability", ("unavailable", "amazon", "flipkart", "listing", "not showing", "out of stock")),
    ("Book Status & Production Updates", ("typesetting", "proof", "cover design", "status", "when will", "production")),
]


def heuristic_classify(subject: str, description: str) -> dict:
    """Offline fallback used when the AI is down, so tickets are never left unsorted."""
    text = f"{subject} {description}".lower()
    category = next((c for c, words in _KEYWORDS if any(w in text for w in words)), "General Inquiry")
    if any(w in text for w in ("lawyer", "legal", "fraud", "scam", "6 months", "six months")):
        priority = "Critical"
    elif category in ("ISBN & Metadata Issues", "Printing & Quality") or "unavailable" in text:
        priority = "High"
    elif category == "General Inquiry":
        priority = "Low"
    else:
        priority = "Medium"
    return {"category": category, "priority": priority, "reason": "AI unavailable: keyword-based fallback"}


# ---------- Draft replies ----------


def payout_cycle(today: date) -> tuple[date, date]:
    """Most relevant quarter-end and its payout deadline (quarter end + 45 days)."""
    ends = sorted(
        date(y, m, d) for y in (today.year - 1, today.year, today.year + 1) for m, d in ((3, 31), (6, 30), (9, 30), (12, 31))
    )
    last = max(e for e in ends if e <= today)
    deadline = last + timedelta(days=45)
    if deadline < today:  # this cycle's window has passed, so point at the next one
        last = min(e for e in ends if e > today)
        deadline = last + timedelta(days=45)
    return last, deadline


_BOOK_FIELDS = ("title", "isbn", "genre", "publication_date", "status", "mrp", "copies_sold",
                "royalty_earned", "royalty_paid", "royalty_pending")


def _book_context(book: Book | None) -> str:
    if not book:
        return "General / account-level query (no specific book selected)."
    data = {f: (float(v) if hasattr(v, "as_tuple") else v) for f in _BOOK_FIELDS if (v := getattr(book, f)) not in (None, "")}
    extra = json.dumps(book.extra, default=str)[:600] if book.extra else ""
    return json.dumps(data) + (f"\nOther book data: {extra}" if extra else "")


def generate_draft(ticket: Ticket, book: Book | None, author: Author) -> str:
    """Only this ticket, this book and the last 4 public messages go to the model, never full history."""
    quarter_end, deadline = payout_cycle(datetime.now(timezone.utc).date())
    history = [f"{m.sender_role}: {m.body[:500]}" for m in ticket.messages if not m.is_internal][-4:]
    user = f"""CONTEXT
Category: {ticket.category}
Author: {author.name} (bank details linked in dashboard: {'unknown' if author.bank_linked is None else ('yes' if author.bank_linked else 'no')})
Book: {_book_context(book)}
Today: {datetime.now(timezone.utc).date().isoformat()}
Current royalty cycle: quarter ending {quarter_end.isoformat()}, payout due by {deadline.isoformat()}
Earlier messages on this ticket: {' | '.join(history) if history else 'none'}

AUTHOR'S TICKET
Subject: {ticket.subject}
{ticket.description[:2000]}

Write the reply."""
    return get_client().complete(draft_system(ticket.category), user, max_tokens=450)
