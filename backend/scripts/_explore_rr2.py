import duckdb

e = duckdb.connect("data/database/exploratory.duckdb", read_only=True)
e.execute("attach 'data/database/superr.duckdb' as o (read_only)")
q = [
    "select innings_number, regulation_flag, restricted_innings_flag, phase_rule, count(*) from exp_pre_delivery_state where competition_type='IPL' group by all order by all",
    "select count(*) , count(distinct (match_id, innings_number, innings_ball_num)) from exp_pre_delivery_state",
    "with s as (select match_id, innings_number, sum(out_runs_row) r, sum(den_legal_inc) lb, sum(out_is_wicket::int) w from exp_pre_delivery_state where competition_type='IPL' group by 1,2) select count(*) n, sum((s.r = i.source_total_runs)::int) eq, sum((s.lb=i.legal_ball_count)::int) eqb, sum((s.w=i.wicket_rows)::int) eqw from s join o.innings i using(match_id, innings_number)",
    "select out_extras_type, count(*), sum(den_legal_inc) from exp_pre_delivery_state where competition_type='IPL' group by 1",
    "select count(*) from exp_pre_delivery_state s join o.deliveries d using(match_id, innings_number, innings_ball_num) where s.competition_type='IPL' and s.striker_id=d.striker_id",
    "select striker_batting_order, count(*) from exp_pre_delivery_state where competition_type='IPL' group by 1 order by 1",
    "select sum(den_bowler_credited_wicket), sum(out_is_wicket::int), sum((out_dismissal_type='RunOut')::int) from exp_pre_delivery_state where competition_type='IPL'",
    "select count(*) from exp_pre_delivery_state where competition_type='IPL' and dls_exclude_primary",
]
for s in q:
    print(">>", s[:150])
    print(e.execute(s).fetchdf().to_string())
