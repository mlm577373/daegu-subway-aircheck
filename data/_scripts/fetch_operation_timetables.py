"""Fetch public historical timetable evidence with provenance; no credentials."""
from pathlib import Path
import urllib.request,urllib.parse,json,hashlib
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'data/timetable_change/sources';OUT.mkdir(parents=True,exist_ok=True)
requests=[
('line1_pre_archive.csv','https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000002831458&fileDetailSn=1',None),
('line2_pre_archive.csv','https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000002831517&fileDetailSn=1',None),
('line1_post_20241007.xlsx','https://www.dtro.or.kr/icms/cmm/fms/FileDown.do?atchFileId=FILE_000000000041317x2moneYf&fileSn=1',None),
('line2_post_20241007.xlsx','https://www.dtro.or.kr/icms/cmm/fms/FileDown.do?atchFileId=FILE_000000000041317x2moneYf&fileSn=2',None),
('line1_2022_detail.html','https://www.data.go.kr/tcs/dss/selectDpkDetailInfo.do',{'publicDataDetailPk':'uddi:c1c2a479-d106-4864-9494-a6147017bd60','publicDataHistSn':'3'}),
('line2_2022_detail.html','https://www.data.go.kr/tcs/dss/selectDpkDetailInfo.do',{'publicDataDetailPk':'uddi:f718c8f3-4b0c-4a4d-a623-de26827374a6','publicDataHistSn':'3'}),
('official_notice_74097.html','https://www.dtro.or.kr/index.do?menu_id=00000289&menu_link=icms/bbs/selectBoardArticle.do?bbsId%3DBBS_00253&nttId=74097',None)
]
def fetch(item):
    name,url,params=item;p=OUT/name
    try:
        if p.exists() and p.stat().st_size>100:return {'file':name,'url':url,'params':params,'cached':True,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        body=urllib.parse.urlencode(params).encode() if params else None
        req=urllib.request.Request(url,data=body,headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.data.go.kr/','X-Requested-With':'XMLHttpRequest'})
        with urllib.request.urlopen(req,timeout=25) as r:b=r.read();actual=r.url;mime=r.headers.get('Content-Type')
        if name.endswith('.xlsx') and not b.startswith(b'PK'):raise ValueError('Not an XLSX ZIP file')
        p.write_bytes(b)
        return {'file':name,'url':url,'params':params,'actual_url':actual,'bytes':len(b),'mime':mime,'sha256':hashlib.sha256(b).hexdigest()}
    except Exception as e:return {'file':name,'url':url,'params':params,'error':str(e)}
if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(fetch,requests))
    (OUT/'fetch_manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    for r in rows:print(json.dumps({k:v for k,v in r.items() if k not in ['url','actual_url']},ensure_ascii=True),flush=True)
