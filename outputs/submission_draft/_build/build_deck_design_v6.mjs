import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const runtime='C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt/dependencies';
process.env.RUNTIME_NODE_MODULES=runtime+'/node/node_modules';
const {Presentation,PresentationFile}=await import(pathToFileURL(runtime+'/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs').href);
const SKILL='C:/Users/김민준/.codex/plugins/cache/openai-primary-runtime/presentations/26.1112.11217/skills/presentations';
const {finalizePresentation,applyPresentationChartFont}=await import(pathToFileURL(SKILL+'/container_tools/artifact_tool_utils.mjs').href);
const build=path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Z]:)/,'$1'));
// URL decoding is essential for Korean workspace paths.
const B=decodeURIComponent(build), O=path.dirname(B), workspace=path.resolve(O,'../..');
const c=JSON.parse(await fs.readFile(path.join(B,'content.json'),'utf8'));
const F=c.font,green='#176A48',black='#173C32',gray='#62736B';
const deck=Presentation.create({slideSize:{width:1280,height:720}});
const manifests=[];const owners=[];
function text(s,t,x,y,w,h,size=26,bold=false,color=black){
  const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  a.text=t;a.text.style={fontSize:size,typeface:size>=38?'Noto Serif KR':F,color,bold:size>=38?false:bold};a.text.insets=0;return a;
}
function slide(title,note,source='분석 근거 문서 참조'){
  const s=deck.slides.add();s.background.fill='#FCFAF5';
  text(s,title,60,48,1160,83,42,true);
  text(s,String(deck.slides.items.length).padStart(2,'0'),1170,673,60,28,16,false,gray);
  s.speakerNotes.text=note;manifests.push({number:deck.slides.items.length,title,note});return s;
}
function paras(s,items,y=150,size=27,gap=116){items.forEach((t,i)=>text(s,t,65,y+i*gap,1140,gap-16,size));}
function table(s,headers,values,widths,y=157,height=430,size=23){
  const v=[headers,...values],tb=s.tables.add({rows:v.length,columns:headers.length,left:60,top:y,width:1160,height,columnWidths:widths,values:v});
  tb.borders.assign({fill:'#FCFAF5',width:2,style:'solid'});
  tb.cells.block({row:0,column:0,rowCount:v.length,columnCount:headers.length}).assign({textStyle:{fontSize:size,typeface:F,color:black},margins:{top:v.length>8?4:(headers.length>5?6:12),bottom:v.length>8?4:(headers.length>5?6:10),left:headers.length>5?8:18,right:headers.length>5?8:16}});
  tb.cells.block({row:0,column:0,rowCount:1,columnCount:headers.length}).assign({fill:'#DEE8D7',textStyle:{bold:true,fontSize:size,typeface:F,color:black}});
  for(let i=0;i<v.length;i++){tb.rows[i].height=height/v.length;if(i>0){tb.cells.block({row:i,column:0,rowCount:1,columnCount:headers.length}).assign({fill:i%2?'#EDF2EC':'#F4F6F0'});tb.getCell(i,0).text.style={fontSize:size,typeface:F,color:black,bold:false};}}
  owners.push(deck.slides.items.length);return tb;
}
const riskSrc='outputs/management_map/risk_weight_station_sensitivity.csv';
const effectSrc='outputs/operation_change/tables/station_event_estimates.csv';
let s=slide('大구 도시철도 승강장 초미세먼지'.replace('大','대'),'2026 대구광역시 기후·환경·탄소중립 공공데이터 AI 활용대회 부문 2. 핵심 결과와 관리 제안의 텍스트 구조 초안. 상세 수치와 한계는 동봉 Word 참조.','2026 공공데이터 AI 활용대회 부문 2');
s.background.fill='#E8EFE3';
s.shapes.items[0].text.style={fontSize:27,typeface:F,color:green};
s.shapes.items[1].text.style={fontSize:16,typeface:F,color:'#62736B'};
text(s,'고농도 패턴으로 보는\n도시철도 미세먼지 관리',60,198,1160,190,65,false,black);
text(s,'관리 우선 후보와 열차 운행 관련 반응',65,420,1130,65,32,false,green);
text(s,'2022~2024년 57개 측정지점 분석',65,554,1130,45,25,false,black);
text(s,'2025·2026년 각 1~4월 보조 검토',65,597,1130,42,22,false,'#62736B');


