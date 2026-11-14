import urllib.request, urllib.parse, http.cookiejar, http.client, pathlib, json, re, time, threading
ROOT=pathlib.Path(__file__).resolve().parent
if ROOT.name=='_scripts':ROOT=ROOT.parent
S=ROOT/'_sources'
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
connections=threading.local()
def fetch(url, data=None, timeout=90):
    headers={'User-Agent':'Mozilla/5.0','Referer':url.split('/web/')[0]+'/web/last_amb_hour_data?pMENU_NO=123' if 'airkorea' in url else ('https://www.inair.or.kr/info/excel.html' if 'inair' in url else 'https://www.data.go.kr/data/15002503/fileData.do'),'X-Requested-With':'XMLHttpRequest'}
    if url.startswith('https://www.inair.or.kr/'):
        inair_connection=getattr(connections,'inair',None)
        if inair_connection is None:
            inair_connection=http.client.HTTPSConnection('www.inair.or.kr',timeout=timeout)
            connections.inair=inair_connection
        headers['Content-Type']='application/x-www-form-urlencoded; charset=UTF-8'
        try:
            inair_connection.request('GET' if data is None else 'POST',url.split('www.inair.or.kr',1)[1],None if data is None else urllib.parse.urlencode(data),headers)
            response=inair_connection.getresponse();b=response.read();h=dict(response.headers)
            if response.status!=200:raise RuntimeError(f'HTTP {response.status}')
            return b,h
        except Exception:
            inair_connection.close();connections.inair=None;raise
    r=opener.open(urllib.request.Request(url,data=None if data is None else urllib.parse.urlencode(data).encode(),headers=headers),timeout=timeout)
    return r.read(),dict(r.headers)
def save(name,url,data=None):
    b,h=fetch(url,data);(S/name).write_bytes(b);print(name,len(b),h.get('Content-Type'),flush=True);return b
if __name__=='__main__':
    hist=(S/'ridership_history.html').read_text(encoding='utf-8')
    rows=re.findall(r'class="openFileDetailPopup open-modal" data-public-pk="([^"]+)"\s+data-public-detail-sn="([^"]+)">\s*([^<]+)',hist)
    rows=[{'pk':a,'sn':b,'name':c.strip()} for a,b,c in rows]
    (S/'ridership_history_index.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    for suffix in ['20210630','20260430']:
        x=next(x for x in rows if x['name'].endswith(suffix))
        save('ridership_detail_'+suffix+'.html','https://www.data.go.kr/tcs/dss/selectDpkDetailInfo.do',{'publicDataDetailPk':x['pk'],'publicDataHistSn':x['sn']})
    save('airkorea_stations.json','https://www.airkorea.or.kr/web/statistic/getStationLIst?mang_code=3&district=053')
    save('inair_stations_live.json','https://www.inair.or.kr/info/main/selectListExcel.do',{'name':''})
    for start,end in [('2021040100','2021040123'),('2026111200','2026111223')]:
        t=time.monotonic();save('inair_probe_'+start+'.json','https://www.inair.or.kr/info/main/selectDetailExcel.do',{'view_start_date':start,'view_end_date':end,'loc_code':'A1116C'});print('elapsed',time.monotonic()-t,flush=True)
