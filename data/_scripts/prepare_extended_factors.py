"""Prepare NOAA hourly weather and source-checked Korean named holidays."""
from pathlib import Path
import pandas as pd
import numpy as np
import json, hashlib, re
ROOT=Path(__file__).resolve().parents[2]; SRC=ROOT/'data/weather/sources'
W=ROOT/'data/weather'; C=ROOT/'data/calendar'
W.mkdir(exist_ok=True); C.mkdir(exist_ok=True)
def save(df,path):df.to_csv(path,index=False,encoding='utf-8-sig')
data=[];quality=[]
for year in [2021,2022,2023,2024]:
    df=pd.read_csv(SRC/f'noaa_47143099999_{year}.csv',dtype=str)
    df['source_file']=f'noaa_47143099999_{year}.csv';data.append(df)
raw=pd.concat(data,ignore_index=True)
utc=pd.to_datetime(raw.DATE,utc=True)
raw['time_kst']=utc.dt.tz_convert('Asia/Seoul').dt.tz_localize(None)
for field,target in [('TMP','temperature_c'),('DEW','dewpoint_c')]:
    p=raw[field].str.split(',',expand=True)
    value=pd.to_numeric(p[0],errors='coerce')/10
    raw[target]=value.where(p[1].isin(['1','5']) & value.ne(999.9))
    for flag,n in p[1].value_counts(dropna=False).items():quality.append({'field':field,'quality_code':flag,'n':int(n)})
wind=raw.WND.str.split(',',expand=True)
speed=pd.to_numeric(wind[3],errors='coerce')/10
direction=pd.to_numeric(wind[0],errors='coerce')
raw['wind_speed_mps']=speed.where(wind[4].isin(['1','5']) & speed.ne(999.9))
raw['wind_direction_deg']=direction.where(wind[1].isin(['1','5']) & direction.between(0,360))
for col,target in [(4,'WND_speed'),(1,'WND_direction')]:
    for flag,n in wind[col].value_counts(dropna=False).items():quality.append({'field':target,'quality_code':flag,'n':int(n)})
# Approximate RH over liquid water, derived from temperature and dewpoint, not directly observed.
T=raw.temperature_c;Td=raw.dewpoint_c
rh=100*np.exp(17.502*Td/(240.97+Td)-17.502*T/(240.97+T))
raw['relative_humidity_derived_pct']=rh.where(rh.between(0,100) & Td.le(T))
rad=np.deg2rad(raw.wind_direction_deg)
raw['wind_from_east_mps']=raw.wind_speed_mps*np.sin(rad)
raw['wind_from_north_mps']=raw.wind_speed_mps*np.cos(rad)
calm=raw.wind_speed_mps.eq(0)
raw.loc[calm,['wind_from_east_mps','wind_from_north_mps']]=0
raw['precipitation_1h_mm']=np.nan
raw['precipitation_1h_reported_mm']=np.nan
raw['precipitation_1h_condition']=''
for col in ['AA1','AA2','AA3','AA4']:
    if col not in raw:continue
    p=raw[col].fillna('').str.split(',',expand=True)
    if p.shape[1]<4:continue
    depth=pd.to_numeric(p[1],errors='coerce')/10
    reported=p[0].eq('01') & p[3].isin(['1','5']) & depth.ne(999.9)
    take=raw.precipitation_1h_reported_mm.isna() & reported
    raw.loc[take,'precipitation_1h_reported_mm']=depth[take]
    raw.loc[take,'precipitation_1h_condition']=p.loc[take,2]
    # Codes 2 (trace) and 3 (accumulation-period marker) are not ordinary numeric one-hour values.
    v=depth.where(reported & p[2].eq('9'))
    raw['precipitation_1h_mm']=raw.precipitation_1h_mm.fillna(v)
raw=raw[raw.time_kst.between('2022-01-01','2024-12-31 23:00:00')].copy()
assert raw.STATION.eq('47143099999').all()
raw=raw[raw.time_kst.dt.minute.eq(0)&raw.time_kst.dt.second.eq(0)]
features=['temperature_c','dewpoint_c','relative_humidity_derived_pct','wind_speed_mps','wind_direction_deg','wind_from_east_mps','wind_from_north_mps','precipitation_1h_mm','precipitation_1h_reported_mm','precipitation_1h_condition']
raw['quality_count']=raw[features[:4]].notna().sum(axis=1)
raw=raw.sort_values(['time_kst','quality_count'],ascending=[True,False])
duplicate_n=int(raw.duplicated('time_kst').sum());raw=raw.drop_duplicates('time_kst')
weather=raw[['time_kst','DATE','STATION','NAME','LATITUDE','LONGITUDE','REPORT_TYPE','source_file']+features].rename(columns={'DATE':'time_utc','STATION':'weather_station_id'})
grid=pd.date_range('2022-01-01','2024-12-31 23:00',freq='h')
weather=weather.set_index('time_kst').reindex(grid).rename_axis('time_kst').reset_index()
weather['weather_complete']=weather[['temperature_c','relative_humidity_derived_pct','wind_speed_mps','wind_from_east_mps','wind_from_north_mps']].notna().all(axis=1)
save(weather,W/'weather_hourly_2022_2024.csv')
save(pd.DataFrame(quality),W/'quality_code_counts.csv')
weather['year']=weather.time_kst.dt.year
coverage=weather.groupby('year').agg(expected_hours=('time_kst','size'),observed_rows=('time_utc','count'),temperature_n=('temperature_c','count'),humidity_derived_n=('relative_humidity_derived_pct','count'),wind_speed_n=('wind_speed_mps','count'),weather_complete_n=('weather_complete','sum'),precipitation_1h_n=('precipitation_1h_mm','count')).reset_index()
save(coverage,W/'coverage_yearly.csv')