s=slide('주제 선정 배경', 'SBS·TBC 2026-02-20 https://news.sbs.co.kr/news/endPage.do?news_id=N1008448922\n영남일보 2024-04-21 https://www.yeongnam.com/web/view.php?key=20240418010002733\n실제 기사 페이지의 제목·날짜·보도 사진 일부를 화면 캡처하여 인용. SBS 화면은 TBC 박동주 기자 보도. 영남일보 사진은 영남일보 DB. 2026-11-16 열람. 기사 수치는 본 분석 결과가 아니며 서로 다른 측정·집계 조건을 직접 비교하지 않는다.');
const shot=async(name,rect,frame)=>s.images.add({blob:new Uint8Array(await fs.readFile(path.join(B,'news',name+'_page.png'))),contentType:'image/png',alt:name+' 기사 화면 일부',fit:'contain',crop:{left:rect[0]/1440,top:rect[1]/1200,right:1-(rect[0]+rect[2])/1440,bottom:1-(rect[1]+rect[3])/1200},position:{left:frame[0],top:frame[1],width:frame[2],height:frame[3]}});
text(s,'SBS·TBC  2026.02.20',60,120,550,35,22,true,green);
text(s,'영남일보  2024.04.21',670,120,550,35,22,true,green);
await shot('sbs',[170,237,850,107],[60,160,550,85]);
await shot('yeongnam',[120,292,920,110],[670,160,550,85]);
await shot('sbs',[170,356,850,478],[112,250,445,250]);
await shot('yeongnam',[210,559,340,203],[735,250,419,250]);
text(s,'연 1회 측정과 매시간 측정,\n집계 방식에 따라 평가가 달랐다.',60,515,550,85,26);
text(s,'2023년 농도는 전년보다 높아졌지만,\n측정 결과는 기준치 이하였다.',670,515,550,85,26);
text(s,'어느 역에서, 언제 고농도가 반복되고 시민 이용과 겹칠까?',60,620,1150,50,29,true,green);

s=slide('분석에서 확인할 내용','일반 독자와 비전문 담당자를 위한 문제 정의. 환경 관리의 활용 가능성은 제안이며 이미 확인한 정책 효과가 아니다.');
[
['고농도 패턴','어느 역에서 높은 농도가 자주 나타나고, 다음 시간에도 이어질까?'],
['이용과 시간대','이용 시간과 얼마나 겹치며, 어떤 요일과 시간대에 반복될까?'],
['열차 운행과의 관계','위험도가 높은 후보 중 운행 변화에 더 반응하는 역이 있을까?'],
['역별 관리 방향','이 결과를 바탕으로 무엇을 먼저 점검하면 좋을까?']
].forEach(([a,b],i)=>{text(s,'0'+(i+1),65,160+i*116,85,60,42,true,green);text(s,a,170,155+i*116,1010,45,30,true);text(s,b,170,203+i*116,1010,50,26,false,gray);});

s=slide('자료와 분석 범위','outputs/management_map/validation.json\noutputs/operation_change/tables/source_coverage.csv\n원자료 출처는 마지막 장 및 Word 9절 참조.','자료 범위와 품질은 상세 Word 1절 참조');
table(s,['자료','분석에 사용한 범위'],[
['승강장 PM2.5','2022~2024년 57개 지점의 시간별 초미세먼지 농도'],
['실외 농도와 승하차량','동일 시간 표기의 역별 결합자료'],
['기상과 공휴일','기온·습도·풍속 등을 고려한 비교'],
['열차 시간표','개편 전 보관본과 2024년 10월 7일 당시 공식 시간표'],
['2025년과 2026년','각각 확보된 1~4월 시간대별 프로필의 보조 검토']
],[285,875],150,410,24);
text(s,'미세먼지·이용량·날씨 자료를 역과 시간에 맞춰 연결했다. PM2.5는 초미세먼지를 뜻한다.',65,590,1140,55,23,false,gray);

s=slide('종합 관리 위험도의 세 관점',`${riskSrc}\noutputs/management_map/risk_reference.json\n탐색 고농도 경계 43.15 µg/m³. 법정 기준 아님. 동률 중간 순위, 각 1/3 가중치.`);
table(s,['관점','쉽게 읽는 방법'],[
['고농도 발생 빈도','측정된 시간 중 높은 농도가 나타난 시간의 비율'],
['다음 시간 유지','농도가 높아진 뒤 다음 시간에도 높은 상태가 이어진 비율'],
['이용 겹침','전체 승하차량 중 높은 농도의 시간에 겹친 비중']
],[300,860],160,295,27);
text(s,'고농도는 43.15 µg/m³ 이상으로 구분했다.\n세 비율을 0~100점으로 바꿔 같은 비중으로 평균했다.',65,495,1140,100,26);
text(s,'사용한 기법: 백분위 순위 변환과 동일 가중치 종합지수',65,610,1140,40,23,false,gray);

