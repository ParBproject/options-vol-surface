import { useEffect, useMemo, useRef, useState } from "react";
import { linspace, sviVol } from "./volmath.js";
import { useWidth } from "./charts.jsx";

// Map IV to a dark-teal -> emerald -> amber -> red ramp.
function color(t, alpha = 1) {
  const stops = [[13, 60, 52], [16, 185, 129], [251, 191, 36], [248, 113, 113]];
  const u = Math.max(0, Math.min(0.999, t)) * (stops.length - 1);
  const i = Math.floor(u), f = u - i;
  const c = stops[i].map((v, j) => Math.round(v + f * (stops[i + 1][j] - v)));
  return `rgba(${c[0]},${c[1]},${c[2]},${alpha})`;
}

export default function Surface3D({ slices, quotes, showQuotes, selected, onSelect }) {
  const [wrap, W] = useWidth(700);
  const H = Math.round(Math.min(520, Math.max(320, W * 0.62)));
  const canvas = useRef(null);
  const [rot, setRot] = useState({ yaw: -0.65, pitch: 0.55 });
  const drag = useRef(null);
  const ks = useMemo(() => linspace(-0.3, 0.3, 41), []);
  const tmax = Math.sqrt(slices[slices.length - 1].days / 365);
  const inQ = (s, k) => k >= s.k_quoted_min && k <= s.k_quoted_max;
  const vols = slices.flatMap((s) => ks.filter((k) => inQ(s, k)).map((k) => sviVol(k, s.svi, s.days / 365)));
  const vmin = Math.min(...vols), vmax = Math.max(...vols);

  useEffect(() => {
    const cv = canvas.current, dpr = window.devicePixelRatio || 1;
    cv.width = W * dpr; cv.height = H * dpr;
    const ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const { yaw, pitch } = rot, cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    const scale = Math.min(W, H * 1.4) * 0.33;
    const proj = (x, y, z) => {
      const X = x * cy - y * sy, Y = x * sy + y * cy;
      return [W / 2 + X * scale, H * 0.56 - (z * cp - Y * sp) * scale, Y * cp + z * sp];
    };
    const P = (k, T, v) => proj(k / 0.3, (Math.sqrt(T) / tmax) * 2 - 1, Math.min(0.9, ((v - vmin) / (vmax - vmin)) * 1.2 - 0.6));
    // floor box
    ctx.strokeStyle = "#1f2630"; ctx.lineWidth = 1;
    const corners = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([x, y]) => proj(x, y, -0.6));
    ctx.beginPath(); corners.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); ctx.stroke();
    const quads = [];
    for (let i = 0; i < slices.length - 1; i++) {
      const a = slices[i], b = slices[i + 1];
      for (let j = 0; j < ks.length - 1; j++) {
        const pts = [[a, ks[j]], [a, ks[j + 1]], [b, ks[j + 1]], [b, ks[j]]].map(([s, k]) => P(k, s.days / 365, sviVol(k, s.svi, s.days / 365)));
        const v = [[a, ks[j]], [b, ks[j + 1]]].map(([s, k]) => sviVol(k, s.svi, s.days / 365));
        const quoted = inQ(a, ks[j]) && inQ(a, ks[j + 1]) && inQ(b, ks[j]) && inQ(b, ks[j + 1]);
        quads.push({ pts, quoted, depth: pts.reduce((s, p) => s + p[2], 0) / 4, t: ((v[0] + v[1]) / 2 - vmin) / (vmax - vmin) });
      }
    }
    quads.sort((p, q) => q.depth - p.depth);
    for (const q of quads) {
      ctx.beginPath(); q.pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath();
      ctx.fillStyle = q.quoted ? color(q.t, 0.92) : "rgba(154,167,180,0.10)"; ctx.fill();
      ctx.strokeStyle = "rgba(6,8,11,0.35)"; ctx.stroke();
    }
    // selected slice outline
    const s = slices.find((x) => x.expiry === selected);
    if (s) {
      ctx.beginPath(); ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 2;
      ks.forEach((k, i) => { const [x, y] = P(k, s.days / 365, sviVol(k, s.svi, s.days / 365)); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
      ctx.stroke(); ctx.lineWidth = 1;
    }
    if (showQuotes) {
      ctx.fillStyle = "#e6edf3";
      for (const sl of slices) {
        const q = quotes[sl.expiry];
        q.k.forEach((k, i) => {
          if (Math.abs(k) > 0.3) return;
          const [x, y] = P(k, sl.days / 365, q.iv[i]);
          ctx.fillRect(x - 1, y - 1, 2, 2);
        });
      }
    }
    // axis labels
    ctx.fillStyle = "#9aa7b4"; ctx.font = "11px ui-monospace, monospace";
    const lab = (x, y, z, t) => { const [px, py] = proj(x, y, z); ctx.fillText(t, px, py); };
    lab(-1.05, -1.25, -0.6, "k=-0.3"); lab(0.85, -1.25, -0.6, "k=+0.3");
    lab(1.15, -1, -0.6, `${slices[0].days}d`); lab(1.15, 1, -0.6, `${slices[slices.length - 1].days}d`);
    ctx.fillText(`IV ${(vmin * 100).toFixed(0)}%–${(vmax * 100).toFixed(0)}% (quoted range)`, 12, 20);
  }, [W, H, rot, slices, quotes, showQuotes, selected, ks, tmax, vmin, vmax]);

  const down = (e) => { drag.current = { x: e.clientX, y: e.clientY, ...rot }; e.currentTarget.setPointerCapture(e.pointerId); };
  const move = (e) => {
    if (!drag.current) return;
    const d = drag.current;
    setRot({ yaw: d.yaw + (e.clientX - d.x) * 0.008, pitch: Math.max(0.05, Math.min(1.45, d.pitch + (e.clientY - d.y) * 0.006)) });
  };
  const key = (e) => {
    const step = { ArrowLeft: [-0.1, 0], ArrowRight: [0.1, 0], ArrowUp: [0, -0.08], ArrowDown: [0, 0.08] }[e.key];
    if (!step) return;
    e.preventDefault();
    setRot((r) => ({ yaw: r.yaw + step[0], pitch: Math.max(0.05, Math.min(1.45, r.pitch + step[1])) }));
  };
  return (
    <div ref={wrap}>
      <canvas ref={canvas} style={{ height: H }} tabIndex={0} role="img"
        aria-label="3D implied volatility surface: log-moneyness by maturity. Drag or use arrow keys to rotate."
        onPointerDown={down} onPointerMove={move} onPointerUp={() => (drag.current = null)} onKeyDown={key}
        onDoubleClick={() => setRot({ yaw: -0.65, pitch: 0.55 })} />
      <div className="legend">
        <span>Drag or arrow keys to rotate · double-click to reset</span>
        <span><i style={{ background: color(0) }} />low IV</span><span><i style={{ background: color(0.99) }} />high IV</span>
        {showQuotes && <span><i style={{ background: "#e6edf3" }} />market quotes</span>}
        <span><i style={{ background: "#fff" }} />selected expiry</span>
        <span><i style={{ background: "rgba(154,167,180,0.4)" }} />SVI extrapolation (no quotes), clipped</span>
      </div>
      <div className="pills" style={{ marginTop: 8 }} role="group" aria-label="Select expiry">
        {slices.map((s) => (
          <button key={s.expiry} className="pill" aria-pressed={s.expiry === selected} onClick={() => onSelect(s.expiry)}>{s.days}d</button>
        ))}
      </div>
    </div>
  );
}
