import { useEffect, useState } from "react";
import {
  Area, Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "./api";

const CUTOFFS = ["08:00", "09:00", "10:00"];
const mw = (v) => (v == null ? "–" : `${Math.round(v).toLocaleString()} MW`);
const pct = (v) => (v == null ? "–" : `${(v * 100).toFixed(1)}%`);
const fmtTick = (iso) => new Date(iso).toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "Europe/London" });

function Stat({ label, value, hint }) {
  return (
    <div className="stat">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      <div className="stat-hint">{hint}</div>
    </div>
  );
}

export default function App() {
  const [meta, setMeta] = useState(null);
  const [cutoff, setCutoff] = useState("09:00");
  const [range, setRange] = useState({ start: "", end: "" });
  const [summary, setSummary] = useState(null);
  const [horizon, setHorizon] = useState([]);
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => { api.meta().then((d) => { setMeta(d); setRange({ start: d.from, end: d.to }); }).catch((e) => setError(e.message)); api.horizon().then(setHorizon).catch((e) => setError(e.message)); }, []);
  useEffect(() => { api.summary(cutoff).then(setSummary).catch((e) => setError(e.message)); }, [cutoff]);
  useEffect(() => {
    if (range.start && range.end && range.start <= range.end)
      api.series(range.start, range.end, cutoff).then((r) => setRows(r.rows.map((d) => ({ ...d, band: [d.low, d.high] })))).catch((e) => setError(e.message));
  }, [range, cutoff]);

  const m = summary?.metrics;
  const periodLabel = meta?.from && meta?.to
    ? `${new Date(`${meta.from}T12:00:00`).toLocaleDateString("en-GB", { month: "long", year: "numeric" })}${meta.from.slice(0, 7) !== meta.to.slice(0, 7) ? ` – ${new Date(`${meta.to}T12:00:00`).toLocaleDateString("en-GB", { month: "long", year: "numeric" })}` : ""}`
    : "";
  if (error) return <main className="page"><p className="error">Could not load data: {error}. Check that the backend is running and data/*.csv exists.</p></main>;

  return (
    <main className="page">
      <header>
        <h1>How far can you trust tomorrow's wind forecast?</h1>
        <p className="lede">
          For every half-hour of delivery, we use the latest forecast that existed when you had to place your
          day-ahead bid, and compare it with what the wind farms actually generated. Great Britain, wind only, {periodLabel}.
        </p>
        <label className="control">
          Bid decision time (D-1, London)
          <select value={cutoff} onChange={(e) => setCutoff(e.target.value)}>
            {CUTOFFS.map((c) => <option key={c}>{c}</option>)}
          </select>
        </label>
      </header>

      {m && (
        <section className="stats" aria-label="Accuracy at decision time">
          <Stat label="Typical miss (MAE)" value={mw(m.mae)} hint={`${pct(m.wape)} of generation`} />
          <Stat label="Large-miss size (RMSE)" value={mw(m.rmse)} hint="punishes big errors" />
          <Stat label="Bias" value={mw(m.bias)} hint={m.bias > 0 ? "forecast runs high" : "forecast runs low"} />
          <Stat label="80% of errors fall between" value={`${Math.round(m.p10).toLocaleString()} to ${Math.round(m.p90).toLocaleString()}`} hint="MW, forecast − actual" />
        </section>
      )}

      <p className="note">Scope note: FUELHH reports operationally metered, transmission-connected generation and excludes embedded wind. WINDFOR is Elexon’s peak wind generation forecast; its dataset description does not specify whether embedded wind is included, so the two series may differ in scope.</p>

      <section>
        <div className="section-head">
          <h2>Forecast you had vs. what happened</h2>
          <div className="range">
            <input type="date" aria-label="From" min={meta?.from} max={meta?.to} value={range.start} onChange={(e) => setRange({ ...range, start: e.target.value })} />
            <span>to</span>
            <input type="date" aria-label="To" min={meta?.from} max={meta?.to} value={range.end} onChange={(e) => setRange({ ...range, end: e.target.value })} />
          </div>
        </div>
        <p className="note">The shaded band is where actual generation landed 80% of the time, given this forecast.</p>
        <div className="chart tall">
          <ResponsiveContainer>
            <ComposedChart data={rows}>
              <CartesianGrid stroke="#d9e1e5" vertical={false} />
              <XAxis dataKey="startTime" tickFormatter={fmtTick} minTickGap={60} />
              <YAxis tickFormatter={(v) => `${v / 1000}k`} width={44} label={{ value: "MW", angle: -90, position: "insideLeft" }} />
              <Tooltip labelFormatter={fmtTick} formatter={(v) => (Array.isArray(v) ? `${Math.round(v[0])} to ${Math.round(v[1])} MW` : `${Math.round(v)} MW`)} />
              <Legend />
              <Area dataKey="band" name="Likely range (80%)" stroke="none" fill="#b9cdf2" fillOpacity={0.6} isAnimationActive={false} />
              <Line dataKey="forecast" name="Forecast at decision time" stroke="#3b3fa8" dot={false} strokeWidth={2} isAnimationActive={false} />
              <Line dataKey="actual" name="Actual" stroke="#0e8a7b" dot={false} strokeWidth={2} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="two">
        <div>
          <h2>Accuracy drops as the horizon grows</h2>
          <p className="note">Mean absolute error by how long before delivery the forecast was published.</p>
          <div className="chart">
            <ResponsiveContainer>
              <BarChart data={horizon}>
                <CartesianGrid stroke="#d9e1e5" vertical={false} />
                <XAxis dataKey="label" /><YAxis width={44} tickFormatter={(v) => `${v / 1000}k`} />
                <Tooltip formatter={(v) => mw(v)} />
                <Bar dataKey="mae" name="MAE" fill="#3b3fa8" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div>
          <h2>Which hours are hardest to call</h2>
          <p className="note">Mean absolute error by hour of delivery day (London time).</p>
          <div className="chart">
            <ResponsiveContainer>
              <BarChart data={summary?.hourly || []}>
                <CartesianGrid stroke="#d9e1e5" vertical={false} />
                <XAxis dataKey="hour" /><YAxis width={44} tickFormatter={(v) => `${v / 1000}k`} />
                <Tooltip formatter={(v) => mw(v)} />
                <Bar dataKey="mae" name="MAE" fill="#0e8a7b" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <footer>
        Data: Elexon BMRS (FUELHH actuals, WINDFOR forecasts). Error = forecast − actual. The 80% band is calibrated on the
        same period it describes, so treat it as descriptive, not a guarantee.
      </footer>
    </main>
  );
}
