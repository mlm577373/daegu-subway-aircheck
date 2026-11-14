"""Local descriptive analysis. Run with pandas, numpy and Pillow installed."""
from pathlib import Path
import json, html
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/basic_patterns'
for folder in ['figures', 'tables']:
    (OUT / folder).mkdir(parents=True, exist_ok=True)
def progress(n, message):
    checks = ['결측·상태코드·실내외 동시 관측 수 집계', '비교기간과 관측률을 명시한 요약표 작성', 'PNG·SVG 그림과 해석 보고서 작성', '수치 대조와 그림 가독성 검증']
    text = '# 현재 작업: 분석 표본 품질 점검과 기본 패턴 시각화\n\n'
    text += f'- 상태: {"완료" if n == 4 else "진행 중"}\n- 진행: {n} / 4단계 완료\n- 현재 단계: {message}\n- 승인 범위: 품질 요약표, PNG·SVG 그림, 해석 보고서 로컬 저장\n- Git 커밋·업로드는 하지 않는다.\n- 이 파일은 이번 작업의 진행 상황만 표시한다.\n\n## 체크리스트\n\n'
    text += '\n'.join(f'- [{"x" if i < n else " "}] {s}' for i,s in enumerate(checks))
    text += '\n\n## 산출물\n\n- outputs/basic_patterns/figures/\n- outputs/basic_patterns/tables/\n- outputs/basic_patterns/report.md\n'
    (ROOT / 'task.md').write_text(text, encoding='utf-8-sig')
def save(df, name):
    df.to_csv(OUT / 'tables' / (name + '.csv'), encoding='utf-8-sig', index=False)

cols = ['analysis_station_id','indoor_station_code','line','station_name','date','hour','indoor_pm25','indoor_status_raw','indoor_quality_flag','outdoor_pm25','outdoor_match_status','ridership_match_status']
parts=[]
for file in sorted((ROOT/'data/merged').glob('merged_hourly_*.csv')):
    part=pd.read_csv(file, usecols=cols, keep_default_na=True)
    parts.append(part)
    print(file.name, len(part), flush=True)
d=pd.concat(parts, ignore_index=True)
d['month']=d.date.str[:7]
d['year']=d.date.str[:4]
d['value']=d.indoor_pm25.where(d.indoor_quality_flag.eq('status_blank_unverified') & d.indoor_pm25.ge(0) & np.isfinite(d.indoor_pm25))
d['paired']=d.value.notna() & d.outdoor_pm25.notna()
d['status']=d.indoor_status_raw.fillna('').str.strip().replace('', '(공백: 의미 미확인)')
stations=d[['analysis_station_id','indoor_station_code','line','station_name']].drop_duplicates().sort_values(['line','analysis_station_id'])
ids=stations.analysis_station_id.tolist()
labels=(stations.line+' '+stations.station_name).tolist()
months=json.loads((ROOT/'data/collection_plan.json').read_text(encoding='utf-8-sig'))['months']
calendar=pd.period_range('2021-04','2026-04',freq='M').astype(str).tolist()
grid=pd.MultiIndex.from_product([ids,months],names=['analysis_station_id','month'])
g=d.groupby(['analysis_station_id','month'])
monthly=g.agg(returned_rows=('value','size'),valid_n=('value','count'),mean=('value','mean'),median=('value','median'),p25=('value',lambda x:x.quantile(.25)),p75=('value',lambda x:x.quantile(.75)),p90=('value',lambda x:x.quantile(.9)),paired_n=('paired','sum')).reindex(grid).reset_index()
for c in ['returned_rows','valid_n','paired_n']:
    monthly[c]=monthly[c].fillna(0).astype(int)
monthly['expected_hours']=pd.PeriodIndex(monthly.month,freq='M').days_in_month*24
monthly['coverage']=monthly.valid_n/monthly.expected_hours
monthly['missing_rows']=monthly.expected_hours-monthly.returned_rows
monthly['reported_invalid_n']=monthly.returned_rows-monthly.valid_n
monthly=monthly.merge(stations,on='analysis_station_id',validate='many_to_one')
monthly['eligible_75pct']=monthly.coverage.ge(.75)
save(monthly,'station_month_quality_and_concentration')
save(d.groupby(['year','status']).size().rename('rows').reset_index(),'status_by_year')
save(d.groupby(['analysis_station_id','status']).size().rename('rows').reset_index().merge(stations,on='analysis_station_id'),'status_by_station')
save(d.groupby(['year','indoor_quality_flag']).size().rename('rows').reset_index(),'indoor_quality_flags')
for col in ['outdoor_match_status','ridership_match_status']:
    save(d.groupby(['year',col]).size().rename('rows').reset_index(),col)
