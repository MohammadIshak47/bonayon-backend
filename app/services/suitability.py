"""
ENGINE 1: transparent rule-based crop suitability.

score = 100 * (w_rain*rain_match + w_temp*temp_match + w_soil*soil_match + w_season*season_match) - risk_penalty
  range_match  = 1.0 inside [lo, hi]; outside it decays linearly to 0 at RANGE_DECAY_FRACTION * (hi - lo) away.
  soil_match   = 1 if soil is in the crop's suitable list, else SOIL_MISMATCH_MATCH.
  season_match = 1 if the season is one of the crop's seasons, else 0.
  risk_penalty = HEATWAVE_PENALTY * heatwave_month_density + DRYSPELL_PENALTY * mean_dry_spell_likelihood

DEVIATION FROM THE SPEC TEXT: the spec wrote "15 x heatwave - 10 x dryspell", which would make dry-spell risk
RAISE the score. Both risks are implemented as penalties (added) so that more risk always lowers the score.
"""
from app.core import agronomy as cfg
from app.models import Crop
from app.services.analysis import Analysis


def range_match(value: float, lo: float, hi: float) -> float:
    if lo <= value <= hi:
        return 1.0
    distance = lo - value if value < lo else value - hi
    reach = (hi - lo) * cfg.RANGE_DECAY_FRACTION
    return max(0.0, 1.0 - distance / reach) if reach > 0 else 0.0


def tier_for(score: float) -> str:
    for cutoff, name in cfg.TIERS:
        if score >= cutoff:
            return name
    return "poor"


def season_stats(a: Analysis, season: str) -> dict:
    months = cfg.SEASON_MONTHS[season]
    temps = [a.monthly[m]["temp"] for m in months if a.monthly[m]["temp"] is not None]
    heat_months = [m for m in months if m in a.risk and a.risk[m]["heatwave_days"] >= cfg.HEATWAVE_MONTH_MIN_DAYS]
    dry = [a.risk[m]["dry_spell_likelihood"] / 100 for m in months if m in a.risk]
    return {
        "annual_rain": sum(v["rain"] for v in a.monthly.values()),
        "season_temp": sum(temps) / len(temps),
        "heat_density": len(heat_months) / len(months),
        "heat_months": heat_months,
        "dry_likelihood": sum(dry) / len(dry) if dry else 0.0,
    }


def score_crops(crops: list[Crop], a: Analysis, soil: str, season: str) -> list[dict]:
    st = season_stats(a, season)
    mn = cfg.MONTH_NAMES
    results = []
    for c in crops:
        rain_m = range_match(st["annual_rain"], c.rain_min_mm, c.rain_max_mm)
        temp_m = range_match(st["season_temp"], c.temp_min_c, c.temp_max_c)
        soil_ok = soil in c.suitable_soils
        season_ok = season in c.seasons
        soil_m = 1.0 if soil_ok else cfg.SOIL_MISMATCH_MATCH
        season_m = 1.0 if season_ok else 0.0
        penalty = cfg.HEATWAVE_PENALTY * st["heat_density"] + cfg.DRYSPELL_PENALTY * st["dry_likelihood"]
        base = 100 * (cfg.WEIGHTS["rain"] * rain_m + cfg.WEIGHTS["temp"] * temp_m + cfg.WEIGHTS["soil"] * soil_m + cfg.WEIGHTS["season"] * season_m)
        score = round(min(100.0, max(0.0, base - penalty)), 1)
        rain_in, temp_in = rain_m == 1.0, temp_m == 1.0
        expl = [
            f"{'✓' if rain_in else '✗'} Annual rainfall {st['annual_rain']:,.0f} mm {'within' if rain_in else 'outside'} range {c.rain_min_mm:,.0f}–{c.rain_max_mm:,.0f} mm",
            f"{'✓' if temp_in else '✗'} {season} average temperature {st['season_temp']:.1f} °C {'within' if temp_in else 'outside'} range {c.temp_min_c:.0f}–{c.temp_max_c:.0f} °C",
            f"{'✓' if soil_ok else '✗'} {soil.replace('_', ' ').capitalize()} soil {'is' if soil_ok else 'is not'} in the suitable list" + ("" if soil_ok else f" (partial credit {cfg.SOIL_MISMATCH_MATCH:.0%})"),
            f"{'✓' if season_ok else '✗'} {season} {'is' if season_ok else 'is not'} a growing season for this crop",
        ]
        notes = []
        if st["heat_months"]:
            notes.append("Heatwave-prone months in this season: " + ", ".join(mn[m - 1] for m in st["heat_months"]) + f" (penalty {cfg.HEATWAVE_PENALTY * st['heat_density']:.1f} points).")
        if st["dry_likelihood"] > 0:
            notes.append(f"Dry spells of {cfg.DRY_SPELL_MIN_DAYS}+ days occurred in about {st['dry_likelihood'] * 100:.0f}% of past years in this season (penalty {cfg.DRYSPELL_PENALTY * st['dry_likelihood']:.1f} points)." + (" This crop is highly water-sensitive." if c.water_sensitivity.value == "high" else ""))
        results.append({"crop_id": str(c.id), "name_en": c.name_en, "name_bn": c.name_bn, "score": score, "tier": tier_for(score), "explanations": expl, "risk_notes": notes})
    results.sort(key=lambda r: (-r["score"], r["name_en"]))
    return results[: cfg.TOP_N]
