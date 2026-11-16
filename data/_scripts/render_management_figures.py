"""Render two report-ready figures from the map's exact saved evidence."""
from pathlib import Path
import json, math
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'outputs/management_map'
stations=json.loads((OUT/'stations.json').read_text(encoding='utf-8'))
BG='#ffffff'; INK='#172d42'; MUTED='#566b7d'; LINE='#d6e0e7'
COLORS=['#27834b','#d08a24','#c84335','#9e3030','#87939d']
LEVELS=['반복 고농도 <5%','반복 고농도 5~10%','반복 고농도 10~20%','반복 고농도 ≥20%','관측 부족']
def font(size,bold=False):return ImageFont.truetype('C:/Windows/Fonts/'+('malgunbd.ttf' if bold else 'malgun.ttf'),size)
def text(draw,xy,s,size=24,fill=INK,bold=False):draw.text(xy,s,font=font(size,bold),fill=fill)
VIEW='composite'
def color(s):
    v=s['perspectives'][VIEW]
    cuts=[.33,.67] if VIEW=='composite' else [.25,.5,.75] if VIEW=='persistence' else [.05,.1,.2]
    return COLORS[sum(v['value']>=c for c in cuts) if v['available'] and v['value'] is not None else 4]
def new(w,h,title,subtitle):
    im=Image.new('RGB',(w,h),BG);dr=ImageDraw.Draw(im)
    text(dr,(65,45),title,48,bold=True);text(dr,(68,117),subtitle,26,MUTED)
    return im,dr
def project(lon,lat):return math.radians(lon),-math.log(math.tan(math.pi/4+math.radians(lat)/2))

def map_figure():
    im,dr=new(2400,1800,'종합 관리 위험도: 어디부터 확인할까','대구 지하철 승강장 57개 측정지점 · 2022~2024년 1~12월 · 전체 도시철도 역 조사 아님')
    # Mercator projection; preserve aspect ratio rather than stretching latitude/longitude.
    raw=[project(s['lon'],s['lat']) for s in stations]
    minx,maxx=min(x for x,y in raw),max(x for x,y in raw);miny,maxy=min(y for x,y in raw),max(y for x,y in raw)
    scale=min(1520/(maxx-minx),1210/(maxy-miny)); cx=(minx+maxx)/2;cy=(miny+maxy)/2
    def pos(lon,lat):
        x,y=project(lon,lat);return (int(850+(x-cx)*scale),int(910+(y-cy)*scale))
    layer=Image.new('RGB',(1700,1450),'#f6f8fa');ld=ImageDraw.Draw(layer)
    geo=json.loads((OUT/'sources/local_context.geojson').read_text(encoding='utf-8'))
    district_labels=[]
    for f in geo['features']:
        if f['geometry']['type'] not in ['Polygon','MultiPolygon']:continue
        polygons=f['geometry']['coordinates'] if f['geometry']['type']=='MultiPolygon' else [f['geometry']['coordinates']]
        for poly in polygons:
            pts=[(pos(*p)[0],pos(*p)[1]-190) for p in poly[0]]
            ld.polygon(pts,fill='#edf1f4',outline=LINE,width=2)
            visible=[p for p in pts if 100<p[0]<1600 and 180<p[1]<1300]
            if visible:
                x=sum(p[0] for p in visible)/len(visible);y=sum(p[1] for p in visible)/len(visible)
                district_labels.append((x,y,f['properties']['name']))
    for x,y,name in district_labels:text(ld,(x,y),name,26,'#9caab5')
    im.paste(layer,(0,190));dr=ImageDraw.Draw(im)
    # Number callouts use a deterministic non-overlap search; exact locations remain dots.
    occupied=[]
    for i,s in enumerate(stations,1):
        x,y=pos(s['lon'],s['lat']);r=9
        dr.ellipse((x-r,y-r,x+r,y+r),fill=color(s),outline=BG,width=2)
        candidates=[]
        for radius in [24,44,64,88,112]:
            for j in range(12):
                a=j*math.pi/6; xx=int(x+radius*math.cos(a));yy=int(y+radius*math.sin(a))
                box=(xx-19,yy-17,xx+19,yy+17)
                overlaps=sum(not(box[2]<b[0] or box[0]>b[2] or box[3]<b[1] or box[1]>b[3]) for b in occupied)
                candidates.append((overlaps*10000+radius,xx,yy,box))
        _,xx,yy,box=min(candidates);occupied.append(box)
        dr.line((x,y,xx,yy),fill='#9aa9b4',width=2)
        dr.rounded_rectangle(box,5,fill=BG,outline=color(s),width=2)
        label=f'{i:02d}';bbox=dr.textbbox((0,0),label,font=font(20,True))
        text(dr,(xx-(bbox[2]-bbox[0])/2,yy-15),label,20,color(s),True)
    text(dr,(85,215),'북 ↑',25,MUTED)
    # 5 km scale at mid-latitude, computed in projection coordinates.
    km5=5000/(6371000*math.cos(math.radians(35.86)))*scale
    dr.line((90,1540,90+km5,1540),fill=INK,width=4);text(dr,(90,1550),'5 km',22)
    text(dr,(1740,190),'지도 번호 / 호선별 측정지점',25,bold=True)
    for i,s in enumerate(stations,1):
        y=245+(i-1)*23
        dr.ellipse((1740,y+5,1752,y+17),fill=color(s))
        text(dr,(1770,y),f'{i:02d}  {s["line"]}  {s["name"]}'+(' *' if '잠정' in s['coordinate_note'] else '')+f'   {s["risk_score"]:.1f}점',20)
    y=1635
    for j,l in enumerate(['낮은 편 <33점','중간 33~67점 미만','높은 편 ≥67점','판단 유보']):
        x=65+j*455;dr.ellipse((x,y+8,x+20,y+28),fill=COLORS[j if j<3 else 4]);text(dr,(x+32,y),l,23)
    text(dr,(65,1685),'세 관점의 백분위 점수 평균(동일 비중) · 상대적인 관리 지표이며 건강 위해 확률·법정 위험등급 아님',23,MUTED)
    text(dr,(65,1724),'위치: KRIC · * 현충로·율하 지도용 잠정 대체 위치 · 배경: 통계청 2013 경계 가공본(현재 경계와 다를 수 있음)',21,MUTED)
    return im

