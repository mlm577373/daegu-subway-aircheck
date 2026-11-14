"""Descriptive screening, not causal attribution or a legal compliance test."""
from pathlib import Path
import json, html
import numpy as np
import pandas as pd
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/inspection_candidates'
for folder in ['tables','figures']: (OUT/folder).mkdir(parents=True,exist_ok=True)
def progress(n,msg):
    checks=['지표·대상기간·표본 요건 명문화','여섯 관점과 기준 민감도 집계','후보 이유표·시각화·보고서 작성','집계 수치·그림·선정 규칙 검증']
    text=f'# 현재 작업: 우선 점검 후보 선정\n\n- 상태: 진행 중\n- 진행: {n} / 4단계 완료\n- 현재 단계: {msg}\n- 승인 범위: 현재 자료의 여섯 관점 분석·후보 선정·시각화\n- 추가 수집·원인 확정·Git 커밋 및 업로드 없음\n- 이 파일은 이번 작업만 표시한다.\n\n## 체크리스트\n\n'
    text+='\n'.join(f'- [{"x" if i<n else " "}] {s}' for i,s in enumerate(checks))
    text+='\n\n## 산출물\n\n- outputs/inspection_candidates/plan.md\n- outputs/inspection_candidates/report.md\n- outputs/inspection_candidates/tables/\n- outputs/inspection_candidates/figures/\n'
    (ROOT/'task.md').write_text(text,encoding='utf-8-sig')
def save(df,name): df.to_csv(OUT/'tables'/f'{name}.csv',index=False,encoding='utf-8-sig')
progress(1,'선정 계획 작성 완료; 비교기간 결합본 집계 중')
cols=['analysis_station_id','line','station_name','date','hour','indoor_pm25','indoor_quality_flag','outdoor_pm25','board_alight_count','outdoor_station_name']
parts=[]
for year in [2022,2023,2024]:
    p=pd.read_csv(ROOT/f'data/merged/merged_hourly_{year}.csv',usecols=cols)
    parts.append(p); print(year,len(p),flush=True)
d=pd.concat(parts,ignore_index=True)
del parts
d['value']=d.indoor_pm25.where(d.indoor_quality_flag.eq('status_blank_unverified') & np.isfinite(d.indoor_pm25) & d.indoor_pm25.ge(0))
d['time']=pd.to_datetime(d.date)+pd.to_timedelta(d.hour,unit='h')
d['month']=d.date.str[:7]; d['year']=d.date.str[:4]
sid='analysis_station_id'
meta=d[[sid,'line','station_name']].drop_duplicates().sort_values(['line',sid]).set_index(sid)
expected=1096*24
threshold=float(d.value.quantile(.9))
d['high']=d.value.ge(threshold)
s=d.groupby(sid).value.agg(n='count',mean='mean',median='median',p90=lambda x:x.quantile(.9),p95=lambda x:x.quantile(.95)).join(meta)
s['expected_hours']=expected; s['coverage']=s.n/expected; s['eligible']=s.coverage.ge(.9)
s['high_n']=d.groupby(sid).high.sum(); s['high_rate']=s.high_n/s.n
runs={}
for code,g in d.groupby(sid):
    g=g.sort_values('time'); high=g.high.to_numpy(); t=g.time.to_numpy()
    count=best=0
    for j,h in enumerate(high):
        count=(count+1 if j and t[j]-t[j-1]==np.timedelta64(1,'h') else 1) if h else 0
        best=max(best,count)
    runs[code]=best
