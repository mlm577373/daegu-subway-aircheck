from collect_data import get, ROOT
import json, gzip, csv, calendar

with (ROOT/'subway_air'/'coverage_station_month.csv').open(encoding='utf-8-sig') as f:
    targets=[r for r in csv.DictReader(f) if int(r['returned_rows'])==0]
for r in targets:
    code=r['station_code'];ym=r['month'];year,month=map(int,ym.split('-'))
    start=ym.replace('-','')+'0100';end=ym.replace('-','')+str(calendar.monthrange(year,month)[1])+'23'
    rows=json.loads(get('https://www.inair.or.kr/info/main/selectDetailExcel.do',{'view_start_date':start,'view_end_date':end,'loc_code':code}))
    dest=ROOT/'_sources'/f'inair_empty_recheck_{code}_{ym.replace("-","")}.json'
    dest.write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')
    print(code,ym,'rows',len(rows),flush=True)
    if rows:raise RuntimeError('New records found; re-collect this station-month and rebuild outputs')
