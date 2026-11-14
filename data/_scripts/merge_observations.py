"""Left-join observations using the user's approved same-label convention."""
from pathlib import Path
import csv,json,sqlite3,datetime as dt,functools,collections,hashlib,time,math

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'merged';OUT.mkdir(exist_ok=True)
WORK=ROOT/'_work';WORK.mkdir(exist_ok=True)
def read(p):
 with p.open(encoding='utf-8-sig',newline='') as f:yield from csv.DictReader(f)
cross={r['indoor_station_code']:r for r in read(ROOT/'mapping/station_crosswalk.csv')}
spatial={r['indoor_station_code']:r for r in read(ROOT/'mapping/station_outdoor_crosswalk_initial.csv')}
selected={(r['ridership_line'],r['ridership_station_code']) for r in cross.values()}
def numeric(s):
 try:
  n=float(s)
  return n if math.isfinite(n) and n>=0 else None
 except (ValueError,TypeError):return None
def integer(s):
 try:return int(s)
 except (ValueError,TypeError):return None

db=sqlite3.connect(WORK/'merge_inputs.sqlite3');db.execute('PRAGMA cache_size=-65536');db.execute('PRAGMA mmap_size=134217728');db.execute('PRAGMA journal_mode=WAL')
db.execute('CREATE TABLE IF NOT EXISTS build_info(key TEXT PRIMARY KEY,value TEXT)')
inputs=sorted(list((ROOT/'outdoor_air/prepared').glob('*.csv'))+list((ROOT/'ridership/prepared').glob('*.csv')))
signature=hashlib.sha256(json.dumps([(str(p.relative_to(ROOT)),p.stat().st_size,p.stat().st_mtime_ns) for p in inputs]).encode()).hexdigest()
cached=db.execute("SELECT value FROM build_info WHERE key='imports_complete_v1'").fetchone()
if not cached or json.loads(cached[0]).get('source_signature')!=signature:
 db.execute('DROP TABLE IF EXISTS outdoor');db.execute('DROP TABLE IF EXISTS riders')
 db.execute('CREATE TABLE outdoor(code TEXT,t TEXT,raw_time TEXT,pm25 TEXT,pm10 TEXT,so2 TEXT,co TEXT,o3 TEXT,no2 TEXT,source TEXT,PRIMARY KEY(code,t)) WITHOUT ROWID')
 db.execute('CREATE TABLE riders(line TEXT,code TEXT,date TEXT,direction TEXT,hours TEXT,source TEXT,PRIMARY KEY(line,code,date,direction)) WITHOUT ROWID')
 nout=nrid=0
 for f in sorted((ROOT/'outdoor_air/prepared').glob('*.csv')):
  batch=[]
  for r in read(f):
   h=int(r['hour_ending']);assert 1<=h<=24
   if h==24:key=(dt.date.fromisoformat(r['date'])+dt.timedelta(days=1)).isoformat()+'T00:00'
   else:key=f"{r['date']}T{h:02}:00"
   batch.append((r['station_code'],key,r['source_date_hour'],r['pm25_raw'],r['pm10_raw'],r['so2_raw'],r['co_raw'],r['o3_raw'],r['no2_raw'],r['source_file']))
   if len(batch)==10000:db.executemany('INSERT INTO outdoor VALUES(?,?,?,?,?,?,?,?,?,?)',batch);nout+=len(batch);batch=[]
  if batch:db.executemany('INSERT INTO outdoor VALUES(?,?,?,?,?,?,?,?,?,?)',batch);nout+=len(batch)
  db.commit();print('IMPORT_OUTDOOR',f.name,nout,flush=True)
 for f in sorted((ROOT/'ridership/prepared').glob('*.csv')):
  batch=[]
  for r in read(f):
   if (r['line'],r['station_code']) not in selected:continue
   assert r['direction'] in ('승차','하차')
   values=[integer(r[f'h{h:02}_{h+1:02}']) for h in range(5,24)]
   batch.append((r['line'],r['station_code'],r['date'],r['direction'],json.dumps(values,separators=(',',':')),r['source_file']))
  db.executemany('INSERT INTO riders VALUES(?,?,?,?,?,?)',batch);nrid+=len(batch);db.commit();print('IMPORT_RIDERSHIP',f.name,nrid,flush=True)
 db.execute("INSERT OR REPLACE INTO build_info VALUES('imports_complete_v1',?)",(json.dumps({'outdoor':nout,'ridership':nrid,'source_signature':signature}),));db.commit()

@functools.lru_cache(maxsize=4096)
def daily(line,code,date):
 return {direction:json.loads(values) for direction,values in db.execute('SELECT direction,hours FROM riders WHERE line=? AND code=? AND date=?',(line,code,date))}
@functools.lru_cache(maxsize=32768)
def outside(code,key):
 return db.execute('SELECT raw_time,pm25,pm10,so2,co,o3,no2 FROM outdoor WHERE code=? AND t=?',(code,key)).fetchone()

