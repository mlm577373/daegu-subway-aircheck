from pathlib import Path
import csv,json,zipfile,xml.etree.ElementTree as E,re,math
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'mapping';SRC=OUT/'sources'
def readcsv(p,enc='utf-8-sig'):
 with p.open(encoding=enc,newline='') as f:return list(csv.DictReader(f))
def save(name,rows):
 with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def norm(s):
 s=re.sub(r'\([^)]*\)','',s).strip().removesuffix('역')
 return {'대공원':'수성알파시티','신남':'청라언덕'}.get(s,s)
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(SRC/'kric_station_coordinates.xlsx') as z:
 strings=[''.join(x.itertext()) for x in E.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',ns)]
 rows=[]
 for row in E.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//s:sheetData/s:row',ns):
  v={}
  for c in row.findall('s:c',ns):
   x=c.find('s:v',ns);value=x.text if x is not None else ''
   if c.get('t')=='s':value=strings[int(value)]
   v[re.sub(r'\d','',c.get('r'))]=value
  rows.append(v)
stations=[]
for r in rows[1:]:
 stations.append({'operator':r.get('A',''),'line':r.get('B',''),'source_station_name':r.get('C',''),'latitude':float(r['D']),'longitude':float(r['E'])})
save('kric_station_coordinates.csv',stations)
cross=readcsv(OUT/'station_crosswalk.csv');indoor=[]
for r in cross:
 candidates=[s for s in stations if s['line']==r['indoor_line'] and norm(s['source_station_name'])==norm(r['canonical_match_name'])]
 if len(candidates)!=1:raise RuntimeError(f'Coordinate match ambiguous: {r["indoor_station_code"]}: {candidates}')
 s=candidates[0];assert 35<float(s['latitude'])<37 and 127<float(s['longitude'])<130
 indoor.append({'analysis_station_id':r['analysis_station_id'],'indoor_station_code':r['indoor_station_code'],'line':r['indoor_line'],'indoor_station_name':r['indoor_station_name'],'coordinate_station_name':s['source_station_name'],'latitude':s['latitude'],'longitude':s['longitude'],'source':'KRIC id=213; page modified 2026-02-05','coordinate_note':'official station representative decimal-degree coordinates; historical movement and datum details unverified'})
save('indoor_station_coordinates.csv',indoor)
raw=readcsv(SRC/'outdoor_station_coordinates_20241231.csv','cp949')
print('OUTDOOR_HEADER',list(raw[0]),flush=True)
targets=json.loads((ROOT/'_sources/airkorea_stations.json').read_text(encoding='utf-8'))['stationList'];outdoor=[]
for t in targets:
 candidates=[r for r in raw if r['측정소코드'].strip()==t['STATION_CODE']]
 if len(candidates)!=1:raise RuntimeError(f'Outdoor coordinate absent or duplicate: {t}')
 r=candidates[0];lat=float(r['위도']);lon=float(r['경도']);assert 35<lat<37 and 127<lon<130
 outdoor.append({'outdoor_station_code':t['STATION_CODE'],'outdoor_station_name':t['NAME'],'coordinate_source_station_name':r['측정소명'],'network':r['측정소구분'],'address':r['주소'],'latitude':lat,'longitude':lon,'source_snapshot':'2024-12-31','source_dataset':'data.go.kr/15150453','coordinate_note':'historical relocation and datum details unverified'})
save('outdoor_station_coordinates.csv',outdoor)
def distance(a,b):
 y1,y2=map(math.radians,[float(a['latitude']),float(b['latitude'])]);dy=y2-y1;dx=math.radians(float(b['longitude'])-float(a['longitude']))
 return 6371.0088*2*math.asin(min(1,math.sqrt(math.sin(dy/2)**2+math.cos(y1)*math.cos(y2)*math.sin(dx/2)**2)))
mapping=[];issues=[]
for s in indoor:
 ranked=sorted((distance(s,o),o['outdoor_station_code'],o) for o in outdoor)
 d,code,o=ranked[0];d2,code2,o2=ranked[1]
 mapping.append({'analysis_station_id':s['analysis_station_id'],'indoor_station_code':s['indoor_station_code'],'line':s['line'],'indoor_station_name':s['indoor_station_name'],'outdoor_station_code':code,'outdoor_station_name':o['outdoor_station_name'],'distance_km':round(d,4),'second_candidate_code':code2,'second_candidate_name':o2['outdoor_station_name'],'second_distance_km':round(d2,4),'selection_rule':'fixed_nearest_of_20_downloaded_urban_stations_by_haversine','mapping_status':'provisional_distance_only; historical location and environment not reviewed','coordinate_snapshots':'railway page 2026-02-05; ambient 2024-12-31','missing_policy':'no switch when selected station has missing observations'})
 if d>10:
  issues.append({'indoor_station_code':s['indoor_station_code'],'station_name':s['indoor_station_name'],'source_latitude':s['latitude'],'source_longitude':s['longitude'],'rejected_candidate':code,'rejected_distance_km':round(d,4),'issue':'coordinate format review: nearest station over 10 km; packed DMS plausible but not assumed or corrected'})
  mapping[-1].update(outdoor_station_code='',outdoor_station_name='',distance_km='',mapping_status='coordinate_format_review_required; outdoor left blank')
save('station_outdoor_crosswalk_initial.csv',mapping)
save('coordinate_review_required.csv',issues)
print('COORDINATES',len(indoor),len(outdoor),'MAPPED',sum(bool(r['outdoor_station_code']) for r in mapping),'MAX_ACCEPTED_DISTANCE_KM',max(r['distance_km'] for r in mapping if r['distance_km']!=''),'REVIEW',len(issues),flush=True)
