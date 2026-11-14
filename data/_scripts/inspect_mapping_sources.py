"""Read a few official metadata pages; do not download observation datasets."""
from pathlib import Path
import urllib.request,json,re

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'mapping'/'sources';OUT.mkdir(parents=True,exist_ok=True)
urls={
 'kric_station_location':'https://data.kric.go.kr/rips/M_01_01/detail.do?id=213',
 'inair_map':'https://www.inair.or.kr/info/map.html',
 'airkorea_station_info':'https://www.airkorea.or.kr/web/stationInfo?pMENU_NO=93',
}
records=[]
for name,url in urls.items():
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as r:
   b=r.read(2000000);status=r.status;final=r.url
  (OUT/(name+'.html')).write_bytes(b)
  records.append({'source':name,'url':url,'http_status':status,'bytes':len(b),'final_url':final})
  print(name,status,len(b),flush=True)
 except Exception as e:
  records.append({'source':name,'url':url,'error':str(e)})
  print(name,type(e).__name__,str(e),flush=True)
(OUT/'metadata_page_checks.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
