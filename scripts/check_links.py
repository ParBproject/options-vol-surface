"""Check every http(s) link in README.md and the web app source; writes docs/linkcheck.txt. ONLINE."""
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
files = [ROOT / "README.md", *sorted((ROOT / "web" / "src").glob("*.jsx")), ROOT / "web" / "index.html"]
# XML namespace ids (w3.org/2000/svg) are skipped: they are identifiers, not links.
URL_RE = r"https?://[^\s\"'<>)\]]+"
urls = sorted({u.rstrip(").,") for f in files for u in re.findall(URL_RE, f.read_text()) if "w3.org/2000/svg" not in u})
local = sorted(set(re.findall(r"\]\((docs/[^)]+)\)", (ROOT / "README.md").read_text())))
lines, bad = [], 0
for u in urls:
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 linkcheck"})
        code = urllib.request.urlopen(req, timeout=20).status
    except Exception as e:  # noqa: BLE001
        code = getattr(e, "code", str(e))
    bad += code != 200
    lines.append(f"{code}  {u}")
for rel in local:
    ok = (ROOT / rel).exists()
    bad += not ok
    lines.append(f"{'OK ' if ok else 'MISSING'}  {rel}")
(ROOT / "docs" / "linkcheck.txt").write_text("\n".join(lines) + f"\n{len(lines)} links, {bad} broken\n")
print("\n".join(lines), f"\n{len(lines)} links, {bad} broken")
