from .conftest import login


def test_login_rejects_bad_password(client):
    r = client.post("/api/auth/login", json={"email": "a1@test.com", "password": "nope"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_routes_require_auth(client):
    assert client.get("/api/books").status_code == 401
    assert client.get("/api/admin/tickets").status_code == 401


def test_author_cannot_use_admin_routes(client):
    assert client.get("/api/admin/tickets", headers=login(client, "a1@test.com")).status_code == 403


def test_authors_only_see_own_books_and_tickets(client):
    h1, h2 = login(client, "a1@test.com"), login(client, "a2@test.com")
    books = client.get("/api/books", headers=h1).json()
    assert [b["title"] for b in books] == ["Book 1"]
    t = client.post("/api/tickets", headers=h1, json={"subject": "Royalty question", "description": "I have not received any royalty yet."}).json()
    assert client.get(f"/api/tickets/{t['id']}", headers=h2).status_code == 404
    assert client.get("/api/tickets", headers=h2).json() == []


def test_cannot_attach_ticket_to_someone_elses_book(client):
    h1, h2 = login(client, "a1@test.com"), login(client, "a2@test.com")
    other_book = client.get("/api/books", headers=h2).json()[0]["id"]
    r = client.post("/api/tickets", headers=h1, json={"book_id": other_book, "subject": "Hello", "description": "A description long enough."})
    assert r.status_code == 404


def test_validation_error_shape(client):
    r = client.post("/api/tickets", headers=login(client, "a1@test.com"), json={"subject": "x", "description": "short"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_ticket_lifecycle_with_ai_down(client):
    """No API key: ticket still created, keyword fallback classifies, admin writes manually, notes stay private."""
    ha, hd = login(client, "a1@test.com"), login(client, "admin@test.com")
    t = client.post("/api/tickets", headers=ha, json={"subject": "Wrong ISBN on Amazon", "description": "The ISBN on Amazon differs from my printed copy."}).json()

    admin_view = client.get(f"/api/admin/tickets/{t['id']}", headers=hd).json()
    assert admin_view["ai_status"] == "failed"
    assert admin_view["category"] == "ISBN & Metadata Issues" and admin_view["priority"] == "High"

    assert client.post(f"/api/admin/tickets/{t['id']}/draft", headers=hd).status_code == 503  # graceful

    client.patch(f"/api/admin/tickets/{t['id']}", headers=hd, json={"priority": "Critical", "assignee": "me"})
    client.post(f"/api/admin/tickets/{t['id']}/notes", headers=hd, json={"body": "internal only"})
    client.post(f"/api/admin/tickets/{t['id']}/reply", headers=hd, json={"body": "We are escalating this."})

    author_view = client.get(f"/api/tickets/{t['id']}", headers=ha).json()
    assert author_view["status"] == "In Progress"
    assert [m["body"] for m in author_view["messages"]] == ["We are escalating this."]
    assert "priority" not in author_view

    final = client.get(f"/api/admin/tickets/{t['id']}", headers=hd).json()
    assert final["priority_overridden"] is True and final["assigned_to"]["name"] == "Admin"


def test_queue_sorts_urgent_first_and_filters(client):
    ha, hd = login(client, "a1@test.com"), login(client, "admin@test.com")
    for subject, body in [("Update bio", "Can I update my author bio please?"),
                          ("Royalty missing", "I have not received royalty for 6 months, this is unacceptable.")]:
        client.post("/api/tickets", headers=ha, json={"subject": subject, "description": body})
    queue = client.get("/api/admin/tickets", headers=hd).json()
    assert queue[0]["subject"] == "Royalty missing"
    assert len(client.get("/api/admin/tickets?priority=Low", headers=hd).json()) == 1
    assert client.get("/api/admin/tickets?status=Bogus", headers=hd).status_code == 422
