import uuid

import pytest

from app.core import agronomy as cfg
from app.models import Crop, WaterSensitivity
from app.services.analysis import Analysis
from app.services.suitability import range_match, score_crops, tier_for


def crop(**kw) -> Crop:
    base = dict(id=uuid.uuid4(), name_en="Test Rice", name_bn="ধান", seasons=["Rabi"], rain_min_mm=1200, rain_max_mm=2200,
                temp_min_c=20, temp_max_c=35, suitable_soils=["clay"], water_sensitivity=WaterSensitivity.high,
                rotation_after=[], seed_kg_per_decimal=0.3, npk_note=None, is_active=True)
    base.update(kw)
    return Crop(**base)


def analysis(annual_rain=1800.0, temp=25.0, heat_days=0.0, dry_pct=0.0) -> Analysis:
    monthly = {m: {"temp": temp, "rain": annual_rain / 12} for m in range(1, 13)}
    risk = {m: {"month": m, "heatwave_days": heat_days, "dry_spell_likelihood": dry_pct, "monsoon_onset": m == 5} for m in range(1, 13)}
    return Analysis(bundle=None, monthly=monthly, risk=risk, basis_years=20)  # type: ignore[arg-type]


def top(c, a=None, soil="clay", season="Rabi"):
    return score_crops([c], a or analysis(), soil, season)[0]


def test_perfect_match_scores_100_and_is_excellent():
    r = top(crop())
    assert r["score"] == 100.0 and r["tier"] == "excellent"


def test_explanations_cover_every_factor_with_marks():
    r = top(crop())
    assert len(r["explanations"]) == 4 and all(e.startswith("✓") for e in r["explanations"])
    assert "1,800 mm" in r["explanations"][0] and "1,200–2,200" in r["explanations"][0]


def test_rainfall_outside_range_penalizes_and_is_explained():
    r = top(crop(), analysis(annual_rain=900))
    assert r["score"] < 100 and r["explanations"][0].startswith("✗")


def test_further_outside_range_scores_lower():
    near, far = top(crop(), analysis(annual_rain=1000))["score"], top(crop(), analysis(annual_rain=500))["score"]
    assert far < near < 100


def test_wrong_season_loses_the_season_weight():
    r = top(crop(), season="Kharif")
    assert r["score"] == pytest.approx(100 - 100 * cfg.WEIGHTS["season"], abs=0.1)
    assert r["explanations"][3].startswith("✗")


def test_unsuitable_soil_gets_partial_credit_not_zero():
    r = top(crop(), soil="sandy")
    assert r["score"] == pytest.approx(100 - 100 * cfg.WEIGHTS["soil"] * (1 - cfg.SOIL_MISMATCH_MATCH), abs=0.1)
    assert r["explanations"][2].startswith("✗") and "partial credit" in r["explanations"][2]


def test_heatwave_and_dry_spell_risk_lower_the_score():
    clean = top(crop())["score"]
    hot = top(crop(), analysis(heat_days=3))
    dry = top(crop(), analysis(dry_pct=50))
    assert hot["score"] == pytest.approx(clean - cfg.HEATWAVE_PENALTY, abs=0.1) and hot["risk_notes"]
    assert dry["score"] == pytest.approx(clean - cfg.DRYSPELL_PENALTY * 0.5, abs=0.1) and dry["risk_notes"]


def test_dry_spell_never_raises_a_score():  # guards the sign fix documented in suitability.py
    assert top(crop(), analysis(dry_pct=80))["score"] <= top(crop(), analysis(dry_pct=0))["score"]


def test_score_is_clamped_to_0_100():
    worst = top(crop(seasons=["Kharif"], suitable_soils=["peat"], rain_min_mm=5000, rain_max_mm=6000, temp_min_c=-20, temp_max_c=-10), analysis(heat_days=5, dry_pct=100))
    assert 0 <= worst["score"] <= 5


def test_ranking_is_descending_and_limited_to_top_five():
    crops = [crop(name_en=f"Crop {i}", rain_min_mm=1200 - i * 300, rain_max_mm=1300 - i * 300) for i in range(8)]
    ranked = score_crops(crops, analysis(), "clay", "Rabi")
    assert len(ranked) == cfg.TOP_N and [r["score"] for r in ranked] == sorted((r["score"] for r in ranked), reverse=True)


@pytest.mark.parametrize("score,tier", [(100, "excellent"), (75, "excellent"), (74.9, "good"), (55, "good"), (54.9, "marginal"), (35, "marginal"), (34.9, "poor"), (0, "poor")])
def test_tier_boundaries(score, tier):
    assert tier_for(score) == tier


def test_range_match_shape():
    assert range_match(5, 0, 10) == 1.0 and range_match(0, 0, 10) == 1.0 and range_match(10, 0, 10) == 1.0
    assert range_match(12.5, 0, 10) == pytest.approx(0.5)   # halfway to the decay reach (5 units)
    assert range_match(100, 0, 10) == 0.0
