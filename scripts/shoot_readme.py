"""Capture README screenshots + demo GIF from the live (or local) site. Needs Playwright Chromium and ffmpeg."""
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://parbproject.github.io/options-vol-surface/"
IMG = Path(__file__).resolve().parents[1] / "docs" / "img"
IMG.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(600)
    pg.screenshot(path=IMG / "overview.png")
    pg.screenshot(path=IMG / "full.png", full_page=True)
    pg.get_by_text("Greeks explorer").scroll_into_view_if_needed()
    pg.locator("section", has_text="Greeks explorer").screenshot(path=IMG / "greeks.png")
    pg.locator("section", has_text="Calendar check").screenshot(path=IMG / "arbitrage.png")
    m = b.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, device_scale_factor=2)
    m.goto(URL, wait_until="networkidle")
    m.wait_for_timeout(600)
    m.screenshot(path=IMG / "mobile.png")
    tmp = Path(tempfile.mkdtemp())
    pg.set_viewport_size({"width": 1200, "height": 760})
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(400)
    cv = pg.locator("canvas")
    cv.scroll_into_view_if_needed()
    pg.evaluate("window.scrollTo(0, 120)")
    n = 0

    def snap(k=1):
        global n
        for _ in range(k):
            pg.screenshot(path=tmp / f"f{n:04d}.png")
            n += 1

    snap(4)
    box = cv.bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    for i in range(24):
        pg.mouse.move(cx + i * 12, cy - (i % 12) * 2)
        snap(1)
    pg.mouse.up()
    for d in ["7d", "57d", "251d", "603d"]:
        pg.get_by_role("button", name=d, exact=True).click()
        pg.wait_for_timeout(100)
        snap(4)
    b.close()
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "6", "-i", str(tmp / "f%04d.png"), "-vf",
                "scale=900:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer",
                str(IMG / "demo.gif")], check=True)
print("frames", n, "->", IMG)
