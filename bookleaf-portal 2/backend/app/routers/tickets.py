from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.errors import AppError
from ..db import get_db
from ..deps import require_author
from ..models import Book, Ticket, User
from ..schemas import AuthorTicketOut, TicketCreate
from ..services.tickets import run_classification, serialize_author

router = APIRouter(prefix="/api/tickets", tags=["Author tickets"])


def _own_ticket(db: Session, user: User, ticket_id: int) -> Ticket:
    t = db.get(Ticket, ticket_id)
    # 404 (not 403) so authors cannot probe which ticket ids exist.
    if t is None or t.author_id != user.author.id:
        raise AppError(404, "TICKET_NOT_FOUND", "Ticket not found.")
    return t


@router.post("", response_model=AuthorTicketOut, status_code=201)
def create_ticket(payload: TicketCreate, bg: BackgroundTasks, user: User = Depends(require_author), db: Session = Depends(get_db)):
    if payload.book_id is not None:
        book = db.get(Book, payload.book_id)
        if book is None or book.author_id != user.author.id:
            raise AppError(404, "BOOK_NOT_FOUND", "That book is not on your account.")
    t = Ticket(author_id=user.author.id, book_id=payload.book_id, subject=payload.subject.strip(),
               description=payload.description.strip())
    db.add(t)
    db.commit()
    db.refresh(t)
    bg.add_task(run_classification, t.id)  # AI runs after the response; ticket exists regardless
    return serialize_author(t)


@router.get("", response_model=list[AuthorTicketOut])
def list_my_tickets(user: User = Depends(require_author), db: Session = Depends(get_db)):
    rows = db.scalars(select(Ticket).where(Ticket.author_id == user.author.id).order_by(Ticket.updated_at.desc())).all()
    return [serialize_author(t) for t in rows]


@router.get("/{ticket_id}", response_model=AuthorTicketOut)
def get_my_ticket(ticket_id: int, user: User = Depends(require_author), db: Session = Depends(get_db)):
    return serialize_author(_own_ticket(db, user, ticket_id))
