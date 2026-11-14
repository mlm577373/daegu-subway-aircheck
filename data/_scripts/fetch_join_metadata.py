from pathlib import Path
import urllib.request,json
import urllib.parse
import re
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'mapping'/'sources';OUT.mkdir(exist_ok=True)
sources={
 'kric_station_coordinates.xlsx':'https://data.kric.go.kr/rips/dataset/download.file?type=filedata&id=213&operation=1',
 'inair_kakaoMap.js':'https://www.inair.or.kr/info/dist/kakaoMap.js',
}
if __name__=='__main__' and 'outdoor' in __import__('sys').argv:
 def read(url,data=None):
  req=urllib.request.Request(url,data=None if data is None else urllib.parse.urlencode(data).encode(),headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.data.go.kr/data/15150453/fileData.do','X-Requested-With':'XMLHttpRequest'})
  with urllib.request.urlopen(req,timeout=40) as r:return r.read()
 page=read('https://www.data.go.kr/data/15150453/fileData.do');(OUT/'outdoor_coordinate_portal.html').write_bytes(page)
 text=page.decode('utf-8');m=re.search(r"fn_fileDataDown\('15150453',\s*'([^']+)',\s*'([^']*)',\s*'([^']+)'",text)
 if not m:raise RuntimeError('No public download metadata found')
 pk,aid,sn=m.groups()
 info=json.loads(read('https://www.data.go.kr/tcs/dss/selectFileDataDownload.do',{'publicDataPk':'15150453','publicDataDetailPk':pk,'atchFileId':aid,'fileDetailSn':sn,'publicDataTyCode':'PR0051'}))
 if not info.get('status'):raise RuntimeError('Download metadata unavailable')
 aid=info['atchFileId'];sn=info['fileDetailSn']
 limit=json.loads(read('https://www.data.go.kr/cmm/cmm/check-limit.json',{'atchFileId':aid,'fileDetailSn':sn}))
 if limit.get('needCaptcha'):raise RuntimeError('Captcha required; no automated download attempted')
 url='https://www.data.go.kr/cmm/cmm/fileDownload.do?'+urllib.parse.urlencode({'atchFileId':aid,'fileDetailSn':sn})
 b=read(url);(OUT/'outdoor_station_coordinates_20241231.csv').write_bytes(b)
 (OUT/'outdoor_coordinate_download.json').write_text(json.dumps({'source_url':'https://www.data.go.kr/data/15150453/fileData.do','pk':pk,'atchFileId':aid,'fileDetailSn':sn,'bytes':len(b)},ensure_ascii=False,indent=2),encoding='utf-8')
 print('outdoor_coordinates',len(b),b[:50],flush=True)
 __import__('sys').exit(0)
if __name__=='__main__' and 'map' in __import__('sys').argv:
 url='https://www.inair.or.kr/info/main/mainList2.do'
 try:
  req=urllib.request.Request(url,data=b'',headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.inair.or.kr/info/map.html','X-Requested-With':'XMLHttpRequest'})
  with urllib.request.urlopen(req,timeout=40) as r:b=r.read()
  (OUT/'inair_map_metadata.json').write_bytes(b)
  x=json.loads(b);print('map_metadata',len(x),'sample',str(x[0])[:700] if isinstance(x,list) and x else str(x)[:300],flush=True)
 except Exception as e:print(type(e).__name__,str(e),flush=True)
 __import__('sys').exit(0)
records=[]
for name,url in sources.items():
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://data.kric.go.kr/rips/M_01_01/detail.do?id=213' if 'kric' in url else 'https://www.inair.or.kr/info/map.html'}),timeout=40) as r:
   b=r.read();h=dict(r.headers)
  (OUT/name).write_bytes(b);print(name,len(b),b[:12],flush=True)
  records.append({'file':name,'url':url,'bytes':len(b),'headers':h})
 except Exception as e:
  records.append({'file':name,'url':url,'error':str(e)});print(name,type(e).__name__,str(e),flush=True)
(OUT/'join_metadata_fetch.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
