"""
NASA POWER daily point client.

ASSUMPTION (from NASA POWER documentation, NOT verified against the live service from this project):
  GET {base}?parameters=T2M_MAX,T2M,PRECTOTCORR,RH2M,WS2M&community=AG&longitude=..&latitude=..&start=YYYYMMDD&end=YYYYMMDD&format=JSON
  -> {"properties": {"parameter": {"T2M_MAX": {"YYYYMMDD": value, ...}, ...}}, ...}
  and the fill value for missing data is -999.
The response is validated strictly, so a different shape fails loudly with ProviderError instead of being guessed.
"""
import time
from datetime import date, timedelta

import httpx
from pydantic import BaseModel, ValidationError

from app.integrations.climate_provider import ClimateProvider, DailyClimate, ProviderError

PARAMETERS = ["T2M_MAX", "T2M", "PRECTOTCORR", "RH2M", "WS2M"]
FILL_VALUE = -999.0
CHUNK_DAYS = 365 * 5  # keep each request small enough for the timeout


class _Props(BaseModel):
    parameter: dict[str, dict[str, float]]


class _Response(BaseModel):
    properties: _Props


class NasaPowerProvider(ClimateProvider):
    name = "NASA POWER"

    def __init__(self, base_url: str, timeout_s: float = 10.0, retries: int = 2, backoff_s: float = 1.0,
                 client: httpx.Client | None = None) -> None:
        self.base_url, self.retries, self.backoff_s = base_url, retries, backoff_s
        self.client = client or httpx.Client(timeout=timeout_s)

    def fetch_daily(self, lat: float, lon: float, start: date, end: date) -> list[DailyClimate]:
        out: list[DailyClimate] = []
        s = start
        while s <= end:
            e = min(end, s + timedelta(days=CHUNK_DAYS - 1))
            out.extend(self._parse(self._get(lat, lon, s, e)))
            s = e + timedelta(days=1)
        return out

    def _get(self, lat: float, lon: float, s: date, e: date) -> dict:
        params = {"parameters": ",".join(PARAMETERS), "community": "AG", "longitude": lon, "latitude": lat,
                  "start": s.strftime("%Y%m%d"), "end": e.strftime("%Y%m%d"), "format": "JSON"}
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                r = self.client.get(self.base_url, params=params)
                if r.status_code >= 500:
                    raise ProviderError(f"NASA POWER returned HTTP {r.status_code}")
                if r.status_code >= 400:
                    raise ProviderError(f"NASA POWER rejected the request (HTTP {r.status_code})")
                return r.json()
            except (httpx.TransportError, ValueError, ProviderError) as exc:
                last = exc
                if isinstance(exc, ProviderError) and "rejected" in str(exc):
                    break  # 4xx will not succeed on retry
                if attempt < self.retries:
                    time.sleep(self.backoff_s * (2 ** attempt))
        raise ProviderError(f"NASA POWER request failed: {last}")

    @staticmethod
    def _parse(payload: dict) -> list[DailyClimate]:
        try:
            params = _Response.model_validate(payload).properties.parameter
        except ValidationError as exc:
            raise ProviderError(f"Unexpected NASA POWER response shape: {exc.errors()[0]['loc']}") from exc
        missing = [p for p in PARAMETERS if p not in params]
        if missing:
            raise ProviderError(f"NASA POWER response lacks parameters: {missing}")

        def val(name: str, key: str) -> float | None:
            v = params[name].get(key)
            return None if v is None or v == FILL_VALUE else v

        rows: list[DailyClimate] = []
        for key in sorted(params["T2M_MAX"]):
            try:
                d = date(int(key[:4]), int(key[4:6]), int(key[6:8]))
            except ValueError as exc:
                raise ProviderError(f"Unexpected date key in NASA POWER response: {key!r}") from exc
            rows.append(DailyClimate(d, val("T2M_MAX", key), val("T2M", key), val("PRECTOTCORR", key), val("RH2M", key), val("WS2M", key)))
        return rows
