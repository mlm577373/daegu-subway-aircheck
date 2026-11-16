"""Text-first contest drafts from verified local analysis outputs."""
from pathlib import Path
import csv,json,hashlib
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

R=Path(__file__).resolve().parents[2];O=R/'outputs/submission_draft';B=O/'_build';B.mkdir(parents=True,exist_ok=True)
def rows(path):
    with (R/path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
risk=rows('outputs/management_map/risk_weight_station_sensitivity.csv')
top=[r for r in risk if float(r['baseline_rank'])<=10]
effects=rows('outputs/operation_change/tables/station_event_estimates.csv')
primary={r['analysis_station_id']:r for r in effects if r['config']=='adjusted56'}
pool=json.loads((R/'outputs/operation_change/pooled_point_estimates.json').read_text(encoding='utf-8'))
FONT='Noto Sans KR'
doc=Document();sec=doc.sections[0]
sec.page_width=Inches(8.5);sec.page_height=Inches(11)
sec.top_margin=sec.bottom_margin=Inches(.7);sec.left_margin=sec.right_margin=Inches(.72)
for name,size in [('Normal',10.5),('Title',23),('Subtitle',11),('Heading 1',17),('Heading 2',12.5)]:
    st=doc.styles[name];st.font.name=FONT;st.font.size=Pt(size);st.font.color.rgb=RGBColor(0,0,0)
    st.element.rPr.rFonts.set(qn('w:eastAsia'),FONT)
    st.paragraph_format.space_after=Pt(7)
doc.styles['Normal'].paragraph_format.line_spacing=1.05
doc.styles['Normal'].paragraph_format.space_after=Pt(4)
doc.styles['Subtitle'].font.italic=False
for st in doc.styles:
    for border in list(st.element.iter(qn('w:pBdr'))):border.getparent().remove(border)
for name in ['Heading 1','Heading 2']:doc.styles[name].paragraph_format.keep_with_next=True
footer=sec.footer.paragraphs[0];footer.alignment=2
footer.add_run('분석 근거  |  ')
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');footer._p.append(fld)
for run in footer.runs:run.font.size=Pt(8)

def p(t,style=None):return doc.add_paragraph(t,style)
def h(t):doc.add_heading(t,level=2)
def page(t):
    newpage=len(doc.paragraphs)>2
    hd=doc.add_heading(t,level=1)
    if newpage:hd.paragraph_format.page_break_before=True
def table(headers,data,widths=None,size=9.1):
    tb=doc.add_table(rows=1,cols=len(headers));tb.autofit=False
    if widths:
        for c,w in zip(tb.columns,widths):c.width=Inches(w)
    for c,t in zip(tb.rows[0].cells,headers):c.text=str(t)
    repeat=OxmlElement('w:tblHeader');tb.rows[0]._tr.get_or_add_trPr().append(repeat)
    for values in data:
        for c,t in zip(tb.add_row().cells,values):c.text=str(t)
    for i,row in enumerate(tb.rows):
        pr=row._tr.get_or_add_trPr();no=OxmlElement('w:cantSplit');pr.append(no)
        for j,c in enumerate(row.cells):
            if widths:c.width=Inches(widths[j])
            cp=c._tc.get_or_add_tcPr();m=OxmlElement('w:tcMar')
            for side in ['top','bottom','left','right']:
                z=OxmlElement('w:'+side);z.set(qn('w:w'),'45');z.set(qn('w:type'),'dxa');m.append(z)
            cp.append(m)
            if i==0:
                shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'E8EEE9');cp.append(shade)
            for para in c.paragraphs:
                para.paragraph_format.space_after=Pt(0);para.paragraph_format.space_before=Pt(0);para.paragraph_format.line_spacing=1.05
                for run in para.runs:run.font.name=FONT;run.font.size=Pt(size);run.bold=i==0;run._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),FONT)
    doc.add_paragraph().paragraph_format.space_after=Pt(1)
    return tb
def small(t):
    pp=p(t)
    for run in pp.runs:run.font.size=Pt(8.5)

