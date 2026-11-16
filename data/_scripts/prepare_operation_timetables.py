"""Parse historical CSV and dated official XLSX into scheduled hourly counts."""
from pathlib import Path
import csv,json,re,zipfile,xml.etree.ElementTree as ET
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];SRC=ROOT/'data/timetable_change/sources';OUT=ROOT/'data/timetable_change'
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def norm(s):
    s=re.sub(r'\([^)]*\)','',str(s)).strip().removesuffix('역').replace(' ','')
    s=re.sub(r'^[12](?=[가-힣])','',s)
    return {'수성알파시티':'대공원','성당못':'서부정류장','대곡정부대구청사':'대곡','성서공단':'성서산업단지','성서산단':'성서산업단지','신내':'신매'}.get(s,s)
meta=pd.read_csv(ROOT/'data/mapping/indoor_station_coordinates.csv')
mapping={(r.line,norm(r.indoor_station_name)):r.analysis_station_id for r in meta.itertuples()}
def minute(v):
    v=str(v).strip()
    m=re.fullmatch(r'(\d{1,2}):(\d{2})(?::(\d{2}))?',v)
    if m:return int(m[1])*60+int(m[2])+int(m[3] or 0)/60
    try:
        x=float(v)
        if 0<x<1:return x*1440
    except ValueError:pass
    return None
events=[]
for line in [1,2]:
    rows=list(csv.reader((SRC/f'line{line}_pre_archive.csv').open(encoding='cp949')))[1:]
    picks={}
    for r in rows:
        if len(r)<4:continue
        day='weekday' if '평일' in r[0] else 'saturday' if '토요일' in r[0] else 'holiday'
        direction='up' if '(상)' in r[0] else 'down'
        key=(day,direction,norm(r[1]))
        if key not in picks or r[2]=='출발':picks[key]=r
    for (day,direction,name),r in picks.items():
        sid=mapping.get((f'{line}호선',name))
        if not sid:continue
        for val in r[3:]:
            m=minute(val)
            if m is not None:events.append({'version':'archive_pre','line':line,'day_type':day,'direction':direction,'analysis_station_id':sid,'station_name':name,'minute':m,'hour':int(m//60)%24})
    z=zipfile.ZipFile(SRC/f'line{line}_post_20241007.xlsx')
    shared=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml'))]
    for sheet in [n for n in z.namelist() if re.fullmatch(r'xl/worksheets/sheet\d+.xml',n)]:
        day=None;direction=None
        for row in ET.fromstring(z.read(sheet)).findall('m:sheetData/m:row',NS):
            cells={}
            for c in row:
                val=c.find('m:v',NS)
                if val is None:continue
                value=shared[int(val.text)] if c.attrib.get('t')=='s' else val.text
                col=re.sub(r'\d','',c.attrib['r']);cells[col]=value
            title=' '.join(str(v) for v in cells.values() if '시 각 표' in str(v))
            if title:
                day='weekday' if '평일' in title else 'saturday' if '토요일' in title else 'holiday'
                direction='up' if ('설화' in title or '문양' in title) else 'down'
            if not day or 'A' not in cells:continue
            name=norm(cells['A']);sid=mapping.get((f'{line}호선',name))
            if not sid:continue
            for col,v in cells.items():
                if col=='A':continue
                m=minute(v)
                if m is not None:events.append({'version':'official_post','line':line,'day_type':day,'direction':direction,'analysis_station_id':sid,'station_name':name,'minute':m,'hour':int(m//60)%24})
e=pd.DataFrame(events);e.to_csv(OUT/'scheduled_events.csv',index=False,encoding='utf-8-sig')
grid=pd.MultiIndex.from_product([['archive_pre','official_post'],['weekday','saturday','holiday'],meta.analysis_station_id.tolist(),range(24)],names=['version','day_type','analysis_station_id','hour'])
counts=e.groupby(['version','day_type','analysis_station_id','hour']).size().reindex(grid,fill_value=0).rename('scheduled_count').reset_index()
wide=counts.pivot(index=['day_type','analysis_station_id','hour'],columns='version',values='scheduled_count').reset_index()
wide['delta']=wide.official_post-wide.archive_pre
wide.to_csv(OUT/'hourly_schedule_change.csv',index=False,encoding='utf-8-sig')
daily=e.groupby(['version','day_type','analysis_station_id']).size().rename('count').reset_index()
daily.to_csv(OUT/'daily_schedule_counts.csv',index=False,encoding='utf-8-sig')
ref=daily[daily.analysis_station_id.isin(['DG_L1_1300','DG_L2_2300'])]
print(ref.to_string(index=False),flush=True)
print(wide[wide.analysis_station_id.isin(['DG_L1_1300','DG_L2_2300'])&wide.day_type.eq('weekday')&wide.hour.between(15,21)].to_string(index=False),flush=True)
assert daily.groupby(['version','day_type']).analysis_station_id.nunique().eq(57).all()
validation={'stations':57,'versions':['archive_pre','official_post'],'event_rows':len(e),'count_rows':len(wide),'post_effective_date':'2024-10-07','pre_archive_label':'20220430; last modified date and continuous applicability need corroboration','count_definition':'scheduled departures where available; terminal arrivals otherwise; XLSX minute-level public timetable; both directions summed; not realized operations','reference_daily_counts':ref.to_dict('records')}
(OUT/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf-8')
