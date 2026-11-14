"""Sequential, cached collection of public Daegu air-quality data."""
from collect_probe import ROOT, S, fetch
import sys, json, gzip, csv, calendar, datetime as dt, time, pathlib, traceback
sys.path.insert(0,str(ROOT/'_tools'))
import xlrd
from concurrent.futures import ThreadPoolExecutor

TODAY=dt.date(2026,11,13)
START=dt.date(2021,4,1)
LOG=ROOT/'collection_log.jsonl'

def log(kind,**kw):
    rec={'at':dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(),'kind':kind,**kw}
    with LOG.open('a',encoding='utf-8') as f:f.write(json.dumps(rec,ensure_ascii=False)+'\n')
    print(json.dumps(rec,ensure_ascii=True),flush=True)

def get(url,data=None):
    for attempt in range(3):
        try:return fetch(url,data,timeout=60)[0]
        except Exception as e:
            log('retry',url=url,error=str(e),attempt=attempt+1)
            if attempt==2:raise
            time.sleep(2*(attempt+1))

def months(a,b):
    cur=a.replace(day=1)
    while cur<=b:
        last=cur.replace(day=calendar.monthrange(cur.year,cur.month)[1])
        yield max(a,cur),min(b,last)
        cur=(last+dt.timedelta(days=1))

def selected_months(plan):
    allowed=set(plan['months'])
    a,b=map(dt.date.fromisoformat,[plan['start'],plan['end']])
    return [(s,e) for s,e in months(a,b) if s.strftime('%Y-%m') in allowed]

def xls_rows(path):
    book=xlrd.open_workbook(str(path));sh=book.sheet_by_index(0)
    if sh.ncols!=10:raise ValueError(f'Unexpected outdoor columns: {sh.ncols}')
    rows=[sh.row_values(i) for i in range(1,sh.nrows) if str(sh.cell_value(i,0)).strip()]
    if any(not str(r[0]).startswith(('2021-','2022-','2023-','2024-','2025-','2026-')) for r in rows):raise ValueError('Unexpected outdoor dates')
    return rows

def air_download(a,b,path,codes):
    if not path.exists():
        body={'mang_code':'3','district':'053','from_date':str(a),'to_date':str(b),'station_list_':codes,'flag':'Y','windowid':'daegu-public-research'}
        raw=get('https://www.airkorea.or.kr/web/lastAmbHourDataExcel_',body)
        if not raw.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):raise ValueError('Outdoor response is not XLS')
        temp=path.with_suffix('.tmp');temp.write_bytes(raw);xls_rows(temp);temp.replace(path)
    return xls_rows(path)

