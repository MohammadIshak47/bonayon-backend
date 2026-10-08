"""End-to-end smoke test of the running API, using the same requests the React frontend sends.
Run:  python -m scripts.smoke_test http://localhost:5173     (through the Vite dev proxy)
 or:  python -m scripts.smoke_test http://localhost:8000     (directly)
Needs seeded districts/crops and an admin (ADMIN_EMAIL / ADMIN_PASSWORD env, default admin@bonayon.test / AdminPass123)."""
import os
import sys
import uuid

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/") + "/api/v1"
ADMIN = (os.environ.get("ADMIN_EMAIL", "admin@bonayon.test"), os.environ.get("ADMIN_PASSWORD", "AdminPass123"))
c = httpx.Client(base_url=BASE, timeout=120)
n = 0


def check(cond: bool, label: str) -> None:
    global n
    n += 1
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        sys.exit(1)


def keys(d: dict, *ks: str) -> bool:
    return all(k in d for k in ks)


email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
d = c.get("/districts").json()
check(len(d) == 64 and keys(d[0], "id", "name_en", "name_bn", "division", "lat", "lon"), "GET /districts -> 64 districts")
did = next(x["id"] for x in d if x["name_en"] == "Rajshahi")

r = c.post("/auth/register", json={"name": "Smoke Tester", "email": email, "phone": "01712345678", "password": "SmokePass123"})
check(r.status_code == 201 and r.json()["role"] == "farmer", "register (frontend payload) -> 201 farmer")
check(c.post("/auth/register", json={"name": "Smoke Tester", "email": email, "phone": "01712345678", "password": "SmokePass123"}).status_code == 409, "duplicate email -> 409")
r = c.post("/auth/login", data={"username": email, "password": "SmokePass123"})  # form-encoded, as the frontend sends it
check(r.status_code == 200 and r.json()["token_type"] == "bearer", "login (form-encoded username/password) -> token")
H = {"Authorization": f"Bearer {r.json()['access_token']}"}
check(c.post("/auth/login", data={"username": email, "password": "nope"}).status_code == 401, "wrong password -> 401")
check(c.get("/auth/me", headers=H).json()["email"] == email, "GET /auth/me")

crops = c.get("/crops", headers=H).json()
seasons = sorted({s for cr in crops for s in cr["seasons"]})
check(len(crops) == 8 and seasons == ["Kharif", "Rabi"], f"GET /crops -> 8 crops, seasons {seasons} (frontend derives its season list from these)")

farm = c.post("/farms", headers=H, json={"name": "Smoke Farm", "district_id": did, "upazila": None}).json()
check(keys(farm, "id", "name", "district_id"), "create farm")
page = c.get("/farms", headers=H, params={"page": 1, "size": 12}).json()
check(page["total"] == 1 and keys(page, "items", "total", "page", "size"), "GET /farms -> {items,total,page,size}")
plot = c.post(f"/farms/{farm['id']}/plots", headers=H, json={"name": "Plot 1", "area_decimal": 12.5, "soil_type": "clay_loam", "crop_id": None, "planting_date": None, "season": "Rabi"}).json()
check(plot["area_decimal"] == 12.5 and plot["season"] == "Rabi", "create plot (frontend payload with nulls)")
check(len(c.get(f"/farms/{farm['id']}/plots", headers=H).json()) == 1, "GET /farms/{id}/plots -> array")

p = c.get(f"/climate/{did}/profile", params={"years": 20}).json()
check(len(p["months"]) == 12 and p["source"] and p["insufficient_data"] is False and p["data_span"], f"public climate profile (source: {p['source']})")
rc = c.get(f"/climate/{did}/risk-calendar", headers=H).json()
check(len(rc["months"]) == 12 and sum(m["monsoon_onset"] for m in rc["months"]) == 1, "risk calendar: 12 months, exactly one monsoon onset")
an = c.get(f"/climate/{did}/anomalies", headers=H).json()
check(len(an["years"]) >= 1 and keys(an["years"][0], "year", "temp_anomaly_c", "rainfall_anomaly_pct"), "anomalies")
check(c.get(f"/climate/{did}/risk-calendar").status_code == 401, "risk calendar requires login")

