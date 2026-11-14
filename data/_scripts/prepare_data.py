"""Export source-faithful, common-month CSVs and coverage checks; no imputation."""
import pathlib,json,csv,gzip,datetime as dt,collections,sys,hashlib
from collect_probe import ROOT
from collect_support import decode_csv
sys.path.insert(0,str(ROOT/'_tools'))
import xlrd

def write_csv(path,fields,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def ridership(plan):
    inventory=json.loads((ROOT/'ridership'/'inventory.json').read_text(encoding='utf-8'))
    results=[];issues=[];aliases=[]
    fields=['date','line','station_code','station_name','direction']+[f'h{h:02d}_{h+1:02d}' for h in range(5,24)]+['daily_total','source_file']
    for meta in inventory:
        raw=ROOT/meta['file'];rows,_=decode_csv(raw.read_bytes());year=meta['year'];records={};duplicates=0;conflicts=collections.defaultdict(list)
        for ix,r in enumerate(rows[1:],2):
            if len(r)!=25:
                issues.append({'file':meta['file'],'row':ix,'kind':'unexpected_columns','detail':len(r)});continue
            date=f'{year}-{int(r[0]):02d}-{int(r[1]):02d}'
            dt.date.fromisoformat(date)
            if not(plan['start']<=date<=plan['end']) or date[:7] not in plan['months']:continue
            code=r[2].strip();direction=r[4].strip();key=(date,code,direction)
            values=[int(x.replace(',','')) if x.strip() else None for x in r[5:]]
            rec=dict(zip(fields,[date,code[0],code,r[3].strip(),direction]+values+[raw.name]))
            if key in records:
                old=records[key]
                if [old[k] for k in fields[5:-1]]==values:
                    duplicates+=1
                    if old['station_name']!=rec['station_name']:aliases.append({'date':date,'station_code':code,'old_name':old['station_name'],'new_name':rec['station_name']})
                    records[key]=rec
                else:
                    conflicts[key].extend([old,rec]);issues.append({'file':meta['file'],'row':ix,'kind':'conflicting_duplicate','detail':str(key)})
            else:records[key]=rec
            if all(x is not None for x in values) and sum(values[:-1])!=values[-1]:issues.append({'file':meta['file'],'row':ix,'kind':'daily_total_mismatch','detail':str(key)})
        for key in conflicts:records.pop(key,None)
        if conflicts:write_csv(ROOT/'ridership'/'review'/f'conflicting_rows_{year}.csv',fields,[r for rows in conflicts.values() for r in rows])
        output=ROOT/'ridership'/'prepared'/f'ridership_{year}.csv'
        write_csv(output,fields,[records[k] for k in sorted(records)])
        dates=sorted(set(k[0] for k in records));results.append({'year':year,'rows':len(records),'first_date':dates[0],'last_date':dates[-1],'days':len(dates),'duplicate_rows_removed':duplicates,'conflicting_keys_excluded':len(conflicts)})
    write_csv(ROOT/'ridership'/'review'/'issues.csv',['file','row','kind','detail'],issues)
    write_csv(ROOT/'ridership'/'review'/'station_name_aliases.csv',['date','station_code','old_name','new_name'],aliases)
    return results

def outdoors(plan):
    fields=['source_date_hour','date','hour_ending','region_raw','station_name','station_code','so2_raw','co_raw','o3_raw','no2_raw','pm10_raw','pm25_raw','source_file']
    summaries=[];seen=set();year_files={};writers={}
    try:
        for p in sorted((ROOT/'outdoor_air'/'raw').glob('*.xls')):
            sh=xlrd.open_workbook(str(p)).sheet_by_index(0);month=p.stem[-6:];month=month[:4]+'-'+month[4:];count=0;valid=0;stations=set()
            if month not in plan['months']:continue
            for i in range(1,sh.nrows):
                r=[str(x) for x in sh.row_values(i)]
                if not r[0].strip():continue
                date=r[0][:10];hour=int(r[0][-2:]);code=r[3];year=date[:4]
                if not plan['start']<=date<=plan['end'] or date[:7] not in plan['months']:raise ValueError('Outdoor date outside common months')
                key=(r[0],code)
                if key in seen:raise ValueError(f'Duplicate outdoor key {key}')
                seen.add(key)
                if year not in writers:
                    dest=ROOT/'outdoor_air'/'prepared'/f'outdoor_air_{year}.csv';dest.parent.mkdir(parents=True,exist_ok=True)
                    year_files[year]=dest.open('w',encoding='utf-8-sig',newline='');writers[year]=csv.writer(year_files[year]);writers[year].writerow(fields)
                writers[year].writerow([r[0],date,hour]+r[1:]+[p.name]);count+=1;stations.add(code)
                if r[9].strip() not in ('','-999','-'):valid+=1
            summaries.append({'month':month,'rows':count,'pm25_nonempty':valid,'stations_with_rows':len(stations)})
    finally:
        for f in year_files.values():f.close()
    write_csv(ROOT/'outdoor_air'/'coverage_monthly.csv',['month','rows','pm25_nonempty','stations_with_rows'],summaries)
    return summaries

def indoors(plan):
    stations=json.loads((ROOT/'subway_air'/'stations.json').read_text(encoding='utf-8'));lookup={s['loc_code']:s for s in stations}
    write_csv(ROOT/'subway_air'/'stations.csv',['station_code','line','station_name','location','address'],[dict(zip(['station_code','line','station_name','location','address'],[s['loc_code'],s['subway'],s['loc_nm'],s['loc_name'],s['mng_adres']])) for s in stations])
    fields=['station_code','line','station_name','date_hour_label','pm25_raw','status_raw','pollutant','source_file'];summaries=[];year_files={};writers={};counts=collections.Counter()
    try:
        for p in sorted((ROOT/'subway_air'/'raw').glob('*/*.json.gz')):
            code=p.parent.name;s=lookup[code];month=p.name[:6];month=month[:4]+'-'+month[4:]
            if month not in plan['months']:continue
            with gzip.open(p,'rt',encoding='utf-8') as f:rows=json.load(f)
            nonempty=0;statuses=collections.Counter();seen=set()
            for r in sorted(rows,key=lambda r:r['ymdh']):
                label=r['ymdh'];date=label[:10];year=date[:4]
                if not plan['start']<=date<=plan['end'] or date[:7] not in plan['months']:raise ValueError('Indoor date outside common months')
                if label in seen:raise ValueError('Indoor duplicate timestamp')
                seen.add(label);value=r.get('val1');status=r.get('stat1');statuses[str(status)]+=1
                if value is not None and str(value).strip():nonempty+=1
                if year not in writers:
                    dest=ROOT/'subway_air'/'prepared'/f'subway_air_{year}.csv';dest.parent.mkdir(parents=True,exist_ok=True)
                    year_files[year]=dest.open('w',encoding='utf-8-sig',newline='');writers[year]=csv.writer(year_files[year]);writers[year].writerow(fields)
                writers[year].writerow([code,s['subway'],s['loc_nm'],label,value,status,r.get('item_name'),str(p.relative_to(ROOT))]);counts[year]+=1
            day0=dt.date.fromisoformat(month+'-01');day1=(day0.replace(day=28)+dt.timedelta(days=4)).replace(day=1)
            expected=(min(day1-dt.timedelta(days=1),dt.date.fromisoformat(plan['end']))-max(day0,dt.date.fromisoformat(plan['start']))).days*24+24
            summaries.append({'station_code':code,'line':s['subway'],'station_name':s['loc_nm'],'month':month,'expected_hours':expected,'returned_rows':len(rows),'pm25_nonempty':nonempty,'missing_values_or_hours':expected-nonempty,'duplicate_timestamps':len(rows)-len(seen),'status_counts':json.dumps(dict(statuses),ensure_ascii=False)})
    finally:
        for f in year_files.values():f.close()
    fields2=['station_code','line','station_name','month','expected_hours','returned_rows','pm25_nonempty','missing_values_or_hours','duplicate_timestamps','status_counts']
    write_csv(ROOT/'subway_air'/'coverage_station_month.csv',fields2,summaries)
    totals={'requested_station_months':len(stations)*len(plan['months']),'downloaded_station_months':len(summaries),'returned_rows':sum(s['returned_rows'] for s in summaries),'pm25_nonempty':sum(s['pm25_nonempty'] for s in summaries),'empty_station_months':sum(s['pm25_nonempty']==0 for s in summaries),'rows_per_year':dict(counts)}
    return totals

def main():
    plan=json.loads((ROOT/'collection_plan.json').read_text(encoding='utf-8'))
    stations=json.loads((ROOT/'subway_air'/'stations.json').read_text(encoding='utf-8'))
    missing=[]
    for month in plan['months']:
        if not (ROOT/'outdoor_air'/'raw'/f"daegu_urban_{month.replace('-','')}.xls").exists():missing.append('outdoor:'+month)
        for station in stations:
            if not (ROOT/'subway_air'/'raw'/station['loc_code']/f"{month.replace('-','')}.json.gz").exists():missing.append(station['loc_code']+':'+month)
    if missing:raise RuntimeError(f'Collection incomplete: {len(missing)} missing station-month files; first examples: {missing[:5]}')
    summary={'period':{'start':plan['start'],'end':plan['end'],'months':len(plan['months']),'excluded_months':plan['excluded_months_without_ridership_file']}}
    summary['ridership']=ridership(plan);print('RIDERSHIP',json.dumps(summary['ridership']),flush=True)
    summary['outdoor']=outdoors(plan);print('OUTDOOR',sum(x['rows'] for x in summary['outdoor']),flush=True)
    summary['indoor']=indoors(plan);print('INDOOR',json.dumps(summary['indoor']),flush=True)
    (ROOT/'collection_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    files=[]
    for area in ['ridership','outdoor_air','subway_air']:
        for p in sorted((ROOT/area).rglob('*')):
            if p.is_file():files.append({'file':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    write_csv(ROOT/'file_manifest.csv',['file','bytes','sha256'],files)
    print('TOTAL_BYTES',sum(x['bytes'] for x in files),flush=True)

if __name__=='__main__':main()
