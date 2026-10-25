"""Core analysis: decision-time forecast selection and accuracy metrics.

Sign convention: error = forecast - actual (positive = over-forecast).
"""
from pathlib import Path

import numpy as np
import pandas as pd

LONDON = "Europe/London"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HORIZON_BINS = [0, 6, 12, 18, 24, 36, 48, 72]


def load_data(data_dir: Path = DATA_DIR) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (actuals, forecasts). Actuals: startTime, actual. Forecasts: startTime, publishTime, forecast."""
    act = pd.read_csv(data_dir / "actuals.csv")
    fc = pd.read_csv(data_dir / "forecasts.csv")
    act["startTime"] = pd.to_datetime(act["startTime"], utc=True)
    for c in ("startTime", "publishTime"):
        fc[c] = pd.to_datetime(fc[c], utc=True)
    return act, fc


def decision_cutoff(start_time: pd.Series, cutoff: str = "09:00") -> pd.Series:
    """For each delivery timestamp, the UTC instant of the D-1 decision cutoff.

    D is the Europe/London calendar date of the delivery half-hour; the cutoff is
    `cutoff` (HH:MM, London time) on D-1.
    """
    hh, mm = (int(x) for x in cutoff.split(":"))
    local_naive = start_time.dt.tz_convert(LONDON).dt.tz_localize(None)
    cut_naive = local_naive.dt.normalize() - pd.Timedelta(days=1) + pd.Timedelta(hours=hh, minutes=mm)
    return cut_naive.dt.tz_localize(LONDON, ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("UTC")


def decision_time_forecast(fc: pd.DataFrame, cutoff: str = "09:00") -> pd.DataFrame:
    """Latest forecast per target time that was published at or before the D-1 cutoff."""
    df = fc.copy()
    df["cutoff"] = decision_cutoff(df["startTime"], cutoff)
    df = df[df["publishTime"] <= df["cutoff"]]
    df = df.sort_values("publishTime").groupby("startTime", as_index=False).last()
    return df[["startTime", "publishTime", "forecast"]]


def evaluation_frame(act: pd.DataFrame, fc: pd.DataFrame, cutoff: str = "09:00") -> pd.DataFrame:
    dec = decision_time_forecast(fc, cutoff)
    df = dec.merge(act, on="startTime", how="inner").sort_values("startTime")
    df["error"] = df["forecast"] - df["actual"]
    return df.reset_index(drop=True)


def _metrics(err: pd.Series, actual: pd.Series) -> dict:
    if len(err) == 0:
        return {"n": 0}
    return {
        "n": int(len(err)),
        "mae": float(err.abs().mean()),
        "rmse": float(np.sqrt((err**2).mean())),
        "bias": float(err.mean()),
        "wape": float(err.abs().sum() / actual.sum()) if actual.sum() else None,
        "p10": float(err.quantile(0.10)),
        "p50": float(err.quantile(0.50)),
        "p90": float(err.quantile(0.90)),
    }


def summary_metrics(df: pd.DataFrame) -> dict:
    return _metrics(df["error"], df["actual"])


def hourly_metrics(df: pd.DataFrame) -> list[dict]:
    hour = df["startTime"].dt.tz_convert(LONDON).dt.hour
    out = []
    for h, g in df.groupby(hour):
        m = _metrics(g["error"], g["actual"])
        out.append({"hour": int(h), "mae": m["mae"], "bias": m["bias"], "n": m["n"]})
    return out


def horizon_metrics(act: pd.DataFrame, fc: pd.DataFrame) -> list[dict]:
    """Error by forecast horizon (startTime - publishTime), using every published forecast."""
    df = fc.merge(act, on="startTime", how="inner")
    df["horizon_h"] = (df["startTime"] - df["publishTime"]).dt.total_seconds() / 3600
    df = df[(df["horizon_h"] >= 0) & (df["horizon_h"] < HORIZON_BINS[-1])].copy()
    df["error"] = df["forecast"] - df["actual"]
    df["bin"] = pd.cut(df["horizon_h"], HORIZON_BINS, right=False)
    out = []
    for b, g in df.groupby("bin", observed=True):
        m = _metrics(g["error"], g["actual"])
        out.append({"label": f"{int(b.left)}-{int(b.right)}h", "mae": m["mae"], "rmse": m["rmse"], "bias": m["bias"], "n": m["n"]})
    return out


def series(df: pd.DataFrame, start: str, end: str, p10: float, p90: float) -> list[dict]:
    """Rows for [start, end] (London dates, inclusive) with an actual-generation band.

    actual = forecast - error, so P10/P90 of actual come from P90/P10 of error.
    """
    local_date = df["startTime"].dt.tz_convert(LONDON).dt.strftime("%Y-%m-%d")
    d = df[(local_date >= start) & (local_date <= end)].copy()
    d["low"] = (d["forecast"] - p90).clip(lower=0)
    d["high"] = d["forecast"] - p10
    d["startTime"] = d["startTime"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    d["publishTime"] = d["publishTime"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return d[["startTime", "publishTime", "actual", "forecast", "low", "high"]].round(1).to_dict("records")