p('고농도 패턴으로 보는 도시철도 미세먼지 관리', 'Title')
p('관리 우선 후보와 열차 운행 관련 반응', 'Subtitle')
p('분석 방법과 수치 근거', 'Subtitle')
p('2026 대구광역시 기후·환경·탄소중립 공공데이터 AI 활용대회\n부문 2 공공데이터 분석 시각화\n수정일 2026년 11월 16일')
h('이 문서의 목적')
p('15장 PPT의 분석 흐름에 맞춘 상세 근거 문서다. 기사에서 출발한 분석 질문, 관리 위험도 계산, 후보 역의 패턴과 시간대, 운행 변화 비교, 후보별 관리 제안을 설명한다. PPT에는 이해를 돕는 요약을 담고, 이 문서에는 계산 기준과 역별 수치, 비교 조건에 따른 변화를 수록했다.')
h('주제 선정 배경')
p('SBS·TBC의 2026년 2월 20일 보도는 대구 지하역사 공기질 평가가 연 1회 측정자료와 매시간 자동측정자료 중 무엇을 사용하는지에 따라 달라진 문제를 다뤘다. 이는 측정 시점과 집계 방식을 구분해 공기질을 읽어야 한다는 분석 동기다. 기사에서 다룬 2025년 연평균 수치는 이번 2022~2024년 관리 위험도 계산 결과가 아니다.')
p('영남일보의 2024년 4월 21일 보도는 2023년 대구 지하역사 미세먼지와 초미세먼지 농도가 전년보다 높아졌지만 측정 결과는 기준치 이하였다고 전했다. 이 보도는 기준 충족 여부와 함께 시간에 따른 변화를 살펴볼 필요를 보여준다. 두 기사의 측정 조건을 같다고 간주하거나 기사 수치로 이번 위험도를 산출하지 않았다.')
h('분석 질문과 시각화')
p('어느 역에서 고농도가 자주 나타나고 다음 시간에도 이어지며 시민 이용과 겹치는가? 어떤 요일과 시간대에 반복되는가? 위험도가 높은 후보 안에서 열차 운행 변화와 관련된 반응이 상대적으로 나타나는가? 종합 관리 위험도 지도, 후보별 점수와 비율 표, 반복 시간대 행렬로 답하고 후보별 점검 방향을 제안한다.')
h('PPT와 함께 읽는 순서')
p('PPT 2장은 기사 배경, 3~5장은 분석 질문·자료·위험도 방법, 6~10장은 지도·후보·패턴·시간대 결과, 11장은 운행 분석 방법, 12~13장은 후보별 해석과 관리 제안, 14장은 출처, 15장은 해석 범위다. 이 문서 1~7절이 주요 분석을 뒷받침하며 8절은 시각화 이용 안내, 9절은 출처, 10절은 한계다.')

page('1 사용 자료와 분석 범위')
table(['자료','사용 목적','기간과 범위'],[
['InAir 승강장 PM2.5','고농도 패턴과 후보 선정','57개 지점, 주 분석 2022~2024년'],
['AirKorea 실외 PM2.5','외부 대기와 함께 변하는 부분 고려','기존 역별 실외 매칭 자료'],
['역별 시간대 승하차량','고농도와 이용의 겹침 평가','2022~2024년 연간 결합자료'],
['NOAA 기상 및 공휴일','기온·습도·풍속 등 조건 조정','기존 2022~2024년 결합자료'],
['대구교통공사 시간표','2024년 운행 시간 이동 비교','개편 전 보관본과 2024년 당시 공식 첨부']],[1.65,2.05,3.25])
table(['연도','확보 기간','잠정 유효 실내 역 시간 관측 수'],[
['2022','1월 1일~12월 31일','487,139'],['2023','1월 1일~12월 31일','483,444'],['2024','1월 1일~12월 31일','490,466'],['2025','1월 1일~4월 30일','159,948'],['2026','1월 1일~4월 30일','156,118']],[.7,2.5,3.75])
p('2025·2026년 자료는 사용을 허용한 범위에 포함하되, 확보된 1~4월의 시간대별 관측 수·평균·중앙값을 비교하는 보조 자료로 정리했다. 주 관리 위험도와 후보 순위는 계절 구성이 같은 2022~2024년 연간 자료에 고정했다. 두 해의 자료를 연간 순위에 혼합하거나, 수집되지 않은 달을 0으로 채우지 않았다.')
p('2022~2024년 기대 관측 수는 57개 지점 합계 1,499,328개이며 잠정 유효 관측은 1,461,049개다. 반월당은 호선별 별도 측정지점이다. 57개는 자료가 있는 측정지점의 수로 대구 전체 역의 수를 의미하지 않는다.')
small('수치 근거: outputs/management_map/validation.json, outputs/operation_change/tables/source_coverage.csv')