progress(1,'관측률·월별 요약표 작성 완료; 비교기간 집계 중')
base=d[d.year.isin(['2022','2023','2024'])]
expected=1096*24
summary=base.groupby('analysis_station_id').value.agg(n='count',mean='mean',median='median',p90=lambda x:x.quantile(.9),maximum='max').reindex(ids).reset_index().merge(stations,on='analysis_station_id')
summary['expected_hours']=expected
summary['coverage']=summary.n/expected
summary['paired_n']=base.groupby('analysis_station_id').paired.sum().reindex(ids).values
summary['paired_rate_of_valid']=summary.paired_n/summary.n
save(summary,'station_comparison_2022_2024')
hour=base.groupby(['analysis_station_id','hour']).value.agg(n='count',mean='mean',median='median',p90=lambda x:x.quantile(.9)).reset_index()
hour['expected_days']=1096
hour['coverage']=hour.n/1096
save(hour.merge(stations,on='analysis_station_id'),'station_hour_2022_2024')
overall={'returned_rows':len(d),'expected_hours':int(monthly.expected_hours.sum()),'provisional_valid_n':int(d.value.notna().sum()),'paired_n':int(d.paired.sum()),'stations':len(ids),'collected_months':len(months),'baseline_valid_n':int(base.value.notna().sum()),'baseline_expected_hours':expected*len(ids)}
(OUT/'tables/summary.json').write_text(json.dumps(overall,ensure_ascii=False,indent=2),encoding='utf-8')
progress(2,'요약표 완료; PNG·SVG 그림 작성 중')

class Canvas:
    def __init__(self,w,h,title,subtitle):
        self.w,self.h=w,h
        self.im=Image.new('RGB',(w,h),'white'); self.draw=ImageDraw.Draw(self.im)
        self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="white"/>']
        self.text(25,18,title,26); self.text(25,58,subtitle,15)
    def text(self,x,y,s,size=15,color='#222222'):
        font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',size)
        self.draw.text((x,y),str(s),font=font,fill=color)
        self.svg.append(f'<text x="{x}" y="{y+size}" font-family="Malgun Gothic, sans-serif" font-size="{size}" fill="{color}">{html.escape(str(s))}</text>')
    def rect(self,x,y,w,h,color):
        self.draw.rectangle((x,y,x+w,y+h),fill=color)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}"/>')
    def line(self,x1,y1,x2,y2,color='#888888',width=1):
        self.draw.line((x1,y1,x2,y2),fill=color,width=width)
        self.svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>')
    def dot(self,x,y,color,r=4):
        self.draw.ellipse((x-r,y-r,x+r,y+r),fill=color)
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>')
    def save(self,name):
        self.im.save(OUT/'figures'/f'{name}.png',dpi=(180,180))
        (OUT/'figures'/f'{name}.svg').write_text(''.join(self.svg)+'</svg>',encoding='utf-8')

def color(v,maximum):
    if not np.isfinite(v): return '#dddddd'
    t=max(0,min(1,float(v)/maximum))
    a=np.array([239,249,232]); b=np.array([0,91,112])
    rgb=(a+(b-a)*t).astype(int)
    return '#%02x%02x%02x'%tuple(rgb)
def matrix(table,col,columns,coverage=None):
    m=table.pivot(index='analysis_station_id',columns=col,values='median').reindex(index=ids,columns=columns)
    if coverage is not None:
        q=table.pivot(index='analysis_station_id',columns=col,values='coverage').reindex(index=ids,columns=columns)
        m=m.where(q.ge(coverage))
    return m
