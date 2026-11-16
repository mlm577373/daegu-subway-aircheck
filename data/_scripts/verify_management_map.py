"""Independent recomputation of annual-only metrics, scores and timing rules."""
from pathlib import Path
from collections import defaultdict
from datetime import datetime,date,timedelta
from statistics import median
import csv,json,math,re
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/management_map';SID='analysis_station_id'
stations=json.loads((OUT/'stations.json').read_text(encoding='utf-8'))
values=defaultdict(list);cells=defaultdict(list);qc=defaultdict(lambda:[0,0]);qt=defaultdict(lambda:[0,0]);usage=defaultdict(lambda:[0,0.,0.]);trans=defaultdict(lambda:[0,0]);prev={}
slots=['아침 06~09시','낮 10~15시','저녁 16~19시','밤 20~23시'];expected=defaultdict(int)
for year in [2022,2023,2024]:
    yr=str(year);dt=date(year,1,1)
    while dt.year==year:
        day='주말' if dt.weekday()>=5 else '평일'
        for slot,hours in zip(slots,[4,6,4,4]):expected[(yr,day,slot)]+=hours
        dt+=timedelta(days=1)
    with (ROOT/f'data/merged/merged_hourly_{year}.csv').open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            assert row['date'].startswith(yr)
            if row['indoor_quality_flag']!='status_blank_unverified':continue
            try:v=float(row['indoor_pm25'])
            except ValueError:continue
            if not math.isfinite(v) or v<0:continue
            sid=row[SID];h=int(row['hour']);stamp=datetime.fromisoformat(row['date'])+timedelta(hours=h)
            old=prev.get(sid)
            if old:
                assert stamp>old[0]
                if stamp-old[0]==timedelta(hours=1) and old[0].year==year and old[1]>=43.15:
                    trans[(sid,yr)][0]+=1;trans[(sid,yr)][1]+=int(v>=43.15)
            prev[sid]=(stamp,v);values[(sid,yr)].append(v)
            try:u=float(row['board_alight_count'])
            except ValueError:u=float('nan')
            if 5<=h<=23 and math.isfinite(u) and u>=0:
                usage[(sid,yr)][0]+=1;usage[(sid,yr)][1]+=u;usage[(sid,yr)][2]+=u if v>=43.15 else 0
            if h<6:continue
            day='주말' if stamp.weekday()>=5 else '평일';slot=slots[0 if h<=9 else 1 if h<=15 else 2 if h<=19 else 3];q=(stamp.month-1)//3+1
            cells[(sid,yr,day,slot)].append(v)
            qc[(sid,yr,day,slot,q)][0]+=1;qc[(sid,yr,day,slot,q)][1]+=int(v>=43.15)
            qt[(sid,yr,q)][0]+=1;qt[(sid,yr,q)][1]+=int(v>=43.15)
    print('verified annual source',year,flush=True)
def close(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-9),(a,b)
for s in stations:
    sid=s[SID]
    for p in s['periods']:
        yrs=['2022','2023','2024'] if p['period']=='2022~24' else [p['period']]
        vals=[v for y in yrs for v in values[(sid,y)]];n=len(vals);hi=sum(v>=43.15 for v in vals)
        assert n==p['n'] and hi==p['high_n'];close(median(vals),p['median']);close(hi/n,p['rate'])
        tn=sum(trans[(sid,y)][0] for y in yrs);th=sum(trans[(sid,y)][1] for y in yrs)
        assert tn==p['transition_n'] and th==p['stay_high_n'];close(th/tn,p['continuation_rate'])
        un,ut,uh=[sum(usage[(sid,y)][j] for y in yrs) for j in range(3)]
        assert un==p['usage_n'];close(ut,p['usage_total']);close(uh,p['usage_high_total']);close(uh/ut,p['usage_high_share'])
        close(n/p['expected'],p['coverage']);close(un/p['expected_usage'],p['usage_coverage'])
    for r in s['cells']:
        y=r['period'];vals=cells[(sid,y,r['day'],r['slot'])];n=len(vals);hi=sum(v>=43.15 for v in vals)
        assert n==r['n'] and hi==r['high_n'] and expected[(y,r['day'],r['slot'])]==r['expected']
        total_n=sum(qt[(sid,y,q)][0] for q in [1,2,3,4]);total_h=sum(qt[(sid,y,q)][1] for q in [1,2,3,4])
        rate=hi/n;other=(total_h-hi)/(total_n-n);close(rate,r['rate']);close(other,r['other_rate'])
        positives=0
        for q in [1,2,3,4]:
            qn,qh=qc[(sid,y,r['day'],r['slot'],q)];an,ah=qt[(sid,y,q)]
            positives+=int(qn>0 and an>qn and qh/qn>(ah-qh)/(an-qn))
        assert positives==r['positive_subperiods']
        passed=n/r['expected']>=.75 and n>=100 and hi>=10 and rate>=.05 and rate-other>=.03 and rate>=1.25*other and positives>=2
        assert passed==r['period_pass']
    for day in ['평일','주말']:
        for slot in slots:
            yes=sum(r['period_pass'] for r in s['cells'] if r['day']==day and r['slot']==slot)>=2 and s['sufficient']
            assert yes==({'day':day,'slot':slot} in s['chosen'])
ref=json.loads((OUT/'risk_reference.json').read_text(encoding='utf-8'))
for s in stations:
    p=next(p for p in s['periods'] if p['period']=='2022~24')
    scores=[]
    for key,col in [('frequency','rate'),('persistence','continuation_rate'),('overlap','usage_high_share')]:
        a=ref['metrics'][col];v=p[col];sc=(sum(x<v for x in a)+.5*sum(x==v for x in a))/len(a)*100
        close(sc,s['risk_components'][key]);scores.append(sc)
    close(sum(scores)/3,s['risk_score']);assert 0<=s['risk_score']<=100
assert len(stations)==57 and len(ref['metrics']['rate'])==57
prior=list(csv.DictReader((ROOT/'outputs/inspection_candidates/tables/all_station_metrics.csv').open(encoding='utf-8-sig')))
lookup={s[SID]:next(p for p in s['periods'] if p['period']=='2022~24') for s in stations}
for r in prior:
    p=lookup[r[SID]];assert p['n']==int(r['n']);close(p['rate'],r['high_rate']);close(p['median'],r['median'])
assert sum(p['n'] for p in lookup.values())==1461049
for folder in ['recent_validation_management','management_conditions']:assert not (ROOT/'outputs'/folder).exists()
for file in ['stations.json','period_metrics.csv','timing_evidence.csv','station_timing.csv','index.html','map-fragment.html']:
    content=(OUT/file).read_text(encoding='utf-8-sig');assert not re.search(r'202[56](?:-|年|년| /|~|·)',content),file
for doc in [ROOT/'README.md']:
    # README includes contest year and the separately authorized follow-up scope.
    # Annual map year restrictions are verified above on the map outputs themselves.
    content=doc.read_text(encoding='utf-8-sig')
    for target in re.findall(r'\]\(([^)]+)\)',content):
        if not target.startswith(('https://','http://')):assert (ROOT/target).exists(),target
v=json.loads((OUT/'validation.json').read_text(encoding='utf-8'))
v.update(independent_recalculation_passed=True,independent_cell_rows_verified=1368,prior_baseline_rows_matched=57,composite_scores_verified=57,retired_results_absent=True,report_links_valid=True,no_later_year_results_in_current_outputs=True)
(OUT/'validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(v,ensure_ascii=True),flush=True)
