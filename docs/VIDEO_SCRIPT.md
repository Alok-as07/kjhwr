# Video script (max 10 min: Part 1 about 4:30, Part 2 about 5:00)

Tip: record the screen, speak from the bullets rather than reading. Replace [numbers] with your real results.

## Part 1: Customer pitch (about 4:30)

**0:00 Hook (20s)**
"Every morning your desk commits to buying tomorrow's power. The wind forecast tells you how much you can skip buying,
but until now you couldn't see how much to trust it. This portal answers that."

**0:20 The problem (40s)**
- Day-ahead decisions are made on D-1, so you work from forecasts, not actuals.
- Over-trust the forecast and you're short and exposed to imbalance prices; under-trust it and you over-buy thermal.
- Both require knowing the *size* of typical forecast errors.

**1:00 What you see on screen (90s)**
- Open the dashboard. "For every half-hour, we show the latest forecast that existed at your bid cutoff, not a later one."
- Point at the chart: forecast line, actual line, shaded 80% range. Pick a windy day and a calm day.
- Change the date range. Change the cutoff (08:00 / 09:00 / 10:00): "if your cutoff moves, the answer updates."

**2:30 What it tells you (90s)**
- KPI cards: "In January, the typical miss was [X] MW, about [Y]% of generation. The forecast ran [high/low] by [Z] MW on average."
- "80% of the time the error stayed within [P10] to [P90] MW. That is the buffer to plan around."
- Horizon chart: "Forecasts get [N]x worse as lead time grows, so the freshest forecast before cutoff matters."
- Hour-of-day chart: "[hours] are hardest to call; consider a larger buffer there."

**4:00 Close (30s)**
"This is a pilot on one month of national wind data. Next: more months, regional data, and turning the error band into a
recommended buy volume. Happy to run it on your history."

## Part 2: Tech lead review (about 5:00)

**0:00 Overview (45s)**
- Architecture diagram on a slide: Elexon API -> fetch script -> CSV cache -> FastAPI (pandas) -> React (Recharts). One Docker image serves both.
- Why cached CSV: deterministic, no API dependency at runtime, fast on a free dyno.

**0:45 Core logic: `analysis.py` (120s)**
- `decision_cutoff`: D-1 at HH:MM in Europe/London, converted to UTC (DST-safe).
- `decision_time_forecast`: filter `publishTime <= cutoff`, take latest per `startTime`. "This is the key no-leakage rule."
- Metrics and sign convention. Why WAPE not MAPE. Why the band uses P90/P10 of error flipped.
- Horizon analysis uses all forecasts; decision-time analysis uses one per target.
- Show the unit tests, especially the post-cutoff publish being ignored.

**2:45 API and frontend (60s)**
- Endpoints: `/api/summary`, `/horizon`, `/series`, `/meta`; input validation; `lru_cache` per cutoff.
- React: three data hooks, Recharts, no state library needed at this size.

**3:45 Practices and trade-offs (60s)**
- Docker multi-stage build; README documents run and deploy; AI-use disclosure.
- Honest limitations: band not out-of-sample, hourly/half-hourly alignment by inner join, one month only.
- What I'd do next: cross-validated bands, per-regime errors (wind level), CI pipeline, caching Elexon pulls on a schedule.

**4:45 Wrap (15s)** "Everything needed to run it is in the README."
