// Browser math must reproduce the Python results.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { bsPrice, calendarGrid, forward, gFunction, greeks, linspace, sviVol } from "../src/volmath.js";

const app = JSON.parse(readFileSync(new URL("../public/data/app.json", import.meta.url)));
const py = JSON.parse(readFileSync(new URL("../../results/summary.json", import.meta.url)));
const close = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol * Math.max(1, Math.abs(b)), `${msg}: ${a} vs ${b}`);

test("SVI ATM / 90% / 110% vols match Python for every slice", () => {
  for (const s of py.slices) {
    const T = s.days / 365;
    close(sviVol(0, s.svi, T), s.atm_iv, 1e-12, `${s.expiry} atm`);
    close(sviVol(Math.log(0.9), s.svi, T), s.iv_90, 1e-12, `${s.expiry} 90`);
  }
});

test("butterfly g(k) minimum matches Python on the quoted range", () => {
  for (const s of py.slices) {
    const k = app.quotes[s.expiry].k;
    const g = Math.min(...linspace(Math.min(...k), Math.max(...k), 200).map((x) => gFunction(x, s.svi)));
    close(g, s.butterfly_min_g, 1e-4, s.expiry);
    assert.equal(g >= 0, s.butterfly_ok);
  }
});

test("calendar violation count matches Python", () => {
  const d = calendarGrid(py.slices, linspace(app.grid.k_min, app.grid.k_max, app.grid.n));
  assert.equal(d.flat().filter((x) => x < -1e-6).length, py.arbitrage.calendar_violations);
});

test("Greeks example matches Python", () => {
  const g = py.greeks_example, i = app.inputs, S = app.snapshot.spot_close, T = g.days / 365;
  const F = forward(S, i.rate, i.div_yield, T);
  close(sviVol(Math.log(g.strike / F), py.slices.find((s) => s.expiry === g.expiry).svi, T), g.svi_vol, 1e-12, "vol");
  close(bsPrice(S, g.strike, T, i.rate, i.div_yield, g.svi_vol, "call"), g.call_price, 1e-9, "price");
  for (const kind of ["call", "put"]) {
    const js = greeks(S, g.strike, T, i.rate, i.div_yield, g.svi_vol, kind);
    for (const [k, v] of Object.entries(g[kind])) close(js[k], v, 1e-9, `${kind} ${k}`);
  }
});
