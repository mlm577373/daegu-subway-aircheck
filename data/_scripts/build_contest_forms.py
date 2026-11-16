from pathlib import Path
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
import json

R=Path(__file__).resolve().parents[2]; O=R/'outputs/submission_draft'; B=O/'_build'
d=Document(); sec=d.sections[0]
# Attached Korean administrative forms are reproduced on A4.
sec.page_width=Cm(21);sec.page_height=Cm(29.7)
sec.top_margin=sec.bottom_margin=Cm(1.7);sec.left_margin=sec.right_margin=Cm(1.8)
for name in ['Normal','Title','Heading 1','Heading 2']:
 st=d.styles[name];st.font.name='Noto Sans KR';st.font.color.rgb=RGBColor(0,0,0);st.font.size=Pt(10.5 if name=='Normal' else 18)
 st.paragraph_format.space_after=Pt(6)
 st.paragraph_format.line_spacing=1.12
 st.element.get_or_add_rPr()
for name in ['Title','Subtitle']:
 st=d.styles[name]
 for el in list(st.element):
  if el.tag==qn('w:pPr'):
   for x in list(el):
    if x.tag==qn('w:pBdr'):el.remove(x)

def p(t='',bold=False,size=None):
 a=d.add_paragraph();r=a.add_run(t);r.bold=bold
 if size:r.font.size=Pt(size)
 return a
def heading(n,title):
 newpage=len(d.paragraphs)>0
 lead=p('붙임 '+str(n),True,10)
 if newpage:lead.paragraph_format.page_break_before=True
 d.add_paragraph(title,'Title');p('접수번호:                         ※ 미기재',False,9)
def table(rows,widths,header=False,fs=10):
 t=d.add_table(rows=0, cols=len(widths));t.autofit=False;t.alignment=WD_TABLE_ALIGNMENT.CENTER
 for c,w in zip(t.columns,widths):c.width=Cm(w)
 for ri,row in enumerate(rows):
  cells=t.add_row().cells
  for j,(cell,value,w) in enumerate(zip(cells,row,widths)):
   cell.width=Cm(w);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
   cell.text=str(value)
   tcpr=cell._tc.get_or_add_tcPr()
   borders=OxmlElement('w:tcBorders')
   for edge in ['top','left','bottom','right']:
    el=OxmlElement('w:'+edge);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'5');el.set(qn('w:color'),'D9D9D9');borders.append(el)
   tcpr.append(borders)
   margins=OxmlElement('w:tcMar')
   for e in ['top','bottom','left','right']:
    x=OxmlElement('w:'+e);x.set(qn('w:w'),'90');x.set(qn('w:type'),'dxa');margins.append(x)
   tcpr.append(margins)
   if (header and ri==0) or (not header and j==0):
    shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'F0F0F0');tcpr.append(shade)
   for para in cell.paragraphs:
    para.paragraph_format.space_after=Pt(2);para.paragraph_format.line_spacing=1.08
    for run in para.runs:run.font.size=Pt(fs);run.bold=(header and ri==0)
 return t
def sign(sentence):
 p(sentence);p('2026.        .        .')
 p('참 가 자:                                      (인 또는 서명)')
 p('법정대리인:                                  (인 또는 서명)')
 p('※ 만 14세 미만 아동인 경우 법정대리인 동의 포함',False,9)
 p('대구광역시 탄소중립지원센터장 귀하',True,12)

heading(1,'2026 대구광역시 기후·환경·탄소중립\n공공데이터 AI 활용대회 참가 신청서')
table([['성명','                              ','생년월일','      년    월    일 (    세)'],['연락처','','성별','□ 남    □ 여'],['이메일','','주소','도로명주소:']], [2,6,2,7.4])
p('출품작',True)
table([['응모 부문','□ (부문1) 아이디어 기획 제안\n☑ (부문2) 데이터 분석·시각화'],['작품명','고농도 패턴으로 보는 도시철도 미세먼지 관리\n관리 우선 후보와 열차 운행 관련 반응'],['활용 데이터 및 AI','공공데이터: 승강장·실외 PM2.5, 시간대별 승하차량, 기상, 열차 시간표, 역·측정소 위치, 달력, 지도 경계\nAI 도구: ChatGPT 및 Codex (OpenAI)'],['작품 개요','대구 도시철도 57개 측정지점의 2022~2024년 시간별 자료를 연결해 고농도 발생 빈도, 다음 시간 유지, 이용 겹침을 종합한 상대 관리 위험도를 산출했다. 지도와 반복 시간대 시각화로 관리 우선 후보를 제시하고, 2024년 10월 운행시간 개편 전후를 비교해 후보별 점검 방향을 보완했다. 2025·2026년 각 1~4월 자료는 보조 검토에 사용했다. PPT, 상세 분석 근거 Word와 인터랙티브 지도 HTML을 제출한다.']], [3.2,14.2])
p('제출: 붙임 1~5 작성 후 출품작과 함께 제출 (smeeheo@dpi.re.kr)',False,9)
sign('위와 같이 참가 신청서를 제출합니다.')

