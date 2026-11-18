"""Check in a headless browser that every Why Selected row shows real reasons and no retired status word.

Needs the backend on :8000 and the dev server on :5173. Usage: python scripts/check_why_reasons.py
"""

import sys

from playwright.sync_api import sync_playwright

PLACEHOLDER = "On the submitted list. Open the player for the full evidence."
bad = 0
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("http://localhost:5173", wait_until="networkidle")
    page.get_by_role("navigation", name="Main").get_by_text("Why Selected / Why Not Selected", exact=True).click()
    for role in ("Batters", "Bowlers"):
        page.get_by_role("button", name=role, exact=True).first.click()
        page.wait_for_selector("table tbody tr")
        page.wait_for_load_state("networkidle")
        rows = page.locator("table tbody tr")
        for i in range(rows.count()):
            cells = rows.nth(i).locator("td").all_inner_texts()
            name, reasons = cells[0].strip(), cells[3].strip()
            ok = bool(reasons) and PLACEHOLDER not in reasons and "xploratory" not in reasons.lower()
            if not ok:
                bad += 1
            if i < 3 or not ok:
                print(f"{'PASS' if ok else 'FAIL'}  {role}  {name}: {reasons[:150]!r}")
        print(f"{role}: {rows.count()} rows checked")
    page.screenshot(path="scripts/why_bowlers.png")
    browser.close()
print("all rows have reasons" if not bad else f"{bad} rows without reasons")
sys.exit(1 if bad else 0)
