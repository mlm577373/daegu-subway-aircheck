"""Render the 2022-2024 baseline map; no later-year analysis."""
from pathlib import Path
import json
from baseline_management import analyze
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/management_map"
def dump(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def build_map(stations):
    allgeo=json.loads((OUT/'sources/municipalities.geojson').read_text(encoding='utf-8'))
    names={'22310':'달성군','22070':'달서구','22060':'수성구','22050':'북구','22040':'남구','22030':'서구','22020':'동구','22010':'중구','37100':'경산시'}
    features=[f for f in allgeo['features'] if f['properties']['code'] in names]
    for f in features:
        code=f['properties']['code']
        if code=='37100':assert f['properties']['name_eng']=='Gyeongsan-si'
        f['properties']={'name':names[code],'source_code':code,'source_name_eng':f['properties']['name_eng']}
    context=[]
    if (OUT/'sources/osm_context.json').exists():
        osm=json.loads((OUT/'sources/osm_context.json').read_text(encoding='utf-8'))
        for el in osm.get('elements',[]):
            pts=[[p['lon'],p['lat']] for p in el.get('geometry',[])]
            if len(pts)>1:context.append({'type':'Feature','properties':{'kind':'river' if el.get('tags',{}).get('waterway') else 'rail'},'geometry':{'type':'LineString','coordinates':pts}})
    geo={'type':'FeatureCollection','features':features}
    dump(OUT/'sources/local_context.geojson',{'type':'FeatureCollection','features':features+context})
    template=(ROOT/'data/_scripts/management_map_template.html').read_text(encoding='utf-8')
    libraries='\n'.join((OUT/'sources'/f).read_text(encoding='utf-8') for f in ['d3-array.min.js','d3-geo.min.js'])
    fragment=template.replace('__LIBRARIES__',libraries).replace('__STATIONS__',json.dumps(stations,ensure_ascii=False,allow_nan=False)).replace('__GEOMETRY__',json.dumps(geo,ensure_ascii=False)).replace('__CONTEXT__',json.dumps(context,ensure_ascii=False))
    (OUT/'map-fragment.html').write_text(fragment,encoding='utf-8')
    wrapper='<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>대구 승강장 관리 시점</title><style>:root{--background:#f5f7fa;--foreground:#18283a;--card:#fff;--card-foreground:#18283a;--muted:#e9edf2;--muted-foreground:#4c5e70;--border:#cbd4dc;--viz-series-1:#27834b;--viz-series-2:#c58b35;--viz-series-3:#bd533a;--viz-series-4:#7c3048;--viz-series-5:#667581;--blue:#5e9fb7;--font-size-base:15px}body{margin:24px auto;padding:0 20px;max-width:1250px;background:var(--background);color:var(--foreground);font:15px/1.6 system-ui,sans-serif}button,select,input{font:inherit}button,select{padding:6px 10px}button{cursor:pointer}.card{background:var(--card);padding:16px;border-radius:12px}.table{border-collapse:collapse;width:100%}.table td,.table th{padding:8px;text-align:left;border-bottom:1px solid var(--border)}.table-responsive{overflow-x:auto}.text-small{font-size:12px}.form-label{display:flex;gap:8px;align-items:center}.btn{border:1px solid var(--border);border-radius:6px;background:var(--card);color:var(--foreground)}h1,h2,h3,p{margin:0}h2{font-size:22px}h3{font-size:17px}.viz-controls,.viz-row{display:flex;gap:12px;flex-wrap:wrap}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}</style><body>'+fragment+'</body></html>'
    (OUT/'index.html').write_text(wrapper,encoding='utf-8')
    print('map written',len(fragment.encode()),'bytes; context ways',len(context),flush=True)

if __name__=='__main__':
    import sys
    build_map(json.loads((OUT/'stations.json').read_text(encoding='utf-8')) if '--map-only' in sys.argv else analyze())
