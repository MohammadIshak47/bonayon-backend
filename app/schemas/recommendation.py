import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.farm import SoilType
from app.models.recommendation import RecommendationType


class CropChoiceIn(BaseModel):
    district_id: uuid.UUID
    soil_type: SoilType
    season: str = Field(min_length=1, max_length=20)


class SeasonPlanIn(BaseModel):
    """Either a plot_id, or district_id + soil_type + season (never a mix)."""
    plot_id: uuid.UUID | None = None
    district_id: uuid.UUID | None = None
    soil_type: SoilType | None = None
    season: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def _one_form(self) -> "SeasonPlanIn":
        raw = [self.district_id, self.soil_type, self.season]
        if self.plot_id and any(raw):
            raise ValueError("send either plot_id or district_id + soil_type + season, not both")
        if not self.plot_id and not all(raw):
            raise ValueError("send plot_id, or all of district_id, soil_type and season")
        return self


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: RecommendationType
    plot_id: uuid.UUID | None
    district_id: uuid.UUID
    season: str
    payload: dict[str, Any]
    explanations: list[Any]
    advisory_text: str | None
    disclaimer: str
    created_at: datetime


class RotationSuggestIn(BaseModel):
    season_1_crop_id: uuid.UUID


class RotationSuggestionOut(BaseModel):
    crop_id: uuid.UUID
    name_en: str
    name_bn: str
    explanation: str


class RotationSuggestOut(BaseModel):
    suggestions: list[RotationSuggestionOut]


class RotationPlanIn(BaseModel):
    plot_id: uuid.UUID
    season_1_crop_id: uuid.UUID
    season_2_crop_id: uuid.UUID
    note: str | None = Field(default=None, max_length=500)


class RotationPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    plot_id: uuid.UUID
    season_1_crop_id: uuid.UUID
    season_2_crop_id: uuid.UUID
    note: str | None
    created_at: datetime


class EstimateIn(BaseModel):
    crop_id: uuid.UUID
    area_decimal: float = Field(gt=0)


class EstimateOut(BaseModel):
    crop_id: uuid.UUID
    crop_name: str
    area_decimal: float
    seed_kg: float
    npk_note: str | None
    label: str


class DashboardOut(BaseModel):
    farms_count: int
    plots_count: int
    plans_count: int  # number of saved season plans
    latest_recommendation: RecommendationOut | None
    recent_recommendations: list[RecommendationOut]


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    entity: str
    entity_id: uuid.UUID | None
    created_at: datetime