raw=(B/'forms_extracted.txt').read_text(encoding='utf-8')
heading(2,'개인정보 수집 이용 동의서')
# Preserve the supplied consent clauses; only repair the extracted typo.
block=raw.split('【개인정보 수집 및 초상권 이용 동의 안내】')[1].split('위와 같이 개인정보 수집 이용 동의서를 제출합니다.')[0]
block=block.replace('참갓 ᅟᅵᆫ청','참가 신청')
p('【개인정보 수집 및 초상권 이용 동의 안내】',True)
for line in block.splitlines():
 if line.strip():p(line.strip(),size=10)
sign('위와 같이 개인정보 수집 이용 동의서를 제출합니다.')

heading(3,'서약서')
block=raw.split('본인은 제출한 작품 및 서류의 모든 내용이 사실임을 확인함.')[1].split('위와 같이 서약서를 제출합니다.')[0]
p('◦ 본인은 제출한 작품 및 서류의 모든 내용이 사실임을 확인함.',size=10)
for line in block.splitlines():
 if line.strip():p(line.strip(),size=10)
sign('위와 같이 서약서를 제출합니다.')

heading(4,'AI 프롬프트 활용 내역서')
table([['주요 사용 AI','ChatGPT 및 Codex (OpenAI)'],['활용 목적','☑ 데이터 수집·전처리 및 분석 코드 작성\n☑ 아이디어 구상 및 기획서 작성\n☑ 시각화 그래픽 및 이미지 생성\n☑ 기타: PPT·Word 구성 및 편집']], [3.2,14.2])
p('AI 활용 내역 및 프롬프트 상세내용',True,12)
cases=[
('사례 1  종합 관리 위험도와 지도','지표 설계 및 시각화 코드 작성','세 관점을 합쳐서 하나의 전체적인 미세먼지 위험도를 만들었으면 좋겠어. 그리고 지도에 표현해줘. 또 지도의 색이 파란색 주황색 빨간색으로 되어있는데 파란색 대신 초록색이 더 가시성이 있을것 같아','고농도 발생 빈도, 다음 시간 유지, 이용 겹침을 계산하고 백분위 순위와 동일 가중치로 종합했다. 사용자가 분석 기간과 색상을 조정했으며, 원자료와 저장된 결과를 대조해 지도와 수치표를 구성했다.'),
('사례 2  후보별 운행 관련 반응','운행 변화 비교와 관리 방향 해석','그냥 위험도 높은 후보역들 기준으로 어떤 역이 운행에 상대적으로 영향을 많이 받는지를 설명해서 보고서에 넣으면 될것 같아. 외부 대기에는 당연히 모든 역이 압도적으로 영향 받겠지.','시간표 변경을 활용한 삼중차분 형태의 고정효과 회귀분석과 민감도 검토를 구현했다. 입력 문장의 외기 영향 우세는 검증된 사실로 채택하지 않았다. 위험도 상위 후보의 관련 반응을 점검 제안으로 정리하고, 상세 수치와 불확실성은 분석 근거 문서에 남겼다.'),
('사례 3  지역 이슈와 분석 근거 정리','주제 선정 배경 구성과 결과 설명의 일관성 검토','1순위랑 보조 기사 두개 기사 사진 캡쳐해서 간략한 뒷받침 내용과 함께 앞쪽에 페이지를 만들어줘. 그리고 ppt와 내용이 일치하도록 분석근거 word를 다듬어줘.','대구 지하역사 공기질의 측정·집계 방식 차이를 다룬 SBS·TBC 보도와 농도 변화를 다룬 영남일보 기사를 확인했다. 기사 화면 일부와 요약을 주제 선정 배경에 활용하고, 역별·시간별 패턴을 분석하는 이유로 연결했다. 기사 내용과 직접 계산한 결과를 구분했으며, PPT와 Word의 분석 기간, 지표 정의, 후보 역, 수치와 관리 제안을 대조해 설명을 맞췄다.')]
for title,purpose,prompt,detail in cases:
 p(title,True,11);p('[활용 목적] '+purpose, size=9.5);p('[입력 프롬프트] “'+prompt+'”',size=9.5);p('[활용 및 보완 내용] '+detail,size=9.5)

