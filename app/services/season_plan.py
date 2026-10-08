"""ENGINE 3 helpers: planting window from season months + monsoon onset + risk calendar (all thresholds in agronomy.py)."""
from app.core import agronomy as cfg
from app.services.analysis import Analysis


def planting_window(a: Analysis, season: str) -> dict:
    months = cfg.SEASON_MONTHS[season]
    n = cfg.PLANTING_WINDOW_MONTHS
    candidates = [months[i:i + n] for i in range(len(months) - n + 1)]
    onset = next((m for m, r in a.risk.items() if r["monsoon_onset"]), None)
    note = f"Chosen as the {n}-month stretch of {season} with the lowest combined heatwave and dry-spell risk in past data"
    if season == "Kharif" and onset in months:  # rain-fed crops should not start before the rains
        later = [c for c in candidates if months.index(c[0]) >= months.index(onset)]
        if later:
            candidates = later
            note += f", starting no earlier than monsoon onset ({cfg.MONTH_NAMES[onset - 1]})"

    def risk(window: list[int]) -> float:
        return sum(cfg.WINDOW_HEATWAVE_WEIGHT * a.risk[m]["heatwave_days"] + cfg.WINDOW_DRYSPELL_WEIGHT * a.risk[m]["dry_spell_likelihood"] / 10 for m in window if m in a.risk)

    best = min(candidates, key=lambda w: (risk(w), months.index(w[0])))
    warnings = []
    for m in best:
        r = a.risk.get(m)
        if not r:
            continue
        if r["heatwave_days"] >= cfg.RISK_WARN_HEATWAVE_DAYS:
            warnings.append(f"{cfg.MONTH_NAMES[m - 1]}: about {r['heatwave_days']:.1f} heatwave days on average.")
        if r["dry_spell_likelihood"] >= cfg.RISK_WARN_DRYSPELL_PCT:
            warnings.append(f"{cfg.MONTH_NAMES[m - 1]}: a dry spell of {cfg.DRY_SPELL_MIN_DAYS}+ days occurred in {r['dry_spell_likelihood']:.0f}% of past years.")
    return {"start": cfg.MONTH_NAMES[best[0] - 1], "end": cfg.MONTH_NAMES[best[-1] - 1], "note": note + ".", "risk_warnings": warnings}


def advisory_text(district: str, crop: dict, season: str, soil: str, window: dict, years: int) -> str:
    """Plain f-string template assembly (no LLM)."""
    risk = " Watch for: " + " ".join(window["risk_warnings"]) if window["risk_warnings"] else " No month in this window stands out as high-risk in past data."
    return (f"Using {years} years of climate history for {district}, {crop['name_en']} scores highest for {season} on {soil.replace('_', ' ')} soil "
            f"({crop['score']:.0f} out of 100, rated {crop['tier']}). Suggested planting window: {window['start']} to {window['end']}.{risk} "
            f"This is a rule-based estimate built on prototype assumptions, so use it as guidance and not as a guarantee.")
