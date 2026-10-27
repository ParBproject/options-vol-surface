import { useEffect, useMemo, useState } from "react";
import { XYChart, useWidth } from "./charts.jsx";
import Surface3D from "./Surface3D.jsx";
import { bsPrice, calendarGrid, forward, gFunction, greeks, linspace, sviVol } from "./volmath.js";

const pct = (x, d = 1) => `${(x * 100).toFixed(d)}%`;
const GREEKS = { delta: "Delta", gamma: "Gamma", vega: "Vega", theta: "Theta", rho: "Rho" };

function CalendarHeat({ slices, grid }) {
  const [ref, W] = useWidth();
  const d = calendarGrid(slices, grid);
  const mx = Math.max(...d.flat().map(Math.abs));
  const L = 110, Rp = 16, cw = (W - L - Rp) / grid.length, ch = 18;
  const quoted = (i, k) => [slices[i], slices[i + 1]].every((s) => k >= s.k_quoted_min && k <= s.k_quoted_max);
  return (
    <div ref={ref}>
      <svg viewBox={`0 0 ${W} ${d.length * ch + 28}`} width="100%" role="img"
        aria-label="Calendar check heatmap: change in total variance between consecutive expiries; red cells are violations">
        {d.map((row, i) => (
          <g key={i}>
            <text x={L - 6} y={i * ch + 13} textAnchor="end">{slices[i].days}d→{slices[i + 1].days}d</text>
            {row.map((v, j) => (
              <rect key={j} x={L + j * cw} y={i * ch} width={cw + 0.5} height={ch - 2}
                fill={v < -1e-6 ? "#f87171" : `rgba(16,185,129,${0.15 + 0.85 * Math.min(1, v / mx)})`}
                opacity={quoted(i, grid[j]) ? 1 : 0.45} />
            ))}
          </g>
        ))}
        {[-0.3, -0.15, 0, 0.15, 0.3].map((k) => (
          <text key={k} x={L + ((k + 0.3) / 0.6) * (W - L - Rp)} y={d.length * ch + 14} textAnchor="middle">{k.toFixed(2)}</text>
        ))}
        <text x={L + (W - L - Rp) / 2} y={d.length * ch + 27} textAnchor="middle">log-moneyness k</text>
      </svg>
    </div>
  );
}