sources=[
('승강장 시간별 초미세먼지 측정자료','환경부·한국환경공단 InAir','https://www.inair.or.kr/info/excel.html'),
('과거 시간별 실외 대기질 자료','한국환경공단 AirKorea','https://www.airkorea.or.kr/web/last_amb_hour_data'),
('역별 시간대 승하차 인원','대구교통공사','https://www.data.go.kr/data/15002503/fileData.do'),
('Global Hourly 기상 관측자료\n관측소 47143099999','미국 NOAA NCEI','https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database'),
('1호선 열차 시간표\n개편 전 보관본','대구교통공사','https://www.data.go.kr/data/15065526/fileData.do'),
('2호선 열차 시간표\n개편 전 보관본','대구교통공사','https://www.data.go.kr/data/3033376/fileData.do'),
('2024년 10월 7일 적용 1호선 시간표\n공식 공지 첨부 1','대구교통공사','https://www.dtro.or.kr/index.do?menu_id=00000289&menu_link=icms/bbs/selectBoardArticle.do?bbsId%3DBBS_00253&nttId=74097'),
('2024년 10월 7일 적용 2호선 시간표\n공식 공지 첨부 2','대구교통공사','https://www.dtro.or.kr/index.do?menu_id=00000289&menu_link=icms/bbs/selectBoardArticle.do?bbsId%3DBBS_00253&nttId=74097'),
('철도 역 위치 좌표','한국철도협회 철도산업정보센터 KRIC','https://data.kric.go.kr/rips/M_01_01/detail.do?id=213'),
('대기오염 측정소 위치 정보','한국환경공단','https://www.data.go.kr/data/15150453/fileData.do'),
('2022~2024년 월력요항·달력 자료','한국천문연구원','https://astro.kasi.re.kr/kor/life/post/calendarData?search_year=2024'),
('통계청 2013 행정경계 가공본\n지도 배경','통계청 원자료·southkorea-maps 가공','https://github.com/southkorea/southkorea-maps/tree/master/kostat/2013')]
sources=[
 ('승강장 시간별 PM2.5','환경부·한국환경공단 InAir',sources[0][2]),
 ('실외 대기질·측정소 위치','한국환경공단 AirKorea',sources[1][2]+'\n'+sources[9][2]),
 ('역별 시간대 승하차량 및 열차 시간표\n호선별·개편 전후 자료 통합','대구교통공사','\n'.join(sources[i][2] for i in [2,4,5,6])),
 sources[3],sources[8],sources[10],sources[11]]
heading(5,'공공데이터 사용 내역서')
table([['활용 데이터 수','총 7개 데이터셋 활용 (출처별 통합 집계)'],['주요 제공기관','환경부·한국환경공단, 대구교통공사, NOAA NCEI, 한국철도협회, 한국천문연구원, 통계청']], [3.2,14.2])
p('동일 출처의 자료는 하나로 묶었다. 연도·호선·개편 시점별 파일을 중복 집계하지 않았으며 아래 목록은 1~7번 전체다.',size=9)
vals=[['연번','공공데이터명','제공기관','데이터 출처 URL']]+[[i,*row] for i,row in enumerate(sources,1)]
table(vals,[.8,4.2,3.2,9.2],True,8.5)
p('주 분석은 2022~2024년이다. 2025·2026년은 각 1~4월 보조 검토에 사용했다. 기상과 운행 개편 분석은 2022~2024년 기준이다. 지도 경계는 통계청 2013 자료의 가공본이다.',size=9)

# Explicit Korean fonts for every run, avoiding hidden theme substitutions in Word.
for run in d.element.iter(qn('w:r')):
 rp=run.find(qn('w:rPr'))
 if rp is None:rp=OxmlElement('w:rPr');run.insert(0,rp)
 rf=rp.find(qn('w:rFonts'))
 if rf is None:rf=OxmlElement('w:rFonts');rp.insert(0,rf)
 for k in list(rf.attrib):del rf.attrib[k]
 for k in ['ascii','hAnsi','eastAsia','cs']:rf.set(qn('w:'+k),'Noto Sans KR')
 rf.set(qn('w:hint'),'eastAsia')
out=O/'공모전_붙임1-5_수정본.docx';d.save(out)
print(out.name)
(B/'forms_sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf-8')
