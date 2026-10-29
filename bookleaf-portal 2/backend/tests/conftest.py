import os
import sys
from pathlib import Path

# Tests run on a throwaway SQLite file and never call the real AI.
os.environ["DATABASE_URL"] = "sqlite:///./test_bookleaf.db"
os.environ["ANTHROPIC_API_KEY"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import Author, Book, User


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add(User(email="admin@test.com", password_hash=hash_password("pw"), role="admin", name="Admin"))
        for i in (1, 2):
            u = User(email=f"a{i}@test.com", password_hash=hash_password("pw"), role="author", name=f"Author {i}")
            db.add(u)
            db.flush()
            a = Author(user_id=u.id, name=u.name, bank_linked=True)
            db.add(a)
            db.flush()
            db.add(Book(author_id=a.id, title=f"Book {i}", isbn=f"978000000000{i}", status="Published & Live",
                        mrp=299, copies_sold=10, royalty_earned=500, royalty_paid=0, royalty_pending=500))
        db.commit()
    with TestClient(app) as c:
        yield c


def login(client, email):
    r = client.post("/api/auth/login", json={"email": email, "password": "pw"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