export default function App() {
  const [app, setApp] = useState(null);
  const [sel, setSel] = useState(null);
  const [showQuotes, setShowQuotes] = useState(true);
  const [kind, setKind] = useState("call");
  const [mny, setMny] = useState(1.0);
  const [greek, setGreek] = useState("delta");

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/app.json`).then((r) => r.json()).then((a) => {
      setApp(a);
      setSel(a.greeks_example.expiry);
    });
  }, []);

  const derived = useMemo(() => {
    if (!app || !sel) return null;
    const s = app.slices.find((x) => x.expiry === sel);
    const T = s.days / 365, S = app.snapshot.spot_close, r = app.inputs.rate, q = app.inputs.div_yield;
    const F = forward(S, r, q, T);
    const quotes = app.quotes[sel];
    const kq = linspace(Math.min(...quotes.k), Math.max(...quotes.k), 160);
    const K = Math.round(F * mny);
    const vol = sviVol(Math.log(K / F), s.svi, T);
    const g = greeks(S, K, T, r, q, vol, kind);
    const strikes = linspace(F * 0.8, F * 1.2, 120);
    const curve = strikes.map((k) => greeks(S, k, T, r, q, sviVol(Math.log(k / F), s.svi, T), kind)[greek]);
    return { s, T, S, F, K, vol, g, price: bsPrice(S, K, T, r, q, vol, kind), quotes, kq, strikes, curve };
  }, [app, sel, mny, kind, greek]);

  if (!derived) return <div className="wrap"><p className="note">Loading surface…</p></div>;
  const { s, T, F, K, vol, g, price, quotes, kq, strikes, curve } = derived;
  const sl = app.slices, arb = app.arbitrage;
  const grid = linspace(app.grid.k_min, app.grid.k_max, app.grid.n);

  return (
    <div className="wrap">
      <header>
        <div className="eyebrow">SPY · close of {app.snapshot.asof_close_date}</div>
        <h1>Implied <span>volatility surface</span></h1>
        <p className="lede">
          {app.counts.iv_solved.toLocaleString()} out-of-the-money quotes across {sl.length} expiries ({sl[0].days} to{" "}
          {sl[sl.length - 1].days} days), spot ${app.snapshot.spot_close.toFixed(2)}. Implied vols are Black-Scholes
          from last trades. Each expiry is a raw SVI fit. ATM, 90% and 110% below are that fit at K/F = 1, 0.9 and 1.1.
        </p>
      </header>

      <div className="kpis" style={{ marginBottom: 16 }}>
        {[["SVI ATM, " + sl[0].days + "d", pct(sl[0].atm_iv, 2)], ["SVI ATM, " + sl[sl.length - 1].days + "d", pct(sl[sl.length - 1].atm_iv, 2)],
          ["SVI skew 90/110, " + sl[0].days + "d", `${(sl[0].skew_90_110 * 100).toFixed(1)} pts`],
          ["SVI fit RMSE", `${(Math.min(...sl.map((x) => x.fit_rmse_vol)) * 100).toFixed(2)}–${(Math.max(...sl.map((x) => x.fit_rmse_vol)) * 100).toFixed(2)} pts`],
          ["Slices with g(k) ≥ 0", `${arb.butterfly_ok_slices} / ${sl.length}`],
          ["Calendar violations", `${arb.calendar_violations} / ${arb.calendar_grid_points}`]].map(([l, v]) => (
          <div className="kpi" key={l}><div className="v">{v}</div><div className="l">{l}</div></div>
        ))}
      </div>

      <div className="grid">
        <section className="card span-8">
          <h2>Implied volatility surface (SVI)</h2>
          <div className="seg">
            <button className="pill" aria-pressed={showQuotes} onClick={() => setShowQuotes(!showQuotes)}>Market quotes</button>
          </div>
          <Surface3D slices={sl} quotes={app.quotes} showQuotes={showQuotes} selected={sel} onSelect={setSel} />
        </section>
        <section className="card span-4">
          <h2>SVI vol at the forward</h2>
          <XYChart height={190} label="SVI implied volatility at the forward, by days to expiry" xfmt={(v) => `${Math.round(v)}d`} yfmt={(v) => pct(v, 1)}
            series={[{ name: "ATM", color: "#10b981", x: sl.map((x) => x.days), y: sl.map((x) => x.atm_iv) },
              { name: "dots", dots: true, color: "#10b981", r: 3.5, x: sl.map((x) => x.days), y: sl.map((x) => x.atm_iv) }]} />
          <h2 style={{ marginTop: 12 }}>Skew, 90% minus 110% of forward</h2>
          <XYChart height={170} label="SVI skew by days to expiry" xfmt={(v) => `${Math.round(v)}d`} yfmt={(v) => `${(v * 100).toFixed(0)}`}
            series={[{ name: "skew", color: "#fbbf24", x: sl.map((x) => x.days), y: sl.map((x) => x.skew_90_110) }]} />
          {sl.some((x) => x.k_quoted_max < Math.log(1.1)) && (
            <p className="note">
              On {sl.filter((x) => x.k_quoted_max < Math.log(1.1)).map((x) => `${x.days}d`).join(" and ")}, K/F = 1.1 is past the last quoted call, so that side of the skew is the fitted wing.
            </p>
          )}
        </section>

        <section className="card span-6">
          <h2>Smile · {sel} ({s.days}d) · SVI vs market</h2>
          <XYChart label={`Smile for ${sel}`} xLabel="log-moneyness k = ln(K/F)" xfmt={(v) => v.toFixed(2)} yfmt={(v) => pct(v, 0)}
            series={[{ name: "quotes", dots: true, color: "#9aa7b4", x: quotes.k, y: quotes.iv },
              { name: "SVI", color: "#10b981", width: 2.5, x: kq, y: kq.map((k) => sviVol(k, s.svi, T)) }]} />
          <p className="note">
            {s.n_quotes} quotes · SVI RMSE {(s.fit_rmse_vol * 100).toFixed(2)} vol pts · a={s.svi.a.toFixed(4)} b={s.svi.b.toFixed(3)} ρ=
            {s.svi.rho.toFixed(3)} m={s.svi.m.toFixed(3)} σ={s.svi.sigma.toFixed(3)}
          </p>
        </section>
        <section className="card span-6">
          <h2>Butterfly check · g(k) for {s.days}d <span className={`badge ${s.butterfly_ok ? "ok" : "bad"}`}>{s.butterfly_ok ? "no arbitrage" : "arbitrage"}</span></h2>
          <XYChart label="Gatheral g function; negative values mean negative implied density" zeroLine xLabel="log-moneyness k"
            xfmt={(v) => v.toFixed(2)} yfmt={(v) => v.toFixed(2)}
            series={[{ name: "g", color: "#10b981", x: kq, y: kq.map((k) => gFunction(k, s.svi)) }]} />
          <p className="note">Minimum g = {s.butterfly_min_g.toFixed(4)} on the quoted range. g(k) ≥ 0 means the implied risk-neutral density is non-negative.</p>
        </section>

        <section className="card span-12">
          <h2>Greeks explorer</h2>
          <div className="controls" style={{ marginBottom: 12 }}>
            <label className="field">Expiry
              <select value={sel} onChange={(e) => setSel(e.target.value)}>
                {sl.map((x) => <option key={x.expiry} value={x.expiry}>{x.expiry} ({x.days}d)</option>)}
              </select>
            </label>
            <div className="pills" role="group" aria-label="Option type">
              {["call", "put"].map((k) => <button key={k} className="pill" aria-pressed={kind === k} onClick={() => setKind(k)}>{k}</button>)}
            </div>
            <label className="field">Strike {K} ({pct(mny, 0)} of forward {F.toFixed(2)})
              <input type="range" min={0.8} max={1.2} step={0.01} value={mny} onChange={(e) => setMny(+e.target.value)} />
            </label>
            <div className="pills" role="group" aria-label="Greek to plot">
              {Object.entries(GREEKS).map(([k, n]) => <button key={k} className="pill" aria-pressed={greek === k} onClick={() => setGreek(k)}>{n}</button>)}
            </div>
          </div>
          <div className="kpis" style={{ marginBottom: 12 }}>
            {[["SVI vol", pct(vol, 2)], ["Price", `$${price.toFixed(2)}`], ["Delta", g.delta.toFixed(3)], ["Gamma", g.gamma.toFixed(4)],
              ["Vega (per 1 vol pt)", (g.vega / 100).toFixed(3)], ["Theta (per day)", (g.theta / 365).toFixed(3)]].map(([l, v]) => (
              <div className="kpi" key={l}><div className="v">{v}</div><div className="l">{l}</div></div>
            ))}
          </div>
          <XYChart height={220} label={`${GREEKS[greek]} across strikes`} xLabel="strike" vline={K}
            xfmt={(v) => v.toFixed(0)} yfmt={(v) => (Math.abs(v) < 0.1 ? v.toFixed(4) : v.toFixed(2))}
            series={[{ name: greek, color: "#10b981", x: strikes, y: curve }]} />
          <p className="note">Uses the SVI vol at each strike (so the smile feeds the Greeks), r = {pct(app.inputs.rate, 2)} flat, q = {pct(app.inputs.div_yield, 2)}.</p>
        </section>

        <section className="card span-12">
          <h2>Calendar check · Δ total variance between consecutive expiries</h2>
          <CalendarHeat slices={sl} grid={grid} />
          <p className="note">
            Red cells: total variance falls with maturity ({arb.calendar_violations} of {arb.calendar_grid_points} grid points), on{" "}
            {arb.calendar_pairs.map((p) => `${p.near}→${p.far}`).join(", ")}.{" "}
            {arb.calendar_violations_in_quoted_range === 0
              ? "None of them sit inside the strikes quoted on both expiries."
              : `${arb.calendar_violations_in_quoted_range} of them sit inside the strikes quoted on both expiries.`}{" "}
            Faded cells are outside that overlap. Each expiry is fit on its own.
          </p>
        </section>
      </div>
      <footer>
        yfinance chain snapshot, {app.snapshot.snapshot_utc} UTC. Yahoo only publishes the current chain, and this one was taken after the close, so the IVs are last trades.{" "}
        <a href="https://github.com/ParBproject/options-vol-surface">Code, method and limits</a>.
      </footer>
    </div>
  );
}
