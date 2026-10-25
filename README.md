# Wind forecast reliability portal

Web app for a UK utility's day-ahead desk: shows the latest wind forecast available at bid time next to actual
generation, and quantifies forecast error. Scope: GB national wind, Elexon BMRS only, January 2026.

> **AI disclosure:** this project was built with assistance from Claude (Anthropic) for scaffolding and code drafting.
> I reviewed, ran and own the final code. <!-- edit to describe your own usage accurately -->

**Live app:** <paste Vercel/Heroku URL here>

## Key design decision
A buyer decides on day D-1 for delivery day D. For every half-hour of D, the app uses the **latest WINDFOR forecast with
`publishTime` <= the D-1 cutoff** (default 09:00 London time, configurable in the UI). Later forecasts are ignored, as they
were not available when the decision was made. Error = forecast - actual (positive = over-forecast).

Metrics: MAE, RMSE, bias, WAPE (sum|err| / sum actual, used instead of MAPE because wind output can be near zero),
and P10/P50/P90 of error. These also give an 80% "likely actual range" band around each forecast.
Separately, error is broken down by forecast horizon (all forecasts, not just decision-time) and by hour of day.

Alignment: WINDFOR is hourly and FUELHH is half-hourly, so evaluation uses timestamps where both exist (inner join on `startTime`).

**Scope note:** WINDFOR is Elexon's forecast of peak wind generation (in MW), while FUELHH reports half-hourly, operationally metered generation by fuel type (also in MW). Elexon describes FUELHH as transmission-connected BMU generation and excludes embedded wind. The WINDFOR dataset description does not make embedded-wind coverage explicit, so identical scope cannot be confirmed; interpret the comparison as forecast versus FUELHH metered outturn, with the possibility of a scope contribution to any bias.

## Layout
```
backend/app/analysis.py    cutoff logic, error metrics (pure pandas, unit-tested)
backend/app/elexon.py      Elexon API client
backend/app/main.py        FastAPI endpoints (/api/meta, /summary, /horizon, /series); serves built UI in Docker
backend/scripts/fetch_data.py   downloads Jan 2026 data to backend/data/*.csv (--synthetic for offline dev only)
backend/tests/             unit tests
frontend/src/              React (Vite + Recharts) dashboard
Dockerfile, docker-compose.yml, heroku.yml
docs/VIDEO_SCRIPT.md       demo video script
```

## Run it
```bash
# 1. get data (commit the CSVs so deployment needs no network)
cd backend && pip install -r requirements.txt
python -m scripts.fetch_data

# 2a. Docker (UI + API on http://localhost:8000)
cd .. && docker compose up --build

# 2b. or dev mode
cd backend && uvicorn app.main:app --reload      # terminal 1
cd frontend && npm install && npm run dev        # terminal 2 -> http://localhost:5173

# tests
cd backend && pytest
```

## Deploy (Heroku, container stack)
```bash
heroku create && heroku stack:set container
git push heroku main
```
Vercel does not run Docker containers, so Heroku (or Render/Fly) is the straightforward fit for this Dockerfile.

## Limitations
- The 80% band is fitted on the same month it describes (descriptive, not out-of-sample).
- One month of data; no weather inputs; national level only.
