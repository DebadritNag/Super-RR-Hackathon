"""Open the dashboard in a headless browser and check that no table repeats a player name.

Needs the backend on :8000 and the dev server on :5173. Usage: python scripts/check_duplicates.py
"""

import sys
from collections import Counter

from playwright.sync_api import sync_playwright

PAGES = [
    "Top 10 Batters",
    "Top 10 Bowlers",
    "Batter Profiles",
    "Bowler Profiles",
    "Why Selected / Why Not Selected",
]
bad = 0
errors: list[str] = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("http://localhost:5173", wait_until="networkidle")
    for label in PAGES:
        roles = ["batters", "bowlers"] if label.startswith("Why") else [None]
        page.get_by_role("navigation", name="Main").get_by_text(label, exact=True).first.click()
        for role in roles:
            if role:
                page.get_by_role("button", name=role.capitalize(), exact=True).first.click()
            page.wait_for_selector("table tbody tr", timeout=60000)
            page.wait_for_load_state("networkidle")
            # Name plus the "different player, id N" label, so two real players sharing a name count as distinct.
            names = page.locator("table tbody tr td:has(button)").all_inner_texts()
            dups = {n: c for n, c in Counter(names).items() if c > 1}
            tag = f"{label}{' (' + role + ')' if role else ''}"
            print(f"{'PASS' if not dups else 'FAIL'}  {tag}: {len(names)} names, duplicates {dups or 'none'}")
            bad += bool(dups)
    page.screenshot(path="scripts/why_bowlers.png", full_page=False)
    browser.close()
print("browser console errors:", errors or "none")
sys.exit(1 if bad or errors else 0)
