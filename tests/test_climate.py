from datetime import date, timedelta

import httpx
import pytest

from app.integrations.climate_provider import ClimateProvider, DailyClimate, ProviderError
from app.integrations.mock_provider import MockProvider
from app.integrations.nasa_power import NasaPowerProvider
from app.repositories import catalog as catalog_repo
from app.services.climate_service import ensure_climate, flag_days, missing_ranges
from tests.conftest import district_id

D = date(2020, 1, 1)


class Counting(ClimateProvider):
    name = "counting"

    def __init__(self):
        self.inner, self.calls = MockProvider(), 0

    def fetch_daily(self, lat, lon, start, end):
        self.calls += 1
        return self.inner.fetch_daily(lat, lon, start, end)


class Failing(ClimateProvider):
    name = "failing"

    def fetch_daily(self, lat, lon, start, end):
        raise ProviderError("provider is down")


def day(offset, rain=None, tmax=30.0):
    return DailyClimate(D + timedelta(days=offset), tmax, 25.0, rain, 70.0, 2.0)


# ---- mock provider ----
def test_mock_provider_is_deterministic_and_range_independent():
    p = MockProvider()
    a = p.fetch_daily(23.8, 90.4, date(2021, 5, 1), date(2021, 5, 10))
    b = p.fetch_daily(23.8, 90.4, date(2021, 5, 5), date(2021, 5, 12))
    assert a[4:] [:6] == b[:6]
    assert all(15 <= r.temp_avg <= 40 for r in a)


# ---- flagging ----
def test_heatwave_threshold_is_inclusive_at_35():
    rows = flag_days([day(0, 5, 34.9), day(1, 5, 35.0), day(2, 5, 40.0)])
    assert [r["heatwave_day"] for r in rows] == [False, True, True]


def test_dry_spell_needs_seven_consecutive_dry_days():
    six = flag_days([day(i, 0.0) for i in range(6)])
    seven = flag_days([day(i, 0.0) for i in range(7)])
    assert not any(r["dry_spell"] for r in six)
    assert all(r["dry_spell"] for r in seven)


def test_rain_or_missing_value_breaks_a_dry_spell():
    days = [day(i, 0.0) for i in range(4)] + [day(4, 5.0)] + [day(i, 0.0) for i in range(5, 12)]
    flags = [r["dry_spell"] for r in flag_days(days)]
    assert flags[:5] == [False] * 5 and all(flags[5:])  # first run of 4 is too short; second run of 7 counts
    gap = flag_days([day(i, 0.0) for i in range(4)] + [day(4, None)] + [day(i, 0.0) for i in range(5, 9)])
    assert not any(r["dry_spell"] for r in gap)


def test_missing_ranges_merges_small_gaps_only():
    existing = {D + timedelta(days=i) for i in range(0, 100)} - {D + timedelta(days=10), D + timedelta(days=12)}
    assert missing_ranges(D, D + timedelta(days=99), existing) == [(D + timedelta(days=10), D + timedelta(days=12))]
    assert len(missing_ranges(D, D + timedelta(days=99), {D})) == 1


# ---- caching + failure behaviour (real PostgreSQL) ----
def test_second_request_is_served_from_cache(seeded):
    dist = catalog_repo.list_districts(seeded)[0]
    p = Counting()
    first = ensure_climate(seeded, dist, 2, p)
    calls = p.calls
    second = ensure_climate(seeded, dist, 2, p)
    assert calls == 1 and p.calls == calls  # no second fetch
    assert len(first.frame) == len(second.frame) and first.sufficient


def test_only_missing_days_are_requested_when_the_window_moves(seeded):
    dist = catalog_repo.list_districts(seeded)[0]
    p = Counting()
    today = date(2024, 6, 1)
    ensure_climate(seeded, dist, 2, p, today=today)
    ensure_climate(seeded, dist, 2, p, today=today + timedelta(days=10))
    assert p.calls == 2  # one small extra request for the 10 new days, not a full re-download


def test_provider_failure_falls_back_to_cache_and_flags_stale(seeded):
    dist = catalog_repo.list_districts(seeded)[0]
    today = date(2024, 6, 1)
    ensure_climate(seeded, dist, 2, MockProvider(), today=today)
    b = ensure_climate(seeded, dist, 2, Failing(), today=today + timedelta(days=40))
    assert b.stale is True and b.sufficient is True and not b.frame.empty


def test_provider_failure_without_cache_is_insufficient_not_invented(seeded):
    dist = catalog_repo.list_districts(seeded)[0]
    b = ensure_climate(seeded, dist, 2, Failing())
    assert b.stale is True and b.sufficient is False and b.frame.empty