def establish_period():
    inventory_path=ROOT/'ridership'/'inventory.json'
    if not inventory_path.exists():raise RuntimeError('Ridership inventory must be completed first')
    inventory=json.loads(inventory_path.read_text(encoding='utf-8'))
    stations=json.loads((S/'airkorea_stations.json').read_bytes())['stationList']
    codes=','.join(s['STATION_CODE'] for s in stations)
    latest=dt.date(2026,4,30)
    probes=[]
    for a,b in months(dt.date(2026,5,1),TODAY-dt.timedelta(days=1)):
        path=S/f'airkorea_availability_{a:%Y%m}.xls'
        rows=air_download(a,b,path,codes)
        days=sorted(set(str(r[0])[:10] for r in rows))
        nonempty=sum(str(r[9]).strip() not in ('','-999','-') for r in rows)
        probes.append({'start':str(a),'end':str(b),'rows':len(rows),'pm25_nonempty':nonempty,'first':days[0] if days else None,'last':days[-1] if days else None})
        log('outdoor_availability',**probes[-1])
        if days and nonempty:latest=max(latest,dt.date.fromisoformat(days[-1]))
        time.sleep(.2)
    a=max(START,min(dt.date.fromisoformat(x['first_date']) for x in inventory))
    b=min(latest,max(dt.date.fromisoformat(x['last_date']) for x in inventory))
    available_months=set(m for x in inventory for m in x['months'])
    selected=[s.strftime('%Y-%m') for s,e in months(a,b) if s.strftime('%Y-%m') in available_months]
    excluded=[s.strftime('%Y-%m') for s,e in months(a,b) if s.strftime('%Y-%m') not in available_months]
    plan={'start':str(a),'end':str(b),'months':selected,'excluded_months_without_ridership_file':excluded,'timezone':'Asia/Seoul','inair_ui_earliest':'2021-04-01','outdoor_latest_verified':str(latest),'ridership_latest_in_selected_files':max(x['last_date'] for x in inventory),'outdoor_network':'3 (urban ambient)','outdoor_stations':stations,'outdoor_later_month_probes':probes,'note':'Dataset-level date overlap; individual stations may have missing or unavailable months. 2025/2026 outdoor values are marked provisional by provider.'}
    (ROOT/'collection_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    log('period_confirmed',start=str(a),end=str(b))
    return plan

def outdoors(plan):
    p=ROOT/'outdoor_air'/'raw';p.mkdir(parents=True,exist_ok=True)
    codes=','.join(s['STATION_CODE'] for s in plan['outdoor_stations'])
    a,b=map(dt.date.fromisoformat,[plan['start'],plan['end']]);failed=[]
    for start,end in selected_months(plan):
        dest=p/f'daegu_urban_{start:%Y%m}.xls'
        try:
            rows=air_download(start,end,dest,codes)
            log('outdoor_month',month=f'{start:%Y-%m}',rows=len(rows),pm25_nonempty=sum(str(r[9]).strip() not in ('','-999','-') for r in rows))
        except Exception as e:
            failed.append({'month':f'{start:%Y-%m}','error':str(e)});log('outdoor_failed',**failed[-1])
        time.sleep(.2)
    (ROOT/'outdoor_air'/'failed.json').write_text(json.dumps(failed,ensure_ascii=False,indent=2),encoding='utf-8')

def indoors(plan):
    p=ROOT/'subway_air'/'raw';p.mkdir(parents=True,exist_ok=True)
    live=json.loads((S/'inair_stations_live.json').read_bytes())
    stations=[s for s in live if (s.get('mng_adres') or '').startswith('대구광역시') and s.get('subway') in ('1호선','2호선')]
    (ROOT/'subway_air'/'stations.json').write_text(json.dumps(stations,ensure_ascii=False,indent=2),encoding='utf-8')
    if len(set(s['loc_code'] for s in stations))!=len(stations):raise ValueError('Duplicate station codes')
    a,b=map(dt.date.fromisoformat,[plan['start'],plan['end']]);failed=[];count=0
    def download(job):
            s,start,end=job
            code=s['loc_code'];dest=p/code/f'{start:%Y%m}.json.gz';dest.parent.mkdir(exist_ok=True)
            try:
                if dest.exists():
                    with gzip.open(dest,'rt',encoding='utf-8') as f:rows=json.load(f)
                else:
                    rows=json.loads(get('https://www.inair.or.kr/info/main/selectDetailExcel.do',{'view_start_date':start.strftime('%Y%m%d')+'00','view_end_date':end.strftime('%Y%m%d')+'23','loc_code':code}))
                    if not isinstance(rows,list):raise ValueError('Indoor response is not a list')
                    lo=str(start)+':00';hi=str(end)+':23'
                    if any(not lo<=r['ymdh']<=hi for r in rows):raise ValueError('Indoor timestamp outside requested range')
                    if len(set(r['ymdh'] for r in rows))!=len(rows):raise ValueError('Duplicate indoor timestamps')
                    if any(r.get('item_name')!='초미세먼지(PM2.5)' for r in rows):raise ValueError('Unexpected indoor pollutant')
                    temp=dest.with_suffix('.tmp')
                    with gzip.open(temp,'wt',encoding='utf-8') as f:json.dump(rows,f,ensure_ascii=False,separators=(',',':'))
                    temp.replace(dest)
                    time.sleep(.5)
                return None
            except Exception as e:
                return {'station_code':code,'month':f'{start:%Y-%m}','error':str(e)}
    # At most four requests in flight; a pause follows each successful download.
    with ThreadPoolExecutor(max_workers=4) as pool:
        for start,end in selected_months(plan):
            for error in pool.map(download,[(s,start,end) for s in stations]):
                if error:failed.append(error);log('indoor_failed',**error)
                else:count+=1
            log('indoor_month_complete',month=f'{start:%Y-%m}',completed_station_months=count,failed=len(failed),expected_stations=len(stations))
    (ROOT/'subway_air'/'failed.json').write_text(json.dumps(failed,ensure_ascii=False,indent=2),encoding='utf-8')
    log('download_complete',station_months=count,failures=len(failed))

if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'all'
    if mode=='period':establish_period()
    else:
        plan=json.loads((ROOT/'collection_plan.json').read_text(encoding='utf-8'))
        if mode in ('outdoor','all'):outdoors(plan)
        if mode in ('indoor','all'):indoors(plan)
