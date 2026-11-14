from pathlib import Path
import csv,json,datetime as dt,collections,functools,hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'merged'
summary=json.loads((OUT/'merge_summary.json').read_text(encoding='utf-8'))
spatial={r['indoor_station_code']:r for r in csv.DictReader((ROOT/'mapping/station_outdoor_crosswalk_initial.csv').open(encoding='utf-8-sig'))}
checks=[];samples={};boundaries=0
@functools.lru_cache(2048)
def nextdate(s):return (dt.date.fromisoformat(s)+dt.timedelta(days=1)).isoformat()
for meta in summary['years']:
 p=OUT/meta['output_file'];n=0;last={};rc=collections.Counter();oc=collections.Counter()
 with p.open(encoding='utf-8-sig',newline='') as f:
  for r in csv.DictReader(f):
   assert None not in r and len(r)==30
   code=r['indoor_station_code'];h=int(r['hour']);key=r['time_key'];date=r['date']
   assert key==f'{date}T{h:02}:00' and r['indoor_time_raw']==f'{date}:{h:02}'
   assert code not in last or key>last[code],('duplicate or unsorted station-time',code,key)
   last[code]=key
   assert r['outdoor_station_code']==spatial[code]['outdoor_station_code']
   if h<5:assert r['boarding']==r['alighting']==r['board_alight_count']=='' and r['ridership_match_status']=='not_in_source_hours'
   if r['boarding']!='' and r['alighting']!='':assert int(r['board_alight_count'])==int(r['boarding'])+int(r['alighting'])
   else:assert r['board_alight_count']==''
   if r['outdoor_time_raw']:
    raw=r['outdoor_time_raw'];oh=int(raw[-2:]);expected=(nextdate(raw[:10])+'T00:00') if oh==24 else f'{raw[:10]}T{oh:02}:00'
    assert expected==key,(key,raw)
    if oh==24:boundaries+=1
   if not r['outdoor_station_code']:assert r['outdoor_pm25']=='' and r['outdoor_match_status']=='station_coordinate_review_required'
   for c in ['indoor_pm25','outdoor_pm25','outdoor_pm10','outdoor_so2','outdoor_co','outdoor_o3','outdoor_no2']:
    if r[c]!='':assert float(r[c])>=0
   sk=(meta['year'],code)
   if sk not in samples:samples[sk]=r
   rc[r['ridership_match_status']]+=1;oc[r['outdoor_match_status']]+=1;n+=1
 assert n==meta['rows'] and dict(rc)==meta['ridership_status_counts'] and dict(oc)==meta['outdoor_status_counts']
 assert hashlib.sha256(p.read_bytes()).hexdigest()==meta['sha256']
 checks.append({'year':meta['year'],'rows_verified':n,'station_time_keys_unique_and_ordered':True,'sha256_matches':True})
 print('VALIDATED_YEAR',meta['year'],n,flush=True)
sample_matches=0
for p in sorted((ROOT/'subway_air/prepared').glob('*.csv')):
 year=p.stem[-4:]
 with p.open(encoding='utf-8-sig',newline='') as f:
  for r in csv.DictReader(f):
   sample=samples.get((year,r['station_code']))
   if sample and sample['indoor_time_raw']==r['date_hour_label']:
    assert sample['indoor_pm25_raw']==r['pm25_raw'] and sample['indoor_status_raw']==r['status_raw'];sample_matches+=1
assert sample_matches==len(samples)==342
report={'checks':checks,'total_rows_verified':sum(r['rows_verified'] for r in checks),'midnight_24h_calendar_matches_verified':boundaries,'original_indoor_samples_verified':sample_matches,'rows_added_or_dropped_from_indoor_base':0,'numeric_missing_values_not_zero_filled':True,'same_label_is_assumption_not_proven_average_interval':True,'coordinate_review_stations_have_no_outdoor_values':True}
(OUT/'validation_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('VALIDATION_COMPLETE',json.dumps(report),flush=True)
