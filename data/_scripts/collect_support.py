from collect_probe import *
import csv, io, sys
sys.path.insert(0,str(ROOT/'_tools'))
import xlrd

def decode_csv(b):
    for enc in ['utf-8-sig','cp949']:
        try:return list(csv.reader(io.StringIO(b.decode(enc)))),enc
        except UnicodeDecodeError:pass
    raise ValueError('Unknown CSV encoding')

def ridership():
    p=ROOT/'ridership'/'raw';p.mkdir(parents=True,exist_ok=True)
    history=json.loads((S/'ridership_history_index.json').read_text(encoding='utf-8'))
    index=[]
    for yr in range(2021,2027):
        suffix=f'{yr}1231' if yr<2025 else ('20250430' if yr==2025 else '20260430')
        x=next(x for x in history if x['name'].endswith(suffix))
        detail=S/('ridership_detail_'+suffix+'.html')
        if not detail.exists(): detail.write_bytes(fetch('https://www.data.go.kr/tcs/dss/selectDpkDetailInfo.do',{'publicDataDetailPk':x['pk'],'publicDataHistSn':x['sn']})[0])
        m=re.search(r"fn_fileDataDown\('15002503', '([^']+)', '([^']+)', '([^']+)', 'csv'",detail.read_text(encoding='utf-8'))
        pk,aid,sn=m.groups(); dest=p/f'ridership_{suffix}.csv'
        if not dest.exists():
            limit=json.loads(fetch('https://www.data.go.kr/cmm/cmm/check-limit.json',{'atchFileId':aid,'fileDetailSn':sn})[0])
            if limit.get('needCaptcha'): raise RuntimeError('CAPTCHA required; user interaction needed')
            b,h=fetch('https://www.data.go.kr/cmm/cmm/fileDownload.do?'+urllib.parse.urlencode({'atchFileId':aid,'fileDetailSn':sn}));dest.write_bytes(b)
        rows,encoding=decode_csv(dest.read_bytes())
        dates=sorted(set(f'{yr}-{int(r[0]):02d}-{int(r[1]):02d}' for r in rows[1:] if len(r)>4 and r[0].strip().isdigit()))
        record={'year':yr,'snapshot':suffix,'file':str(dest.relative_to(ROOT)),'pk':pk,'atchFileId':aid,'fileDetailSn':sn,'encoding':encoding,'rows':len(rows)-1,'first_date':dates[0],'last_date':dates[-1],'days':len(dates),'months':sorted(set(d[:7] for d in dates))}
        index.append(record); print('RIDERSHIP',json.dumps(record),flush=True)
        time.sleep(.3)
    (ROOT/'ridership'/'inventory.json').write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':ridership()