hm=matrix(hour,'hour',list(range(24)),.75)
mm=matrix(monthly,'month',calendar,.75)
scale=float(np.ceil(max(hm.max().max(),mm.max().max())/10)*10)
def heatmap(m,name,title,maxval,units,sub,notcollected=False):
    cw=22 if len(m.columns)>30 else 45
    left,top,rh=190,115,25
    c=Canvas(max(1050,left+cw*len(m.columns)+40),top+rh*57+135,title,sub)
    for i,label in enumerate(labels):
        c.text(12,top+i*rh+2,label,14)
        for j,col in enumerate(m.columns):
            x,y=left+j*cw,top+i*rh
            c.rect(x,y,cw-1,rh-1,color(m.iloc[i,j],maxval))
            if notcollected and col not in months:
                c.line(x,y+rh-2,x+cw-2,y,'#999999')
    for j,col in enumerate(m.columns):
        if isinstance(col,int): c.text(left+j*cw,top-26,f'{col:02d}',13)
        elif j%3==0: c.text(left+j*cw,top-25,col[2:],12)
    y=top+57*rh+20
    for k in range(150): c.rect(left+k*2,y,2,15,color(k/149*maxval,maxval))
    c.text(left,y+20,'0',14)
    c.text(left+285,y+20,f'{maxval:g} {units}',14)
    c.text(left+360,y,'회색: 결측/관측률 75% 미만' if units!='%' else '회색 사선: 미수집 월',14)
    if notcollected: c.text(left+360,y+25,'사선: 2025년 5~12월 미수집',14)
    c.text(20,y+62,'잠정 표본: 수치 유효 + 상태 공백(의미 미확인). 관측률 분모는 해당 기간의 모든 시간.',13)
    c.save(name)
coverage=monthly.pivot(index='analysis_station_id',columns='month',values='coverage').reindex(index=ids,columns=calendar)*100
heatmap(coverage,'01_monthly_coverage','역별·월별 잠정 사용 표본 관측률',100,'%', '2021.04~2026.04 | 수집된 53개월, 57개 측정지점',True)
heatmap(hm,'02_hourly_median','역별·시간대별 PM2.5 중앙값',scale,'µg/m³','2022~2024 | 같은 시각 표기 기준 | 관측률 75% 이상 셀 표시')
heatmap(mm,'03_monthly_median','역별·월별 PM2.5 중앙값',scale,'µg/m³','2021.04~2026.04 | 관측률 75% 이상 셀 표시 | 시간대 그림과 동일 색 범위',True)
c=Canvas(1100,57*26+180,'역별 PM2.5 평균·중앙값·90백분위수','2022~2024 | 관측 가능한 잠정 표본 전체 | 관측량·기간 차이를 함께 확인')
x0,x1=205,830
maxx=float(np.ceil(summary[['mean','median','p90']].max().max()/10)*10)
for v in np.linspace(0,maxx,6):
    x=x0+v/maxx*(x1-x0); c.line(x,110,x,110+57*26,'#eeeeee'); c.text(x-8,85,f'{v:g}',13)
for i,(_,row) in enumerate(summary.iterrows()):
    y=120+i*26; c.text(12,y-10,labels[i],14)
    for col,cl in [('mean','#d95f02'),('median','#167daa'),('p90','#7b3294')]: c.dot(x0+row[col]/maxx*(x1-x0),y,cl)
    c.text(855,y-10,f'n={row["n"]:,} ({row.coverage:.1%})',13)
c.text(205,110+57*26+18,'주황: 평균   파랑: 중앙값   보라: 90백분위수 | 단위 µg/m³',15)
c.save('04_station_distribution')
selected=[]
for code in [summary.loc[summary['median'].idxmax(),'analysis_station_id'],summary.assign(spread=summary.p90-summary['median']).sort_values('spread',ascending=False).iloc[0].analysis_station_id,summary.sort_values('coverage').iloc[0].analysis_station_id]:
    if code not in selected: selected.append(code)
