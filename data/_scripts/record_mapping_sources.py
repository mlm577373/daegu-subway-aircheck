from pathlib import Path
import re,html,json,csv
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'mapping'
def save(name,rows):
 with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

rows=[
 {'dataset':'subway_station_coordinates','official_url':'https://data.kric.go.kr/rips/M_01_01/detail.do?id=213','availability':'live_metadata_and_xlsx_download_link_confirmed','advertised_fields':'철도운영기관명;선명;역명;경도;위도','download_url':'https://data.kric.go.kr/rips/dataset/download.file?type=filedata&id=213&operation=1','coverage_status':'57 target stations and coordinate CRS not file-verified','file_downloaded':'no','next_check':'download with approval; check CRS, 57 station matches, aliases and historical relocations'},
 {'dataset':'outdoor_station_metadata','official_url':'https://www.airkorea.or.kr/web/stationInfo?pMENU_NO=93','availability':'live_address_operator_installation_year_page_confirmed','advertised_fields':'측정소명;주소;운영기관;설치년도;측정항목','download_url':'','coverage_status':'current names only; coordinate and relocation history not verified','file_downloaded':'metadata HTML only','next_check':'obtain official coordinates and dated location history; installation year is not operation continuity'},
 {'dataset':'line2_exit_coordinates_fallback','official_url':'https://www.data.go.kr/data/15133920/fileData.do','availability':'official_dataset_description_confirmed','advertised_fields':'역명;출구번호;위도;경도','download_url':'','coverage_status':'line 2 only; exit not platform or intake location; not file-verified','file_downloaded':'no','next_check':'fallback only; choose a representative station point explicitly'},
]
save('location_source_inventory.csv',rows)
page=(OUT/'sources'/'airkorea_station_info.html').read_text(encoding='utf-8')
blocks=re.findall(r'<li id="liMapAddr\d+">(.*?)</li>',page,re.S)
def plain(s):return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',s))).strip()
targets=json.loads((ROOT/'_sources'/'airkorea_stations.json').read_text(encoding='utf-8'))['stationList']
metadata=[]
for target in targets:
 candidates=[]
 for block in blocks:
  m=re.search(r'<span class="cen">(.*?)</span></div>\s*<div>(.*?)<button',block,re.S)
  details=re.findall(r'<span class="contMapAddrDetailD">(.*?)</span>',block,re.S)
  if m and plain(m[1])==target['NAME'] and len(details)>=3 and '대구' in plain(details[0]):
   candidates.append((plain(m[2]),plain(details[0]),plain(details[1]),plain(details[2])))
 if len(candidates)==1:
  address,operator,year,items=candidates[0];status='unique_name_and_operator_candidate'
 else:address=operator=year=items='';status=f'review_required_{len(candidates)}_candidates'
 metadata.append({'outdoor_station_code':target['STATION_CODE'],'outdoor_station_name':target['NAME'],'address_current':address,'operator':operator,'installation_year_advertised':year,'items_advertised':items,'latitude':'','longitude':'','verification_status':status,'source_url':rows[1]['official_url'],'checked_date':'2026-11-14','note':'current page metadata; no station assignment or historical-location assertion'})
save('outdoor_station_metadata_candidates.csv',metadata)
print('OUTDOOR_METADATA',len(metadata),'unambiguous_candidates',sum(r['verification_status']=='unique_name_and_operator_candidate' for r in metadata))
