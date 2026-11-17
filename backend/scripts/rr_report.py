"""Render ``rr_historical_performance_and_recruitment_gaps.md`` from ``rr_analysis_tables.json``.

Tables are generated from the data. The prose states only numbers that appear in those tables
or in the verification log, and every media item is a paraphrase attributed to its link.
"""

from __future__ import annotations

PERIOD_ORDER = ["2022", "2023", "2024", "2025", "2022-2025", "2026"]
MARK = {"RR_BETTER_SUPPORTED": " (+)", "RR_WORSE_SUPPORTED": " (-)", "LOW_SAMPLE": " (low n)"}

MEDIA = [
    (
        "ESPNcricinfo, IPL 2025 RR team preview (March 2025)",
        "https://www.espncricinfo.com/story/ipl-2025-rr-team-preview-can-revamped-rajasthan-royals-cope-with-dearth-of-overseas-batters-1476923",
        "Reports that RR rebuilt the bowling group at the 2025 mega auction (Archer, Deshpande, Hasaranga, Theekshana) and bought no overseas batters.",
    ),
    (
        "Live Hindustan, end of RR's IPL 2025 campaign (Hindi)",
        "https://www.livehindustan.com/cricket/ipl/rajasthan-royals-journey-from-ipl-2025-ended-they-won-only-4-matches-in-14-games-the-season-was-the-worst-for-rr-201747790642425.html",
        "Headline states RR won 4 of 14 matches in 2025, their worst season. Only the headline summary was seen.",
    ),
    (
        "Cricket Times, RR SWOT analysis ahead of IPL 2026 (March 2026)",
        "https://crickettimes.com/2026/03/swot-analysis-of-rajasthan-royals-rrs-report-card-ahead-of-the-ipl-2026/",
        "Describes 2025 as a poor season in which Jaiswal was the one bright spot and the side lacked finishing instinct.",
    ),
    (
        "Mumbai Mirror, RR chase redemption after last season (March 2026)",
        "https://www.mumbaimirror.indiatimes.com/sport/ipl-2026-rajasthan-royals-chase-redemption-after-heartbreaking-last-season/articleshow/129659300.html",
        "Argues that better composure in 2025 chases would have put RR in the playoffs.",
    ),
    (
        "Times of India, IPL auction 2026 and RR (December 2025)",
        "https://timesofindia.indiatimes.com/sports/cricket/ipl/top-stories/ipl-auction-2026-after-smart-trading-rajasthan-royals-a-few-minor-fixes-away-from-a-balanced-squad/articleshow/125949250.cms",
        "Says RR traded for Jadeja and Curran (Samson went the other way) to address a long-standing balance problem and to get batting depth to number eight.",
    ),
    (
        "Indian Express, quick comment on Riyan Parag (April 2026)",
        "https://indianexpress.com/article/sports/cricket/riyan-parag-81-rusn-7-matches-rajasthan-royals-failure-ipl-10650786/",
        "Says RR leaned heavily on the top three (Jaiswal, Sooryavanshi, Jurel) and that weak returns lower down were masked while the top order scored.",
    ),
    (
        "IPL official site, Qualifier 2 match report (May 2026)",
        "https://www.iplt20.com/news/article/tata-ipl-2026-qualifier-2-gt-vs-rr-match-report",
        "Reports that GT chased 215 to beat RR by seven wickets in Qualifier 2. Agrees with the organiser data.",
    ),
]


