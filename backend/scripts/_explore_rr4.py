import duckdb
c=duckdb.connect('data/database/exploratory.duckdb',read_only=True)
c.execute("attach 'data/database/superr.duckdb' as o (read_only)")
print(c.execute('''select m.match_id, cast(m.match_date as date) dt, m.home_team, m.away_team, m.result, m.result_status,
 (select count(*) from o.deliveries d where d.match_id=m.match_id) nd,
 (select count(*) from exp_pre_delivery_state s where s.match_id=m.match_id and s.regulation_flag and not s.dls_exclude_primary and s.innings_number in (1,2) and s.innings_phase is not null) nf,
 (select count(*) from exp_pre_delivery_state s where s.match_id=m.match_id and s.dls_exclude_primary) ndls
 from o.matches m where m.competition_type='IPL' and m.has_deliveries and m.match_id not in (select match_id from exp_pre_delivery_state s where s.regulation_flag and not s.dls_exclude_primary and s.innings_number in (1,2) and s.innings_phase is not null)''').fetchdf().to_string())
print(c.execute('''select m.match_id, cast(m.match_date as date) dt, m.home_team, m.away_team, m.result, m.result_status, m.has_deliveries from o.matches m join o.competitions k using(comp_id) where m.competition_type='IPL' and k.season in (2024,2025) and not m.has_deliveries''').fetchdf().to_string())
print(c.execute('''select count(*), sum(dls_exclude_primary::int) from (select match_id, innings_number, any_value(dls_exclude_primary) dls_exclude_primary from exp_pre_delivery_state where competition_type='IPL' group by 1,2)''').fetchall())