page('2 종합 관리 위험도 계산')
p('여기서 위험도는 이 표본 안에서 관리 관심을 기울일 순서를 뜻한다. 개인의 건강 위해 확률이나 법정 위험등급을 계산한 것은 아니다. 평균 농도가 높은 역만 선정하지 않도록 발생 빈도, 유지, 이용 겹침을 함께 보았다.')
table(['관점','계산 방법','해석할 때 주의할 점'],[
['고농도 발생 빈도','유효 실내 관측 중 43.15 µg/m³ 이상인 시간 비율','43.15는 기존 탐색 경계이며 법정 기준이 아님'],
['다음 시간 유지','고농도 시각에서 정확히 1시간 뒤를 평가할 수 있는 경우 중 다음 시간도 고농도인 비율','전체 사건 지속시간이나 독립 사건 수와 다름'],
['이용 겹침','실내와 승하차 동시 관측 구간의 승하차량 중 고농도 시간에 겹친 비중','고유 인원·체류시간·실제 흡입 노출량은 아님']],[1.25,2.9,2.8])
h('점수 환산과 표시')
p('각 비율을 57개 지점 사이의 백분위 점수 0~100으로 바꾸고 같은 비중으로 평균했다. 동률은 중간 순위를 적용했다. 종합점수 = 발생 빈도 점수 × 1/3 + 유지 점수 × 1/3 + 이용 겹침 점수 × 1/3이다.')
p('지도는 33점 미만을 초록, 33점 이상 67점 미만을 주황, 67점 이상을 빨강으로 표시한다. 색은 상대 점수를 읽기 위한 구분이며 안전 판정이나 객관적 건강 위해 등급이 아니다.')
h('관측 품질 기준')
p('전체 농도 관측률은 75% 이상이어야 한다. 유지 비율은 고농도 후 다음 시간을 평가할 수 있는 경우가 20회 이상이어야 한다. 이용 겹침은 05~23시 기대 시간 대비 동시 관측률 75% 이상이고 승하차 합계가 양수여야 한다. 현재 연간 표본에서는 57개 지점 모두 종합점수를 산출할 수 있었다.')
p('상태값이 공백인 자료를 잠정 유효로 사용했지만 정상 품질이 확정된 것은 아니다. 음수·비유한 값과 다른 상태값은 제외했고 결측을 건너뛰어 연속 시간으로 연결하지 않았다.')
small('산식 근거: data/_scripts/baseline_management.py, outputs/management_map/risk_reference.json')

page('3 관리 우선 후보와 선정 이유')
p('같은 비중의 종합점수에서 상위 10개 지점을 우선 설명 대상으로 삼았다. 동점이 있어 순위 숫자는 건너뛸 수 있다. 각 비율은 2022~2024년 전체 자료의 값이며 점수와 원래 비율은 서로 다른 값이다.')
table(['역','점수','발생 빈도','다음 시간 유지','이용 겹침'],[[r['name'],f"{float(r['score']):.1f}",f"{float(r['rate'])*100:.1f}%",f"{float(r['stay'])*100:.1f}%",f"{float(r['overlap_rate'])*100:.1f}%"] for r in top],[1.65,.7,1.4,1.6,1.6],9.5)
h('후보 선정이 얼마나 안정적인가')
p('각 관점의 비중을 20~60% 범위에서 바꾼 45가지 조합을 비교했다. 기본 상위 10개와의 일치 수는 7~10개였다. 월배·신천·이곡·반고개·신매는 모든 조합에서 상위 10개에 포함됐다. 성서산업단지는 45개 중 44개 조합에서 포함됐다.')
p('이곡은 발생 빈도와 이용 겹침이 모두 높은 편이다. 반고개는 높은 다음 시간 유지 비율이 함께 나타난다. 성서산업단지는 이용 겹침 비중이 25.0%로 두드러진다. 이런 차이를 함께 제시하면 단순 농도 순위보다 선정 이유를 구체적으로 설명할 수 있다.')
p('동일 비중은 분석상의 선택이다. 발생 빈도와 이용 겹침은 서로 관련되어 일부 특성을 중복 반영할 수 있으므로 점수의 작은 차이를 절대적인 우열로 해석하지 않는다.')
small('수치 근거: outputs/management_map/risk_weight_station_sensitivity.csv, risk_weight_sensitivity.json')