for k,code in enumerate(selected,1):
    s=monthly[monthly.analysis_station_id.eq(code)].set_index('month').reindex(calendar)
    row=stations[stations.analysis_station_id.eq(code)].iloc[0]
    c=Canvas(1300,590,f'{row.line} {row.station_name}: 월별 변화','점: 중앙값 / 세로선: 25~75백분위수 | 아래 막대: 관측률 | 75% 미만 월은 농도 표시 제외')
    vmax=float(np.ceil(s.p75.max()/10)*10); vmax=max(vmax,10)
    for val in np.linspace(0,vmax,6):
        y=365-val/vmax*245; c.line(65,y,1265,y,'#eeeeee'); c.text(12,y-9,f'{val:g}',13)
    prev=None
    for j,month in enumerate(calendar):
        x=75+j*19.5; r=s.loc[month]
        if month not in months:
            c.rect(x-8,110,17,380,'#eeeeee'); prev=None
        elif pd.notna(r.coverage):
            c.rect(x-7,485-r.coverage*75,14,r.coverage*75,'#339999')
            if r.coverage>=.75 and pd.notna(r['median']):
                y=365-r['median']/vmax*245
                c.line(x,365-r.p25/vmax*245,x,365-r.p75/vmax*245,'#80b1d3',3)
                if prev: c.line(*prev,x,y,'#167daa',2)
                c.dot(x,y,'#167daa'); prev=(x,y)
            else: prev=None
        if j%6==0: c.text(x-10,495,month,12)
    c.text(15,380,'µg/m³',13); c.text(12,400,'100%',13); c.text(12,475,'0%',13)
    c.text(25,545,'미수집 구간은 연결하지 않음. 월별 관측 시간 구성이 달라질 수 있어 원인·추세의 확정 근거로 사용하지 않음.',14)
    c.save(f'05_example_{k}_{code}')

top=summary.sort_values('median',ascending=False).head(5)
low=summary.sort_values('coverage').head(5)
def tab(frame,columns):
    return frame[columns].to_markdown(index=False,floatfmt='.2f')
# Avoid optional tabulate dependency.
def table(frame,columns):
    lines=['| '+' | '.join(columns)+' |','|'+'|'.join(['---']*len(columns))+'|']
    for _,r in frame.iterrows(): lines.append('| '+' | '.join(f'{r[k]:.2f}' if isinstance(r[k],(float,np.floating)) else str(r[k]) for k in columns)+' |')
    return '\n'.join(lines)
