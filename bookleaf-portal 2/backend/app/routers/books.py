from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_author
from ..models import Book, User
from ..schemas import BookOut

router = APIRouter(prefix="/api/books", tags=["Author books"])


@router.get("", response_model=list[BookOut])
def my_books(user: User = Depends(require_author), db: Session = Depends(get_db)):
    """Always scoped to the logged-in author; no author id is ever taken from the request."""
    return db.scalars(select(Book).where(Book.author_id == user.author.id).order_by(Book.id)).all()
