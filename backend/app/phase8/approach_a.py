"""Approach A: context-adjusted statistical performance under continuous pressure intensity.

Pipeline per role (batter or bowler, never mixed):

1. Expected-outcome models (``expected.py``) give a player-blind pre-delivery expectation; the
   oriented residual is positive when the player did better than expected.
2. The A residual of a delivery is the equal-weight mean of the standardised runs and wicket
   residuals (components standardised by their TRAIN standard deviation, so the combination is
   inverse-variance weighted on that scale). Dot and boundary components are reported only.
3. Pressure units: deliveries with intensity >= 0.5, weighted by intensity, aggregated per
   player-match-innings. ``normal_baseline`` is the unweighted mean residual of deliveries below 0.5.
4. REML shrinkage (``reml.py``) per scope (COMBINED with format-centred units, IPL, T20I).
5. Reliability on unshrunk precision-weighted means, match-cluster bootstrap for ranks.

Nothing here uses a player identity, a rank or a score level to choose anything.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd

from app.phase8.constants import SEED
from app.phase8.expected import SPECS, TargetSpec, oriented_residual, spec_for
from app.phase8.reliability import (
    icc1,
    out_of_time_correlation,
    precision_weighted_means,
    split_half,
)
from app.phase8.reml import RemlError, fit_reml, posterior
from app.phase8.stability import match_count_draws, point_ranking, rank_stability
from app.phase8.units import ROLE_COL, build_units

HIGH_CUT = 0.5
INNINGS2_ONLY = ("P3", "P5", "P6")
SCOPES = ("COMBINED", "IPL", "T20I")
A_COMPONENTS = ("runs", "wicket")


# ---------------------------------------------------------------------------------------------
# residuals
# ---------------------------------------------------------------------------------------------
def component_residuals(
    df: pd.DataFrame, results: dict[tuple[str, str], dict[str, Any]]
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Oriented residual per (role, target) plus the A residual and its standardisation constants."""
    out = pd.DataFrame(index=df.index)
    sds: dict[str, float] = {}
    train = (df["period"] == "TRAIN").to_numpy()
    for spec in SPECS:
        r = oriented_residual(results[(spec.role, spec.name)], spec)
        out[f"r_{spec.role}_{spec.name}"] = r
        sds[f"{spec.role}_{spec.name}"] = float(np.nanstd(r.to_numpy()[train], ddof=1))
    for role in ("batter", "bowler"):
        zr = out[f"r_{role}_runs"] / sds[f"{role}_runs"]
        wk = out[f"r_{role}_wicket"].copy()
        if role == "bowler":
            # A wide or no-ball cannot be a bowler-credited wicket: observed 0 and expected 0 by
            # rule (structural, not a missing value), so the wicket component is 0 on those balls.
            wk = wk.where(df["den_legal_inc"] == 1, 0.0).where(zr.notna())
        zw = wk / sds[f"{role}_wicket"]
        out[f"a_{role}"] = (zr + zw) / 2.0
    return out, sds


def final_intensity(w: pd.DataFrame, primary: str) -> tuple[pd.Series, dict[str, Any]]:
    """Intensity series for the primary candidate with the predeclared innings-1 rule."""
    col = f"w_{primary}"
    s = w[col].copy()
    info: dict[str, Any] = {"primary": primary, "innings1_fallback": None}
    if primary in INNINGS2_ONLY:
        inn1 = w["w_P4"].where(w["w_P4"].notna())
        info["innings1_fallback"] = "P4"
        s = s.where(s.notna(), inn1)
    return s, info


# ---------------------------------------------------------------------------------------------
# units, counts and eligibility
# ---------------------------------------------------------------------------------------------
def pressure_units(df: pd.DataFrame, role: str, w: pd.Series, resid: pd.Series) -> pd.DataFrame:
    """Pressure units (intensity >= 0.5) with Kish precision ``prec = w^2 / sum w^2``."""
    u = build_units(df, role, w.where(w >= HIGH_CUT), resid, HIGH_CUT)
    u["prec"] = u["w"] ** 2 / u["w2"]
    return u


