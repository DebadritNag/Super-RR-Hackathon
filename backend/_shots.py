import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("d:/Data/.agents/tasks/phase9_screens")
OUT.mkdir(parents=True, exist_ok=True)
PAGES = [
    "Overview", "Top 10 Batters", "Top 10 Bowlers", "Batter Profiles", "Bowler Profiles",
    "Player Comparison", "Why Selected / Why Not Selected", "Pressure Methodology",
    "Data & Validation", "Experimental AI Predictions",
]
res = []
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h in ((375, 800), (1440, 900)):
        pg = b.new_page(viewport={"width": w, "height": h})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://localhost:5173", wait_until="networkidle")
        for name in PAGES:
            if w < 800:
                btn = pg.get_by_role("button", name=re.compile("menu", re.I))
                if btn.count():
                    btn.first.click()
                    pg.wait_for_timeout(200)
            link = pg.get_by_role("button", name=name, exact=True)
            if not link.count():
                link = pg.get_by_text(name, exact=True)
            link.first.click()
            pg.wait_for_load_state("networkidle")
            pg.wait_for_timeout(500)
            text = pg.inner_text("body")
            html_hit = bool(re.search("xploratory", pg.content(), re.I))
            slug = re.sub(r"\W+", "_", name).strip("_")
            pg.screenshot(path=str(OUT / f"{slug}_{w}.png"), full_page=True)
            res.append({"page": name, "width": w, "text_has_word": bool(re.search("xploratory", text, re.I)),
                        "dom_has_word": html_hit, "chars": len(text)})
        res.append({"width": w, "page_errors": errs})
    b.close()
Path(OUT / "result.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
bad = [r for r in res if r.get("text_has_word") or r.get("dom_has_word")]
sys.exit(1 if bad else 0)
