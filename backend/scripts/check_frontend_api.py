"""Smoke-check every API call made by frontend/src/services/submissionApi.ts.

Calls the running backend with the frontend's Origin header so CORS is checked too.
Read-only: GET requests only. Usage: python scripts/check_frontend_api.py
"""

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
ORIGIN = "http://localhost:5173"
results = []


def call(path, headers=None):
    req = urllib.request.Request(
        BASE + path, headers={"Origin": ORIGIN, "Accept": "application/json", **(headers or {})}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read() or b"null")
            return r.status, body, r.headers.get("access-control-allow-origin")
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read() or b"null")
        except Exception:
            body = None
        return e.code, body, e.headers.get("access-control-allow-origin")
    except Exception as e:  # connection failure
        return 0, str(e), None


def check(name, path, expect=200, headers=None):
    status, body, acao = call(path, headers)
    ok = status == expect
    note = ""
    if isinstance(body, dict):
        note = "keys=" + ",".join(sorted(body.keys())[:8])
    results.append((ok, name, path, status, expect, acao, note))
    return body if status == 200 else None


ov = check("overview", "/submission/overview")
ids = {}
for role in ("batters", "bowlers"):
    t = check(f"top10 {role}", f"/submission/top10/{role}")
    rows = (t or {}).get("rows") or (t or {}).get("players") or (t or {}).get("items") or []
    ids[role] = [r.get("player_id") for r in rows if isinstance(r, dict) and r.get("player_id")]
for role in ("batters", "bowlers"):
    pid = (ids.get(role) or [None])[0]
    if pid:
        check(f"player {role}", f"/submission/players/{role}/{pid}")
        check(f"radar {role} IPL", f"/submission/radar/{role}/{pid}?format=IPL")
        check(f"radar {role} T20I", f"/submission/radar/{role}/{pid}?format=T20I")
        two = ",".join(str(i) for i in ids[role][:2])
        check(f"compare {role}", f"/submission/compare/{role}?player_ids={two}")
    else:
        results.append(
            (False, f"player {role}", "-", 0, 200, None, "no player_id found in top10 response")
        )
    check(f"why {role}", f"/submission/why/{role}?limit=50&offset=0")
    check(f"profiles {role}", f"/submission/profiles/{role}?limit=50")
    check(f"profiles {role} search", f"/submission/profiles/{role}?limit=50&q=a")
check("methodology", "/submission/methodology")
check("validation", "/submission/validation")
for role in ("batters", "bowlers"):
    check(
        f"experimental-ai {role} (no token -> refused)",
        f"/internal/experimental-ai/{role}",
        expect=None,
    )

bad = 0
for ok, name, path, status, expect, acao, note in results:
    if expect is None:  # internal route: must refuse without a token
        ok = status in (401, 403, 503)
        expect = "401/403/503"
    if not ok:
        bad += 1
    cors = "CORS ok" if acao in (ORIGIN, "*") else f"CORS MISSING ({acao})"
    print(
        f"{'PASS' if ok else 'FAIL'}  {status}  (expect {expect})  {cors}  {name}  {path}  {note}"
    )
print(f"\n{len(results) - bad} of {len(results)} checks passed")
sys.exit(1 if bad else 0)