def three_maps():
    global VIEW
    im,dr=new(3000,1720,'종합 관리 위험도: 어디부터 확인할까','자료가 있는 57개 지점 · 관측률 75% 적용 · 색은 2022~2024년 1~12월 비율 중 낮은 값')
    definitions=[('frequency','① 얼마나 자주 나타났나','고농도 시간 / 유효 관측 시간',[5,10,20]),('persistence','② 다음 시간에도 유지됐나','1시간 뒤에도 고농도 / 다음 시간 평가 가능',[25,50,75]),('overlap','③ 이용과 얼마나 겹쳤나','고농도 시간 승하차량 / 동시 관측 전체 승하차량',[5,10,20])]
    for j,(key,title,formula,cuts) in enumerate(definitions):
        VIEW=key;panel=map_figure().crop((0,190,1700,1640));panel=panel.resize((950,810),Image.Resampling.LANCZOS)
        x=35+j*1000
        text(dr,(x,192),title,34,bold=True);text(dr,(x,247),formula,23,MUTED)
        im.paste(panel,(x,292));dr=ImageDraw.Draw(im)
        labels=[f'<{cuts[0]}%',f'{cuts[0]}~{cuts[1]}%',f'{cuts[1]}~{cuts[2]}%',f'≥{cuts[2]}%','판단 유보']
        for k,l in enumerate(labels):
            xx=x+k*188;dr.ellipse((xx,1120,xx+17,1137),fill=COLORS[k]);text(dr,(xx+24,1109),l,22)
    VIEW='frequency'
    for i,s in enumerate(stations):
        col=i//19;row=i%19
        text(dr,(65+col*980,1180+row*23),f'{i+1:02d} {s["line"]} {s["name"]}',21)
    text(dr,(65,1630),'고농도: 43.15 μg/m³ 이상(탐색 기준). 지속은 시간 간 연결 비율이며 사건별 지속시간이 아닙니다. 이용 겹침은 실제 노출 인원·인과효과가 아닙니다.',22,MUTED)
    text(dr,(65,1670),'관측량 또는 분모가 부족하면 회색. 현충로·율하는 지도용 잠정 위치. 배경: 통계청 2013 경계 가공본. 색 구간은 안전·위험 등급이 아닙니다.',22,MUTED)
    im.save(OUT/'management_map.png',dpi=(300,300))
    return im

