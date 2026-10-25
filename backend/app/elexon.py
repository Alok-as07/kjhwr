"""Thin client for the Elexon BMRS stream endpoints.

NOTE: parameter names follow the BMRS API docs as I understand them; check them
against https://bmrs.elexon.co.uk/api-documentation if a call returns 400.
"""
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import requests

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"


def _get(dataset: str, params: dict) -> list[dict]:
    r = requests.get(f"{BASE}/{dataset}/stream", params={**params, "format": "json"}, timeout=90)
    r.raise_for_status()
    return r.json()


def fetch_actuals(start: date, end: date, step_days: int = 7) -> pd.DataFrame:
    rows, d = [], start
    while d <= end:
        chunk_end = min(d + timedelta(days=step_days - 1), end)
        rows += _get("FUELHH", {"settlementDateFrom": d.isoformat(), "settlementDateTo": chunk_end.isoformat(), "fuelType": ["WIND"]})
        d = chunk_end + timedelta(days=1)
    df = pd.DataFrame(rows)
    df = df[df["fuelType"] == "WIND"]
    df = df.rename(columns={"generation": "actual"})[["startTime", "actual"]]
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    return df.drop_duplicates("startTime").sort_values("startTime")


def fetch_forecasts(publish_start: date, publish_end: date) -> pd.DataFrame:
    rows, d = [], publish_start
    while d <= publish_end:
        frm = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        to = frm + timedelta(days=1)
        rows += _get("WINDFOR", {"publishDateTimeFrom": frm.strftime("%Y-%m-%dT%H:%M:%SZ"), "publishDateTimeTo": to.strftime("%Y-%m-%dT%H:%M:%SZ")})
        d += timedelta(days=1)
    df = pd.DataFrame(rows).rename(columns={"generation": "forecast"})[["startTime", "publishTime", "forecast"]]
    for c in ("startTime", "publishTime"):
        df[c] = pd.to_datetime(df[c], utc=True)
    return df.drop_duplicates(["startTime", "publishTime"]).sort_values(["startTime", "publishTime"])