page('4 반복적으로 확인할 시간대')
p('57개 지점 중 44개에서 반복적으로 확인할 시간대를 찾았고, 13개에서는 뚜렷한 집중 시점을 찾지 못했다. 집중 시점이 없다는 것은 농도가 낮거나 관리가 불필요하다는 뜻이 아니다.')
table(['후보 역과 반복 확인 시간대'],[[r['name']+'   '+r['timing']] for r in top],[6.95],9.6)
h('시간대를 선정한 방법')
p('평일·주말과 아침 06~09시, 낮 10~15시, 저녁 16~19시, 밤 20~23시를 나누어 같은 연도의 나머지 06~23시와 비교했다. 구간 관측률 75% 이상, 유효 100시간 이상, 고농도 10시간 이상, 고농도 비율 5% 이상을 요구했다.')
p('나머지 시간보다 고농도 비율이 3%p 이상이면서 1.25배 이상 높고, 네 분기 중 두 분기 이상에서 차이 방향이 같아야 한다. 이 조건을 세 해 중 두 해 이상 통과한 시간대를 표시했다. 공휴일은 이 시간대 분류에서 별도로 나누지 않았다.')
p('이 시간대는 반복 패턴의 요약이다. 개별 날짜의 고농도를 예측하거나, 아침 고농도의 원인이 열차라고 확인한 것은 아니다. 오후 운행 개편 분석의 결과와 아침 집중 시점은 구분해야 한다.')
small('PPT 6장의 지도와 9~10장의 시간대 행렬은 동일한 저장 결과를 시각화했다. 행렬의 초록 칸은 반복 조건을 통과한 구간을 표시한다.')

page('5 열차 운행 변화의 관련성 검토')
p('위험도가 높다는 사실만으로 원인을 알 수는 없다. 후보 역 안에서 운행 변화에 상대적으로 더 반응한 곳이 있는지 알아보기 위해 2024년 10월 7일 시간표 개편을 활용했다. 이때 평일 오후 혼잡 운행 시간대가 이동했다. 기준 역 반월당의 양방향 평일 예정 횟수는 296회로 같고 시간대별 배분이 달라졌다.')
p('개편 전후 각 8주의 평일 14~22시를 비교하고 2022·2023년 같은 계절에 나타난 시간대 변화도 함께 고려했다. 실외 농도, 기온, 습도, 풍속과 날짜별 차이를 조정했다. 주 분석은 54개 지점의 역 시간 관측 93,663개를 사용했다. 현충로·율하는 기존 실외 매칭 문제, 만촌은 최소 관측일 요건으로 제외됐다.')
h('사용한 분석 기술')
p('삼중차분 형태의 비교: 운행이 늘거나 줄어든 시간대의 개편 전후 농도 차이를 비교하고, 이를 2022·2023년 같은 계절의 차이와 대조했다. 고정효과 회귀분석: 날짜별 차이, 연도별 시간대 차이, 공통 개편 전후 시간대 차이를 모형에서 함께 고려했다. 실외 농도와 기온·습도·풍속도 조정했다. 민감도 분석: 비교 기간, 이용량 조정 여부, 시간 정렬을 바꾸고 2023년을 가짜 개편 연도로 두어 결과가 유지되는지 확인했다.')
h('비교 조건을 바꾼 통합 결과')
configs=[('raw56','기본 비교 8주'),('adjusted56','실외 기상 조정 8주'),('usage56','이용량 추가 조정'),('adjusted42','기간 변경 6주'),('adjusted70','기간 변경 10주'),('clock_minus1','시간 정렬 -1시간'),('clock_plus1','시간 정렬 +1시간'),('placebo2023','가짜 개편 2023년')]
table(['조건','추정 농도 차이','근사 95% 구간'],[[label,f"{pool[key]['point_estimate']:+.3f}",f"{pool[key]['ci_low']:+.3f} ~ {pool[key]['ci_high']:+.3f}"] for key,label in configs],[2.8,1.5,2.65],9.3)
p('단위는 시간당 예정 열차 수 1회 변화에 대응하는 µg/m³다. 실제 운행 횟수를 측정한 것은 아니다. 주 분석 구간은 0을 포함하고, 시간 정렬과 가짜 개편에서도 반응이 달라졌다. 운행 영향이 없다는 증명도, 열차가 미세먼지를 증가시킨다는 확정도 아니다.')
small('주 단위 공통 변동을 고려한 정규 근사 구간이다. 보관된 과거 시간표의 개편 직전까지의 완전한 적용 여부와 동시 운행 변경은 불확실성으로 남는다.')