def timing_figure():
    im,dr=new(2600,2180,'어느 요일·시간대에 관리 확인을 강화할까','57개 측정지점 동일 기준 · 과거 2022~24년과 최근 2022~2024년 1~12월에서 반복된 구간만 표시')
    slots=['아침 06~09시','낮 10~15시','저녁 16~19시','밤 20~23시']
    for panel,line in enumerate(['1호선','2호선']):
        left=60+panel*1290; group=[s for s in stations if s['line']==line]
        text(dr,(left,190),line,32,bold=True)
        for day_i,day in enumerate(['평일','주말']):
            text(dr,(left+282+day_i*260,236),day,25,bold=True)
            for j,l in enumerate(['아침','낮','저녁','밤']):text(dr,(left+277+day_i*260+j*65,279),l,21)
        text(dr,(left+810,236),'고농도 비율',24,bold=True)
        text(dr,(left+800,279),'2022 / 23 / 24',21)
        text(dr,(left+1010,236),'연도 관측률',24,bold=True)
        text(dr,(left+1010,279),'2022 / 23 / 24',21)
        for row,s in enumerate(group):
            y=326+row*50;index=stations.index(s)+1
            if row%2==0:dr.rectangle((left,y-2,left+1210,y+46),fill='#f5f7f9')
            text(dr,(left,y),f'{index:02d} {s["name"]}',23,bold=True)
            if not s['chosen']:text(dr,(left+10,y+25),'집중 시점 없음' if s['sufficient'] else '관측 부족·판단 유보',17,MUTED)
            for di,day in enumerate(['평일','주말']):
                for j,slot in enumerate(slots):
                    x=left+282+di*260+j*65;yes={'day':day,'slot':slot} in s['chosen']
                    dr.rectangle((x,y+6,x+44,y+36),fill=color(s) if yes else '#e2e8ed')
                    if yes:text(dr,(x+12,y+5),'●',21,BG)
                    elif not s['sufficient']:text(dr,(x+14,y+3),'×',22,'#6c7e8d')
            p=s['periods'][:3]; rates=' / '.join(f'{100*x["rate"]:.1f}%' for x in p)
            cov=' / '.join(f'{100*x["coverage"]:.0f}%' for x in p)
            text(dr,(left+800,y+8),rates,17,MUTED if not s['sufficient'] else INK)
            text(dr,(left+1010,y+8),cov,17,MUTED)
    text(dr,(65,1980),'● 반복 관리 확인 시점   빈칸: 채택 근거 부족   ×: 관측 부족·판단 유보   |   아침 06~09 · 낮 10~15 · 저녁 16~19 · 밤 20~23시',24)
    counts=json.loads((OUT/'validation.json').read_text(encoding='utf-8'))
    text(dr,(65,2025),f'{counts["timing_stations"]}곳 집중 시점 확인 · {counts["no_distinct_timing"]}곳 뚜렷한 집중 시점 없음 · {counts["insufficient"]}곳 관측 부족. 집중 시점이 없다고 관리가 불필요한 것은 아닙니다.',24,MUTED)
    text(dr,(65,2070),'구간 고농도 비율 ≥5%, 나머지 시간보다 ≥3%p·≥1.25배, 관측량·연도/월 반복 요건 적용. 24시간 고농도 비율과 시점 판정은 별개입니다.',22,MUTED)
    text(dr,(65,2110),'토·일을 주말로 구분(공휴일 별도 구분 없음). 3년 연중 탐색 결과이며 연중 권고·인과효과·통계적 유의성 판정이 아닙니다.',22,MUTED)
    im.save(OUT/'management_timing.png',dpi=(300,300))
    return im

if __name__=='__main__':
    a,b=map_figure(),timing_figure()
    a.save(OUT/'management_map.png',dpi=(300,300))
    a.thumbnail((1100,825));b.thumbnail((1100,925))
    preview=Image.new('RGB',(2200,925),BG);preview.paste(a,(0,0));preview.paste(b,(1100,0));preview.save(OUT/'figures_preview.png')
    print('Two PNG figures written at 300 dpi; preview written.')
