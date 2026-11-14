from collect_probe import ROOT
import http.client,urllib.parse,gzip,json,time
t=time.monotonic();c=http.client.HTTPSConnection('www.inair.or.kr',timeout=60)
c.request('POST','/info/main/selectDetailExcel.do',urllib.parse.urlencode({'view_start_date':'2026040100','view_end_date':'2026043023','loc_code':'A1116C'}),{'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8','Referer':'https://www.inair.or.kr/info/excel.html','X-Requested-With':'XMLHttpRequest','Accept-Encoding':'gzip','User-Agent':'Mozilla/5.0'})
r=c.getresponse();b=r.read();print('status',r.status,'encoding',r.getheader('Content-Encoding'),'wire_bytes',len(b),'seconds',time.monotonic()-t)
if r.getheader('Content-Encoding')=='gzip':b=gzip.decompress(b)
rows=json.loads(b)
if len(rows)!=720 or any(not '2026-04-01:00'<=x['ymdh']<='2026-04-30:23' for x in rows):raise ValueError('Unexpected response')
p=ROOT/'subway_air'/'raw'/'A1116C'/'202604.json.gz';p.parent.mkdir(exist_ok=True)
with gzip.open(p,'wt',encoding='utf-8') as f:json.dump(rows,f,ensure_ascii=False,separators=(',',':'))
print('saved',len(rows))
