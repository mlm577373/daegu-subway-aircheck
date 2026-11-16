"""Annual 2022-2024 management patterns. No later-year data are read."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/management_map'
SID='analysis_station_id';YEARS=[2022,2023,2024];COVERAGE=.75;HIGH=43.15
SLOTS={'아침 06~09시':(6,9),'낮 10~15시':(10,15),'저녁 16~19시':(16,19),'밤 20~23시':(20,23)}
def save(name,obj):
    target=OUT/name
    temp=target.with_suffix(target.suffix+'.tmp')
    temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    temp.replace(target)

def analyze():
    OUT.mkdir(parents=True,exist_ok=True)
    cols=[SID,'line','station_name','date','hour','indoor_pm25','indoor_quality_flag','board_alight_count']
    parts=[]
    for y in YEARS:
        p=pd.read_csv(ROOT/f'data/merged/merged_hourly_{y}.csv',usecols=cols)
        assert p.date.str[:4].eq(str(y)).all()
        parts.append(p);print('read full calendar',y,len(p),flush=True)
    d=pd.concat(parts,ignore_index=True);del parts
    assert not d.duplicated([SID,'date','hour']).any()
    d['time']=pd.to_datetime(d.date)+pd.to_timedelta(d.hour,unit='h')
    d['year']=d.time.dt.year.astype(str);d['month']=d.time.dt.month
    d['day']=np.where(d.time.dt.dayofweek.ge(5),'주말','평일')
    d['slot']=''
    for label,(lo,hi) in SLOTS.items():d.loc[d.hour.between(lo,hi),'slot']=label
    d['value']=d.indoor_pm25.where(d.indoor_quality_flag.eq('status_blank_unverified')&d.indoor_pm25.ge(0)&np.isfinite(d.indoor_pm25))
    d['high']=d.value.ge(HIGH);d=d.sort_values([SID,'time']).reset_index(drop=True)
    nx=d.groupby(SID)[['time','value','year']].shift(-1)
    d['transition']=d.high & nx.time.sub(d.time).eq(pd.Timedelta(hours=1)) & nx.value.notna() & nx.year.eq(d.year)
    d['stay']=d.transition & nx.value.ge(HIGH)
    d['paired']=d.value.notna()&d.hour.between(5,23)&d.board_alight_count.ge(0)&np.isfinite(d.board_alight_count)
    d['usage']=d.board_alight_count.where(d.paired)
    d['high_usage']=d.usage.where(d.high,0)
    meta=d[[SID,'line','station_name']].drop_duplicates().sort_values(SID)
    assert len(meta)==57
    expected={'2022':8760,'2023':8760,'2024':8784,'2022~24':26304}
    periods=[]
    for per in ['2022','2023','2024','2022~24']:
        x=d if per=='2022~24' else d[d.year.eq(per)]
        s=x.groupby(SID).agg(n=('value','count'),median=('value','median'),high_n=('high','sum'),transition_n=('transition','sum'),stay_high_n=('stay','sum'),usage_n=('paired','sum'),usage_total=('usage','sum'),usage_high_total=('high_usage','sum')).reset_index()
        s['period']=per;s['expected']=expected[per];s['coverage']=s.n/s.expected;s['rate']=s.high_n/s.n
        s['expected_usage']=s.expected/24*19;s['usage_coverage']=s.usage_n/s.expected_usage
        s['continuation_rate']=s.stay_high_n/s.transition_n.replace(0,np.nan)
        s['usage_high_share']=s.usage_high_total/s.usage_total.replace(0,np.nan)
        periods.append(s)
    period=pd.concat(periods,ignore_index=True)
    period.to_csv(OUT/'period_metrics.csv',index=False,encoding='utf-8-sig')
    pooled=period[period.period.eq('2022~24')].set_index(SID)
    # Each component is the midrank percentile among sufficiently observed baseline stations.
    valid=pooled.coverage.ge(COVERAGE)&pooled.usage_coverage.ge(COVERAGE)&pooled.usage_total.gt(0)&pooled.transition_n.ge(20)
    metrics=['rate','continuation_rate','usage_high_share'];reference=pooled.loc[valid,metrics]
    assert reference.notna().all().all()
    def percentile(v,col):
        a=reference[col].to_numpy();return float(((a<v).sum()+.5*(a==v).sum())/len(a)*100)
    references={col:sorted(reference[col].astype(float).tolist()) for col in metrics}
    save('risk_reference.json',{'period':'2022-01-01 to 2024-12-31','n':len(reference),'metrics':references,'weights':[1/3]*3,'method':'midrank empirical percentile; equal mean; 0-100 relative management index, not health risk probability','bins':[33,67]})
    scope=d[d.hour.ge(6)]
    calendar=pd.DataFrame({'time':pd.date_range('2022-01-01','2024-12-31',freq='D')})
    calendar['year']=calendar.time.dt.year.astype(str);calendar['day']=np.where(calendar.time.dt.dayofweek.ge(5),'주말','평일')
    days=calendar.groupby(['year','day']).size()
    g=scope.groupby([SID,'year','day','slot']).agg(n=('value','count'),high_n=('high','sum'),median=('value','median')).reset_index().rename(columns={'year':'period'})
    total=scope.groupby([SID,'year']).agg(total_n=('value','count'),total_high=('high','sum'))
    g=g.join(total,on=[SID,'period'])
    g['expected']=[int(days.loc[(r.period,r.day)])*(SLOTS[r.slot][1]-SLOTS[r.slot][0]+1) for r in g.itertuples()]
    g['coverage']=g.n/g.expected;g['rate']=g.high_n/g.n
    g['other_rate']=(g.total_high-g.high_n)/(g.total_n-g.n)
    g['difference']=g.rate-g.other_rate
    g['period_pass']=g.coverage.ge(.75)&g.n.ge(100)&g.high_n.ge(10)&g.rate.ge(.05)&g.difference.ge(.03)&g.rate.ge(1.25*g.other_rate)
    # Direction should repeat in at least two sufficiently observed quarters in each passing year.
    scope=scope.copy();scope['quarter']=scope.time.dt.quarter
    qcells=scope.groupby([SID,'year','day','slot','quarter']).agg(n=('value','count'),h=('high','sum'))
    qt=scope.groupby([SID,'year','quarter']).agg(n=('value','count'),h=('high','sum'))
    def quarters(r):
        good=0
        for quarter in [1,2,3,4]:
            a=qcells.loc[(getattr(r,SID),r.period,r.day,r.slot,quarter)]
            b=qt.loc[(getattr(r,SID),r.period,quarter)]
            if a.n>0 and b.n>a.n and a.h/a.n>(b.h-a.h)/(b.n-a.n):good+=1
        return good
    g['positive_subperiods']=[quarters(r) for r in g.itertuples()]
    g['period_pass'] &= g.positive_subperiods.ge(2)
    g.to_csv(OUT/'timing_evidence.csv',index=False,encoding='utf-8-sig')
    coords=pd.read_csv(ROOT/'data/mapping/indoor_station_coordinates.csv').set_index(SID)
    overrides={'DG_L1_1260':(35.841112872935,128.58192339191,'https://jusoga.com/b/2720010300400000005000001/대구광역시-남구-대명로-지하-222-대명동'),'DG_L1_1420':(35.8697,128.693,'https://www.findlatlng.org/place/yulha')}
    stations=[]
    for m in meta.itertuples(index=False):
        sid=getattr(m,SID);r=pooled.loc[sid];p=period[period[SID].eq(sid)]
        sufficient=bool(r.coverage>=COVERAGE)
        chosen=[]
        for day in ['평일','주말']:
            for slot in SLOTS:
                rows=g[g[SID].eq(sid)&g.day.eq(day)&g.slot.eq(slot)]
                if sufficient and int(rows.period_pass.sum())>=2:chosen.append({'day':day,'slot':slot})
        ps={}
        for key,col in zip(['frequency','persistence','overlap'],metrics):
            available=sufficient and np.isfinite(r[col])
            if key=='persistence':available &= r.transition_n>=20
            if key=='overlap':available &= r.usage_coverage>=COVERAGE and r.usage_total>0
            ps[key]={'available':bool(available),'value':float(r[col]) if available else None}
        components={key:percentile(r[col],col) for key,col in zip(['frequency','persistence','overlap'],metrics)} if valid.loc[sid] else {}
        score=sum(components.values())/3 if components else None
        ps['composite']={'available':score is not None,'value':score/100 if score is not None else None}
        c=coords.loc[sid]
        station={SID:sid,'line':m.line,'name':m.station_name,'sufficient':sufficient,'chosen':chosen,'timing':' / '.join(z['day']+' '+z['slot'] for z in chosen) if chosen else ('뚜렷한 집중 시점 없음' if sufficient else '관측 부족·판단 유보'),
                 'perspectives':ps,'risk_score':score,'risk_components':components,'level':'판단 유보' if score is None else '낮은 편' if score<33 else '중간' if score<67 else '높은 편',
                 'lat':float(c.latitude),'lon':float(c.longitude),'coordinate_note':'KRIC 역 대표 좌표; 측정기 정확한 설치 위치 아님',
                 'periods':p.drop(columns=[SID]).astype(object).where(p.drop(columns=[SID]).notna(),None).to_dict('records'),
                 'cells':g[g[SID].eq(sid)].drop(columns=[SID]).astype(object).where(g[g[SID].eq(sid)].drop(columns=[SID]).notna(),None).to_dict('records')}
        if sid in overrides:
            station['lat'],station['lon'],station['coordinate_url']=overrides[sid];station['coordinate_note']='지도용 잠정 대체 좌표; 원본·실외 매칭 불변'
        stations.append(station)
    save('stations.json',stations)
    pd.DataFrame([{k:v for k,v in s.items() if k not in ['periods','cells','perspectives','chosen','risk_components']} for s in stations]).to_csv(OUT/'station_timing.csv',index=False,encoding='utf-8-sig')
    assert len(g)==1368
    assert pooled.n.sum()==d.value.notna().sum()
    validation={'passed':True,'analysis_years':YEARS,'period':'2022-01-01 to 2024-12-31','stations':57,'valid_n':int(d.value.notna().sum()),'coverage_threshold':COVERAGE,'threshold':HIGH,'timing_cells':len(g),'timing_stations':sum(bool(s['chosen']) for s in stations),'no_distinct_timing':sum(s['sufficient'] and not s['chosen'] for s in stations),'insufficient':sum(not s['sufficient'] for s in stations),'composite_available':int(valid.sum()),'perspective_available':{k:sum(s['perspectives'][k]['available'] for s in stations) for k in ['frequency','persistence','overlap']},'checks':['only three explicit full-year source files read','leap day included','unique station hour','all 57 retained','equal weights with no imputation']}
    save('validation.json',validation)
    print(json.dumps(validation,ensure_ascii=True),flush=True)
    return stations
