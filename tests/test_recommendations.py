from app.api.deps import get_climate_provider
from app.core.agronomy import DISCLAIMER
from app.integrations.climate_provider import ClimateProvider, ProviderError
from app.main import app
from tests.conftest import district_id
from tests.test_ownership import make_farm, make_plot


def crop_choice(client, headers, season="Rabi", soil="clay", name="Dhaka"):
    return client.post("/api/v1/recommendations/crop-choice", headers=headers, json={"district_id": district_id(client, name), "soil_type": soil, "season": season})


def test_crop_choice_returns_ranked_top5_with_explanations_and_disclaimer(seeded, client, farmer):
    r = crop_choice(client, farmer)
    assert r.status_code == 201, r.text
    body = r.json()
    results = body["payload"]["results"]
    assert 1 <= len(results) <= 5 and [x["score"] for x in results] == sorted((x["score"] for x in results), reverse=True)
    assert all(len(x["explanations"]) == 4 and x["tier"] in {"excellent", "good", "marginal", "poor"} for x in results)
    assert body["disclaimer"] == DISCLAIMER and body["payload"]["data_fetched_at"] and body["payload"]["limitations"]
    assert body["type"] == "crop_choice" and any("Weights" in e for e in body["explanations"])


def test_crop_choice_is_persisted_and_audited(seeded, client, farmer, admin):
    crop_choice(client, farmer)
    hist = client.get("/api/v1/recommendations", headers=farmer).json()
    assert hist["total"] == 1 and hist["items"][0]["type"] == "crop_choice"
    logs = client.get("/api/v1/admin/audit-logs", headers=admin).json()["items"]
    assert any(l["action"] == "recommendation.crop_choice" for l in logs)


def test_winter_crops_beat_kharif_only_crops_in_rabi(seeded, client, farmer):
    names = [x["name_en"] for x in crop_choice(client, farmer, season="Rabi").json()["payload"]["results"]]
    assert "Aman Rice" not in names[:2]  # Aman is Kharif-only, so the season factor should push it down


def test_unknown_season_is_400_and_bad_soil_is_422(seeded, client, farmer):
    assert crop_choice(client, farmer, season="Winter").status_code == 400
    assert crop_choice(client, farmer, soil="gravel").status_code == 422


def test_insufficient_data_is_reported_honestly_not_guessed(seeded, client, farmer):
    class Down(ClimateProvider):
        name = "down"
        def fetch_daily(self, *a):
            raise ProviderError("down")
    app.dependency_overrides[get_climate_provider] = lambda: Down()
    r = crop_choice(client, farmer)
    assert r.status_code == 503 and r.json()["detail"].startswith("INSUFFICIENT_DATA")
    assert client.get("/api/v1/recommendations", headers=farmer).json()["total"] == 0  # nothing stored


def test_season_plan_from_own_plot(seeded, client, farmer):
    farm = make_farm(client, farmer)
    plot = make_plot(client, farmer, farm["id"], season="Kharif", soil_type="clay_loam")
    r = client.post("/api/v1/recommendations/season-plan", headers=farmer, json={"plot_id": plot["id"]})
    assert r.status_code == 201, r.text
    body = r.json()
    p = body["payload"]
    assert body["plot_id"] == plot["id"] and body["type"] == "season_plan" and body["disclaimer"] == DISCLAIMER
    assert p["crop"]["name_en"] and p["planting_window"]["start"] and p["planting_window"]["end"] and "risk_warnings" in p
    assert "Suggested planting window" in body["advisory_text"] and body["explanations"]


def test_season_plan_with_raw_inputs(seeded, client, farmer):
    r = client.post("/api/v1/recommendations/season-plan", headers=farmer, json={"district_id": district_id(client), "soil_type": "silt_loam", "season": "Rabi"})
    assert r.status_code == 201 and r.json()["plot_id"] is None


def test_season_plan_rejects_someone_elses_plot(seeded, client, farmer, other_farmer):
    farm = make_farm(client, farmer)
    plot = make_plot(client, farmer, farm["id"], season="Rabi")
    assert client.post("/api/v1/recommendations/season-plan", headers=other_farmer, json={"plot_id": plot["id"]}).status_code == 403


def test_season_plan_input_forms(seeded, client, farmer):
    farm = make_farm(client, farmer)
    no_season = make_plot(client, farmer, farm["id"])
    assert client.post("/api/v1/recommendations/season-plan", headers=farmer, json={"plot_id": no_season["id"]}).status_code == 400
    assert client.post("/api/v1/recommendations/season-plan", headers=farmer, json={}).status_code == 422
    mixed = {"plot_id": no_season["id"], "district_id": district_id(client), "soil_type": "clay", "season": "Rabi"}
    assert client.post("/api/v1/recommendations/season-plan", headers=farmer, json=mixed).status_code == 422


def test_history_is_private_paginated_and_filterable(seeded, client, farmer, other_farmer):
    for _ in range(3):
        crop_choice(client, farmer)
    client.post("/api/v1/recommendations/season-plan", headers=farmer, json={"district_id": district_id(client), "soil_type": "clay", "season": "Rabi"})
    crop_choice(client, other_farmer)
    p1 = client.get("/api/v1/recommendations", headers=farmer, params={"size": 3, "page": 1}).json()
    p2 = client.get("/api/v1/recommendations", headers=farmer, params={"size": 3, "page": 2}).json()
    assert p1["total"] == 4 and len(p1["items"]) == 3 and len(p2["items"]) == 1
    only_plans = client.get("/api/v1/recommendations", headers=farmer, params={"type": "season_plan"}).json()
    assert only_plans["total"] == 1
    assert client.get("/api/v1/recommendations", headers=farmer, params={"size": 500}).status_code == 422
