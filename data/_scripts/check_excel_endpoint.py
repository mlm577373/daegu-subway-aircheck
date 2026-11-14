from collect_probe import fetch,S
import time,urllib.parse
t=time.monotonic()
u='https://www.inair.or.kr/info/main/ExcelDown.do?'+urllib.parse.urlencode({'view_start_date':'2026040100','view_end_date':'2026043023','loc_code':'A1214C'})
b,h=fetch(u);(S/'inair_excel_probe_202604_A1214C.xls').write_bytes(b)
print('bytes',len(b),'seconds',time.monotonic()-t,'headers',h,'first',b[:180])