fields=['analysis_station_id','indoor_station_code','ridership_station_code','line','station_name','date','hour','time_key','indoor_time_raw','indoor_pm25_raw','indoor_pm25','indoor_status_raw','indoor_quality_flag','boarding','alighting','board_alight_count','ridership_match_status','outdoor_station_code','outdoor_station_name','outdoor_distance_km','outdoor_time_raw','outdoor_pm25_raw','outdoor_pm25','outdoor_pm10','outdoor_so2','outdoor_co','outdoor_o3','outdoor_no2','outdoor_match_status','time_rule_id']
year_stats=[]
for source in sorted((ROOT/'subway_air/prepared').glob('*.csv')):
 year=source.stem[-4:];dest=OUT/f'merged_hourly_{year}.csv';temp=dest.with_suffix('.tmp');n=0;rc=collections.Counter();oc=collections.Counter();qc=collections.Counter();stations=set();valid_indoor=valid_outdoor=both_values=0
 with temp.open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.writer(f);writer.writerow(fields)
  for r in read(source):
   c=cross[r['station_code']];m=spatial[r['station_code']];label=r['date_hour_label'];date=label[:10];h=int(label[-2:]);assert 0<=h<=23
   key=f'{date}T{h:02}:00';d=daily(c['ridership_line'],c['ridership_station_code'],date)
   if h<5:b=a=None;rs='not_in_source_hours'
   else:
    b=d.get('승차',[None]*19)[h-5];a=d.get('하차',[None]*19)[h-5]
    rs='matched' if b is not None and a is not None else ('both_missing' if b is None and a is None else ('boarding_missing' if b is None else 'alighting_missing'))
   rid_sum=b+a if b is not None and a is not None else None
   val=numeric(r['pm25_raw']);status=r['status_raw'];quality='missing_or_invalid_value' if val is None else ('status_requires_review' if status.strip() else 'status_blank_unverified')
   code=m['outdoor_station_code'];o=outside(code,key) if code else None
   if not code:os='station_coordinate_review_required'
   elif o is None:os='selected_station_time_absent'
   elif numeric(o[1]) is None:os='matched_pm25_missing_or_invalid'
   else:os='matched_pm25_present'
   oval=numeric(o[1]) if o else None
   outvals=[o[0],o[1]]+[numeric(x) for x in o[1:]] if o else ['']*8
   writer.writerow([c['analysis_station_id'],r['station_code'],c['ridership_station_code'],r['line'],r['station_name'],date,h,key,label,r['pm25_raw'],val,status,quality,b,a,rid_sum,rs,code,m['outdoor_station_name'],m['distance_km']]+outvals+[os,'same_label_v1'])
   n+=1;rc[rs]+=1;oc[os]+=1;qc[quality]+=1;stations.add(r['station_code']);valid_indoor+=val is not None;valid_outdoor+=oval is not None;both_values+=val is not None and oval is not None
 temp.replace(dest)
 rec={'year':year,'output_file':dest.name,'rows':n,'stations_with_rows':len(stations),'indoor_value_present':valid_indoor,'outdoor_pm25_present':valid_outdoor,'both_pm25_present':both_values,'ridership_status_counts':dict(rc),'outdoor_status_counts':dict(oc),'indoor_quality_counts':dict(qc),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
 year_stats.append(rec);print('MERGED',json.dumps(rec,ensure_ascii=True),flush=True)

expected=json.loads((ROOT/'collection_summary.json').read_text(encoding='utf-8'))['indoor']['rows_per_year']
for r in year_stats:assert r['rows']==expected[r['year']],r
summary={'created':'2026-11-14','base':'all existing indoor observation rows; left join; no imputation or row dropping','time_rule_id':'same_label_v1','time_definition_status':'unverified averaging anchor; same calendar labels explicitly authorized by user','hour_24_rule':'outdoor date 24 -> next calendar date 00; no minus-one-hour adjustment','ridership_rule':'indoor HH label -> hHH_HH+1 where source exists; 00-04 left missing','outdoor_rule':'fixed nearest of 20 collected urban stations; 55 matched, 2 coordinate-format review; no missing-data station switching','indoor_coordinate_source':'https://data.kric.go.kr/rips/M_01_01/detail.do?id=213','outdoor_coordinate_source':'https://www.data.go.kr/data/15150453/fileData.do','coordinate_limitations':'station representative points; snapshots 2026-02-05 and 2024-12-31; historical relocation/environment/datum not verified','total_rows':sum(r['rows'] for r in year_stats),'spatially_assigned_stations':sum(bool(r['outdoor_station_code']) for r in spatial.values()),'unassigned_station_codes':[k for k,v in spatial.items() if not v['outdoor_station_code']],'years':year_stats,'original_data_modified':False}
(OUT/'merge_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
with (OUT/'columns.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['column']);w.writerows([[c] for c in fields])
db.close();print('COMPLETE',summary['total_rows'],flush=True)
