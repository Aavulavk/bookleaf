"""Seed the DB from the BookLeaf sample dataset.

Usage (from /backend):
    python -m scripts.seed [path/to/bookleaf_sample_data.json] [--reset]

The dataset's exact field names were not available when this was written, so
every field is looked up under several likely names (see FIELD_ALIASES).
If your JSON uses different keys, add them there.
"""
import json
import re
import sys
from pathlib import Path

from sqlalchemy import select

from app.core.security import hash_password
from app.db import Base, SessionLocal, engine
from app.models import Author, Book, User

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "bookleaf_sample_data.json"
AUTHOR_PASSWORD = "Author@123"
ADMINS = [("admin@bookleaf.com", "Admin@123", "BookLeaf Admin"), ("ops@bookleaf.com", "Admin@123", "Ops Team")]

FIELD_ALIASES = {
    "author_id": ("author_id", "authorId", "id"),
    "name": ("name", "author_name", "full_name"),
    "email": ("email", "author_email", "email_address"),
    "bank_linked": ("bank_linked", "bank_details_linked", "bank_account_linked", "bank_details"),
    "title": ("title", "book_title", "name"),
    "isbn": ("isbn", "isbn_number"),
    "genre": ("genre", "category"),
    "publication_date": ("publication_date", "publish_date", "published_date", "pub_date", "date_published"),
    "status": ("status", "publication_status", "book_status"),
    "mrp": ("mrp", "price", "list_price"),
    "copies_sold": ("copies_sold", "total_copies_sold", "units_sold", "sold"),
    "royalty_earned": ("royalty_earned", "total_royalty_earned", "royalty_total"),
    "royalty_paid": ("royalty_paid", "total_royalty_paid"),
    "royalty_pending": ("royalty_pending", "pending_royalty", "royalty_due"),
}


def pick(d: dict, field: str, default=None):
    for key in FIELD_ALIASES[field]:
        if key in d and d[key] not in (None, ""):
            return d[key]
    return default


def num(v, cast=float):
    try:
        return cast(re.sub(r"[^\d.\-]", "", str(v))) if v not in (None, "") else cast(0)
    except ValueError:
        return cast(0)


def truthy(v) -> bool:
    return str(v).strip().lower() in ("true", "yes", "1", "linked", "y") if v is not None else False


def load(path: Path) -> tuple[list[dict], list[dict]]:
    raw = json.loads(path.read_text())
    authors = raw.get("authors", []) if isinstance(raw, dict) else raw
    books = list(raw.get("books", [])) if isinstance(raw, dict) else []
    for a in authors:  # support books nested inside each author
        for b in a.get("books", []) or []:
            books.append({**b, "_owner": pick(a, "author_id")})
    return authors, books


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = Path(args[0]) if args else DEFAULT_PATH
    if "--reset" in sys.argv:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    authors, books = load(path)

    with SessionLocal() as db:
        for email, pw, name in ADMINS:
            if not db.scalar(select(User).where(User.email == email)):
                db.add(User(email=email, password_hash=hash_password(pw), role="admin", name=name))
        db.flush()

        by_source_id: dict = {}
        for a in authors:
            email = str(pick(a, "email", f"author{pick(a, 'author_id')}@example.com")).lower()
            user = db.scalar(select(User).where(User.email == email))
            if not user:
                user = User(email=email, password_hash=hash_password(AUTHOR_PASSWORD), role="author", name=str(pick(a, "name", email)))
                db.add(user)
                db.flush()
                db.add(Author(user_id=user.id, name=user.name, bank_linked=(truthy(pick(a, "bank_linked")) if pick(a, "bank_linked") is not None else None)))
                db.flush()
            by_source_id[pick(a, "author_id")] = user.author

        known = set(sum(FIELD_ALIASES.values(), ())) | {"_owner", "author_id", "id", "book_id"}
        created = skipped = 0
        for b in books:
            owner = by_source_id.get(b.get("_owner", b.get("author_id")))
            if owner is None:
                skipped += 1
                continue
            title = str(pick(b, "title", "Untitled"))
            if db.scalar(select(Book).where(Book.author_id == owner.id, Book.title == title)):
                continue
            db.add(Book(
                author_id=owner.id, title=title,
                isbn=(str(pick(b, "isbn")) if pick(b, "isbn") else None),
                genre=pick(b, "genre"), publication_date=(str(pick(b, "publication_date")) if pick(b, "publication_date") else None),
                status=str(pick(b, "status", "")), mrp=(num(pick(b, "mrp")) if pick(b, "mrp") is not None else None), copies_sold=num(pick(b, "copies_sold"), int),
                royalty_earned=num(pick(b, "royalty_earned")), royalty_paid=num(pick(b, "royalty_paid")),
                royalty_pending=num(pick(b, "royalty_pending")),
                extra={k: v for k, v in b.items() if k not in known} or None,
            ))
            created += 1
        db.commit()

    print(f"Seeded {len(authors)} authors, {created} books ({skipped} books had no matching author).")
    print(f"Author logins: <author email> / {AUTHOR_PASSWORD}")
    for email, pw, _ in ADMINS:
        print(f"Admin login:   {email} / {pw}")


if __name__ == "__main__":
    main()