def centre_by_format(units: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    """Subtract the precision-weighted league mean of each format (format fixed effect)."""
    u = units.copy()
    mu = {}
    for f, g in u.groupby("competition_type"):
        mu[f] = float((g["prec"] * g["y"]).sum() / g["prec"].sum())
    u["y_raw"] = u["y"]
    u["y"] = u["y"] - u["competition_type"].map(mu)
    return u, mu


def player_counts(df: pd.DataFrame, role: str, w: pd.Series, resid: pd.Series) -> pd.DataFrame:
    """Per (player, format) exposure over deliveries with defined intensity and residual."""
    col = ROLE_COL[role]
    ok = w.notna() & resid.notna()
    d = pd.DataFrame(
        {
            "player_id": df.loc[ok, col].to_numpy(),
            "competition_type": df.loc[ok, "competition_type"].to_numpy(),
            "match_id": df.loc[ok, "match_id"].to_numpy(),
            "innings": df.loc[ok, "innings_number"].to_numpy(),
            "w": w[ok].to_numpy(),
            "balls": (
                df.loc[ok, "den_counts_as_ball_faced" if role == "batter" else "den_legal_inc"]
            ).to_numpy(),
        }
    )
    d["w2"] = d["w"] ** 2
    d["unit"] = d["match_id"].astype("int64") * 10 + d["innings"].astype("int64")
    return d


def scope_counts(deliv: pd.DataFrame, units: pd.DataFrame, scope: str) -> pd.DataFrame:
    """Exposure totals for one scope; ``hi_units`` counts pressure units of the player."""
    d = deliv if scope == "COMBINED" else deliv[deliv["competition_type"] == scope]
    u = units if scope == "COMBINED" else units[units["competition_type"] == scope]
    g = d.groupby("player_id")
    out = pd.DataFrame(
        {
            "n_matches": g["match_id"].nunique(),
            "n_innings": g["unit"].nunique(),
            "balls": g["balls"].sum(),
            "sum_w": g["w"].sum(),
            "mean_intensity": g["w"].mean(),
        }
    )
    out["eff_n"] = out["sum_w"] ** 2 / g["w2"].sum()
    out["hi_units"] = u.groupby("player_id").size().reindex(out.index).fillna(0).astype(int)
    out["pressure_matches"] = (
        u.groupby("player_id")["match_id"].nunique().reindex(out.index).fillna(0).astype(int)
    )
    return out


def eligible_players(
    counts: pd.DataFrame, role: str, crit: dict[str, Any], mult: float = 1.0
) -> pd.Series:
    """Boolean per player for the predeclared floors (scaled by ``mult``)."""
    e = crit["eligibility"]
    ball_key = "min_balls_faced" if role == "batter" else "min_balls_bowled"
    return (
        (counts["n_matches"] >= e["min_matches"] * mult)
        & (counts["eff_n"] >= e["min_effective_n"] * mult)
        & (counts["balls"] >= e[ball_key] * mult)
        & (counts["hi_units"] >= e["min_high_intensity_units"] * mult)
    )


# ---------------------------------------------------------------------------------------------
# baseline and delta
# ---------------------------------------------------------------------------------------------
def baseline_table(df: pd.DataFrame, role: str, w: pd.Series, resid: pd.Series) -> pd.DataFrame:
    """Per (player, match) sums of the residual on deliveries with intensity below 0.5."""
    ok = w.notna() & resid.notna() & (w < HIGH_CUT)
    d = pd.DataFrame(
        {
            "player_id": df.loc[ok, ROLE_COL[role]].to_numpy(),
            "match_id": df.loc[ok, "match_id"].to_numpy(),
            "competition_type": df.loc[ok, "competition_type"].to_numpy(),
            "r": resid[ok].to_numpy(),
        }
    )
    return (
        d.groupby(["player_id", "match_id", "competition_type"], sort=True)
        .agg(sr=("r", "sum"), n=("r", "size"))
        .reset_index()
    )


# ---------------------------------------------------------------------------------------------
# bootstrap
# ---------------------------------------------------------------------------------------------
class Boot:
    """Match-cluster draws shared by every table of one cell (strata = period)."""

    def __init__(self, df: pd.DataFrame, n_draws: int = 1000, seed: int = SEED) -> None:
        m = df.drop_duplicates("match_id").sort_values("match_id")
        self.mids = m["match_id"].to_numpy()
        self.counts = match_count_draws(self.mids, n_draws, seed, m["period"].to_numpy())
        self.n_draws = n_draws

    def pos(self, match_ids: np.ndarray) -> np.ndarray:
        return np.searchsorted(self.mids, match_ids)

    def weighted_means(
        self, players: np.ndarray, match_ids: np.ndarray, weight: np.ndarray, value: np.ndarray,
        index: np.ndarray, extra_weight: np.ndarray | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:  # fmt: skip
        """Draws x players of ``sum(c*weight*value)/sum(c*weight)`` and the draw precision sums."""
        ppos = np.searchsorted(index, players)
        ok = (ppos < len(index)) & (index[np.minimum(ppos, len(index) - 1)] == players)
        ppos, mpos = ppos[ok], self.pos(match_ids[ok])
        wt, wv = weight[ok], (weight * value)[ok]
        out = np.full((self.n_draws, len(index)), np.nan)
        den_out = np.zeros((self.n_draws, len(index)))
        for d in range(self.n_draws):
            c = self.counts[d, mpos]
            den = np.bincount(ppos, weights=c * wt, minlength=len(index))
            num = np.bincount(ppos, weights=c * wv, minlength=len(index))
            good = den > 0
            out[d, good] = num[good] / den[good]
            den_out[d] = den
        return out, den_out


def refit_draws(
    units: pd.DataFrame, players: np.ndarray, boot: Boot, n: int | None = None
) -> np.ndarray:
    """Ranking basis of every player in each match-cluster draw with a full REML refit per draw.

    The basis is the posterior mean, or the unshrunk mean in a draw whose refit hits the floor
    (the predeclared rule). Players absent from a draw are NaN.
    """
    n = boot.n_draws if n is None else n
    u = units[units["player_id"].isin(players)].reset_index(drop=True)
    pos = boot.pos(u["match_id"].to_numpy())
    est = np.full((n, len(players)), np.nan)
    for d in range(n):
        try:
            f = fit_reml(u.assign(mult=boot.counts[d, pos]))
        except RemlError:
            continue
        p = f["players"]
        basis = p["ybar"] if f["floor"] else p["theta"]
        est[d, np.searchsorted(players, p.index.to_numpy())] = basis.to_numpy()
    return est


def bootstrap_cell(
    units: pd.DataFrame, base: pd.DataFrame, fit: dict[str, Any], players: np.ndarray, boot: Boot,
    use_posterior: bool,
) -> dict[str, Any]:  # fmt: skip
    """Rank stability and intervals for pressure, baseline and delta.

    Ranks, Top-10 inclusion and rank intervals come from a full REML refit in every draw
    (``boot_method = FULL_REFIT``). The estimate interval keeps the full-sample variance components
    so it describes the same quantity as the point estimate. The fixed-variance rank statistics are
    kept (``*_fixed``) and the largest gap to the refit is recorded in ``check``.
    """
    u = units[units["player_id"].isin(players)]
    ybar, P = boot.weighted_means(
        u["player_id"].to_numpy(),
        u["match_id"].to_numpy(),
        u["prec"].to_numpy(),
        u["y"].to_numpy(),
        players,
    )
    if use_posterior:
        basis = np.full_like(ybar, np.nan)
        ok = P > 0
        basis[ok] = posterior(ybar[ok], P[ok], fit["mu"], fit["tau2"], fit["sigma2"])
    else:
        basis = ybar
    idx = pd.Index(players, name="player_id")
    fixed = rank_stability(basis, idx, top_k=10)
    refit = rank_stability(refit_draws(units, players, boot), idx, top_k=10)
    stab = fixed.copy()
    for c in ("top_k_prob", "rank_median", "rank_low", "rank_high", "draws_present"):
        stab[f"{c}_fixed"] = fixed[c]
        stab[c] = refit[c]
    stab["boot_method"] = "FULL_REFIT"
    j = (
        fixed.set_index("player_id")["top_k_prob"]
        .to_frame("a")
        .join(refit.set_index("player_id")["top_k_prob"].rename("b"))
    )
    sel = j[(j["a"] >= 0.1) | (j["b"] >= 0.1)]
    check = {
        "draws": boot.n_draws,
        "players_compared": int(len(sel)),
        "max_abs_gap": float((sel["a"] - sel["b"]).abs().max()) if len(sel) else 0.0,
    }
    check["fixed_variance_within_0_05"] = bool(check["max_abs_gap"] <= 0.05)
    b = base[base["player_id"].isin(players)]
    bm, _ = boot.weighted_means(
        b["player_id"].to_numpy(), b["match_id"].to_numpy(), b["n"].to_numpy().astype(float),
        (b["sr"] / b["n"]).to_numpy(), players,
    )  # fmt: skip
    delta = ybar - bm
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        d_lo, d_hi = np.nanpercentile(delta, [2.5, 97.5], axis=0)
        s_lo, s_hi = np.nanpercentile(ybar, [2.5, 97.5], axis=0)
        b_lo, b_hi = np.nanpercentile(bm, [2.5, 97.5], axis=0)
        d_se = np.nanstd(delta, axis=0, ddof=1)
    extra = pd.DataFrame(
        {"player_id": players, "delta_low": d_lo, "delta_high": d_hi, "delta_se": d_se,
         "pressure_low": s_lo, "pressure_high": s_hi, "baseline_low": b_lo, "baseline_high": b_hi}
    )  # fmt: skip
    return {"stability": stab.merge(extra, on="player_id"), "check": check}


# ---------------------------------------------------------------------------------------------
# evidence class and status
# ---------------------------------------------------------------------------------------------
def evidence_class(est: pd.DataFrame, min_matches: float) -> pd.Series:
    """Predeclared evidence class (criteria ``evidence_classes``; order: first match wins).

    Needs columns ``eligible, ci_low, n_matches, pos_share, disp, estimate``.
    """
    el = est["eligible"].astype(bool)
    coh = est[el]
    q80 = coh["estimate"].quantile(0.8) if len(coh) else np.nan
    q75 = coh["disp"].quantile(0.75) if len(coh) else np.nan
    m = est["n_matches"] / min_matches
    out = pd.Series("UNCLASSIFIED_LOW", index=est.index, dtype=object)
    strong_lim = (est["estimate"] >= q80) & ((est["ci_low"] <= 0) | (m < 2))
    strong_sub = (est["ci_low"] > 0) & (m >= 2) & (est["pos_share"] >= 0.5)
    inconsistent = (est["pos_share"] < 0.5) | ((est["disp"] > q75) & (est["estimate"] > 0))
    out[strong_lim] = "STRONG_LIMITED"
    out[strong_sub] = "STRONG_SUBSTANTIAL"
    out[inconsistent] = "INCONSISTENT"
    out[~el] = "INSUFFICIENT"
    return out


def list_status(
    crit: dict[str, Any], split_half_sb: float | None, sb_low: float | None, oot_low: float | None,
    floor: bool, n_eligible: int, n_split_players: int, n_oot_players: int,
) -> dict[str, str]:  # fmt: skip
    """Indicative list status from the predeclared thresholds (final status is set in chunk 4)."""
    t = crit["status_thresholds"]
    e = crit["eligibility"]
    if n_eligible < 10:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "fewer than ten eligible players"}
    reasons = []
    if floor:
        reasons.append("between-player variance at the floor (unshrunk ordering)")
    if n_split_players < e["min_players_split_half"]:
        reasons.append("split-half NOT_ESTIMABLE (too few players)")
    if n_oot_players < e["min_players_out_of_time"]:
        reasons.append("out-of-time NOT_ESTIMABLE (too few players)")
    v, p = t["VALIDATED"], t["PROVISIONAL"]
    ok_sh = split_half_sb is not None and np.isfinite(split_half_sb)
    ok_lb = sb_low is not None and np.isfinite(sb_low)
    ok_oot = oot_low is not None and np.isfinite(oot_low)
    prov = (
        not reasons and ok_sh and ok_lb and ok_oot and split_half_sb >= p["split_half_min"]
        and sb_low > p["split_half_lower_bound_gt"] and oot_low > p["out_of_time_lower_bound_gt"]
    )  # fmt: skip
    valid = (
        prov and split_half_sb >= v["split_half_min"] and sb_low >= v["split_half_lower_bound_min"]
        and oot_low > v["out_of_time_lower_bound_gt"]
    )  # fmt: skip
    if valid:
        return {"status": "VALIDATED", "reason": "all VALIDATED thresholds met"}
    if prov:
        return {"status": "PROVISIONAL", "reason": "PROVISIONAL thresholds met, VALIDATED not met"}
    if ok_sh and split_half_sb < p["split_half_min"]:
        reasons.append(f"split-half {split_half_sb:.2f} below {p['split_half_min']}")
    if ok_lb and sb_low <= p["split_half_lower_bound_gt"]:
        reasons.append("split-half lower bound not above 0")
    if ok_oot and oot_low <= p["out_of_time_lower_bound_gt"]:
        reasons.append("out-of-time lower bound not above 0")
    return {"status": "EXPLORATORY", "reason": "; ".join(reasons) or "thresholds not met"}


# ---------------------------------------------------------------------------------------------
# reliability
# ---------------------------------------------------------------------------------------------
def _rel_units(units: pd.DataFrame) -> pd.DataFrame:
    """Unit table for ``reliability.py``: weight is the precision so means match REML."""
    return units.assign(w=units["prec"])[["player_id", "match_id", "match_date", "y", "w"]]


def player_bootstrap_spearman(
    a: pd.Series, b: pd.Series, n: int = 500, seed: int = SEED
) -> tuple[float, float, float]:
    """Spearman correlation of two aligned series with a player-resampling interval."""
    ra, rb = a.rank().to_numpy(), b.rank().to_numpy()
    rho = float(np.corrcoef(ra, rb)[0, 1])
    rng = np.random.default_rng(seed)
    k = len(a)
    vals = []
    av, bv = a.to_numpy(), b.to_numpy()
    for _ in range(n):
        i = rng.integers(0, k, k)
        x, y = pd.Series(av[i]).rank().to_numpy(), pd.Series(bv[i]).rank().to_numpy()
        if x.std() > 0 and y.std() > 0:
            vals.append(float(np.corrcoef(x, y)[0, 1]))
    v = np.asarray(vals)
    return rho, float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


def reliability_block(
    units: pd.DataFrame, players: np.ndarray, crit: dict[str, Any], counts: pd.DataFrame, n_boot: int = 1000
) -> dict[str, Any]:  # fmt: skip
    """Split-half (parity and time), ICC and out-of-time on the unshrunk means of eligible players."""
    e = crit["eligibility"]
    u = units[units["player_id"].isin(players)]
    ru = _rel_units(u)
    half_min = max(int(e["min_matches"] // 2), 2)
    par = split_half(ru, "parity", half_min, n_boot=n_boot)
    tim = split_half(ru, "time", half_min, n_boot=min(n_boot, 300))
    per_format = {}
    for f in ("IPL", "T20I"):
        uf = u[u["competition_type"] == f]
        try:
            per_format[f] = split_half(_rel_units(uf), "parity", max(half_min // 2, 2), n_boot=0)
        except Exception:  # pragma: no cover - degenerate format subset
            per_format[f] = {"r": float("nan"), "spearman_brown": float("nan"), "n_players": 0}
    ic = icc1(ru)
    early = u[u["period"] == "TRAIN"]
    late = u[u["period"] == "VALIDATION"]
    pe = precision_weighted_means(_rel_units(early))
    pl = precision_weighted_means(_rel_units(late))
    pe = pe[pe["n_matches"] >= e["min_matches"]]
    pl = pl[pl["n_matches"] >= e["min_matches_2025_window"]]
    oot = out_of_time_correlation(pe, pl, e["min_players_out_of_time"])
    if oot["status"] == "ESTIMATED":
        j = (
            pe.set_index("player_id")["ybar"]
            .to_frame("a")
            .join(pl.set_index("player_id")["ybar"].rename("b"), how="inner")
        )
        rho, lo, hi = player_bootstrap_spearman(j["a"], j["b"])
        oot.update({"low": lo, "high": hi})
    else:
        oot.update({"low": None, "high": None})
    return {"parity": par, "time": tim, "per_format": per_format, "icc": ic, "oot": oot}


# ---------------------------------------------------------------------------------------------
# one cell: role x intensity x residual
# ---------------------------------------------------------------------------------------------
def run_cell(
    df: pd.DataFrame, deliv: pd.DataFrame, role: str, w: pd.Series, resid: pd.Series,
    crit: dict[str, Any], boot: Boot | None, elig_mult: float = 1.0, reliability: bool = True,
    n_boot_rel: int = 1000,
) -> dict[str, Any]:  # fmt: skip
    """Full estimation for one role, intensity and residual; returns tables and diagnostics."""
    units = pressure_units(df, role, w, resid)
    base = baseline_table(df, role, w, resid)
    result: dict[str, Any] = {"role": role, "units": units, "scopes": {}}
    cu, fmt_mu = centre_by_format(units)
    result["format_means"] = fmt_mu
    for scope in SCOPES:
        su = cu if scope == "COMBINED" else units[units["competition_type"] == scope]
        counts = scope_counts(deliv, units, scope)
        elig = eligible_players(counts, role, crit, elig_mult)
        players = np.sort(elig[elig].index.to_numpy())
        entry: dict[str, Any] = {"counts": counts, "eligible": elig, "players": players}
        result["scopes"][scope] = entry
        if len(players) < 10:
            entry["status"] = "INSUFFICIENT_EVIDENCE"
            continue
        eu = su[su["player_id"].isin(players)]
        try:
            fit = fit_reml(eu)
        except RemlError as exc:  # pragma: no cover - degenerate cell
            entry["status"] = f"NOT_ESTIMABLE: {exc}"
            continue
        entry["fit"] = fit
        entry["units"] = eu
        ps = fit["players"]
        use_post = not fit["floor"]
        ps["basis"] = ps["theta"] if use_post else ps["ybar"]
        entry["rank"] = point_ranking(ps["basis"])
        entry["use_posterior"] = use_post
        if scope == "COMBINED" and boot is not None:
            bc = bootstrap_cell(eu, base, fit, players, boot, use_post)
            entry["boot"] = bc
            if reliability:
                entry["reliability"] = reliability_block(eu, players, crit, counts, n_boot_rel)
    result["baseline"] = base
    return result


def delta_rank(cell: dict[str, Any], base: pd.DataFrame, scope: str = "COMBINED") -> pd.Series:
    """Rank of the unshrunk pressure-minus-baseline difference (sensitivity ranking)."""
    e = cell["scopes"][scope]
    if "fit" not in e:
        return pd.Series(dtype=float)
    b = base.assign(wsum=base["sr"]).groupby("player_id").agg(sr=("sr", "sum"), n=("n", "sum"))
    bl = b["sr"] / b["n"]
    ps = e["fit"]["players"]
    d = ps["ybar"] - bl.reindex(ps.index)
    return point_ranking(d)


def overlap_row(a: pd.Series, b: pd.Series, k: int = 10) -> dict[str, Any]:
    """Spearman and Top-k overlap of two rank series over their common players."""
    j = pd.concat([a.rename("a"), b.rename("b")], axis=1, join="inner").dropna()
    if len(j) < 3:
        return {"n_common": int(len(j)), "spearman": None, "top10_overlap": None}
    return {
        "n_common": int(len(j)),
        "spearman": float(j["a"].corr(j["b"], method="spearman")),
        "top10_overlap": int(len(set(a[a <= k].index) & set(b[b <= k].index))),
    }


def exposure_by_context(
    df: pd.DataFrame, role: str, w: pd.Series, players: np.ndarray
) -> pd.DataFrame:
    """Pressure deliveries (intensity >= 0.5) per player by phase and innings."""
    m = (w >= HIGH_CUT) & df[ROLE_COL[role]].isin(players)
    d = df.loc[m, [ROLE_COL[role], "innings_phase", "innings_number"]].rename(
        columns={ROLE_COL[role]: "player_id"}
    )
    ph = d.pivot_table(index="player_id", columns="innings_phase", aggfunc="size", fill_value=0)
    ph.columns = [f"n_{c}" for c in ph.columns]
    inn = d.pivot_table(index="player_id", columns="innings_number", aggfunc="size", fill_value=0)
    inn.columns = [f"n_innings{int(c)}" for c in inn.columns]
    return ph.join(inn).reset_index()


def component_means(
    df: pd.DataFrame, role: str, w: pd.Series, res: pd.DataFrame, players: np.ndarray
) -> pd.DataFrame:
    """Intensity-weighted pressure mean of each oriented component residual (reported only)."""
    col = ROLE_COL[role]
    m = (w >= HIGH_CUT) & df[col].isin(players)
    out = pd.DataFrame({"player_id": df.loc[m, col].to_numpy()})
    for spec in SPECS:
        if spec.role != role:
            continue
        r = res[f"r_{role}_{spec.name}"][m]
        ww = w[m]
        ok = r.notna().to_numpy()
        t = pd.DataFrame(
            {
                "player_id": out["player_id"].to_numpy()[ok],
                "wr": (ww * r)[ok].to_numpy(),
                "w": ww[ok].to_numpy(),
            }
        )
        g = t.groupby("player_id").sum()
        out = out.join((g["wr"] / g["w"]).rename(f"comp_{spec.name}"), on="player_id")
    return out.drop_duplicates("player_id").reset_index(drop=True)


def observed_expected(
    df: pd.DataFrame,
    role: str,
    w: pd.Series,
    results: dict[tuple[str, str], dict[str, Any]],
    players: np.ndarray,
) -> pd.DataFrame:
    """Observed and expected runs and wicket rates on pressure deliveries (intensity-weighted)."""
    col = ROLE_COL[role]
    m = (w >= HIGH_CUT) & df[col].isin(players)
    out = None
    for name in ("runs", "wicket"):
        spec: TargetSpec = spec_for(role, name)
        r = results[(role, name)]
        y, e = r["y"][m], r["expected"][m]
        ok = (y.notna() & e.notna()).to_numpy()
        t = pd.DataFrame({"player_id": df.loc[m, col].to_numpy()[ok], "wy": (w[m] * y)[ok].to_numpy(),
                          "we": (w[m] * e)[ok].to_numpy(), "w": w[m][ok].to_numpy()})  # fmt: skip
        g = t.groupby("player_id").sum()
        part = pd.DataFrame({f"obs_{name}": g["wy"] / g["w"], f"exp_{name}": g["we"] / g["w"]})
        out = part if out is None else out.join(part, how="outer")
        del spec
    return out.reset_index()
