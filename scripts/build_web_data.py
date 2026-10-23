"""Export the surface, quotes and checks the web app needs to web/public/data/app.json."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "public" / "data" / "app.json"


def main() -> None:
    S = json.loads((ROOT / "results" / "summary.json").read_text())
    pts = pd.read_csv(ROOT / "results" / "iv_points.csv")
    quotes = {}
    for exp, g in pts.groupby("expiry"):
        g = g.sort_values("k")
        quotes[exp[:10]] = {"k": g["k"].round(5).tolist(), "iv": g["iv"].round(5).tolist(),
                            "strike": g["strike"].tolist(), "type": g["type"].str[0].tolist(),
                            "volume": g["volume"].astype(int).tolist()}
    app = {"snapshot": S["snapshot"], "inputs": S["inputs"], "filters": S["filters"], "counts": S["counts"],
           "slices": S["slices"], "arbitrage": S["arbitrage"], "greeks_example": S["greeks_example"],
           "quotes": quotes, "grid": {"k_min": -0.3, "k_max": 0.3, "n": 121}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(app, separators=(",", ":")))
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()