def test_public_profile_endpoint_shape(seeded, client):
    r = client.get(f"/api/v1/climate/{district_id(client)}/profile", params={"years": 3})
    assert r.status_code == 200
    body = r.json()
    assert len(body["months"]) == 12 and body["insufficient_data"] is False and body["stale"] is False
    assert body["source"].startswith("MOCK") and body["fetched_at"] and body["data_span"]["start"] < body["data_span"]["end"]
    assert all(m["rainfall_mm"] is not None for m in body["months"])


def test_profile_reports_insufficient_data_when_provider_is_down(seeded, client):
    from app.api.deps import get_climate_provider
    from app.main import app
    app.dependency_overrides[get_climate_provider] = lambda: Failing()
    body = client.get(f"/api/v1/climate/{district_id(client)}/profile").json()
    assert body["insufficient_data"] is True and body["months"] == [] and body["stale"] is True


def test_risk_calendar_and_anomalies_require_login(seeded, client):
    did = district_id(client)
    assert client.get(f"/api/v1/climate/{did}/risk-calendar").status_code == 401
    assert client.get(f"/api/v1/climate/{did}/anomalies").status_code == 401


def test_risk_calendar_endpoint_with_season_filter(seeded, client, farmer):
    did = district_id(client)
    r = client.get(f"/api/v1/climate/{did}/risk-calendar", headers=farmer, params={"season": "Rabi"}).json()
    assert {m["month"] for m in r["months"]} == {11, 12, 1, 2}
    assert client.get(f"/api/v1/climate/{did}/risk-calendar", headers=farmer, params={"season": "Winter"}).status_code == 400


def test_anomalies_endpoint(seeded, client, farmer):
    r = client.get(f"/api/v1/climate/{district_id(client)}/anomalies", headers=farmer).json()
    assert 1 <= len(r["years"]) <= 5 and r["baseline_years"] and r["insufficient_data"] is False


# ---- NASA POWER client: strict validation, retries, no network ----
def nasa(handler, retries=1):
    return NasaPowerProvider("https://nasa.test/point", retries=retries, backoff_s=0, client=httpx.Client(transport=httpx.MockTransport(handler)))


def payload(**overrides):
    params = {k: {"20240101": 1.0, "20240102": -999.0} for k in ["T2M_MAX", "T2M", "PRECTOTCORR", "RH2M", "WS2M"]}
    params.update(overrides)
    return {"properties": {"parameter": params}}


def test_nasa_parses_valid_payload_and_maps_fill_value_to_none():
    rows = nasa(lambda req: httpx.Response(200, json=payload())).fetch_daily(23.8, 90.4, date(2024, 1, 1), date(2024, 1, 2))
    assert [r.date for r in rows] == [date(2024, 1, 1), date(2024, 1, 2)]
    assert rows[0].temp_max == 1.0 and rows[1].temp_max is None


def test_nasa_missing_parameter_fails_loudly():
    bad = payload()
    del bad["properties"]["parameter"]["RH2M"]
    with pytest.raises(ProviderError, match="lacks parameters"):
        nasa(lambda req: httpx.Response(200, json=bad)).fetch_daily(1, 1, date(2024, 1, 1), date(2024, 1, 2))


@pytest.mark.parametrize("body", [{"unexpected": True}, {"properties": {"parameter": {"T2M": "not-a-dict"}}}, {"properties": []}])
def test_nasa_wrong_shape_fails_loudly(body):
    with pytest.raises(ProviderError):
        nasa(lambda req: httpx.Response(200, json=body)).fetch_daily(1, 1, date(2024, 1, 1), date(2024, 1, 2))


def test_nasa_retries_server_errors_then_raises():
    calls = []
    def handler(req):
        calls.append(1)
        return httpx.Response(503)
    with pytest.raises(ProviderError):
        nasa(handler, retries=2).fetch_daily(1, 1, date(2024, 1, 1), date(2024, 1, 2))
    assert len(calls) == 3


def test_nasa_does_not_retry_client_errors():
    calls = []
    def handler(req):
        calls.append(1)
        return httpx.Response(422)
    with pytest.raises(ProviderError, match="rejected"):
        nasa(handler, retries=2).fetch_daily(1, 1, date(2024, 1, 1), date(2024, 1, 2))
    assert len(calls) == 1


def test_nasa_sends_the_documented_parameters():
    seen = {}
    def handler(req):
        seen.update(dict(req.url.params))
        return httpx.Response(200, json=payload())
    nasa(handler).fetch_daily(23.8, 90.4, date(2024, 1, 1), date(2024, 1, 2))
    assert seen["community"] == "AG" and seen["parameters"] == "T2M_MAX,T2M,PRECTOTCORR,RH2M,WS2M" and seen["start"] == "20240101"
