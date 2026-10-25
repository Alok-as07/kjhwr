import pandas as pd

from app import analysis
from scripts.fetch_data import restrict_january


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def make_fc():
    # Target 2026-01-10 12:00 UTC. In January London == UTC, so the 09:00 cutoff on D-1 is 2026-01-09 09:00 UTC.
    return pd.DataFrame(
        {
            "startTime": [ts("2026-01-10 12:00")] * 3,
            "publishTime": [ts("2026-01-09 06:00"), ts("2026-01-09 08:59"), ts("2026-01-09 09:30")],
            "forecast": [100.0, 120.0, 999.0],
        }
    )


def test_decision_forecast_ignores_post_cutoff_publishes():
    out = analysis.decision_time_forecast(make_fc(), "09:00")
    assert len(out) == 1
    assert out.iloc[0]["forecast"] == 120.0  # latest at/before cutoff, never the 09:30 publish


def test_earlier_cutoff_picks_earlier_forecast():
    out = analysis.decision_time_forecast(make_fc(), "07:00")
    assert out.iloc[0]["forecast"] == 100.0


def test_error_sign_and_metrics():
    act = pd.DataFrame({"startTime": [ts("2026-01-10 12:00")], "actual": [100.0]})
    df = analysis.evaluation_frame(act, make_fc(), "09:00")
    assert df.iloc[0]["error"] == 20.0  # over-forecast is positive
    m = analysis.summary_metrics(df)
    assert m["mae"] == 20.0 and m["bias"] == 20.0 and m["n"] == 1


def test_horizon_bins():
    act = pd.DataFrame({"startTime": [ts("2026-01-10 12:00")], "actual": [100.0]})
    labels = {r["label"] for r in analysis.horizon_metrics(act, make_fc())}
    assert labels == {"24-36h"}  # 26.5h, 27h and 30h horizons


def test_restrict_january_delivery_and_forecast_publication_window():
    act = pd.DataFrame({"startTime": pd.to_datetime([
        "2025-12-31T23:30:00Z", "2026-01-01T00:00:00Z", "2026-01-31T23:30:00Z", "2026-02-01T00:00:00Z"
    ]), "actual": [1, 2, 3, 4]})
    fc = pd.DataFrame({
        "startTime": pd.to_datetime([
            "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z",
            "2026-01-31T23:30:00Z", "2026-02-01T00:00:00Z"
        ]),
        "publishTime": pd.to_datetime([
            "2025-12-24T23:59:00Z", "2025-12-25T00:00:00Z", "2026-02-01T00:00:00Z",
            "2026-01-31T23:59:00Z", "2026-01-31T23:59:00Z"
        ]),
        "forecast": [1, 2, 3, 4, 5],
    })
    actuals, forecasts = restrict_january(act, fc)
    assert actuals.actual.tolist() == [2, 3]
    assert forecasts.forecast.tolist() == [2, 4]