report=f'''# 분석 표본 품질과 기본 패턴

## 범위와 표본

- 결합본 {len(d):,}행, 57개 측정지점(반월당은 호선별 별도).
- 수집기간: 2021년 4월~2025년 4월 및 2026년 1~4월, 총 53개월.
- 2025년 5~12월은 미수집이다. 결측 센서나 농도 0으로 처리하지 않았다.
- 수집기간의 완전 시간격자 {overall['expected_hours']:,}시간 중 잠정 사용 표본 {overall['provisional_valid_n']:,}개({overall['provisional_valid_n']/overall['expected_hours']:.2%}).
- 실내외 PM2.5 동시 수치 관측 {overall['paired_n']:,}개. 실외 측정소를 배정하지 않은 현충로·율하는 실내 분석에는 포함한다.
- 잠정 사용 표본은 유한한 0 이상 실내 수치이면서 상태코드가 공백인 값이다. 공백이 정상 상태를 의미하는지는 확인되지 않았으므로 공식 품질검증 자료라고 해석하지 않는다.

## 비교 방법

역 간 기본 비교는 온전한 연도인 2022~2024년으로 제한했다. 이 기간 잠정 사용 표본은 {overall['baseline_valid_n']:,}개 / 기대 {overall['baseline_expected_hours']:,}시간이다. 부분 연도와 연도별 구성 차이가 섞이는 것을 줄이기 위한 선택이다.

월·시간대 농도 열지도는 기대 시간 대비 관측률 75% 이상인 셀만 표시한다. 75%는 이번 탐색을 위한 표시 기준이며 법정 품질 기준이 아니다. 표에는 기준 미달 셀의 통계와 관측 수도 모두 보존했다. 분포 그림은 비교기간의 가용 표본 전체를 사용하고 역별 n·관측률을 표시했다. 모든 역에 동일한 시각 집합을 적용한 결과는 아니므로 관측 구성 차이는 남아 있다.

시간은 기존 same_label_v1 규칙의 동일 시각 표기를 사용했다. 실제 측정 구간의 시작·종료 시각 일치가 입증된 것은 아니다. 이번 작업에서는 승하차와 농도의 인과·상관 모형을 추정하지 않았다.

## 확인된 기본 패턴

2022~2024년 가용 표본의 중앙값이 큰 5개 지점은 다음과 같다. 관리 우선순위가 아니라 기술통계 순서다. 평균과 90백분위수를 함께 확인해야 일부 고농도에 의한 평균 상승과 지속적인 수준 차이를 구분할 수 있다.

{table(top,['line','station_name','n','coverage','mean','median','p90'])}

관측률이 낮은 5개 지점은 다음과 같다. coverage는 0~1 비율이며 적은 표본을 근거로 역 간 순위를 확정하지 않는다.

{table(low,['line','station_name','n','coverage'])}

월별 관측률 75% 미만인 수집 대상 역·월은 {(monthly.coverage<.75).sum():,}개다. 기대 시간 중 행 자체가 없는 경우와 행은 있으나 잠정 사용 기준에 맞지 않는 경우를 별도 열로 저장했다. 미수집 8개월은 이 집계에서 제외했다.

개별 시계열은 비교기간 중앙값 최대, 90백분위수-중앙값 차이 최대, 관측률 최소라는 규칙으로 골랐다(중복 제거). 선택 지점: {', '.join(stations.set_index('analysis_station_id').loc[selected].apply(lambda r:r.line+' '+r.station_name,axis=1))}. 월별 중앙값과 사분위 범위, 관측률을 같이 표시하며 미수집·기준 미달 구간은 선을 연결하지 않는다.

## 산출물 사용법

- figures/01_monthly_coverage: 먼저 표본이 충분한 역·기간 확인.
- figures/02_hourly_median: 2022~2024년 시간대 중앙값 비교.
- figures/03_monthly_median: 월별 변화 확인. 시간대 그림과 동일한 색 범위이며 자동 절단 없음.
- figures/04_station_distribution: 평균·중앙값·90백분위수와 n 비교.
- figures/05_example_*: 규칙으로 선택한 지점의 개별 시계열.
- 모든 그림은 PNG(180dpi)와 텍스트를 유지한 SVG 두 형식. SVG의 한글 글꼴은 Malgun Gothic을 사용한다.
- tables/station_month_quality_and_concentration.csv: 관측률, 행 부재, 값 부적합, 동시 관측 수, 월별 농도 통계.
- tables/station_hour_2022_2024.csv 및 station_comparison_2022_2024.csv: 그림 재현용 시간대·역별 통계.
- tables/*status*.csv 및 indoor_quality_flags.csv: 원자료 상태와 결합 상태별 행 수. 승하차 00~04시는 원자료 시간대 밖이며 결측 승하차를 0으로 바꾸지 않았다.
- tables/summary.json: 전체 집계 수치.

## 해석의 한계와 다음 단계

공식 상태코드 해석, 기기 보정·교체 이력, 실제 시각 구간, 실외 측정소 대표성은 확인되지 않았다. 따라서 이 그림만으로 원인, 노출량, 법정 기준 초과 여부 또는 관리 우선순위를 확정하지 않는다. 다음 작업으로는 동일한 관측 시각을 맞춘 비교와 실외 조건·계절·요일을 구분한 분석을 제안한다. 이번 작업에서는 추가 분석이나 수집은 수행하지 않았다.

## 재현

스크립트: data/_scripts/analyze_basic_patterns.py. Python 환경에 pandas, numpy, Pillow와 Windows 맑은 고딕 글꼴 필요. 원본·결합 CSV는 수정하지 않으며 outputs/basic_patterns/만 생성한다. Git 커밋·업로드 없음.
'''
(OUT/'report.md').write_text(report,encoding='utf-8-sig')
progress(3,'그림·보고서 작성 완료; 수치 및 이미지 검증 중')
assert len(stations)==57
assert not d.duplicated(['analysis_station_id','date','hour']).any()
assert monthly.returned_rows.sum()==len(d)
assert monthly.valid_n.sum()==d.value.notna().sum()
assert monthly.paired_n.sum()==d.paired.sum()
assert summary.n.sum()==base.value.notna().sum()
assert monthly.missing_rows.ge(0).all()
for file in (OUT/'figures').glob('*.png'):
    with Image.open(file) as im: im.verify()
validation={'passed':True,'checks':['57 station IDs','unique station-date-hour keys','monthly row and valid counts reconcile','paired counts reconcile','baseline counts reconcile','nonnegative missing-row counts','all PNG decode'],'figures_png':len(list((OUT/'figures').glob('*.png'))),'figures_svg':len(list((OUT/'figures').glob('*.svg')))}
(OUT/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(overall,ensure_ascii=False),flush=True)
print('Numeric checks complete; visual review pending.',flush=True)
