import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.agronomy import SEASON_MONTHS
from app.models.crop import WaterSensitivity
from app.models.farm import SoilType


class DistrictOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name_en: str
    name_bn: str
    division: str
    lat: float
    lon: float


class CropOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name_en: str
    name_bn: str
    seasons: list[str]
    rain_min_mm: float
    rain_max_mm: float
    temp_min_c: float
    temp_max_c: float
    suitable_soils: list[str]
    water_sensitivity: WaterSensitivity
    rotation_after: list[str]
    seed_kg_per_decimal: float
    npk_note: str | None
    is_active: bool


class CropIn(BaseModel):
    name_en: str = Field(min_length=2, max_length=80)
    name_bn: str = Field(min_length=1, max_length=80)
    seasons: list[str] = Field(min_length=1)
    rain_min_mm: float
    rain_max_mm: float
    temp_min_c: float
    temp_max_c: float
    suitable_soils: list[SoilType] = Field(min_length=1)
    water_sensitivity: WaterSensitivity
    rotation_after: list[str] = []
    seed_kg_per_decimal: float = Field(gt=0)
    npk_note: str | None = None
    is_active: bool = True

    @field_validator("seasons")
    @classmethod
    def _seasons(cls, v: list[str]) -> list[str]:
        bad = [s for s in v if s not in SEASON_MONTHS]
        if bad:
            raise ValueError(f"unknown season(s) {bad}; allowed: {list(SEASON_MONTHS)}")
        return v

    @model_validator(mode="after")
    def _ranges(self) -> "CropIn":
        if self.rain_max_mm <= self.rain_min_mm or self.temp_max_c <= self.temp_min_c:
            raise ValueError("max must be greater than min for rainfall and temperature ranges")
        return self


class CropPatch(BaseModel):
    """Partial update; any subset of CropIn fields."""
    name_en: str | None = None
    name_bn: str | None = None
    seasons: list[str] | None = None
    rain_min_mm: float | None = None
    rain_max_mm: float | None = None
    temp_min_c: float | None = None
    temp_max_c: float | None = None
    suitable_soils: list[SoilType] | None = None
    water_sensitivity: WaterSensitivity | None = None
    rotation_after: list[str] | None = None
    seed_kg_per_decimal: float | None = Field(default=None, gt=0)
    npk_note: str | None = None
    is_active: bool | None = None
