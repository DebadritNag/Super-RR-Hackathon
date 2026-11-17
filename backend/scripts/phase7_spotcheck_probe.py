"""Phase 7: independent recomputation of Phase 6 spot checks 1-4 (read-only).

Spot 1: split-half chase|q0.75 IPL batter runs odd/even r and Spearman-Brown.
Spot 2: recent-form 2024 IPL batter runs floor/k/tau2.
Spot 3: IPL matches with deliveries 2024-01-01..2025-12-31 from the official DB.
Spot 4: T20I matches with deliveries from 2024 minus TEST-period matches.
Writes data/reports/phase7_spotcheck_probe.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd

B = Path("d:/Data/backend")
out: dict = {}
ex = duckdb.connect(str(B / "data/database/exploratory.duckdb"), read_only=True)
so = duckdb.connect(str(B / "data/database/superr.duckdb"), read_only=True)

cols = [r[0] for r in ex.execute("describe p6_split_half").fetchall()]
out["p6_split_half_columns"] = cols
df = ex.execute("select * from p6_split_half").df()
sel = df[
    (df["definition"] == "chase|q0.75")
    & (df["format"] == "IPL")
    & (df["role"] == "batter")
    & (df["stream"] == "runs")
]
keep = [c for c in ("mode", "window", "players", "r_pearson", "sb_pearson") if c in sel.columns]
out["spot1_rows"] = sel[keep].to_dict("records")
for rec in out["spot1_rows"]:
    if rec.get("r_pearson") is not None and rec.get("mode") == "odd_even":
        r = rec["r_pearson"]
        rec["sb_recomputed_2r_over_1_plus_r"] = 2 * r / (1 + r)

rf = pd.read_csv(B / "data/reports/phase6_recent_form_analyses_2024.csv")
out["spot2_columns"] = rf.columns.tolist()
m = rf[rf.apply(lambda r: "IPL" in map(str, r.values) and "batter" in map(str, r.values), axis=1)]
out["spot2_rows"] = m.head(6).to_dict("records")

ipl = so.execute(
    "select year(match_date) y, count(*) n from matches where competition_type='IPL' "
    "and has_deliveries and match_date between '2024-01-01' and '2025-12-31' group by 1 order by 1"
).fetchall()
out["spot3_ipl_by_year"] = ipl
out["spot3_total"] = sum(n for _, n in ipl)

t_all = so.execute(
    "select count(*) from matches where competition_type='T20I' and has_deliveries "
    "and match_date>='2024-01-01'"
).fetchone()[0]
t_test = ex.execute(
    "select count(*) from p4_match_period where competition_type='T20I' and match_date>='2024-01-01' "
    "and period='TEST'"
).fetchone()[0]
out["spot4"] = {
    "t20i_from_2024_with_deliveries": t_all,
    "of_which_test_period": t_test,
    "difference": t_all - t_test,
}
out["period_counts"] = ex.execute(
    "select period,count(*) from p4_match_period group by 1 order by 1"
).fetchall()

(B / "data/reports/phase7_spotcheck_probe.json").write_text(
    json.dumps(out, indent=2, default=str), encoding="utf-8"
)
print(json.dumps(out, indent=2, default=str)[:6000])
