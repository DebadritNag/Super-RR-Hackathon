"""Read-only extraction of per player/format/match sufficient statistics (proxy definitions).

All-situation descriptive proxies, innings 1 and 2 only. Innings 3/4 are excluded per metric
(role status UNVERIFIED), not deleted. Only official tables are referenced.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from app.core.database import Database

FORMATS = ("IPL", "T20I")
ALL_FORMATS = ("IPL", "T20I", "OTHER_T20")

# Bowler-credited dismissals, from the distinct dismissal_type strings present in the DB:
# Caught, Bowled, LBW, Stump, Hit Wicket. Not credited: RunOut, Retire Out and both spellings of
# obstructing the field ('Obstracting the field' and 'Obstructing the field').
BOWLER_CREDITED = ("Caught", "Bowled", "LBW", "Stump", "Hit Wicket")

# 'other' behaves no-ball-like but its label is unverified; its primary runs are charged.
CHARGED_EXTRAS = ("wide", "Overstep", "other")

_CRED = ", ".join(f"'{x}'" for x in BOWLER_CREDITED)
_CHG = ", ".join(f"'{x}'" for x in CHARGED_EXTRAS)

BATTER_SQL = """
SELECT m.competition_type AS format, d.striker_id AS player_id, d.match_id,
       count(*)::BIGINT AS n,
       sum(CASE WHEN d.is_legal_ball THEN 1 ELSE 0 END)::BIGINT AS legal_balls,
       count(DISTINCT d.innings_number)::BIGINT AS innings,
       sum(d.batter_runs)::DOUBLE AS runs_sum,
       sum(d.batter_runs * d.batter_runs)::DOUBLE AS runs_sum2
FROM deliveries d JOIN matches m USING (match_id)
WHERE m.has_deliveries AND d.innings_number IN (1, 2) AND d.striker_id IS NOT NULL
  AND coalesce(d.extras_type, 'None') NOT IN ('wide', 'Penalty')
GROUP BY ALL ORDER BY 1, 2, 3
"""

BOWLER_SQL = f"""
WITH x AS (
  SELECT m.competition_type AS format, d.bowler_id AS player_id, d.match_id, d.innings_number,
         d.is_legal_ball,
         d.batter_runs + CASE WHEN d.extras_type IN ({_CHG})
                              THEN coalesce(d.extras_primary_runs, 0) ELSE 0 END AS charged,
         CASE WHEN d.is_wicket AND d.dismissal_type IN ({_CRED}) THEN 1 ELSE 0 END AS w
  FROM deliveries d JOIN matches m USING (match_id)
  WHERE m.has_deliveries AND d.innings_number IN (1, 2) AND d.bowler_id IS NOT NULL
    AND coalesce(d.extras_type, 'None') <> 'Penalty'
)
SELECT format, player_id, match_id,
       count(*)::BIGINT AS n,
       sum(CASE WHEN is_legal_ball THEN 1 ELSE 0 END)::BIGINT AS legal_balls,
       count(DISTINCT innings_number)::BIGINT AS innings,
       sum(charged)::DOUBLE AS econ_sum, sum(charged * charged)::DOUBLE AS econ_sum2,
       sum(w)::DOUBLE AS wkt_sum, sum(w * w)::DOUBLE AS wkt_sum2
FROM x GROUP BY ALL ORDER BY 1, 2, 3
"""

WINDOW_SQL = """
SELECT competition_type AS format, count(*)::BIGINT AS matches_with_deliveries,
       min(match_date) AS first_date, max(match_date) AS last_date
FROM matches WHERE has_deliveries GROUP BY 1 ORDER BY 1
"""


@dataclass
class ProxySamples:
    batter: pd.DataFrame
    bowler: pd.DataFrame
    window: dict = field(default_factory=dict)
    names: dict[int, str] = field(default_factory=dict)
    distinct_dismissal_types: list[str] = field(default_factory=list)


def extract_samples(db: Database) -> ProxySamples:
    """Run the proxy SQL against an (ideally read-only) official DB handle."""
    batter = db.execute(BATTER_SQL).df()
    bowler = db.execute(BOWLER_SQL).df()
    win = db.execute(WINDOW_SQL).df()
    window = {
        r.format: {
            "matches_with_deliveries": int(r.matches_with_deliveries),
            "first_date": str(r.first_date)[:10],
            "last_date": str(r.last_date)[:10],
        }
        for r in win.itertuples()
    }
    names = {int(i): n for i, n in db.query("SELECT player_id, player_name FROM players")}
    types = [
        r[0]
        for r in db.query(
            "SELECT DISTINCT dismissal_type FROM deliveries WHERE dismissal_type IS NOT NULL "
            "ORDER BY 1"
        )
    ]
    for df in (batter, bowler):
        for c in ("player_id", "match_id"):
            df[c] = df[c].astype("int64")
    return ProxySamples(batter, bowler, window, names, types)
