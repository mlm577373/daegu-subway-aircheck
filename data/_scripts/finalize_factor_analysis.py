"""Add station-specific starting clues and independent numerical QA."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from PIL import Image,ImageDraw,ImageFont
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'outputs/factor_analysis'
partial=pd.read_csv(OUT/'tables/conditional_partial_r2.csv')
summary=pd.read_csv(OUT/'tables/candidate_factor_summary.csv')
hyp=pd.read_csv(OUT/'tables/hypotheses.csv')
mapping={'실외 농도':('H01','외부 유입·공통 기상과 실외 대리변수 확인'),'시간대':('H03','운행·환기·청소 시간 주기 대조'),'월':('H05','계절별 환기·온습도와 외부 반응 대조'),'요일':('H04','이용·운행·공휴일 구성 대조'),'이용 규모':('H04','승객 이동과 열차 운행의 동반 변화 구분'),'연도':('H06','설비·기기·청소 및 이용 회복 이력 대조')}
rows=[]
for _,s in summary.iterrows():
    code=s.analysis_station_id
    top=partial[partial.model.eq(s.model)&partial.scope.eq(code)].nlargest(2,'partial_r2')
    sentences=[]
    for order,(_,r) in enumerate(top.iterrows(),1):
        hid,action=mapping[r.factor]
        if r.factor=='시간대': evidence=f'조정 패턴 {int(s.peak_hour):02d}시 최대 / {int(s.trough_hour):02d}시 최소, 범위 {s.hour_span:.2f} µg/m³'
        elif r.factor=='월': evidence=f'{int(s.peak_month)}월 최대 / {int(s.trough_month)}월 최소, 범위 {s.month_span:.2f} µg/m³'
        elif r.factor=='실외 농도': evidence=f'실외 10→20 대비 {s.outdoor_10_20:+.2f} µg/m³'
        elif r.factor=='이용 규모': evidence=f'승하차+1 두 배 대비 {s.usage_doubling:+.2f} µg/m³'
        else:
            h=hyp[(hyp.analysis_station_id.eq(code))&hyp.hypothesis_id.eq(code+'_'+hid)].iloc[0]
            evidence=h.station_evidence
        rows.append({'analysis_station_id':code,'line':s.line,'station_name':s.station_name,'clue_order':order,'factor':r.factor,'conditional_partial_r2':r.partial_r2,'evidence':evidence,'hypothesis_to_check':hid,'check':action})
        sentences.append(f'- **{r.factor}**: 조건부 부분 R² {r.partial_r2:.3f}. {evidence}. → {hid}: {action}.')
    text='## 먼저 대조할 관측 단서\n\n'+'\n'.join(sentences)+'\n\n위 순서는 현재 모형에서 추가 설명력이 큰 두 묶음을 골라 점검의 출발점을 정한 것이며, 원인 확률·발생원 기여도·관리 순위가 아니다. 나머지 가설도 배제하지 않는다. 같은 원인이 여러 변수에 걸쳐 나타날 수 있다.\n\n'
    p=OUT/'station_reports'/f'{code}.md'; t=p.read_text(encoding='utf-8-sig')
    if '## 먼저 대조할 관측 단서' not in t:t=t.replace('## 점검할 가설',text+'## 점검할 가설')
    p.write_text(t,encoding='utf-8-sig')
clues=pd.DataFrame(rows)
clues.to_csv(OUT/'tables/station_starting_clues.csv',index=False,encoding='utf-8-sig')
table='| 역 | 먼저 대조할 변수 묶음 | 연결할 점검 가설 |\n|---|---|---|\n'
for code,g in clues.groupby('analysis_station_id',sort=False):
    r=g.iloc[0]
    table+=f'| {r.line} {r.station_name} | '+', '.join(g.factor)+' | '+' / '.join(g.check)+' |\n'
p=OUT/'report.md';t=p.read_text(encoding='utf-8-sig')
if '## 역별 점검의 출발점' not in t:
    t=t.replace('## 점검 가설과 확인 순서','## 역별 점검의 출발점\n\n'+table+'\n조건부 추가 설명력이 큰 두 변수 묶음을 점검 출발점으로 정리했다. 이것은 **원인 확률의 순위가 아니며**, 다른 가설을 배제하지 않는다. 각 역의 구체적 시간대·월·대비는 진단표에 있다.\n\n## 점검 가설과 확인 순서')
p.write_text(t,encoding='utf-8-sig')
# Check within-station estimator against a different explicit-dummy least squares solution.
rng=np.random.default_rng(20261114)
groups=np.repeat(np.arange(7),[71,95,101,82,113,67,89]); n=len(groups)
X=rng.normal(size=(n,4))+groups[:,None]*np.array([.1,.3,-.2,.5])
y=X@np.array([2.,-.4,1.2,.8])+groups*1.7+rng.normal(size=n)
Z=np.column_stack([np.eye(7)[groups],X]); explicit=np.linalg.lstsq(Z,y,rcond=None)[0][-4:]
Xc=X.copy();yc=y.copy()
for group in np.unique(groups):
    pick=groups==group;Xc[pick]-=X[pick].mean(axis=0);yc[pick]-=y[pick].mean()
within=np.linalg.lstsq(Xc,yc,rcond=None)[0]
error=float(np.max(np.abs(explicit-within)));assert error<1e-10
# Independently recompute selected effect contrasts and partial R2 from saved coefficients.
coef=pd.read_csv(OUT/'tables/coefficients.csv'); ef=pd.read_csv(OUT/'tables/effect_contrasts.csv')
maxerr=0.
for _,r in ef.iterrows():
    c=coef[(coef.model.eq(r.model))&coef.scope.eq(r.scope)].set_index('term').coefficient
    if r.contrast=='승하차+1 두 배': v=c.log2_usage_plus1
    elif r.contrast=='실외 10→20': v=c.outdoor_per10
    elif r.contrast=='실외 20→30': v=c.outdoor_per10+c.outdoor_hinge20_per10
    else:v=c.outdoor_per10+c.outdoor_hinge20_per10+c.outdoor_hinge40_per10
    maxerr=max(maxerr,abs(v-r.effect))
assert maxerr<1e-9
assert len(clues)==34 and clues.groupby('analysis_station_id').size().eq(2).all()
for _,r in clues.iterrows():assert (r.analysis_station_id+'_'+r.hypothesis_to_check) in set(hyp.hypothesis_id)
for p in (OUT/'station_reports').glob('*.md'):
    t=p.read_text(encoding='utf-8-sig');assert t.count('### H')==7 and '競' not in t
    assert (OUT/'figures'/('station_'+p.stem+'.png')).exists()
for p in (OUT/'figures').glob('*.png'):
    with Image.open(p) as im:im.verify()
for p in (OUT/'figures').glob('*.svg'):ET.parse(p)
v=json.loads((OUT/'validation.json').read_text(encoding='utf-8'))
v['fixed_effects_vs_explicit_dummy_max_error']=error
v['saved_contrast_recomputation_max_error']=maxerr
v['png_figures']=len(list((OUT/'figures').glob('*.png')))
v['svg_figures']=len(list((OUT/'figures').glob('*.svg')))
v['checks']+=['within estimator agrees with explicit station dummies','saved contrasts independently recomputed','34 starting clues refer to existing hypotheses','17 station reports contain 7 hypotheses and linked figures','all final PNG decode and SVG parse']
(OUT/'validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
# Contact sheet for visual review of every station panel.
canvas=Image.new('RGB',(1450,5*270),'white');draw=ImageDraw.Draw(canvas)
font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',16)
for i,(_,r) in enumerate(summary.iterrows()):
    x=(i%4)*362;y=(i//4)*270
    draw.text((x+5,y+3),f'{r.line} {r.station_name}',fill='black',font=font)
    with Image.open(OUT/'figures'/f'station_{r.analysis_station_id}.png') as im:
        im.thumbnail((355,240));canvas.paste(im,(x+3,y+25))
canvas.save(OUT/'visual_review_contact_sheet.png')
print('Added 34 station-specific starting clues; independent numerical checks passed.')