s['longest_high_run_hours']=pd.Series(runs)
monthly=d.groupby([sid,'month']).value.agg(n='count',median='median').reset_index()
grid=pd.MultiIndex.from_product([s.index,pd.period_range('2022-01','2024-12',freq='M').astype(str)],names=[sid,'month'])
monthly=monthly.set_index([sid,'month']).reindex(grid).reset_index()
monthly['n']=monthly.n.fillna(0).astype(int)
monthly['expected']=pd.PeriodIndex(monthly.month,freq='M').days_in_month*24
monthly['coverage']=monthly.n/monthly.expected
monthly['eligible']=monthly.coverage.ge(.75)
monthly['eligible_stations']=monthly.groupby('month').eligible.transform('sum')
monthly['rank_value']=monthly['median'].where(monthly.eligible & monthly.eligible_stations.ge(40))
monthly['upper_quartile_cut']=monthly.groupby('month').rank_value.transform(lambda x:x.quantile(.75))
monthly['high_month']=monthly.rank_value.ge(monthly.upper_quartile_cut)
s['eligible_months']=monthly.groupby(sid).rank_value.count()
s['high_months']=monthly.groupby(sid).high_month.sum()
s['persistence_rate']=(s.high_months/s.eligible_months).where(s.eligible_months.ge(30) & s.eligible)
annual=d.groupby([sid,'year']).value.agg(n='count',median='median').reset_index()
annual['expected']=np.where(annual.year.eq('2024'),366,365)*24
annual['rank_value']=annual['median'].where(annual.n/annual.expected>=.9)
annual['cut']=annual.groupby('year').rank_value.transform(lambda x:x.quantile(.75))
annual['high_year']=annual.rank_value.ge(annual.cut)
s['high_years']=annual.groupby(sid).high_year.sum()
pair=d.value.notna() & d.outdoor_pm25.notna() & np.isfinite(d.outdoor_pm25) & d.outdoor_pm25.ge(0)
d['gap']=(d.value-d.outdoor_pm25).where(pair)
s['paired_n']=d.groupby(sid).gap.count(); s['paired_rate_of_valid']=s.paired_n/s.n
s['outdoor_gap_median_raw']=d.groupby(sid).gap.median()
s['outdoor_gap_median']=s.outdoor_gap_median_raw.where(s.eligible & s.paired_rate_of_valid.ge(.9))
s['outdoor_eligible_at_95pct']=s.eligible & s.paired_rate_of_valid.ge(.95)
s['outdoor_station']=d.groupby(sid).outdoor_station_name.first()
peer=d.groupby('time').value.agg(peer_n='count',peer_median='median')
d=d.join(peer,on='time',validate='many_to_one')
d['peer_gap']=(d.value-d.peer_median).where(d.peer_n.ge(40))
s['peer_n']=d.groupby(sid).peer_gap.count()
s['peer_gap_median_raw']=d.groupby(sid).peer_gap.median()
s['peer_gap_median']=s.peer_gap_median_raw.where(s.eligible & s.peer_n.div(expected).ge(.9))
usage=d.value.notna() & d.hour.between(5,23) & d.board_alight_count.notna() & np.isfinite(d.board_alight_count) & d.board_alight_count.ge(0)
d['usage_valid']=usage
d['usage_total']=d.board_alight_count.where(usage)
d['usage_high']=d.board_alight_count.where(usage & d.high,0).where(usage)
s['usage_n']=d.groupby(sid).usage_valid.sum()
s['usage_coverage']=s.usage_n/(1096*19)
s['boarding_alighting_total']=d.groupby(sid).usage_total.sum(min_count=1)
s['high_boarding_alighting_total']=d.groupby(sid).usage_high.sum(min_count=1)
s['usage_high_share']=(s.high_boarding_alighting_total/s.boarding_alighting_total).where(s.eligible & s.usage_coverage.ge(.9) & s.boarding_alighting_total.gt(0))
s['median_metric']=s['median'].where(s.eligible)
s['high_rate_metric']=s.high_rate.where(s.eligible)
metrics=['median_metric','high_rate_metric','persistence_rate','outdoor_gap_median','peer_gap_median','usage_high_share']
names=['평상시 수준','고농도 빈도','월별 반복성','실외 대비 차이','동시각 상대 수준','이용 겹침']
thresholds=[]
for q in [.7,.75,.8]:
    suffix=str(int(q*100)); core=[]
    for i,col in enumerate(metrics):
        cut=float(s[col].quantile(q)); flag=f'flag_{i+1}_{suffix}'
        s[flag]=s[col].ge(cut) & s[col].notna()
        thresholds.append({'quantile':q,'metric':col,'name':names[i],'cutoff':cut,'eligible_stations':int(s[col].count()),'flagged_stations':int(s[flag].sum())})
        if i<5: core.append(flag)
    s['core_count_'+suffix]=s[core].sum(axis=1)
    s['candidate_'+suffix]=s['core_count_'+suffix].ge(2) & s.eligible