cc = c.post("/recommendations/crop-choice", headers=H, json={"district_id": did, "soil_type": "silt_loam", "season": "Rabi"}).json()
res = cc["payload"]["results"]
check(0 < len(res) <= 5 and keys(res[0], "crop_id", "name_en", "name_bn", "score", "tier", "explanations", "risk_notes"), f"crop-choice: top {len(res)}, best = {res[0]['name_en']} ({res[0]['score']}, {res[0]['tier']})")
check(cc["disclaimer"].startswith("Data-based advisory") and isinstance(cc["explanations"], list), "recommendation carries disclaimer + explanations")
sp = c.post("/recommendations/season-plan", headers=H, json={"plot_id": plot["id"]}).json()
w = sp["payload"]["planting_window"]
check(keys(w, "start", "end", "note") and isinstance(sp["payload"]["risk_warnings"], list) and sp["advisory_text"], f"season plan: {sp['payload']['crop']['name_en']}, window {w['start']}-{w['end']}")

dash = c.get("/dashboard", headers=H).json()
check((dash["farms_count"], dash["plots_count"], dash["plans_count"]) == (1, 1, 1) and len(dash["recent_recommendations"]) == 2, "dashboard counts are real")
hist = c.get("/recommendations", headers=H, params={"page": 1, "size": 10, "type": "season_plan"}).json()
check(hist["total"] == 1, "history filter by type")

boro = next(x["id"] for x in crops if x["name_en"] == "Boro Rice")
sg = c.post("/rotation/suggest", headers=H, json={"season_1_crop_id": boro}).json()["suggestions"]
check(keys(sg[0], "crop_id", "name_en", "explanation"), f"rotation suggestions: {[s['name_en'] for s in sg]}")
check(c.post("/rotation/plans", headers=H, json={"plot_id": plot["id"], "season_1_crop_id": boro, "season_2_crop_id": sg[0]["crop_id"]}).status_code == 201, "save rotation plan")
est = c.post("/calculator/input-estimate", headers=H, json={"crop_id": boro, "area_decimal": 10}).json()
check(est["seed_kg"] == 3.0 and "estimate" in est["label"], "calculator: 10 decimal of Boro = 3 kg, labeled estimate")

check(c.patch("/users/me", headers=H, json={"name": "Renamed", "phone": "01812345678"}).json()["name"] == "Renamed", "PATCH /users/me (name, phone)")
check(c.patch("/users/me", headers=H, json={"current_password": "SmokePass123", "new_password": "NewSmokePass1"}).status_code == 200, "change password")
check(c.post("/auth/login", data={"username": email, "password": "NewSmokePass1"}).status_code == 200, "login with the new password")

check(c.get("/admin/users", headers=H).status_code == 403, "farmer blocked from /admin (403)")
ar = c.post("/auth/login", data={"username": ADMIN[0], "password": ADMIN[1]})
check(ar.status_code == 200, "admin login")
AH = {"Authorization": f"Bearer {ar.json()['access_token']}"}
users = c.get("/admin/users", headers=AH, params={"query": email}).json()
check(users["total"] == 1, "admin user search")
check(c.patch(f"/admin/users/{users['items'][0]['id']}", headers=AH, json={"is_active": False}).json()["is_active"] is False, "admin deactivates the user")
check(c.get("/auth/me", headers=H).status_code == 401, "deactivated user's token stops working immediately")
logs = c.get("/admin/audit-logs", headers=AH, params={"size": 50}).json()["items"]
check({"recommendation.crop_choice", "recommendation.season_plan", "user.deactivate"} <= {l["action"] for l in logs}, "audit log recorded recommendations and the admin action")
print(f"\nAll {n} checks passed against {BASE}")
