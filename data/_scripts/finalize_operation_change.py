"""Independent checks and a static evidence chart; leaves report/map untouched."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from analyze_operation_change import regress
R=Path(__file__).resolve().parents[2]; O=R/'outputs/operation_change'
p=json.loads((O/'pooled_point_estimates.json').read_text(encoding='utf-8'))
r=pd.read_csv(O/'tables/station_event_estimates.csv'); q=pd.read_csv(O/'tables/model_coverage.csv')
daily=pd.read_csv(R/'data/timetable_change/daily_schedule_counts.csv')
for sid in ['DG_L1_1300','DG_L2_2300']:
    z=daily[daily.analysis_station_id.eq(sid)].set_index(['version','day_type'])['count']
    assert z['archive_pre','holiday']==264 and z['official_post','holiday']==248
    assert z['archive_pre','weekday']==296 and z['official_post','weekday']==296
assert r.clusters.min()>20
assert np.isfinite(r[['effect_per_scheduled_train','se','ci_low','ci_high','q_bh']].to_numpy()).all()
# Independent explicit dummy-variable least squares versus absorbed regression.
rng=np.random.default_rng(74);n=600;g1=np.repeat(np.arange(30),20);g2=np.tile(np.arange(20),30)
X=rng.normal(size=(n,2));y=X@np.array([.7,-.4])+rng.normal(size=30)[g1]+rng.normal(size=20)[g2]+rng.normal(size=n)
f=regress(y,X,[g1,g2],g1//2)
D=np.column_stack([X,np.eye(30)[g1],np.eye(20)[g2][:,1:]])
direct=np.linalg.lstsq(D,y,rcond=None)[0][:2];err=float(np.max(np.abs(direct-f['beta'])))
assert err<1e-9
primary=r[r.config.eq('adjusted56')]
excluded=q[q.config.eq('adjusted56')&~q.eligible].analysis_station_id.tolist()
checks={'reference_counts_match':True,'cluster_count_min':int(r.clusters.min()),'explicit_dummy_coefficient_error':err,'all_intervals_finite':True,'primary_excluded_station_ids':excluded,'station_model_counts':r.groupby('config').size().to_dict()}
(O/'verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
# Public-data measurement labels remain provisional. No causal labels on the plot.
fontpath='C:/Windows/Fonts/malgun.ttf'
font=lambda s:ImageFont.truetype(fontpath,s)
im=Image.new('RGB',(1420,1040),'white');dr=ImageDraw.Draw(im)
dr.text((50,30),'운행 시간표 개편과 승강장 PM2.5: 추정치의 안정성',font=font(33),fill='#163528')
dr.text((50,84),'2024.10.7 개편 · 평일 14~22시 · 2022~2023년 같은 계절 변화와 비교',font=font(21),fill='#444444')
dr.text((50,123),'시간당 예정 열차 1회 변화에 대응하는 농도 차이 (µg/m³) · 점과 근사 95% 구간',font=font(20),fill='#444444')
lo,hi=-.45,1.12;left,right=540,1330
px=lambda v:left+(v-lo)/(hi-lo)*(right-left)
labels=[('raw56','기본 비교 / 전후 8주'),('adjusted56','실외·기상 조정 / 전후 8주'),('usage56','이용량 추가 조정 / 전후 8주'),('adjusted42','기간 변경 / 전후 6주'),('adjusted70','기간 변경 / 전후 10주'),('clock_minus1','시간 정렬 민감도 -1시간'),('clock_plus1','시간 정렬 민감도 +1시간'),('placebo2023','가짜 개편 / 2023년 대조')]
dr.line((px(0),180,px(0),817),fill='#777777',width=2)
for k,(key,label) in enumerate(labels):
    y=220+k*76;v=p[key];color='#0b734b' if key=='adjusted56' else '#777777' if key=='placebo2023' else '#3b6f8c'
    dr.text((50,y-14),label,font=font(22),fill='#222222')
    dr.line((px(v['ci_low']),y,px(v['ci_high']),y),fill=color,width=4)
    x=px(v['point_estimate']);dr.ellipse((x-7,y-7,x+7,y+7),fill=color)
    dr.text((left,y+14),f"{v['point_estimate']:+.2f}  [{v['ci_low']:+.2f}, {v['ci_high']:+.2f}]",font=font(17),fill=color)
for v in [-.4,0,.4,.8,1.1]:
    dr.text((px(v)-19,850),f'{v:g}',font=font(19),fill='#444444')
dr.text((50,905),'해석: 주 분석 구간은 0을 포함합니다. 시간 정렬과 가짜 개편에서도 변화가 나타나',font=font(22),fill='#333333')
dr.text((50,943),'열차 운행의 인과효과 또는 마모 원인으로 단정할 수 없습니다.',font=font(22),fill='#333333')
dr.text((50,991),'주 단위 공통 변동을 반영한 근사 구간 · 예정 시간표 사용 · 실제 운행 및 환기량은 미관측',font=font(17),fill='#666666')
(O/'figures').mkdir(exist_ok=True);im.save(O/'figures/timetable_sensitivity.png')
print(json.dumps({'checks':checks,'positive_primary_stations':primary[primary.q_bh.le(.1)&primary.effect_per_scheduled_train.gt(0)][['station_name','effect_per_scheduled_train','q_bh']].to_dict('records')},ensure_ascii=True))