s['tier']=np.select([~s.eligible,s.core_count_75.ge(3),s.core_count_75.ge(2),s.core_count_75.eq(1)],['資料不足','다수 지표 중첩 후보','복수 지표 후보','개별 지표 주목'],default='선정 기준 미해당')
s['tier']=s.tier.replace('資料不足','자료 부족: 판단 유보')
s['reasons']=s.apply(lambda r:', '.join(names[i] for i in range(5) if r[f'flag_{i+1}_75']),axis=1)
s['usage_note']=np.where(s.flag_6_75,'이용 겹침도 큼','')
s['limitation']=np.where(s.outdoor_gap_median.isna(),'실외 비교 평가 불가; 4개 농도 관점으로 평가','')
s['stable_20_25_30']=s.candidate_70 & s.candidate_75 & s.candidate_80
save(s.reset_index(),'all_station_metrics')
candidate=s[s.candidate_75].sort_values(['core_count_75','median'],ascending=[False,False])
save(candidate.reset_index(),'candidate_reasons')
save(monthly,'monthly_persistence'); save(annual,'annual_levels'); save(pd.DataFrame(thresholds),'selection_thresholds')
save(s.reset_index()[[sid,'line','station_name','core_count_70','candidate_70','core_count_75','candidate_75','core_count_80','candidate_80','stable_20_25_30','outdoor_eligible_at_95pct']],'sensitivity')
progress(2,'여섯 관점·민감도 집계 완료; 후보 이유표와 그림 작성 중')

# Reuse only drawing primitives; importing the previous script would rerun its analysis.
source=(ROOT/'data/_scripts/analyze_basic_patterns.py').read_text(encoding='utf-8')
exec(source[source.index('class Canvas:'):source.index('def color(')])
ordered=s.loc[meta.index]
c=Canvas(1500,57*25+205,'우선 점검 후보: 관점별 근거','2022~2024 | 색: 역 간 지표 백분위(상대적 높음) / ●: 상위 25% 기준 해당 | 등급은 관리 순위가 아님')
left,top,cw=235,120,135
for j,name in enumerate(names): c.text(left+j*cw,88,name,15)
for i,(code,r) in enumerate(ordered.iterrows()):
    y=top+i*25; c.text(12,y+2,f'{r.line} {r.station_name}',14)
    for j,col in enumerate(metrics):
        value=r[col]; pct=s[col].rank(pct=True).loc[code]
        if pd.isna(value): color='#dddddd'
        else:
            a=np.array([247,245,235]); b=np.array([181,54,36]); color='#%02x%02x%02x'%tuple((a+(b-a)*pct).astype(int))
        c.rect(left+j*cw,y,cw-3,23,color)
        if r[f'flag_{j+1}_75']: c.dot(left+j*cw+cw/2,y+12,'#171717',4)
        if pd.isna(value): c.text(left+j*cw+35,y+1,'평가 불가',12)
    c.text(left+6*cw+10,y+1,r.tier+(' · 이용 겹침' if r.flag_6_75 else ''),13)
c.text(25,top+57*25+18,'후보: 앞의 5개 농도 관점 중 2개 이상. 이용 겹침은 보조 표시. 회색은 평가 불가이며 낮은 위험을 뜻하지 않음.',14)
c.text(25,top+57*25+45,'수치·기준·관측률은 all_station_metrics.csv 참조. 상위 25%는 상대적 탐색 기준이며 법정 기준이 아님.',14)
c.save('01_candidate_evidence')
c=Canvas(1300,850,'농도 수준과 고농도 시 이용 규모','2022~2024 | 빨강: 복수 이상 농도 지표 후보 / 회색: 나머지 | 승하차 합은 실제 노출 인원이 아님')
x0,x1,y0,y1=100,1240,700,130
maxx=float(np.ceil(s['median'].max()/5)*5); maxy=float(np.ceil(s.high_boarding_alighting_total.max()/1e6)*1e6)
for v in np.linspace(0,maxx,6):
    x=x0+v/maxx*(x1-x0); c.line(x,y0,x,y1,'#eeeeee'); c.text(x-8,y0+10,f'{v:g}',14)
for v in np.linspace(0,maxy,6):
    y=y0-v/maxy*(y0-y1); c.line(x0,y,x1,y,'#eeeeee'); c.text(15,y-8,f'{v/1e6:.1f}백만',13)
c.text(520,755,'실내 PM2.5 중앙값 (µg/m³)',17); c.text(25,98,'고농도 동시 관측 시간의 누적 승하차 합 (3년)',15)
points=s[s.usage_coverage.ge(.9) & s.eligible]
for code,r in points.iterrows():
    x=x0+r['median']/maxx*(x1-x0); y=y0-r.high_boarding_alighting_total/maxy*(y0-y1)
    c.dot(x,y,'#b53624' if r.candidate_75 else '#9b9b9b',6)
