from tests.conftest import district_id


def make_farm(client, headers, name="Farm A"):
    r = client.post("/api/v1/farms", headers=headers, json={"name": name, "district_id": district_id(client)})
    assert r.status_code == 201, r.text
    return r.json()


def make_plot(client, headers, farm_id, **extra):
    body = {"name": "Plot 1", "area_decimal": 10, "soil_type": "clay", **extra}
    r = client.post(f"/api/v1/farms/{farm_id}/plots", headers=headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_owner_can_crud_their_farm_and_plots(seeded, client, farmer):
    farm = make_farm(client, farmer)
    assert client.get(f"/api/v1/farms/{farm['id']}", headers=farmer).status_code == 200
    assert client.patch(f"/api/v1/farms/{farm['id']}", headers=farmer, json={"name": "Renamed"}).json()["name"] == "Renamed"
    plot = make_plot(client, farmer, farm["id"])
    assert client.patch(f"/api/v1/plots/{plot['id']}", headers=farmer, json={"area_decimal": 12.5}).json()["area_decimal"] == 12.5
    assert len(client.get(f"/api/v1/farms/{farm['id']}/plots", headers=farmer).json()) == 1
    assert client.delete(f"/api/v1/plots/{plot['id']}", headers=farmer).status_code == 204
    assert client.delete(f"/api/v1/farms/{farm['id']}", headers=farmer).status_code == 204


def test_other_user_gets_403_on_farm_and_plot_access(seeded, client, farmer, other_farmer):
    farm = make_farm(client, farmer)
    plot = make_plot(client, farmer, farm["id"])
    fid, pid = farm["id"], plot["id"]
    assert client.get(f"/api/v1/farms/{fid}", headers=other_farmer).status_code == 403
    assert client.patch(f"/api/v1/farms/{fid}", headers=other_farmer, json={"name": "x"}).status_code == 403
    assert client.delete(f"/api/v1/farms/{fid}", headers=other_farmer).status_code == 403
    assert client.get(f"/api/v1/farms/{fid}/plots", headers=other_farmer).status_code == 403
    assert client.post(f"/api/v1/farms/{fid}/plots", headers=other_farmer, json={"name": "p", "area_decimal": 1, "soil_type": "clay"}).status_code == 403
    assert client.get(f"/api/v1/plots/{pid}", headers=other_farmer).status_code == 403  # transitive via the farm
    assert client.patch(f"/api/v1/plots/{pid}", headers=other_farmer, json={"name": "x"}).status_code == 403
    assert client.delete(f"/api/v1/plots/{pid}", headers=other_farmer).status_code == 403


def test_farm_list_only_contains_own_farms_and_paginates(seeded, client, farmer, other_farmer):
    for i in range(3):
        make_farm(client, farmer, f"Mine {i}")
    make_farm(client, other_farmer, "Theirs")
    page = client.get("/api/v1/farms", headers=farmer, params={"size": 2, "page": 2}).json()
    assert page["total"] == 3 and len(page["items"]) == 1
    assert all(f["name"].startswith("Mine") for f in page["items"])


def test_unknown_ids_are_404_and_bad_input_is_422(seeded, client, farmer):
    missing = "00000000-0000-4000-8000-000000000000"
    assert client.get(f"/api/v1/farms/{missing}", headers=farmer).status_code == 404
    assert client.post("/api/v1/farms", headers=farmer, json={"name": "x", "district_id": missing}).status_code == 404
    farm = make_farm(client, farmer)
    assert client.post(f"/api/v1/farms/{farm['id']}/plots", headers=farmer, json={"name": "p", "area_decimal": -5, "soil_type": "clay"}).status_code == 422
    assert client.post(f"/api/v1/farms/{farm['id']}/plots", headers=farmer, json={"name": "p", "area_decimal": 5, "soil_type": "gravel"}).status_code == 422
