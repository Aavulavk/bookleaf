from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .constants import Category, Priority, Status


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    isbn: Optional[str]
    genre: Optional[str]
    publication_date: Optional[str]
    status: str
    mrp: Optional[float]
    copies_sold: int
    royalty_earned: float
    royalty_paid: float
    royalty_pending: float


class TicketCreate(BaseModel):
    book_id: Optional[int] = None  # null = General / Account Level
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)


class MessageOut(BaseModel):
    id: int
    sender_role: str
    body: str
    is_internal: bool = False
    created_at: datetime


class AuthorTicketOut(BaseModel):
    id: int
    subject: str
    description: str
    status: str
    category: str
    book_id: Optional[int]
    book_title: Optional[str]
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut]


class PersonOut(BaseModel):
    id: int
    name: str
    email: Optional[str] = None


class AdminTicketOut(BaseModel):
    id: int
    subject: str
    description: str
    status: str
    category: str
    priority: str
    category_overridden: bool
    priority_overridden: bool
    ai_category: Optional[str]
    ai_priority: Optional[str]
    ai_reason: Optional[str]
    ai_status: str
    has_draft: bool
    book_id: Optional[int]
    book_title: Optional[str]
    author: PersonOut
    assigned_to: Optional[PersonOut]
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = []


class AdminTicketPatch(BaseModel):
    status: Optional[Status] = None
    category: Optional[Category] = None
    priority: Optional[Priority] = None
    assignee: Optional[str] = Field(default=None, pattern="^(me|unassigned)$")


class ReplyIn(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    status: Optional[Status] = None


class NoteIn(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class DraftOut(BaseModel):
    draft: str
    cached: bool


class AdminBookContext(BaseModel):
    book: Optional[BookOut]
    bank_linked: Optional[bool]


class DateRange(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