s=slide('지도에서 본 역별 관리 우선도',`${riskSrc}\noutputs/management_map/stations.json\n위치 KRIC 역 대표 좌표. 배경 통계청 2013 경계 가공본. 현충로·율하 지도용 잠정 위치. 지도 번호는 기존 57개 지점 순서와 일치.`,'2022~2024년 종합 관리 위험도');
s.images.add({blob:new Uint8Array(await fs.readFile(path.join(B,'risk_map_noto.png'))),contentType:'image/png',alt:'대구 57개 측정지점의 종합 관리 위험도 지도',fit:'contain',crop:{left:0,top:190/1800,right:700/2400,bottom:160/1800},position:{left:45,top:130,width:660,height:520}});
text(s,'색으로 살펴보는 관리 우선도',750,150,470,80,28,true);
const mappedStations=JSON.parse(await fs.readFile(path.join(workspace,'outputs/management_map/stations.json'),'utf8'));
const merc=(a,b)=>[a*Math.PI/180,-Math.log(Math.tan(Math.PI/4+b*Math.PI/360))];
const mp=mappedStations.map(a=>merc(a.lon,a.lat)),xs=mp.map(a=>a[0]),ys=mp.map(a=>a[1]);
const minx=Math.min(...xs),maxx=Math.max(...xs),miny=Math.min(...ys),maxy=Math.max(...ys);
const sc=Math.min(1520/(maxx-minx),1210/(maxy-miny));
for(const [id,label,dx,dy] of [['DG_L1_1190','월배',-18,16],['DG_L1_1340','신천',4,-31],['DG_L2_2220','이곡',-25,18],['DG_L2_2280','반고개',-52,-30],['DG_L2_2400','신매',-33,17]]){
  const a=mappedStations.find(a=>a.analysis_station_id===id),[mx,my]=merc(a.lon,a.lat);
  const xx=45+(850+(mx-(minx+maxx)/2)*sc)/1700*660;
  const yy=130+(910+(my-(miny+maxy)/2)*sc-190)/1450*520;
  text(s,label,xx+dx,yy+dy,110,35,22,true);
}
text(s,'초록  낮은 편',750,225,440,42,26,true,'#278352');text(s,'주황  중간',750,270,440,42,26,true,'#B66C13');text(s,'빨강  높은 편',750,315,440,42,26,true,'#BF4940');
text(s,'초록 <33점 · 주황 33~67점 미만\n빨강 67점 이상',750,365,470,65,21,false,gray);
text(s,'여러 비교에서 유지된 우선 후보',750,455,470,50,26,true);
text(s,'월배  신천  이곡\n반고개  신매',750,510,470,105,32,false,green);
text(s,'인터랙티브 지도 HTML을 제출 파일에 첨부했습니다.',65,645,1100,35,22,false,gray);

