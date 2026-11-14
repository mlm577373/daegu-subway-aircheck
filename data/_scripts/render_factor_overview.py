"""Render common-model overview from saved analysis tables, without refitting."""
from pathlib import Path
import html
import numpy as np
import pandas as pd
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'outputs/factor_analysis'
source=(ROOT/'data/_scripts/analyze_basic_patterns.py').read_text(encoding='utf-8')
exec(source[source.index('class Canvas:'):source.index('def color(')])
source=(ROOT/'data/_scripts/analyze_station_factors.py').read_text(encoding='utf-8')
exec(source[source.index('def linepanel('):source.index('def effectrow(')])
coef=pd.read_csv(OUT/'tables/coefficients.csv')
g=coef[coef.model.eq('outdoor_matched')&coef.scope.eq('ALL')].set_index('term')
partial=pd.read_csv(OUT/'tables/conditional_partial_r2.csv')
partial=partial[partial.model.eq('outdoor_matched')&partial.scope.eq('ALL')]
c=Canvas(1450,1050,'전체 역의 공통 조건부 관계','2022~2024, 05~23시 | 실외 동시 관측 55개 지점 | 역 고정효과 및 다른 변수를 함께 고려 | 인과효과 아님')
for x,y,key,levels,title in [(20,100,'hour',list(range(5,24)),'시간대 대비: 05시 기준'),(740,100,'month',list(range(1,13)),'월별 대비: 1월 기준')]:
    a=[]; lo=[]; hi=[]
    for level in levels:
        term=f'{key}_{level}'
        if term in g.index:
            r=g.loc[term]; a.append(r.coefficient); lo.append(r.ci_low); hi.append(r.ci_high)
        else:a.append(0);lo.append(0);hi.append(0)
    linepanel(c,x,y,690,370,title,levels,a,lo,hi)
o=np.arange(0,61,5,dtype=float)
b=g.loc[['outdoor_per10','outdoor_hinge20_per10','outdoor_hinge40_per10'],'coefficient'].to_numpy()
def f(v):return np.column_stack([v/10,np.maximum(v-20,0)/10,np.maximum(v-40,0)/10])@b
linepanel(c,20,510,690,365,'실외 농도 대비: 실외 10 µg/m³ 기준 (점추정)',o,f(o)-f(np.array([10.]))[0])
c.text(760,510,'변수 묶음의 조건부 추가 설명력 (부분 R²)',17)
maximum=max(float(partial.partial_r2.max()),.01)
for i,(_,r) in enumerate(partial.iterrows()):
    yy=565+i*42
    c.text(760,yy,r.factor,15)
    c.rect(880,yy+3,400*r.partial_r2/maximum,18,'#397f9d')
    c.text(1295,yy,f'{r.partial_r2:.3f}',14)
c.text(25,920,'위쪽 선: 주별 군집 95% 근사구간. 기준 범주 0은 추정 오차가 없다는 뜻이 아니라 대비의 정의.',14)
c.text(25,950,'실외 곡선: 20·40에서 꺾임을 허용한 점추정. 아래 오른쪽은 발생원 기여율이 아니며 합이 100%가 되지 않음.',14)
c.text(25,980,'누락 요인: 실제 열차 횟수, 환기·청소, 온습도, 공휴일, 측정기 이력. 역별 모형은 공통 관계와 다를 수 있음.',14)
c.save('00_common_patterns')
report=OUT/'report.md'
t=report.read_text(encoding='utf-8-sig')
heading='## 무엇이 모형 안에서 추가 설명력을 갖는가'
if '00_common_patterns.png' not in t:
    t=t.replace(heading,'![전체 역의 공통 조건부 관계](figures/00_common_patterns.png)\n\n'+heading)
report.write_text(t,encoding='utf-8-sig')
print('Rendered common overview from saved model tables.')
