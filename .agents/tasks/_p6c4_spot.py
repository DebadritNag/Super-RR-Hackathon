"""Independent spot checks for Phase 6 chunk 4 (pandas only, no phase6 estimator code)."""

import sys

sys.path.insert(0, "d:/Data/backend")
import numpy as np
import pandas as pd

from app.phase5 import pipeline as pl

REP = "d:/Data/backend/data/reports/"
study = pl.load_study(n_boot=10, seed=20260512)
press = study.pressure_rows("any|q0.75", "batter", "runs")
press = press[press["comp"] == "IPL"]
out = {}

# (1) 2025-onward IPL batter: sample counts
w = press[pd.to_datetime(press["date"]) >= pd.Timestamp("2025-01-01")]
t25 = pd.read_csv(REP + "phase6_recent_form_analyses_2025.csv")
row = t25[(t25["format"] == "IPL") & (t25["role"] == "batter") & (t25["stream"] == "runs")].iloc[0]
out["matches"] = (w["match_id"].nunique(), int(row["matches"]))
out["pressure_obs"] = (len(w), int(row["pressure_observations"]))
out["players"] = (w["player_id"].nunique(), int(row["players_with_pressure_balls"]))

# (2) odd/even split-half SB from raw per-match sums
pm = w.groupby(["player_id", "match_id"]).agg(
    date=("date", "first"), n=("resid", "size"), s=("resid", "sum")
).reset_index()
pm = pm.sort_values(["player_id", "date", "match_id"])
pm["half"] = pm.groupby("player_id").cumcount() % 2
g = pm.groupby(["player_id", "half"]).agg(n=("n", "sum"), s=("s", "sum")).unstack("half")
g = g.dropna()
ok = (g[("n", 0)] >= 6) & (g[("n", 1)] >= 6)
h0 = g.loc[ok, ("s", 0)] / g.loc[ok, ("n", 0)]
h1 = g.loc[ok, ("s", 1)] / g.loc[ok, ("n", 1)]
r = float(np.corrcoef(h0, h1)[0, 1])
rel = pd.read_csv(REP + "phase6_recent_form_analyses_reliability.csv")
rr = rel[(rel["window_start"] == "2025-01-01") & (rel["format"] == "IPL") & (rel["role"] == "batter")
         & (rel["stream"] == "runs") & (rel["mode"] == "odd_even")].iloc[0]  # fmt: skip
out["split_half_sb"] = (2 * r / (1 + r), float(rr["sb_pearson"]))
out["split_half_players"] = (int(ok.sum()), int(rr["players"]))

# (3) variance component (within-player residual variance), direct formula
d2 = w.assign(r=w["resid"])
pl_ = d2.groupby("player_id")["r"].agg(["size", "var"]).dropna()
pooled_within = float(((pl_["size"] - 1) * pl_["var"]).sum() / (pl_["size"] - 1).sum())
out["within_var_vs_table"] = (pooled_within, float(row["sigma2_within"]))

# (4) adjacent-season Spearman, IPL batter 2024 vs 2025
ss = pd.read_csv(REP + "phase6_robustness_season_checks.csv")
a = ss[(ss["check"] == "adjacent_seasons") & (ss["format"] == "IPL") & (ss["role"] == "batter")
       & (ss["season"] == 2024)].iloc[0]  # fmt: skip
yr = pd.to_datetime(press["date"]).dt.year
y24 = press[yr == 2024].groupby("player_id")["resid"].agg(["size", "mean"])
y25 = press[yr == 2025].groupby("player_id")["resid"].agg(["size", "mean"])
j = y24.join(y25, lsuffix="_a", rsuffix="_b", how="inner")
j = j[(j["size_a"] >= 12) & (j["size_b"] >= 12)]
out["adjacent_spearman"] = (float(j["mean_a"].corr(j["mean_b"], method="spearman")), float(a["value"]))
out["adjacent_players"] = (len(j), int(a["players"]))

for k, (mine, stored) in out.items():
    print(k, mine, stored, "OK" if abs(float(mine) - float(stored)) < 1e-6 else "DIFF")
