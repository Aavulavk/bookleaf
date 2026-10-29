"""Schema. AI-suggested values (ai_*) are stored separately from the final
values (category/priority) so admin overrides stay traceable."""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))  # "author" | "admin"
    name: Mapped[str] = mapped_column(String(255), default="")
    author: Mapped["Author | None"] = relationship(back_populates="user", uselist=False)


class Author(Base):
    __tablename__ = "authors"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    bank_linked: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # None = unknown
    user: Mapped[User] = relationship(back_populates="author")
    books: Mapped[list["Book"]] = relationship(back_populates="author")


class Book(Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    isbn: Mapped[str | None] = mapped_column(String(32), nullable=True)
    genre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    publication_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(80), default="")
    mrp: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)  # null while in production
    copies_sold: Mapped[int] = mapped_column(default=0)
    royalty_earned: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    royalty_paid: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    royalty_pending: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # leftover dataset fields
    author: Mapped[Author] = relationship(back_populates="books")


class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"), index=True)
    book_id: Mapped[int | None] = mapped_column(ForeignKey("books.id"), nullable=True)
    subject: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="Open", index=True)

    # Final values (what the team sees and filters on)
    category: Mapped[str] = mapped_column(String(60), default="General Inquiry", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="Medium", index=True)
    category_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    priority_overridden: Mapped[bool] = mapped_column(Boolean, default=False)

    # What the AI suggested
    ai_category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    ai_priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ai_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|done|failed
    ai_draft: Mapped[str | None] = mapped_column(Text, nullable=True)

    assigned_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    author: Mapped[Author] = relationship()
    book: Mapped[Book | None] = relationship()
    assignee: Mapped[User | None] = relationship()
    messages: Mapped[list["TicketMessage"]] = relationship(
        back_populates="ticket", order_by="TicketMessage.id", cascade="all, delete-orphan"
    )


class TicketMessage(Base):
    __tablename__ = "ticket_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    sender_role: Mapped[str] = mapped_column(String(20))
    body: Mapped[str] = mapped_column(Text)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)  # internal note
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ticket: Mapped[Ticket] = relationship(back_populates="messages")