s=slide('관리 우선 후보의 종합점수',`${riskSrc}\n점수 0~100, 2022~2024년 자료. 동률을 포함한 기본 상위 10개 지점. 모두 상대 점수이며 건강 위해 등급이 아니다.`);
const chartOwner=deck.slides.items.length;
const chart=s.charts.add('bar',{position:{left:60,top:145,width:1140,height:465},categories:[...c.top].reverse().map(r=>r.name),series:[{name:'종합점수',values:[...c.top].reverse().map(r=>Number(Number(r.score).toFixed(1))),fill:green}],barOptions:{direction:'bar',grouping:'clustered',gapWidth:45},hasLegend:false,dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.0',textStyle:{typeface:F,fontSize:21}},xAxis:{min:0,max:100,majorUnit:20,textStyle:{typeface:F,fontSize:21}},yAxis:{textStyle:{typeface:F,fontSize:23}},chartFill:'#FCFAF5',plotAreaFill:'#FCFAF5'});
applyPresentationChartFont(chart,{fontFamily:F});
text(s,'45가지 가중치 비교에서 모두 상위 10개에 포함',65,610,1140,35,23,false,gray);text(s,'월배  신천  이곡  반고개  신매',65,646,1080,42,28,true,green);

s=slide('후보 역의 고농도 패턴',`${riskSrc}\n발생 빈도·다음 시간 유지·이용 겹침은 각기 분모가 다르다. 동일한 비율이나 실제 노출량으로 해석하지 않는다.`);
const patternTable=table(s,['후보 역','발생 빈도','다음 시간 유지','이용 겹침'],c.top.map(r=>[r.name,`${(r.rate*100).toFixed(1)}%`,`${(r.stay*100).toFixed(1)}%`,`${(r.overlap_rate*100).toFixed(1)}%`]),[330,260,300,270],145,450,22);
for(const [i,j] of [[1,1],[7,2],[4,3]]){patternTable.getCell(i,j).fill='#D9E9CF';patternTable.getCell(i,j).text.style={fontSize:22,typeface:F,bold:true,color:green};}
text(s,'성서산업단지는 이용 겹침 25.0%, 반고개는 다음 시간 유지 58.5%로 특성이 다르다.',65,620,1140,40,23);

for(let half=0;half<2;half++){
s=slide(`반복적으로 확인할 시간대 ${half+1}`,`${riskSrc}\noutputs/management_map/timing_evidence.csv\n3년 중 2년 이상 반복 조건 통과. 색칠한 칸은 반복 시간대이며 빈칸은 선정 조건을 통과하지 않은 구간. 원래 시간대 문자열: `+c.top.slice(half*5,half*5+5).map(r=>r.name+': '+r.timing).join(' / '));
text(s,'평일',315,150,400,45,28,true,green);text(s,'주말',815,150,400,45,28,true,green);
const bands=['아침 06~09시','낮 10~15시','저녁 16~19시','밤 20~23시'];
const ts=c.top.slice(half*5,half*5+5);
const headers=['후보 역',...['평일','주말'].flatMap(d=>bands.map(a=>a.replace(' ','\n').replace('시','')))];
const values=ts.map(r=>[r.name,...['평일','주말'].flatMap(d=>bands.map(a=>r.timing.includes(d+' '+a)?'반복':''))]);
const tt=table(s,headers,values,[240,...Array(8).fill(115)],210,350,22);
for(let i=1;i<6;i++)for(let j=1;j<9;j++)if(values[i-1][j]){tt.getCell(i,j).fill=green;tt.getCell(i,j).text.style={fontSize:22,typeface:F,color:'#FFFFFF',bold:true};}
text(s,'초록색 칸은 3년 중 2년 이상 반복 조건을 통과한 시간대',65,592,1140,44,25,true,green);
text(s,'전체 57개 지점 중 44개에서 반복 시점을 확인했다.',65,637,1090,40,23,false,gray);
}

s=slide('열차 운행과 농도의 관계를 살펴본 방법',`${effectSrc}\ndata/_scripts/analyze_operation_change.py\n지점별 날짜 고정효과, 연도별 시간대 효과, 공통 개편 전후 시간대 효과, 외기·기상 조건 조정. 삼중차분 형태의 운행 시간표 변화 비교.`);
text(s,'2024년 10월 7일 오후 혼잡 운행시간 변경을 활용했다.',65,142,1150,60,28,false,gray);
[
['변화 비교','열차가 늘어난 시간과 줄어든 시간의 농도 변화를 비교했다.'],
['과거와 대조','이전 두 해, 같은 계절의 변화도 함께 살펴봤다.'],
['조건 고려','외부 미세먼지와 날씨, 날짜·시간대 차이를 함께 고려했다.']
].forEach(([a,b],i)=>{text(s,'0'+(i+1),65,244+i*102,80,55,38,true,green);text(s,a,165,242+i*102,260,50,29,true);text(s,b,420,242+i*102,790,84,27);});
text(s,'삼중차분  ·  고정효과 회귀분석  ·  민감도 분석',65,592,1150,50,28,true,green);

s=slide('후보 역별로 살펴볼 점',`${effectSrc}\n이곡·성서산업단지의 양의 반응 양상을 재검토 후보로 사용. 근거의 불확실성과 가짜 사건 검토는 마지막 한계 페이지와 Word 상세 수치에 명시.`);
table(s,['후보 역','분석에서 보인 모습','관리와 연결할 점'],[
['이곡 성서산업단지','운행 변화와 함께 농도가 움직이는 양상을 우선 살펴볼 후보','선로 주변 먼지와 열차풍을 먼저 점검'],
['강창 고산','운행 관련 양상을 함께 비교할 추가 후보','실제 열차 통과 시간과 농도 흐름을 대조'],
['신천 반고개','반복·유지·이용 겹침이 함께 높은 우선 후보','아침·밤 시간의 공조와 누적 먼지 점검'],
['월배 신매 사월','아침 또는 밤에 고농도가 반복되는 후보','실내외 농도 차이와 공조 운전 상태 확인']
],[300,470,390],155,400,25);
text(s,'위험도로 관리 관심 대상을 고르고, 운행 관련 반응으로 점검 방향을 보완한다.',65,595,1140,60,26);

s=slide('후보별 관리 방향',`${riskSrc}\n${effectSrc}\n아래 내용은 관측에 근거한 점검 제안이며 실제 시행하거나 효과를 검증한 관리 조치가 아니다.`);
table(s,['후보 묶음','우선 검토할 내용'],[
['이곡 성서산업단지','선로 주변에 쌓인 먼지와 열차풍으로 먼지가 날리는 상태 점검'],
['강창 고산','열차가 지나가는 시간과 농도 변화가 겹치는지 확인'],
['신천 반고개','반복 시간대의 공조·필터 상태와 누적 먼지를 함께 점검'],
['월배 신매 사월','아침·밤 패턴을 반영하고 실내외 농도 차이와 공조 조건을 대조'],
['만촌','평일 저녁의 공조·필터·누적 먼지 상태 확인']
],[320,840],155,400,24);
text(s,'한 가지 조치부터 적용하고, 비슷한 외부 농도와 운행 조건에서 전후의 고농도 패턴을 비교한다.',65,590,1140,70,23,false,gray);

s=slide('자료 출처',c.sources.map(a=>a.join('\n')).join('\n\n')+'\n서체 Noto Sans KR SIL OFL 1.1 https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/LICENSE');
table(s,['주요 자료','제공 기관과 공개 경로'],[
['승강장 실내 공기질','InAir 실내공기질 관리 종합정보망'],
['실외 공기질','AirKorea 과거 대기질 자료'],
['역별 시간대 승하차','대구교통공사 공공데이터포털'],
['기상과 운행 시간표','NOAA NCEI 및 대구교통공사 공식 공지·공공데이터'],
['상세 근거 문서','자료 범위·계산 방법·역별 수치·비교 조건에 따른 변화']
],[330,830],155,390,24);
text(s,'자료 출처 URL은 동봉 Word 9절, 계산 과정과 역별 수치는 2~6절에서 확인할 수 있다.',65,585,1140,75,24);

s=slide('분석의 한계와 해석 범위','운행 반응의 상세 수치·다중검정 보정·가짜 사건 비교·자료 품질은 동봉 Word와 outputs/operation_change/분석메모.md 참조. 이 페이지에 본문 해석의 한계를 모았다.');
const edited=JSON.parse(await fs.readFile(path.join(B,'user_limitations.json'),'utf8'));
const gap=Math.min(150,460/Math.max(1,edited.length));
edited.forEach((v,i)=>{text(s,String(i+1).padStart(2,'0'),65,160+i*gap,75,60,36,true,green);text(s,v,165,157+i*gap,1025,gap-15,27);});

await fs.mkdir(path.join(B,'slides_v6'),{recursive:true});
await fs.writeFile(path.join(B,'slide_manifest_v6.json'),JSON.stringify(manifests,null,2));
for(let i=0;i<deck.slides.items.length;i++){
  const blob=await deck.export({slide:deck.slides.items[i],format:'png',scale:1});
  await fs.writeFile(path.join(B,'slides_v6',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await blob.arrayBuffer()));
  console.log('render',i+1);
}
const candidate=path.join(B,'candidate_v6.pptx');await(await PresentationFile.exportPptx(deck)).save(candidate);
const output=path.join(O,'대구_도시철도_미세먼지_뉴스배경_제출용.pptx');
await fs.mkdir(path.join(workspace,'outputs/_submission_draft_validation'),{recursive:true});
await finalizePresentation({workspaceDir:workspace,candidatePath:candidate,finalPath:output,pythonExecutable:runtime+'/python/python.exe',integrityValidatorPath:SKILL+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:SKILL+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...owners.flatMap(n=>['--require-native-table-slide',String(n)])],requiredNativeTableOwnerSlides:owners,requiredNativeChartOwnerSlides:[chartOwner],materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[F,'Noto Serif KR'],scriptFonts:{ea:F}},verifyArtifactToolImport:true,receiptPath:path.join(workspace,'outputs/_submission_draft_validation/deck_validation_v6.json')});
console.log('DONE',output);
