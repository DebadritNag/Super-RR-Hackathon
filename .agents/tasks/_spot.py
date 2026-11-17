import csv, random, duckdb, collections
rows=collections.defaultdict(list)
with open('d:/Data/updated_ball_by_ball.csv',encoding='utf-8',newline='') as f:
    for r in csv.DictReader(f):
        rows[(int(r['match_id']),int(r['innings']))].append(r)
for k in rows: rows[k].sort(key=lambda r:int(r['innings_ball_num']))
mt={}
with open('d:/Data/matches.csv',encoding='utf-8',newline='') as f:
    for r in csv.DictReader(f): mt[int(r['match_id'])]=r
def tot(k): return sum(int(r['runs'] or 0)+int(r['extras1_runs'] or 0)+int(r['extras_2_runs'] or 0) for r in rows[k])
c=duckdb.connect('data/database/exploratory.duckdb',read_only=True)
random.seed(7)
ok=0;n=0;fails=[]
# 1-3: random innings-2 deliveries, independent recomputation (non-DLS matches)
cands=[k for k in rows if k[1]==2 and (k[0],1) in rows and not mt.get(k[0],{}).get('revised_target','').strip() and not mt[k[0]]['second_inn_revised_overs'].strip() and not mt[k[0]]['first_inn_revised_overs'].strip()]
print('non-DLS chase innings',len(cands))
for k in random.sample(cands,6):
    seq=rows[k]; j=random.randrange(len(seq)); pre=seq[:j]
    runs=sum(int(r['runs'] or 0)+int(r['extras1_runs'] or 0)+int(r['extras_2_runs'] or 0) for r in pre)
    legal=sum(1 for r in pre if r['extras_type'] not in ('wide','Overstep','other'))
    wk=sum(1 for r in pre if r['is_wicket'].strip().lower() in('true','1'))
    target=tot((k[0],1))+1
    exp=dict(rr=target-runs,lb=120-legal,wr=10-wk)
    b=seq[j]['innings_ball_num']
    got=c.execute('select runs_required,legal_balls_remaining,wickets_remaining,team_runs_before,rrr from exp_pre_delivery_state where match_id=? and innings_number=2 and innings_ball_num=?',[k[0],int(b)]).fetchone()
    rrr=exp['rr']/exp['lb']*6 if exp['lb']>0 and exp['rr']>0 else None
    good=(got[0],got[1],got[2])==(exp['rr'],exp['lb'],exp['wr']) and ((rrr is None and got[4] is None) or (rrr is not None and got[4] is not None and abs(rrr-got[4])<1e-9))
    print('chase',k,'ball',b,'indep',exp,'rrr',rrr,'db',got,'OK' if good else 'FAIL'); n+=1; ok+=good
# 4: innings-2 target = innings1 total+1 vs db target, several matches
res=[]
for k in random.sample(cands,8):
    t=c.execute('select max(target) from exp_pre_delivery_state where match_id=? and innings_number=2',[k[0]]).fetchone()[0]
    res.append((k[0],tot((k[0],1))+1,t))
print('target check',res, all(a==b for _,a,b in res)); n+=1; ok+=all(a==b for _,a,b in res)
# 5: DLS matches target vs revised_target
dl=[(m,int(r['revised_target'])) for m,r in mt.items() if r['revised_target'].strip() and (m,2) in rows]
dres=[]
for m,rt in dl[:10]:
    row=c.execute('select max(target),max(target_source) from exp_pre_delivery_state where match_id=? and innings_number=2',[m]).fetchone()
    dres.append((m,rt,row))
print('DLS',dres)
# 6: innings 1 legal balls total per innings vs db (post_innings_legal_balls)
bad=0;chk=0
for k in random.sample([k for k in rows if k[1]==1],25):
    L=sum(1 for r in rows[k] if r['extras_type'] not in ('wide','Overstep','other'))
    d=c.execute('select max(post_innings_legal_balls), max(legal_balls_bowled_before)+0 from exp_pre_delivery_state where match_id=? and innings_number=1',[k[0]]).fetchone()
    chk+=1; bad+= (d[0]!=L)
print('inn1 legal-ball totals mismatches',bad,'of',chk); n+=1; ok+=(bad==0)
# 7: total counts
print('row count csv',sum(len(v) for v in rows.values()),'db state rows',c.execute('select count(*) from exp_pre_delivery_state').fetchone())
# 8: pressure deliveries: chase|q0.9 independent count from exp_pressure_signals
print(c.execute('describe exp_pressure_signals').df()['column_name'].tolist())
print('SUMMARY',ok,'/',n)
