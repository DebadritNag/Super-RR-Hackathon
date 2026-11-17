import json

d = json.load(open("data/reports/rr_analysis_tables.json", encoding="utf-8"))
print(d["scope"], d["season_results"], d["knockout_matches"], d["data_quality"], sep="\n")
for r in d["comparisons"]:
    f = lambda x: "NA" if x is None else f"{x:.2f}"
    print(
        f"{r['metric']:22s}{r['period']:10s}rr={f(r['rr_value'])} lg={f(r['league_value'])} "
        f"d={f(r['difference'])} [{f(r['ci_low'])},{f(r['ci_high'])}] n={r['rr_balls']:.0f} {r['assessment']}"
    )
for r in d["bowler_depth"]:
    print(r)
