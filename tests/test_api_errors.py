from fastapi.testclient import TestClient

from app.api.deps import get_climate_provider
from app.core.db import get_db
from app.main import app


def test_unknown_id_is_404_with_detail_envelope(seeded, client, farmer):
    r = client.get("/api/v1/farms/00000000-0000-4000-8000-000000000000", headers=farmer)
    assert r.status_code == 404 and r.json() == {"detail": "Farm not found"}


def test_invalid_body_is_422_with_detail_list(client, farmer):
    r = client.post("/api/v1/farms", headers=farmer, json={"name": ""})
    assert r.status_code == 422 and isinstance(r.json()["detail"], list) and r.json()["detail"][0]["loc"]


def test_malformed_uuid_is_422(client, farmer):
    assert client.get("/api/v1/farms/not-a-uuid", headers=farmer).status_code == 422


def test_unauthenticated_and_forbidden_use_the_same_envelope(client, farmer):
    assert list(client.get("/api/v1/farms").json()) == ["detail"]
    assert list(client.get("/api/v1/admin/users", headers=farmer).json()) == ["detail"]


def test_unhandled_error_returns_generic_500_without_a_stack_trace(db):
    class Boom:
        name = "boom"
        def fetch_daily(self, *a):
            raise RuntimeError("secret internal detail")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_climate_provider] = lambda: Boom()
    try:
        from tests.conftest import make_user
        make_user(db, "x@example.com")
        from scripts import seed_districts
        seed_districts.seed(db)
        c = TestClient(app, raise_server_exceptions=False)
        did = c.get("/api/v1/districts").json()[0]["id"]
        r = c.get(f"/api/v1/climate/{did}/profile")
        assert r.status_code == 500 and r.json() == {"detail": "Internal server error"}
        assert "secret" not in r.text and "Traceback" not in r.text
    finally:
        app.dependency_overrides.clear()


def test_health_and_districts_are_public(seeded, client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    r = client.get("/api/v1/districts")
    assert r.status_code == 200 and len(r.json()) == 64 and r.headers["cache-control"].startswith("public")


def test_crops_require_login(seeded, client, farmer):
    assert client.get("/api/v1/crops").status_code == 401
    crops = client.get("/api/v1/crops", headers=farmer).json()
    assert len(crops) == 8 and {"rain_min_mm", "suitable_soils", "rotation_after", "seasons"} <= set(crops[0])


def test_cors_allows_only_the_configured_origin(client):
    ok = client.options("/api/v1/districts", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    bad = client.options("/api/v1/districts", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in bad.headers
