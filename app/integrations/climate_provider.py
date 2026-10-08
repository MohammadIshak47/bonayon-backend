from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


class ProviderError(Exception):
    """The climate source failed or returned data in an unexpected shape."""


@dataclass(frozen=True)
class DailyClimate:
    date: date
    temp_max: float | None
    temp_avg: float | None
    rainfall_mm: float | None
    humidity: float | None
    wind_speed: float | None


class ClimateProvider(ABC):
    name: str = "unknown"

    @abstractmethod
    def fetch_daily(self, lat: float, lon: float, start: date, end: date) -> list[DailyClimate]:
        """Daily records for [start, end] inclusive. Raise ProviderError on any failure."""