sources={
 '2022':'https://astro.kasi.re.kr/kor/life/post/calendarData?search_year=2022',
 '2023':'https://astro.kasi.re.kr/kor/life/post/calendarData?search_year=2023',
 '2024':'https://astro.kasi.re.kr/kor/life/post/calendarData?search_year=2024',
 '2023-05-29':'https://www.mpm.go.kr/mpm/comm/newsPress/newsPressRelease/?boardId=bbs_0000000000000029&cntId=3625&mode=view',
 '2023-10-02':'https://www.korea.kr/news/policyNewsView.do?newsId=148919798',
 '2024-10-01':'https://www.mpm.go.kr/mpm/comm/noti/mpmNotice/?boardId=bbs_0000000000000205&cntId=834&mode=view',
 '2022-election':'https://www.korea.kr/multi/visualNewsView.do?newsId=148897861',
}
dates={
2022:[('01-01','신정'),('01-31','설연휴'),('02-01','설날'),('02-02','설연휴'),('03-01','삼일절'),('03-09','대통령선거'),('05-05','어린이날'),('05-08','부처님오신날'),('06-01','지방선거'),('06-06','현충일'),('08-15','광복절'),('09-09','추석연휴'),('09-10','추석'),('09-11','추석연휴'),('09-12','대체공휴일'),('10-03','개천절'),('10-09','한글날'),('10-10','대체공휴일'),('12-25','성탄절')],
2023:[('01-01','신정'),('01-21','설연휴'),('01-22','설날'),('01-23','설연휴'),('01-24','대체공휴일'),('03-01','삼일절'),('05-05','어린이날'),('05-27','부처님오신날'),('05-29','대체공휴일'),('06-06','현충일'),('08-15','광복절'),('09-28','추석연휴'),('09-29','추석'),('09-30','추석연휴'),('10-02','임시공휴일'),('10-03','개천절'),('10-09','한글날'),('12-25','성탄절')],
2024:[('01-01','신정'),('02-09','설연휴'),('02-10','설날'),('02-11','설연휴'),('02-12','대체공휴일'),('03-01','삼일절'),('04-10','국회의원선거'),('05-05','어린이날'),('05-06','대체공휴일'),('05-15','부처님오신날'),('06-06','현충일'),('08-15','광복절'),('09-16','추석연휴'),('09-17','추석'),('09-18','추석연휴'),('10-01','임시공휴일'),('10-03','개천절'),('10-09','한글날'),('12-25','성탄절')]}
holiday=[]
for year,items in dates.items():
    for mmdd,name in items:
        date=f'{year}-{mmdd}';source=sources.get(date,sources[str(year)])
        if date in ['2022-03-09','2022-06-01']:source=sources['2022-election']
        holiday.append({'date':date,'holiday_name':name,'source_url':source})
hol=pd.DataFrame(holiday)
assert len(hol)==56 and not hol.date.duplicated().any()
save(hol,C/'named_holidays_2022_2024.csv')
cal=pd.DataFrame({'date':pd.date_range('2022-01-01','2024-12-31').strftime('%Y-%m-%d')})
cal=cal.merge(hol,on='date',how='left',validate='one_to_one')
cal['named_holiday']=cal.holiday_name.notna().astype(int)
cal['weekday']=pd.to_datetime(cal.date).dt.dayofweek
cal['regular_sunday']=cal.weekday.eq(6).astype(int)
save(cal,C/'calendar_2022_2024.csv')
histories=[]
for line in [1,2]:
    text=(SRC/f'train_line{line}_history.html').read_text(encoding='utf-8')
    matches=re.findall(r'class="openFileDetailPopup open-modal" data-public-pk="([^"]+)"\s+data-public-detail-sn="([^"]+)">\s*([^<]+)',text)
    for pk,sn,name in matches: histories.append({'line':line,'detail_pk':pk,'hist_sn':sn,'name':name.strip()})
