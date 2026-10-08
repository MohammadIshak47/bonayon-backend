import uuid
from datetime import date, datetime

from pydantic import BaseModel


class MonthOut(BaseModel):
    month: int
    temp_avg: float | None
    rainfall_mm: float | None


class DataSpan(BaseModel):
    start: date
    end: date


class ProfileOut(BaseModel):
    district_id: uuid.UUID
    years: int
    months: list[MonthOut]
    annual_rainfall_mm: float | None = None
    mean_temp_c: float | None = None
    data_span: DataSpan | None = None
    fetched_at: datetime | None = None
    stale: bool = False
    source: str
    insufficient_data: bool = False


class RiskMonthOut(BaseModel):
    month: int
    heatwave_days: float
    dry_spell_likelihood: float  # percent of years (0-100)
    monsoon_onset: bool


class RiskCalendarOut(BaseModel):
    district_id: uuid.UUID
    months: list[RiskMonthOut]
    basis_years: int | None = None
    fetched_at: datetime | None = None
    stale: bool = False
    source: str
    insufficient_data: bool = False


class AnomalyYearOut(BaseModel):
    year: int
    temp_anomaly_c: float | None
    rainfall_anomaly_pct: float | None


class AnomaliesOut(BaseModel):
    district_id: uuid.UUID
    years: list[AnomalyYearOut]
    baseline_years: int | None = None
    fetched_at: datetime | None = None
    stale: bool = False
    source: str
    insufficient_data: bool = False
