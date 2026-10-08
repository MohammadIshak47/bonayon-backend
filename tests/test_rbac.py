from app.models import Role
from tests.conftest import make_user


def test_farmer_is_blocked_from_every_admin_endpoint(client, farmer):
    for method, path in [("get", "/admin/users"), ("get", "/admin/crops"), ("get", "/admin/audit-logs")]:
        assert getattr(client, method)(f"/api/v1{path}", headers=farmer).status_code == 403


def test_anonymous_gets_401_on_admin(client):
    assert client.get("/api/v1/admin/users").status_code == 401


def test_admin_can_list_and_deactivate_a_farmer(db, client, admin):
    target = make_user(db, "victim@example.com")
    assert client.get("/api/v1/admin/users", headers=admin).status_code == 200
    r = client.patch(f"/api/v1/admin/users/{target.id}", headers=admin, json={"is_active": False})
    assert r.status_code == 200 and r.json()["is_active"] is False
    logs = client.get("/api/v1/admin/audit-logs", headers=admin).json()
    assert any(entry["action"] == "user.deactivate" for entry in logs["items"])


def test_admin_cannot_deactivate_self_or_another_admin(db, client, admin):
    other = make_user(db, "admin2@example.com", Role.admin)
    me = client.get("/api/v1/auth/me", headers=admin).json()
    assert client.patch(f"/api/v1/admin/users/{me['id']}", headers=admin, json={"is_active": False}).status_code == 403
    assert client.patch(f"/api/v1/admin/users/{other.id}", headers=admin, json={"is_active": False}).status_code == 403


def test_admin_user_search_and_pagination(db, client, admin):
    for i in range(3):
        make_user(db, f"searchme{i}@example.com")
    r = client.get("/api/v1/admin/users", headers=admin, params={"query": "searchme", "size": 2}).json()
    assert r["total"] == 3 and len(r["items"]) == 2 and r["page"] == 1 and r["size"] == 2
