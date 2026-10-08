import math
import random
from datetime import date, timedelta

from app.integrations.climate_provider import ClimateProvider, DailyClimate

# Rough monthly rainfall pattern (mm) with a monsoon peak. SYNTHETIC: for development and tests only.
_MONTH_MM = [8, 20, 40, 90, 200, 350, 400, 380, 250, 120, 25, 5]


class MockProvider(ClimateProvider):
    """Deterministic synthetic data. Each day is seeded by (lat, lon, date), so the same
    request always returns the same values regardless of the requested range."""
    name = "MOCK (synthetic development data)"

    def fetch_daily(self, lat: float, lon: float, start: date, end: date) -> list[DailyClimate]:
        out: list[DailyClimate] = []
        d = start
        while d <= end:
            rng = random.Random(f"{lat:.3f}|{lon:.3f}|{d.isoformat()}")
            doy = d.timetuple().tm_yday
            avg = 25 + 6 * math.sin(2 * math.pi * (doy - 105) / 365) + rng.gauss(0, 1.2)
            tmax = avg + 4 + abs(rng.gauss(0, 1.5))
            mm = _MONTH_MM[d.month - 1]
            p = min(0.8, mm / 300 + 0.05)  # chance of a rainy day
            rain = rng.expovariate(1 / max(0.1, (mm / 30) / p)) if rng.random() < p else 0.0
            out.append(DailyClimate(d, round(tmax, 1), round(avg, 1), round(rain, 1),
                                    round(min(98, 55 + mm / 12 + rng.gauss(0, 4)), 1), round(abs(rng.gauss(2.5, 0.8)), 1)))
            d += timedelta(days=1)
        return out