def f(x, d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def diff_cell(r):
    if r["difference"] is None:
        return "n/a"
    return f"{r['difference']:+.2f} [{f(r['ci_low'])}, {f(r['ci_high'])}]{MARK.get(r['assessment'], '')}"


def pooled_table(doc):
    rows = [r for r in doc["comparisons"] if r["period"] == doc["primary_window"]]
    out = [
        "| Metric | Unit | RR | League excl. RR | Difference [95% CI] | RR balls |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        out.append(
            f"| {r['label']} | {r['unit'].replace('_', ' ')} | {f(r['rr_value'])} | "
            f"{f(r['league_value'])} | {diff_cell(r)} | {r['rr_balls']:.0f} |"
        )
    return "\n".join(out)


def season_table(doc):
    metrics = list(dict.fromkeys(r["metric"] for r in doc["comparisons"]))
    idx = {(r["metric"], r["period"]): r for r in doc["comparisons"]}
    head = "| Metric | " + " | ".join(PERIOD_ORDER) + " |"
    out = [head, "|---|" + "---|" * len(PERIOD_ORDER)]
    for m in metrics:
        label = idx[(m, "2022")]["label"]
        cells = [diff_cell(idx[(m, p)]) for p in PERIOD_ORDER]
        out.append(f"| {label} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def cand_table(t):
    rows = t["rows"]
    if not rows:
        return "_No rows._"
    cols = list(rows[0].keys())
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append(
            "| "
            + " | ".join(
                ""
                if r[c] is None
                else (str(int(r[c])) if float(r[c]).is_integer() else f"{r[c]:.2f}")
                if isinstance(r[c], float)
                else str(r[c])
                for c in cols
            )
            + " |"
        )
    return "\n".join(out)


def render(doc) -> str:
    q = doc["data_quality"]
    spd = {r["pace_or_spin"]: r["mean_kmh"] for r in q["mean_speed_pace_spin"]}
    sr = {r["season"]: r for r in doc["season_results"]}
    ret = doc["retention"]
    prov = doc["provenance"]
    season_rows = "\n".join(
        f"| {s} | {int(sr[s]['n'])} | {int(sr[s]['wins'])} | {int(sr[s]['not_completed'])} | {int(sr[s]['with_deliveries'])} |"
        for s in sorted(sr)
    )
    ko_rows = "\n".join(
        f"| {k['season']} | {k['stage']} | {k['match_date']} | {k['home_team']} v {k['away_team']} | {k['result']} |"
        for k in doc["knockout_matches"]
    )
    depth = "\n".join(
        f"| {d['season']} | {d['kind']} | {d['rr_bowlers']} | {d['league_mean']:.2f} | {d['league_min']}-{d['league_max']} |"
        for d in doc["bowler_depth"]
    )
    media = "\n".join(f"- [{t}]({u}): {s}" for t, u, s in MEDIA)
    excl = "\n".join(
        f"- match {e['match_id']} ({e['match_date']}, {e['home_team']} v {e['away_team']}): {e['result']}"
        for e in doc["excluded_matches_with_deliveries"]
    )
    retention_txt = (
        f"The retention table holds {ret['rows']} rows; {ret['retained_excluded']} confirmed retained players are excluded from the candidate tables."
        if ret["list_received"]
        else "No official retention list has been received (expected 17 November 2026; the retention table is absent or empty in `exploratory.duckdb`). No player is marked retained or available, and every availability value below is UNKNOWN."
    )
    cands = "\n\n".join(
        f"### {k}: {v['title']} ({v['n']} players)\n\nThreshold: at least {v['min_balls']} balls in each listed sample column (IPL 2022-2025 pre-test window). {v['ordering']}.\n\n{cand_table(v)}"
        for k, v in doc["candidate_fit_tables"].items()
    )
    return f"""# Rajasthan Royals: historical performance and recruitment gaps

Descriptive analysis for the SupeRR Selector Season 2 submission. It is not a pressure-performance
result, not a ranking, and not a list of recommended players. Generated by `scripts/rr_analysis.py`
(seed {doc["seed"]}, {doc["n_boot"]} bootstrap draws, resampling matches, {int(doc["ci_level"] * 100)}% percentile intervals).
Machine-readable tables: `rr_analysis_tables.json` (served by `GET /api/v1/rr/analysis`).

The five sections below are kept separate on purpose. Section 1 holds published opinion only
(hypotheses). Section 2 holds numbers recomputed from the organiser data. Sections 3 and 4 are
my interpretation and the hypotheses that follow from it. Section 5 states how far any of it can be trusted.

## 1. Published media observations (hypotheses, not evidence)

I located these items with a web search of result summaries. I did not read each article in full,
so they are paraphrased from the summaries shown and none of the claims in them is verified here.
They are used only to decide what to test in section 2.

{media}

No media source was found that gives a phase-by-phase breakdown. Qualifier 2 (GT won by seven wickets
chasing 215) is the only item above that is also a checkable match fact, and the organiser data agree.

## 2. Verified organiser-data calculations

### 2.1 Scope, provenance and data quality

- Team: `{doc["team"]["team_name"]}`, `team_id` {doc["team"]["team_id"]}, looked up by name in `teams.csv` (via `superr.duckdb`).
- Matches: IPL 2022-2026. Ball rows come from the official ball-by-ball data loaded into `superr.duckdb` (sha256 `{prov["official_db_sha256"]}`); phase labels (powerplay overs 1-6, middle 7-15, death 16-20) come from `exp_pre_delivery_state` in `exploratory.duckdb` (sha256 `{prov["analytical_store_sha256"]}`).
- Rows used: {doc["scope"]["rows"]} deliveries in {doc["scope"]["matches"]} matches. Rule: {doc["scope_rule"]}. Matches per season in the analysis: {doc["scope"]["matches_by_season"]}.
- Matches with deliveries but no usable regulation rows (all DLS-affected, so excluded by the project rule):
{excl}
- League average means all nine other teams in the same season(s) and the same phase definition. RR rows are excluded from it.
- Pace/spin field (`pace_or_spin`, with `bowling_type`): {q["ipl_deliveries"]} IPL deliveries, {q["pace_or_spin_null"]} missing values, no `bowling_type` mapped to both classes ({q["type_class_mismatches"]} mismatches). {q["bowlers_with_more_than_one_type"]} bowlers carry more than one `bowling_type` over the period, so the field is a per-delivery label and not a fixed bowler attribute. Mean `bowl_speed` where the value is between 40 and 170 is {spd["Pace"]} (pace) and {spd["Spin"]} (spin), which agrees with the labels. `bowl_speed` itself is not usable as a measure: {q["bowl_speed_zero_or_negative"]} IPL rows are zero or negative and {q["bowl_speed_above_200"]} exceed 200. I therefore use only the pace/spin class.
- Wickets: batting-side tables count every dismissal including run-outs; bowling-side tables count bowler-credited wickets only. They are different quantities.
- The 2026 rows are read for this descriptive table only. Nothing was tuned on them and the TEST lock log is unchanged by this script.

### 2.2 Season results and knock-out matches (from `matches`)

All RR matches, including play-offs.

| Season | RR matches | RR wins | Not completed | With ball data |
|---|---|---|---|---|
{season_rows}

RR knock-out matches:

| Season | Stage | Date | Match | Result |
|---|---|---|---|---|
{ko_rows}

For 2026 the data agree with the owner's account: RR won the Eliminator (47 runs, 27 May 2026,
against Sunrisers Hyderabad) and lost the match labelled Qualifier (match 73, 29 May 2026) to Gujarat Titans
by seven wickets. The data label that match "Qualifier", with Qualifier 1 (match 71) played by RCB and GT;
the media items above call the 29 May match Qualifier 2. The data show 16 RR matches in 2026: 14 league (8 wins) and 2 play-off (1 win).

### 2.3 RR versus league, pooled 2022-2025 (primary window)

Difference = RR minus league. (+) means the interval excludes zero in RR's favour, (-) means it excludes zero against RR, (low n) means fewer than {doc["min_rr_balls"]} RR balls. Usage rows describe how teams use players and carry no better or worse reading.

{pooled_table(doc)}

### 2.4 RR versus league by season (difference [95% CI])

2026 is shown separately and is descriptive only.

{season_table(doc)}

### 2.5 Bowler depth (bowlers with at least {doc["bowler_depth"][0]["min_balls"]} legal balls in the season)

| Season | Kind | RR bowlers | League mean (other teams) | League range |
|---|---|---|---|---|
{depth}

## 3. Interpretation

Read the intervals before the point estimates. Over 28 metrics and six periods, a handful of intervals exclude zero by chance alone, so a single supported row is a lead and not a finding.

- **Middle-over batting against spin.** No gap is supported. Pooled 2022-2025 RR scored 8.10 runs per over against spin in the middle overs against 8.22 for the league, interval [-0.67, 0.47]; wicket loss rates are also indistinguishable. The 2025 and 2026 rows are wide. The media claim that this was a weakness is not corroborated, and the data also cannot exclude a moderate one.
- **Middle and lower-order batting.** RR batters at positions 6-8 faced fewer of the team's balls than the league (14.58 against 18.23 per 100 balls, interval [-6.78, -0.50]). That is a usage difference. It fits a top-heavy side, but the run rate and dismissal rate at positions 6-8 are not distinguishable from the league pooled; the only supported season rows are a higher dismissal rate at 6-8 in 2024 (183 balls) and against pace in the middle overs in 2023 (259 balls), both small samples.
- **Powerplay.** RR bowling conceded fewer runs per over than the league (7.98 against 8.82, interval [-1.41, -0.22]) and pace bowling in the powerplay shows the same (7.93 against 8.80). Powerplay wicket-taking is not distinguishable. RR batting lost fewer wickets in the powerplay pooled (0.21 against 0.25 per over), but the interval touches zero.
- **Middle-over wicket-taking.** RR bowler-credited wickets in the middle overs were lower than the league pooled (0.23 against 0.27 per over, interval [-0.08, -0.00]), driven by 2025 (0.18 against 0.27, [-0.14, -0.04]). In 2026 the rate (0.30) is not distinguishable. This is the only bowling area where a gap is supported pooled, and it is borderline.
- **Death overs.** Neither death batting (10.72 against 10.77 runs per over) nor death bowling (10.73 against 10.59 conceded) is distinguishable pooled. In 2025 RR conceded 12.18 per over at the death against 10.68, interval [-0.25, 3.19], which is large but not supported. This does not corroborate the "lack of finishing" claim as a pooled pattern.
- **Fast-bowling depth.** RR had three or four pace bowlers with 120+ balls each season against a league mean of 3.2 to 4.3. RR used pace for 57.2% of balls against 63.4% for the league, so the side leaned more on spin. Depth counts are descriptive and carry no interval.
- **Finishing and all-rounders.** No finishing deficit is supported. The data do not support a stated all-rounder need beyond the usage difference at positions 6-8. I did not test chase composure (a media claim) and make no statement on it.

## 4. Recruitment hypotheses

Hypotheses to test with more data, ordered by nothing.

1. A bowler who adds middle-over wicket-taking (pace or spin). Supported only by the pooled 2022-2025 interval and the 2025 season; 2026 does not repeat it.
2. Batting depth at positions 6-8. Rests on a usage difference and two small-sample season rows; run scoring at 6-8 is not shown to be weak.
3. Pace depth. Weak: RR counts are near the league mean.
4. Middle-over batting against spin, death batting and death bowling: no supported gap, so no hypothesis is drawn.

### Descriptive candidate-fit tables (not recommendations)

{retention_txt}

The 2026 squad file (`ipl squad.csv`, sha256 `{prov["squad_snapshot_sha256"]}`) is a snapshot reference only. The column `squad_snapshot_team` shows the team listed there for an exact name match, and "not matched" means no exact name match, not that the player is free. It says nothing about auction availability. The `availability` column is UNKNOWN unless a retention row says otherwise. Players are listed alphabetically. Inclusion means only that a sample threshold is met in the pre-test window; it implies no fit, quality, ranking or recommendation. Sample sufficiency labels come from the descriptive profiles. These tables do not use any pressure score.

{cands}

## 5. Confidence and limitations

- Sample sizes are small: one team over four seasons is about 60 matches, and phase and pace/spin splits cut that to a few hundred balls. Bootstrap intervals resample matches and assume matches are independent.
- No multiplicity correction. About one supported row in twenty is expected by chance, and the supported rows here are few and borderline (two intervals end at -0.00).
- The league average pools other teams. It does not adjust for venue, opposition strength, toss, innings, target or the Impact Player rule. Pooled 2022-2025 league rows are not weighted to RR's seasons.
- DLS-affected rows are excluded, which removes three matches with ball data (listed in 2.1), one of them an RR home match in 2026.
- Pace/spin is a delivery label; the position-based rows depend on `striker_batting_order` as supplied.
- The squad snapshot is not an availability source. Retention status: {("received" if ret["list_received"] else "pending")}. Historical weakness, performance evidence, role fit, availability and evidence confidence are separate questions and only the first two are addressed with data here.
- Media items are unverified hypotheses read from summaries.
- Confidence: moderate that no large gap exists in middle-over batting against spin, death batting or death bowling; low for the middle-over wicket-taking gap; low for the batting-depth idea.
"""
