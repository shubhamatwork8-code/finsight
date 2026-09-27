from app.services.context import current_user_id


def test_protected_route_requires_login(client):
    from app.main import app

    app.dependency_overrides.clear()
    response = client.get("/api/accounts")
    assert response.status_code == 401
    assert response.json()["error"] == "UNAUTHORIZED"


def test_register_login_and_isolation(client):
    from app.main import app

    app.dependency_overrides.clear()
    registered = client.post(
        "/api/auth/register",
        json={"full_name": "Student One", "email": "one@college.edu", "password": "ledger-pass"},
    )
    assert registered.status_code == 201
    token = registered.json()["token"]
    created = client.post(
        "/api/accounts",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Student Checking", "account_type": "CHECKING", "currency": "USD", "opening_balance": "25.00"},
    )
    assert created.status_code == 201
    account_id = created.json()["id"]

    other = client.post(
        "/api/auth/register",
        json={"full_name": "Student Two", "email": "two@college.edu", "password": "ledger-pass"},
    )
    other_token = other.json()["token"]
    hidden = client.get(f"/api/accounts/{account_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert hidden.status_code == 404
    listing = client.get("/api/accounts", headers={"Authorization": f"Bearer {other_token}"})
    assert listing.status_code == 200
    assert listing.json() == []

    demo = client.post("/api/auth/login", json={"email": "demo@finsight.local", "password": "FinSight-demo-1"})
    assert demo.status_code == 200
    current_user_id.set("USR-DEMO")
