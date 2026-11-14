from collect_probe import *
import csv,io
if __name__=='__main__':
    for suffix in ['20210630','20260430']:
        s=(S/('ridership_detail_'+suffix+'.html')).read_text(encoding='utf-8')
        m=re.search(r"fn_fileDataDown\('15002503', '([^']+)', '([^']+)', '([^']+)', 'csv'",s)
        pk,aid,sn=m.groups()
        b,h=fetch('https://www.data.go.kr/cmm/cmm/check-limit.json',{'atchFileId':aid,'fileDetailSn':sn}); print('LIMIT',suffix,b,flush=True)
        if json.loads(b).get('needCaptcha'): raise RuntimeError('CAPTCHA required')
        b=save('ridership_sample_'+suffix+'.csv','https://www.data.go.kr/cmm/cmm/fileDownload.do?'+urllib.parse.urlencode({'atchFileId':aid,'fileDetailSn':sn}))
        for enc in ['utf-8-sig','cp949']:
            try:
                text=b.decode(enc);break
            except UnicodeDecodeError:pass
        rows=list(csv.reader(io.StringIO(text)))
        print('CSV',suffix,'ROWS',len(rows),'HEADER',ascii(rows[0]),'FIRST',ascii(rows[1]),'LAST',ascii(rows[-1]),flush=True)
    stations=json.loads((S/'airkorea_stations.json').read_bytes())['stationList']
    codes=','.join(x['STATION_CODE'] for x in stations)
    for date in ['2021-04-01','2026-04-30','2026-05-01']:
        b=save('airkorea_probe_'+date+'.xls','https://www.airkorea.or.kr/web/lastAmbHourDataExcel_',{'mang_code':'3','district':'053','from_date':date,'to_date':date,'station_list_':codes,'flag':'Y','windowid':'daegu-research'})
        print('MAGIC',date,b[:100],flush=True)