# Label only a reproducible small subset to avoid unreadable overlaps.
label_ids=set(points.nlargest(3,'median').index)|set(points.nlargest(3,'high_boarding_alighting_total').index)
for j,code in enumerate(sorted(label_ids)):
    r=points.loc[code]; x=x0+r['median']/maxx*(x1-x0); y=y0-r.high_boarding_alighting_total/maxy*(y0-y1)
    offset=-22 if j%2 else 8
    c.text(min(x+9,1120),y+offset,f'{r.line} {r.station_name}',13)
c.text(25,805,f'고농도 탐색 기준: PM2.5 ≥ {threshold:g} µg/m³. 실내·승하차 동시 관측률 90% 이상인 역만 표시.',14)
c.save('02_concentration_and_usage')
def md(frame,cols):
    text='| '+' | '.join(cols)+' |\n|'+'|'.join(['---']*len(cols))+'|\n'
    for _,r in frame.iterrows(): text+='| '+' | '.join(f'{r[k]:.2f}' if isinstance(r[k],(float,np.floating)) else str(r[k]) for k in cols)+' |\n'
    return text
report=f'''# 우선 점검 후보 선정

## 결과

2022~2024년 현재 자료에 여섯 관점을 적용했다. **우선 점검 후보 {len(candidate)}개 지점**이며, 이 중 다수 지표 중첩(농도 관점 3개 이상)은 {int((s.core_count_75>=3).sum())}개, 복수 지표(2개)는 {int((s.core_count_75==2).sum())}개다. 반월당은 호선별 별도 지점이다. 후보는 현장 점검을 제안하는 상대적 선별 결과이며 법정 기준 위반, 건강위험 순위, 원인 판정이 아니다.

{md(candidate.reset_index(),['line','station_name','tier','reasons','usage_note','median','high_rate','high_months','eligible_months','outdoor_gap_median','peer_gap_median','coverage'])}

표의 농도·차이는 µg/m³, rate·coverage는 0~1 비율이다. 높은 관측률이어도 공식 품질검증이 확인된 값은 아니다.

## 선정 근거

계획은 plan.md에 사전 기록했다. 평상시 중앙값, 공통 고농도 기준 이상 시간 비율, 월별 상대적 고농도 반복률, 실내-실외 차이 중앙값, 동일 시각 다른 역 대비 차이 중앙값을 사용했다. 각 지표는 평가 가능한 역의 75백분위수 이상이면 표시한다. 5개 중 2개 이상인 역을 후보로 하고, 승하차와 고농도가 겹치는 정도는 보조로만 제시했다. 합산 개수는 독립적인 증거 수나 가중 위험점수가 아니다. 중앙값·고농도·동시각 차이 등은 서로 관련될 수 있다.

고농도 공통 탐색 기준은 전체 잠정 사용 표본의 90백분위수인 **{threshold:g} µg/m³ 이상**이다. 전체 관측을 합쳐 계산했으므로 관측이 많은 역의 기여가 조금 더 크다. 법정 기준이 아니며 시간 자료를 법정 평균 기준과 직접 비교하지 않았다. 고농도 강도(p95)와 최장 연속시간은 보조 통계로 저장하고 선별 조건으로 중복 가산하지 않았다.

기본 관측률 90% 이상, 반복성은 월 관측률 75% 이상이면서 36개월 중 30개월 이상 평가 가능해야 한다. 동시각 비교는 40개 이상 역이 유효한 시각에 한한다. 실외와 이용 지표에도 관측량 요건을 적용했다. 미관측은 0으로 바꾸지 않았다.

## 기준 민감도와 제외 사항

- 상위 20% 기준 후보: {int(s.candidate_80.sum())}개, 상위 25%: {int(s.candidate_75.sum())}개, 상위 30%: {int(s.candidate_70.sum())}개.
- 세 기준에서 모두 후보인 지점: {int(s.stable_20_25_30.sum())}개. 개별 유지 여부는 sensitivity.csv에 저장했다. 이는 기준 변화에 대한 안정성이지 통계적 신뢰구간은 아니다.
- 현충로·율하 등 실외 평가 불가 지점은 all_station_metrics.csv의 limitation 열로 구분했다. 평가 불가를 0으로 처리하지 않았지만, 이들 지점은 4개 농도 관점만으로 판정되어 후보 중첩 개수가 구조적으로 작을 수 있다.
- 실외 동시 관측률을 95%로 높였을 때의 평가 가능 여부도 저장했다. 이는 추가 표본 점검이며 전체 선별 기준 민감도와 구분한다.
- 동일 시각 표기는 same_label_v1 가정이다. 실제 측정 구간 일치, 실외 측정소의 공간 대표성은 확정되지 않았다.

## 시각화

1. figures/01_candidate_evidence.png 및 svg: 전 역의 여섯 관점별 상대 백분위와 상위 25% 표시, 후보 구분. 백분위는 크기 자체를 보여주는 농도 값이 아니므로 원 지표표와 함께 읽는다.
2. figures/02_concentration_and_usage.png 및 svg: 평상시 농도와 고농도 시간 누적 승하차 합. 붉은 점은 후보, 회색 점은 나머지다. 라벨은 농도 상위 3개와 고농도 승하차 합 상위 3개의 합집합만 표시했다. 나머지는 전 역 표에서 확인한다.

승하차 합은 탑승·하차 사건의 합이며 고유 인원·승강장 체류·흡입 노출량을 뜻하지 않는다. 누적값은 관측 시간 수의 영향도 받으므로 관측률과 함께 해석한다. 산점도의 이용 규모는 후보 선정 등급에 반영하지 않았다.

## 해석과 후속 점검

여러 관점에서 높게 나타난 역은 측정기·기록을 확인한 뒤 반복 시간대와 환기·청소 상태 등을 점검할 후보로 제시할 수 있다. 농도만 높은 역과 이용 집중도 함께 큰 역을 구분해 대응 목적을 정하는 것이 적절하다. 선정되지 않은 역도 관리가 불필요하다는 뜻은 아니다.

이번 작업은 원인 분석을 수행하지 않았다. 특히 계절·요일·운행·기상·시설 차이를 통제한 효과 추정은 아니다. 반복성은 월별 상대 순위를 보고, 동시각 지표는 날짜·시간이 같은 도시 전반 조건 일부를 맞추는 기술통계다.

## 재현 및 파일

- data/_scripts/select_inspection_candidates.py: 생성 스크립트(pandas, numpy, Pillow, Windows 맑은 고딕).
- tables/all_station_metrics.csv: 전 57개 지점 원 지표·관측률·판정·평가 불가 이유.
- tables/candidate_reasons.csv: 선정된 후보와 이유.
- tables/monthly_persistence.csv, annual_levels.csv: 월·연도별 근거.
- tables/selection_thresholds.csv, sensitivity.csv: 지표별 임계값과 기준 민감도.
- validation.json: 집계 검증 결과. 원본 데이터 수정·추가 수집·Git 업로드 없음.
'''
(OUT/'report.md').write_text(report,encoding='utf-8-sig')
progress(3,'후보 표·그림·보고서 작성 완료; 규칙 및 가독성 검증 중')
assert len(s)==57 and not d.duplicated([sid,'time']).any()
assert s.n.sum()==1461049
assert s.high_n.sum()==d.high.sum()
assert monthly.n.sum()==s.n.sum()
assert s.paired_n.sum()==pair.sum()
assert s.usage_n.sum()==usage.sum()
assert (s.high_boarding_alighting_total<=s.boarding_alighting_total).all()
assert ((s.core_count_75>=2)&s.eligible).equals(s.candidate_75)
assert set(s[s.candidate_80].index)<=set(s[s.candidate_75].index)<=set(s[s.candidate_70].index)
assert s.loc[d.loc[d.station_name.isin(['現忠路','현충로','율하']),sid].unique(),'outdoor_gap_median'].isna().all()
for file in (OUT/'figures').glob('*.png'):
    with Image.open(file) as im: im.verify()
validation={'passed':True,'baseline_rows':len(d),'valid_n':int(s.n.sum()),'high_threshold':threshold,'candidate_count':len(candidate),'checks':['57 unique stations','unique station-time keys','baseline valid count matches earlier analysis','monthly, high, outdoor-pair and usage counts reconcile','high usage never exceeds total usage','candidate rule and sensitivity nesting','coordinate-review stations not scored on outdoor gap','PNG decoding'],'visual_review':'pending'}
(OUT/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(validation,ensure_ascii=False),flush=True)