page('6 위험도 상위 후보의 운행 관련 반응')
p('다음 표는 상위 후보 안에서 관측된 운행 관련 반응을 비교한다. 추정치의 크기만으로 확정 순위를 매기지 않고 비교 기간, 시간 정렬, 가짜 사건 검토의 일관성을 함께 읽어야 한다. 전체 역 분석에서 나타난 송현·대구역·두류를 상위 10개 목록에 임의로 추가하지 않았다.')
table(['후보 역','추정치','근사 95% 구간','다중검정 보정 q'],[[r['name'],f"{float(primary[r['id']]['effect_per_scheduled_train']):+.2f}" if r['id'] in primary else '미산출',f"{float(primary[r['id']]['ci_low']):+.2f} ~ {float(primary[r['id']]['ci_high']):+.2f}" if r['id'] in primary else '관측일 요건 미달',f"{float(primary[r['id']]['q_bh']):.3f}" if r['id'] in primary else '—'] for r in top],[1.65,1.0,2.5,1.8],9.2)
p('q는 여러 역을 한꺼번에 비교할 때 우연한 발견을 줄이기 위한 보정값이다. 이 상위 후보들은 모두 탐색 기준 q≤0.10을 충족하지 못했다. 따라서 아래 구분은 반응 양상을 바탕으로 한 재검토 순서이며, 통계적으로 확정한 운행 민감도 등급은 아니다.')
h('재검토 후보의 차이')
p('이곡은 비교 기간과 이용량 조정 후에도 양의 반응을 유지했고 시간 정렬을 바꾸어도 방향은 양수였다. 그러나 2023년 가짜 사건에서도 비슷한 양의 추정치가 나타났다. 성서산업단지는 양의 추정치가 비교적 컸지만 구간이 넓고 시간 정렬을 바꾸면 거의 0에 가까워졌다.')
p('강창·고산은 기간 변경 시 양의 반응을 보였으나 시간 정렬 +1시간에서 음수로 바뀌었다. 신천·반고개는 반응이 뚜렷하지 않고, 월배·신매·사월은 운행 증가와 농도 상승의 근거가 부족하다. 음의 추정치를 운행의 정화 효과로 해석하지 않는다.')
small('모형은 실외 조건을 고려하지만 운행과 실외 대기의 기여율을 분해한 것은 아니다. 두 요인 중 무엇이 압도적이라는 결론은 제시하지 않는다.')

