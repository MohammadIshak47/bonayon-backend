import pandas as pd

from app.services.risk_calendar import build_risk_calendar
from app.utils.anomalies import yearly_anomalies
from app.utils.monthly import monthly_table


def synthetic(years=(2000, 2001, 2002), monthly_rain=None, heat_days=None, dry_years=None) -> pd.DataFrame:
    """28 days per month; rainfall spread evenly so each month's total equals monthly_rain[m]."""
    monthly_rain, heat_days, dry_years = monthly_rain or {}, heat_days or {}, dry_years or {}
    rows = []
    for y in years:
        for m in range(1, 13):
            for d in range(28):
                rows.append({"year": y, "month": m, "rainfall_mm": monthly_rain.get(m, 10) / 28, "temp_avg": 25.0,
                             "heatwave_day": d < heat_days.get(m, 0), "dry_spell": (y in dry_years.get(m, ())) and d < 7})
    return pd.DataFrame(rows)


def test_monthly_table_drops_partial_months():
    frame = synthetic()
    frame = frame[~((frame.year == 2000) & (frame.month == 1) & (frame.index % 28 > 10))]  # only 11 days left in Jan 2000
    t = monthly_table(frame)
    assert len(t[(t.year == 2000) & (t.month == 1)]) == 0 and len(t) == 35


def test_heatwave_days_are_averaged_per_month_across_years():
    cal, basis = build_risk_calendar(monthly_table(synthetic(heat_days={4: 4, 5: 2})))
    by = {r["month"]: r for r in cal}
    assert by[4]["heatwave_days"] == 4.0 and by[5]["heatwave_days"] == 2.0 and by[1]["heatwave_days"] == 0.0 and basis == 3


def test_dry_spell_likelihood_is_percent_of_years_with_a_spell():
    cal, _ = build_risk_calendar(monthly_table(synthetic(dry_years={2: (2000, 2001)})))
    by = {r["month"]: r for r in cal}
    assert by[2]["dry_spell_likelihood"] == 66.7 and by[3]["dry_spell_likelihood"] == 0.0


def test_monsoon_onset_is_the_first_month_reaching_50mm_and_only_one():
    rain = {4: 49.0, 5: 50.0, 6: 300.0, 7: 400.0}
    cal, _ = build_risk_calendar(monthly_table(synthetic(monthly_rain=rain)))
    onsets = [r["month"] for r in cal if r["monsoon_onset"]]
    assert onsets == [5]  # 49 mm in April is below the threshold; 50 mm in May counts; later months are not flagged


def test_a_month_without_complete_data_is_omitted_not_invented():
    frame = synthetic()
    frame = frame[frame.month != 3]
    cal, _ = build_risk_calendar(monthly_table(frame))
    assert 3 not in {r["month"] for r in cal} and len(cal) == 11


def test_yearly_anomalies_vs_baseline():
    rows = []
    for y, rain, temp in [(2001, 1000.0, 24.0), (2002, 1200.0, 25.0), (2003, 800.0, 26.0)]:
        for d in range(365):
            rows.append({"year": y, "rainfall_mm": rain / 365, "temp_avg": temp})
    out, baseline = yearly_anomalies(pd.DataFrame(rows), 2)
    assert baseline == 3 and [o["year"] for o in out] == [2002, 2003]
    assert out[0]["rainfall_anomaly_pct"] == 20.0 and out[1]["rainfall_anomaly_pct"] == -20.0
    assert out[0]["temp_anomaly_c"] == 0.0 and out[1]["temp_anomaly_c"] == 1.0


def test_incomplete_years_are_ignored_in_anomalies():
    frame = pd.DataFrame([{"year": 2001, "rainfall_mm": 1.0, "temp_avg": 20.0}] * 100)
    assert yearly_anomalies(frame, 5) == ([], 0)
