"""
ALL engine weights and thresholds live here, never inside logic.

Every value is a PROTOTYPE ASSUMPTION: FAO-informed, configurable, and open to validation by an
agriculture expert. None of this is universal agronomic truth.
"""

DISCLAIMER = "Data-based advisory, not a guarantee — consult your local agriculture officer for critical decisions."

# --- climate flags (computed when a daily record is stored) ---
HEATWAVE_TEMP_C = 35.0          # temp_max >= this => heatwave_day
DRY_DAY_MM = 1.0                # rainfall < this => a "dry" day
DRY_SPELL_MIN_DAYS = 7          # >= this many consecutive dry days => every day in the run is dry_spell

# --- aggregation ---
MIN_DAYS_PER_MONTH = 25         # a (year, month) with fewer valid days is ignored (avoids partial-month bias)
MIN_DAYS_PER_YEAR = 330         # a year with fewer valid days is ignored in anomalies
MIN_RECORDS_FOR_PROFILE = 730   # need at least ~2 years of daily data, otherwise INSUFFICIENT_DATA
MONSOON_ONSET_RAIN_MM = 50.0    # first calendar month whose average rainfall >= this

# --- seasons -> calendar months (Bangladesh, simplified to the two seasons the crop catalog uses) ---
SEASON_MONTHS: dict[str, list[int]] = {
    "Rabi": [11, 12, 1, 2],
    "Kharif": [3, 4, 5, 6, 7, 8, 9, 10],
}

# --- Engine 1: suitability ---
WEIGHTS = {"rain": 0.30, "temp": 0.25, "soil": 0.20, "season": 0.25}
SOIL_MISMATCH_MATCH = 0.3       # soil_match when soil is not in the crop's suitable list
RANGE_DECAY_FRACTION = 0.5      # match falls linearly to 0 at (range width * this) outside the range
HEATWAVE_MONTH_MIN_DAYS = 1.0   # a month counts as a "heatwave month" if avg heatwave days >= this
HEATWAVE_PENALTY = 15.0         # points * heatwave_month_density (0..1)
DRYSPELL_PENALTY = 10.0         # points * mean dry-spell likelihood (0..1)
TIERS = [(75.0, "excellent"), (55.0, "good"), (35.0, "marginal")]  # else "poor"
TOP_N = 5

# --- Engine 3: season plan ---
PLANTING_WINDOW_MONTHS = 2      # length of the suggested planting window
WINDOW_HEATWAVE_WEIGHT = 1.0    # window risk = w1 * heatwave_days + w2 * (dry_spell_likelihood / 10)
WINDOW_DRYSPELL_WEIGHT = 1.0
RISK_WARN_HEATWAVE_DAYS = 1.0   # warn if a month in the window averages >= this many heatwave days
RISK_WARN_DRYSPELL_PCT = 30.0   # warn if dry-spell likelihood >= this percent

# --- Engine 4 ---
ROTATION_EXPLANATION = (
    "Listed in the crop catalog as a next-season option after {prev} (prototype assumption). "
    "Changing crops between seasons can reduce repeated pest and nutrient pressure."
)

# --- Engine 5 ---
ESTIMATE_LABEL = "estimate — verify locally"

LIMITATIONS = [
    "Rule-based scoring with prototype assumptions, not a trained model.",
    "Rainfall is compared as an annual total; temperature as the season's average.",
    "Climate data is satellite-derived (NASA POWER) for the district headquarters location, not your field.",
    "Past climate does not predict a specific year.",
]
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