page('7 후보 역별 관리 방향')
p('관리 우선도는 고농도 패턴으로 정하고, 운행 관련 반응은 무엇을 먼저 점검할지 보완하는 정보로 사용한다. 실제 조치의 효과나 비용 절감 규모는 현재 자료로 산출하지 않았다.')
table(['후보 묶음','관측 근거','우선 검토할 관리 방향'],[
['이곡 성서산업단지','높은 관리 우선도와 양의 운행 반응 양상','선로 주변 퇴적먼지·재비산·열차풍 관련 점검을 우선 검토. 마모 원인 확정이나 일괄 설비 교체로 연결하지 않음'],
['강창 고산','양의 반응이 있으나 시간 정렬에 민감','운행 관련 점검의 보조 후보. 실제 통과 시점과 농도 반응을 먼저 대조'],
['신천 반고개','반복·지속·이용 겹침이 높고 운행 반응은 불명확','반복 시간대의 공조·필터 상태와 누적 먼지 상태를 함께 점검. 특정 원인으로 분류하지 않음'],
['월배 신매 사월','관리 우선도는 높지만 운행 증가 관련 근거 부족','아침·밤 등 각 역 반복 패턴을 관리 계획에 반영. 실내외 농도 차이와 공조 운전 기록을 대조할 후보'],
['만촌','관리 우선 후보이나 운행 주 분석 미산출','평일 저녁 패턴에 따른 관리 확인. 운행 민감도 설명은 보류']],[1.35,2.0,3.6],9.2)
h('관리 효과를 확인하는 방식')
p('청소나 공조 조정을 시범 적용한다면 한 번에 여러 조치를 섞기보다 한 가지 조치부터 비교한다. 조치 전후에 실외 농도, 요일, 시간대, 운행 조건이 비슷한 구간을 골라 고농도 빈도와 다음 시간 유지 비율이 달라졌는지 확인하는 방식을 제안한다. 이는 향후 실행안이며 이번에 시행한 실험이 아니다.')
p('환기량은 실내외 농도 차이와 기존 안전·공조 운전 기준을 고려해 검토한다. 외기가 나쁠 때 무조건 환기를 늘리는 제안은 하지 않는다. 현재 자료만으로 제동 장치나 레일 마모를 원인으로 지목하거나 청소 주기·환기량을 수치로 처방할 수는 없다.')

page('8 지도와 시각화 이용 안내')
p('PPT 6장은 종합 관리 위험도를 지도에 표시한다. 초록은 33점 미만, 주황은 33점 이상 67점 미만, 빨강은 67점 이상이다. 지도에서 크게 표시한 월배·신천·이곡·반고개·신매는 45가지 가중치 비교 모두에서 상위 10개에 포함된 후보다.')
p('동봉한 대구_도시철도_미세먼지_인터랙티브지도.html을 브라우저로 열면 역별 정보를 확인할 수 있다. HTML은 지도와 자료를 포함한 별도 제출 파일이다. PPT의 정적 지도와 동일한 2022~2024년 분석 결과를 사용한다.')
p('PPT 7장은 후보 10개 지점의 종합점수, 8장은 원래 비율을 보여준다. 9~10장의 시간대 행렬은 평일·주말과 네 시간대를 나누어 반복 조건을 통과한 칸을 표시한다. 빈칸은 해당 반복 조건을 충족하지 않은 구간이며 관측이 전혀 없다는 의미가 아니다.')
p('이 자료는 담당자가 먼저 살펴볼 역과 시간대, 역별 점검 방향을 함께 읽기 위한 자료다. 별도의 고농도 예측 모델은 만들지 않았다. 관리 조치 후 효과 검증은 후속 실행안으로 구분한다.')

