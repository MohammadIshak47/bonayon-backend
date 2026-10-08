from tests.conftest import crop_id, district_id
from tests.test_ownership import make_farm, make_plot


def test_calculator_is_seed_rate_times_area_and_labeled_estimate(seeded, client, farmer):
    r = client.post("/api/v1/calculator/input-estimate", headers=farmer, json={"crop_id": crop_id(client, farmer, "Wheat"), "area_decimal": 10})
    assert r.status_code == 200
    assert r.json()["seed_kg"] == 5.0 and r.json()["label"] == "estimate — verify locally" and r.json()["npk_note"]
    assert client.post("/api/v1/calculator/input-estimate", headers=farmer, json={"crop_id": crop_id(client, farmer, "Wheat"), "area_decimal": 0}).status_code == 422


def test_rotation_suggestions_come_from_the_catalog(seeded, client, farmer):
    boro = crop_id(client, farmer, "Boro Rice")
    s = client.post("/api/v1/rotation/suggest", headers=farmer, json={"season_1_crop_id": boro}).json()["suggestions"]
    assert [x["name_en"] for x in s] == ["Mustard"] and s[0]["explanation"]


def test_rotation_plan_save_validates_option_and_ownership(seeded, client, farmer, other_farmer):
    farm = make_farm(client, farmer)
    plot = make_plot(client, farmer, farm["id"])
    boro, mustard, wheat = (crop_id(client, farmer, n) for n in ("Boro Rice", "Mustard", "Wheat"))
    body = {"plot_id": plot["id"], "season_1_crop_id": boro, "season_2_crop_id": mustard, "note": "test"}
    assert client.post("/api/v1/rotation/plans", headers=farmer, json=body).status_code == 201
    assert client.post("/api/v1/rotation/plans", headers=farmer, json={**body, "season_2_crop_id": wheat}).status_code == 400  # not a listed option
    assert client.post("/api/v1/rotation/plans", headers=other_farmer, json=body).status_code == 403
    assert len(client.get("/api/v1/rotation/plans", headers=farmer).json()) == 1
    assert client.get("/api/v1/rotation/plans", headers=other_farmer).json() == []


def test_dashboard_counts_are_real(seeded, client, farmer):
    empty = client.get("/api/v1/dashboard", headers=farmer).json()
    assert empty == {"farms_count": 0, "plots_count": 0, "plans_count": 0, "latest_recommendation": None, "recent_recommendations": []}
    farm = make_farm(client, farmer)
    make_plot(client, farmer, farm["id"])
    make_plot(client, farmer, farm["id"], name="Plot 2")
    client.post("/api/v1/recommendations/season-plan", headers=farmer, json={"district_id": district_id(client), "soil_type": "clay", "season": "Rabi"})
    d = client.get("/api/v1/dashboard", headers=farmer).json()
    assert (d["farms_count"], d["plots_count"], d["plans_count"]) == (1, 2, 1)
    assert d["latest_recommendation"]["type"] == "season_plan" and len(d["recent_recommendations"]) == 1


def test_admin_crop_crud_and_audit(seeded, client, admin, farmer):
    new = {"name_en": "Lentil", "name_bn": "মসুর", "seasons": ["Rabi"], "rain_min_mm": 500, "rain_max_mm": 1500, "temp_min_c": 10, "temp_max_c": 25,
           "suitable_soils": ["silt_loam"], "water_sensitivity": "low", "rotation_after": [], "seed_kg_per_decimal": 0.05, "npk_note": None, "is_active": True}
    r = client.post("/api/v1/admin/crops", headers=admin, json=new)
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    assert client.post("/api/v1/admin/crops", headers=admin, json=new).status_code == 409                       # duplicate name
    assert client.post("/api/v1/admin/crops", headers=admin, json={**new, "name_en": "Bad", "rain_max_mm": 100}).status_code == 422   # max <= min
    assert client.post("/api/v1/admin/crops", headers=admin, json={**new, "name_en": "Bad2", "seasons": ["Winter"]}).status_code == 422
    assert client.patch(f"/api/v1/admin/crops/{cid}", headers=admin, json={"is_active": False}).json()["is_active"] is False
    assert "Lentil" not in [c["name_en"] for c in client.get("/api/v1/crops", headers=farmer).json()]   # inactive crops are hidden from farmers
    assert "Lentil" in [c["name_en"] for c in client.get("/api/v1/admin/crops", headers=admin).json()]
    assert client.patch(f"/api/v1/admin/crops/{cid}", headers=admin, json={"rain_max_mm": 100}).status_code == 400
    assert client.delete(f"/api/v1/admin/crops/{cid}", headers=admin).status_code == 204
    actions = [l["action"] for l in client.get("/api/v1/admin/audit-logs", headers=admin, params={"size": 50}).json()["items"]]
    assert {"crop.create", "crop.update", "crop.delete"} <= set(actions)


def test_crop_used_by_a_rotation_plan_cannot_be_deleted(seeded, client, admin, farmer):
    farm = make_farm(client, farmer)
    plot = make_plot(client, farmer, farm["id"])
    boro, mustard = crop_id(client, farmer, "Boro Rice"), crop_id(client, farmer, "Mustard")
    client.post("/api/v1/rotation/plans", headers=farmer, json={"plot_id": plot["id"], "season_1_crop_id": boro, "season_2_crop_id": mustard})
    r = client.delete(f"/api/v1/admin/crops/{mustard}", headers=admin)
    assert r.status_code == 409 and "Deactivate" in r.json()["detail"]
