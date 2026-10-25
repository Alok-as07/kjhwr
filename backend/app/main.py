import re
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from . import analysis

app = FastAPI(title="Wind forecast accuracy portal")
CUTOFF_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@lru_cache(maxsize=1)
def _data():
    return analysis.load_data()


@lru_cache(maxsize=32)
def _eval(cutoff: str):
    act, fc = _data()
    return analysis.evaluation_frame(act, fc, cutoff)


def _cutoff(c: str) -> str:
    if not CUTOFF_RE.match(c):
        raise HTTPException(422, "cutoff must be HH:MM (London time)")
    return c


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    act, _ = _data()
    return {"from": act["startTime"].min().strftime("%Y-%m-%d"), "to": act["startTime"].max().strftime("%Y-%m-%d"), "default_cutoff": "09:00"}


@app.get("/api/summary")
def summary(cutoff: str = "09:00"):
    df = _eval(_cutoff(cutoff))
    return {"cutoff": cutoff, "metrics": analysis.summary_metrics(df), "hourly": analysis.hourly_metrics(df)}


@app.get("/api/horizon")
def horizon():
    act, fc = _data()
    return analysis.horizon_metrics(act, fc)


@app.get("/api/series")
def series(start: str = Query(...), end: str = Query(...), cutoff: str = "09:00"):
    if not (DATE_RE.match(start) and DATE_RE.match(end)):
        raise HTTPException(422, "start/end must be YYYY-MM-DD")
    df = _eval(_cutoff(cutoff))
    m = analysis.summary_metrics(df)
    return {"cutoff": cutoff, "rows": analysis.series(df, start, end, m["p10"], m["p90"])}


STATIC = Path(__file__).resolve().parent.parent / "static"
if STATIC.exists():  # present in the Docker image (built React app)
    app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