page('9 자료 출처')
sources=[
('공모 공고','대구광역시 탄소중립지원센터 공고 제2026 2호 및 사용자 제공 HWP','https://dcnc.or.kr/bbs/board.php?bo_table=notice&wr_id=193'),
('승강장 PM2.5','실내공기질 관리 종합정보망 InAir','https://www.inair.or.kr/info/excel.html'),
('실외 PM2.5','AirKorea 과거 대기질 자료','https://www.airkorea.or.kr/web/last_amb_hour_data'),
('시간대 승하차','대구교통공사 공공데이터','https://www.data.go.kr/data/15002503/fileData.do'),
('기상','NOAA NCEI Global Hourly 자료','https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database'),
('운행 시간표 1호선','공공데이터포털 과거 파일 이력','https://www.data.go.kr/data/15065526/fileData.do'),
('운행 시간표 2호선','공공데이터포털 과거 파일 이력','https://www.data.go.kr/data/3033376/fileData.do'),
('당시 운행 개편 공지','대구교통공사 열차운행간격 조정 안내와 첨부','https://www.dtro.or.kr/index.do?menu_id=00000289&menu_link=icms/bbs/selectBoardArticle.do?bbsId%3DBBS_00253&nttId=74097')]
data_sources=json.loads((B/'forms_sources.json').read_text(encoding='utf-8'))
for i,(label,owner,url) in enumerate(data_sources,1):small(f'{i}. {label}  {owner}\n{url}')
h('주제 선정 배경 기사')
small('SBS·TBC, 2026.02.20, 대구 지하역사 공기질 평가 관련 보도\nhttps://news.sbs.co.kr/news/endPage.do?news_id=N1008448922')
small('영남일보, 2024.04.21, 대구 지하역사 공기질 변화 관련 보도\nhttps://www.yeongnam.com/web/view.php?key=20240418010002733')
small('PPT 기사 이미지는 2026년 11월 16일 원문 페이지에서 제목·날짜·보도 사진 일부를 화면 캡처해 인용했다. SBS 화면의 보도는 TBC 박동주 기자, 영남일보 사진은 영남일보 DB다. 기사 내용은 분석 배경이며 출처별 통합 데이터셋 7개와 별도로 구분한다.')
small('공공데이터 사용 내역은 별도 붙임 5, AI 활용 내역과 실제 프롬프트는 붙임 4에 기재했다. 서체 Noto Sans KR 및 Noto Serif KR의 이용 조건은 SIL Open Font License 1.1이다. https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/LICENSE')

page('10 분석의 한계와 해석 범위')
for para in json.loads((B/'user_limitations.json').read_text(encoding='utf-8')):p(para)
h('상세 수치를 해석하는 방법')
p('PPT의 후보별 설명은 점검 방향을 고르기 위한 탐색적 해석이다. 6절의 추정치와 신뢰구간, 다중검정 보정값을 함께 읽어야 한다. 상위 10개 후보 중 운행 주 분석에서 q≤0.10을 충족한 역은 없었다. 비교 조건에 따른 변화는 5~6절에 제시했으며, 후보 간 차이를 통계적으로 확정한 순위나 발생원 기여율로 제시하지 않는다.')
p('이용 겹침은 승하차 합계의 비중이며 고유 이용자 수나 실제 흡입 노출량과 다르다. 다음 시간 유지는 정확히 1시간 뒤에 고농도가 이어진 비율이며 전체 사건 길이와 다르다. 동일 가중치와 43.15 µg/m³ 경계는 계산상의 선택이다. 가중치 변화에 대한 후보 안정성은 확인했지만 모든 기준 선택에 대한 보편성을 검증한 것은 아니다.')

for rf in doc.element.iter(qn('w:rFonts')):
    for attr in ['asciiTheme','hAnsiTheme','eastAsiaTheme','cstheme']:
        rf.attrib.pop(qn('w:'+attr),None)
    rf.set(qn('w:hint'),'eastAsia')
    for script in ['ascii','hAnsi','eastAsia','cs']:rf.set(qn('w:'+script),FONT)
for para in list(doc.paragraphs)+[pp for tb in doc.tables for row in tb.rows for cell in row.cells for pp in cell.paragraphs]:
    for run in para.runs:
        pr=run._element.get_or_add_rPr();lang=OxmlElement('w:lang');lang.set(qn('w:val'),'ko-KR');lang.set(qn('w:eastAsia'),'ko-KR');pr.append(lang)
        run.font.color.rgb=RGBColor(0,0,0)
for tb in doc.tables:
    for row in tb.rows:
        for run in row.cells[0].paragraphs[0].runs:
            rf=run._element.get_or_add_rPr().rFonts
            for key in ['ascii','hAnsi','eastAsia','cs']:rf.set(qn('w:'+key),'Noto Serif KR')
out=O/'대구_도시철도_미세먼지_분석근거_수정본.docx';doc.save(out)
print('Updated evidence Word')
