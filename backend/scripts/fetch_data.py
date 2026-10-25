"""Download January 2026 data from Elexon and cache it as CSV.

    python -m scripts.fetch_data                # real data (needs internet)
    python -m scripts.fetch_data --synthetic    # fake data, ONLY for dev/testing
"""
import argparse
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "data"
MONTH_START = pd.Timestamp("2026-01-01T00:00:00Z")
MONTH_END = pd.Timestamp("2026-02-01T00:00:00Z")
PUBLISH_START = pd.Timestamp("2025-12-25T00:00:00Z")


def restrict_january(act: pd.DataFrame, fc: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep January delivery timestamps and only the requested forecast vintages."""
    act = act[(act["startTime"] >= MONTH_START) & (act["startTime"] < MONTH_END)].copy()
    fc = fc[
        (fc["startTime"] >= MONTH_START)
        & (fc["startTime"] < MONTH_END)
        & (fc["publishTime"] >= PUBLISH_START)
        & (fc["publishTime"] < MONTH_END)
    ].copy()
    return act, fc


def synthetic() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(42)
    idx = pd.date_range("2026-01-01", "2026-02-01", freq="30min", tz="UTC", inclusive="left")
    walk = np.cumsum(rng.normal(0, 150, len(idx)))
    truth = np.clip(8000 + 3500 * np.sin(walk / 3000) + (walk * 0.2) % 2000, 200, 20000)
    act = pd.DataFrame({"startTime": idx, "actual": truth.round(0)})
    lookup = act.set_index("startTime")["actual"]
    rows = []
    for p in pd.date_range("2025-12-25", "2026-02-01", freq="6h", tz="UTC", inclusive="left"):
        for h in range(1, 73):
            t = p + pd.Timedelta(hours=h)
            if t in lookup.index and t.minute == 0:
                rows.append((t, p, max(0.0, lookup[t] + rng.normal(0, 150 + 45 * h))))
    fc = pd.DataFrame(rows, columns=["startTime", "publishTime", "forecast"])
    fc["forecast"] = fc["forecast"].round(0)
    return act, fc


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    if a.synthetic:
        act, fc = synthetic()
    else:
        from app import elexon  # imported lazily so --synthetic works offline

        act = elexon.fetch_actuals(date(2026, 1, 1), date(2026, 1, 31))
        fc = elexon.fetch_forecasts(date(2025, 12, 25), date(2026, 1, 31))
    act, fc = restrict_january(act, fc)
    act.to_csv(OUT / "actuals.csv", index=False)
    fc.to_csv(OUT / "forecasts.csv", index=False)
    print(f"actuals: {len(act)} rows, forecasts: {len(fc)} rows -> {OUT}")