save(pd.DataFrame(histories),W/'train_archive_inventory.csv')
manifest={'weather_station':'47143099999','name':'TAEGU ACC KOR AFB, KS','latitude':float(raw.LATITUDE.iloc[0]),'longitude':float(raw.LONGITUDE.iloc[0]),'time_rule':'NOAA UTC + 9h = Asia/Seoul; exact top-of-hour only; no forward fill','quality_rule':'TMP/DEW/WND quality codes 1 and 5 only; no sentinel values; calm wind vector=0 when valid speed=0','humidity':'derived, not observed: 100 exp[17.502 Td/(240.97+Td) - 17.502 T/(240.97+T)]; water-relative approximation','duplicate_times_removed':duplicate_n,'total_hours':len(weather),'complete_weather_hours':int(weather.weather_complete.sum()),'observed_precip_1h_hours':int(weather.precipitation_1h_mm.count()),'rainfall_model_policy':'excluded because explicit valid one-hour precipitation is sparse; blank is NOT zero','holiday_policy':'named holidays including election, substitute, temporary; regular Sundays separately represented by weekday; Labour Day excluded','named_holiday_dates':len(hol),'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SRC.glob('noaa_47143099999_*.csv')}}
manifest['one_hour_reported_but_excluded_conditions']=raw.loc[raw.precipitation_1h_reported_mm.notna(),'precipitation_1h_condition'].value_counts().to_dict()
manifest['rainfall_model_policy']='Excluded entirely: ordinary QC-accepted numeric hourly precipitation not established after condition-code audit. Trace is not dry zero; accumulation markers not treated as ordinary hourly amounts. No daily substitution.'
(W/'preparation_summary.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(W/'README.md').write_text('''# 추가 기상자료

NOAA Global Hourly 공개 원자료, 관측소 47143099999 (TAEGU ACC KOR AFB, KS). 역별 실내·흡기구 기상이 아닌 도시 공통 기상 대리변수다. 현재 기상청 ASOS 지점과 위치·기기·원자료가 같다고 가정하지 않는다.

원자료: https://noaa-global-hourly-pds.s3.amazonaws.com/{year}/47143099999.csv (2021~2024). 2021년 파일은 2022년 KST 첫 9시간을 확보하기 위해 함께 읽는다. 분석용 범위는 2022~2024년 KST다. NOAA ISD의 UTC를 KST로 +9시간 변환하며 정시 관측만 사용한다. 형식·품질 정의: https://www.ncei.noaa.gov/nerms/api/document/5b2ced2e766e4f7091d66ab228a58813/download

상대습도는 온도·이슬점에서 계산한 근사치다. 공식 https://madis.ncep.noaa.gov/madis_rwis_qc_notes.shtml 의 포화수증기압 관계를 역산했다. 실내 습도나 측정기의 습도 오차를 직접 측정한 값이 아니다. 품질코드 1·5만 사용하고 결측 보간은 하지 않는다.

강수의 시간 표기뿐 아니라 조건코드도 확인했다. 1시간 표기 1,588개는 조건 2(미량) 223개, 조건 3(누적기간 표시) 1,365개다. 이 값은 precipitation_1h_reported_mm 및 precipitation_1h_condition에 검토용으로만 보존하며 정상적인 시간별 수치로 쓰지 않는다. 미량을 무강수 0으로 바꾸지 않는다. 명시적 품질 유효 수치 + 일반 조건코드 9만 허용하는 precipitation_1h_mm은 이번 기간 모두 결측이므로 강수는 최종 모형에서 전부 제외한다. 장시간 누적값을 나누거나 일별 강수로 대체하지 않는다. coverage_yearly.csv와 preparation_summary.json에 범위·품질·해시를 기록했다.

기상청 포털의 CSV 다운로드는 로그인 절차가 있어 이번 자동 수집에 사용하지 않았다. NOAA 공개자료를 대신 사용한 사실을 분석 보고서에도 명시한다. data_go_fileDetail.js·train*.html은 과거 운행자료의 공개 이력 조사 기록이며 기상 관측값이 아니다.
''',encoding='utf-8-sig')
(C/'README.md').write_text('''# 공휴일 달력

2022~2024년 명칭이 있는 공휴일 56일을 KASI 연도별 달력자료에 따라 구조화하고 2023년 5월29일 대체공휴일, 2023년 10월2일 및 2024년 10월1일 임시공휴일을 정부 공고로 보완했다. 원 출처는 named_holidays_2022_2024.csv 각 행에 있다. KASI 달력자료는 사전 작성본일 수 있어 추가 지정일을 별도로 확인했다.

정기 일요일은 기존 요일 변수로 반영하므로 named_holiday는 모든 일요일을 뜻하지 않는다. 공휴일 명칭이 일요일과 겹치면 named_holiday도 1이다. 근로자의 날은 이 공휴일 지표에 포함하지 않았다. 휴일 효과를 실제 열차 휴일 운행 여부와 동일시하지 않는다.
''',encoding='utf-8-sig')
assert len(weather)==26304 and not weather.time_kst.duplicated().any()
assert len(cal)==1096 and cal.named_holiday.sum()==56
print(json.dumps(manifest,ensure_ascii=False),flush=True)
print(coverage.to_string(index=False),flush=True)
