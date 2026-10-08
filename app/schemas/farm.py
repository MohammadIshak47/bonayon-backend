import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.farm import SoilType


class FarmIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    district_id: uuid.UUID
    upazila: str | None = Field(default=None, max_length=80)


class FarmPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    district_id: uuid.UUID | None = None
    upazila: str | None = Field(default=None, max_length=80)


class FarmOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    district_id: uuid.UUID
    upazila: str | None
    created_at: datetime


class PlotIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    area_decimal: float = Field(gt=0)
    soil_type: SoilType
    crop_id: uuid.UUID | None = None
    planting_date: date | None = None
    season: str | None = Field(default=None, max_length=20)


class PlotPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    area_decimal: float | None = Field(default=None, gt=0)
    soil_type: SoilType | None = None
    crop_id: uuid.UUID | None = None
    planting_date: date | None = None
    season: str | None = Field(default=None, max_length=20)


class PlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    farm_id: uuid.UUID
    name: str
    area_decimal: float
    soil_type: SoilType
    crop_id: uuid.UUID | None
    planting_date: date | None
    season: str | None
    created_at: datetime
