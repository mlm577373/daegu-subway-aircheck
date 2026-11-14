"""Build join-key metadata only. Does not merge or alter observation records."""
from pathlib import Path
import csv,json,re,collections,datetime as dt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'mapping';OUT.mkdir(exist_ok=True)

def save(name,rows,fields=None):
    fields=fields or list(rows[0])
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def normalized(name,line):
    name=name.strip().replace('(대구)','')
    transfer={'명덕1':'명덕','반월당1':'반월당','반월당2':'반월당','청라언덕2':'청라언덕'}
    if name in transfer:
        assert name[-1]==line
        name=transfer[name]
    return {'대공원':'수성알파시티'}.get(name,name)

def main():
    inventory={};hours=set();directions=set();source_rows=0
    for path in sorted((ROOT/'ridership'/'prepared').glob('*.csv')):
        with path.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f)
            hours.update(h for h in reader.fieldnames if re.fullmatch(r'h\d{2}_\d{2}',h))
            for r in reader:
                source_rows+=1;directions.add(r['direction'])
                key=(r['line'],r['station_code'],r['station_name'])
                if key not in inventory:inventory[key]={'first':r['date'],'last':r['date'],'rows':0,'files':set()}
                x=inventory[key];x['first']=min(x['first'],r['date']);x['last']=max(x['last'],r['date']);x['rows']+=1;x['files'].add(path.name)
    aliases=[];candidates=collections.defaultdict(set)
    for (line,code,name),x in sorted(inventory.items()):
        norm=normalized(name,line);candidates[(line,norm)].add(code)
        aliases.append({'ridership_line':line,'ridership_station_code':code,'observed_station_name':name,'normalized_match_name':norm,'first_observed_date':x['first'],'last_observed_date':x['last'],'observed_rows':x['rows'],'source_files':';'.join(sorted(x['files'])),'date_note':'observed label dates; not official name validity dates'})
    save('ridership_station_aliases.csv',aliases)
    with (ROOT/'subway_air'/'stations.csv').open(encoding='utf-8-sig',newline='') as f:indoor=list(csv.DictReader(f))
    maps=[];issues=[];selected=set()
    for s in indoor:
        line=s['line'].replace('호선','');norm=normalized(s['station_name'],line)
        codes=candidates[(line,norm)]
        if len(codes)!=1:
            issues.append({'indoor_station_code':s['station_code'],'line':line,'name':s['station_name'],'candidate_codes':';'.join(sorted(codes))});continue
        code=next(iter(codes));selected.add((line,code))
        rows=[r for r in aliases if r['ridership_line']==line and r['ridership_station_code']==code]
        names=sorted(set(r['observed_station_name'] for r in rows))
        method='exact_name_and_line' if names==[s['station_name']] else 'explicit_alias_and_line'
        if s['station_code']=='A1222C':method='same_ridership_code_with_official_rename'
        maps.append({'analysis_station_id':f'DG_L{line}_{code}','indoor_station_code':s['station_code'],'indoor_line':s['line'],'indoor_station_name':s['station_name'],'canonical_match_name':norm,'ridership_line':line,'ridership_station_code':code,'ridership_observed_names':';'.join(names),'first_ridership_date':min(r['first_observed_date'] for r in rows),'last_ridership_date':max(r['last_observed_date'] for r in rows),'match_method':method,'verification_status':'unambiguous_in_current_local_files','location':s['location'],'address':s['address'],'latitude':'','longitude':'','outdoor_station_code':'','station_key_ready':1,'hourly_join_ready':0,'note':'time-anchor and outdoor mapping not confirmed'})
    save('station_crosswalk.csv',maps)
    unused=[r for r in aliases if (r['ridership_line'],r['ridership_station_code']) not in selected]
    save('ridership_stations_outside_indoor_scope.csv',unused)
    save('station_match_issues.csv',issues,['indoor_station_code','line','name','candidate_codes'])
    assert len(maps)==len(indoor)==57 and not issues
    for col in ['analysis_station_id','indoor_station_code']:
        assert len(set(r[col] for r in maps))==57
    assert len(set((r['ridership_line'],r['ridership_station_code']) for r in maps))==57
    assert {r['ridership_station_code'] for r in maps if r['indoor_station_code'] in ('A1116C','A1214C')}=={'1300','2300'}

    base=dt.datetime(2025,1,1);time_rows=[]
    def stamp(t):return t.isoformat(timespec='minutes')
    for dataset in ['subway_air','outdoor_air']:
        for hour in (range(24) if dataset=='subway_air' else range(1,25)):
            label=base+dt.timedelta(hours=hour)
            raw=f'2025-01-01:{hour:02}' if dataset=='subway_air' else f'2025-01-01 {hour:02}'
            time_rows.append({'dataset':dataset,'source_hour':hour,'source_label_example':raw,'calendar_label_time':stamp(label),'interval_start_confirmed':'','interval_end_confirmed':'','candidate_start_if_start_label':stamp(label),'candidate_end_if_start_label':stamp(label+dt.timedelta(hours=1)),'candidate_start_if_end_label':stamp(label-dt.timedelta(hours=1)),'candidate_end_if_end_label':stamp(label),'status':'average_interval_anchor_unverified','timezone_convention':'Asia/Seoul; confirm provider metadata','allow_hourly_join':0})
    for h in sorted(hours):
        start,end=map(int,re.findall(r'\d+',h));a=base+dt.timedelta(hours=start);b=base+dt.timedelta(hours=end)
        time_rows.append({'dataset':'ridership','source_hour':start,'source_label_example':h,'calendar_label_time':'','interval_start_confirmed':stamp(a),'interval_end_confirmed':stamp(b),'candidate_start_if_start_label':'','candidate_end_if_start_label':'','candidate_start_if_end_label':'','candidate_end_if_end_label':'','status':'explicit_hour_band; boundary inclusion not specified','timezone_convention':'Asia/Seoul; working local convention','allow_hourly_join':0})
    save('time_crosswalk_examples.csv',time_rows)
    assert len(time_rows)==67 and len(hours)==19
    assert next(r for r in time_rows if r['dataset']=='outdoor_air' and r['source_hour']==24)['calendar_label_time']=='2025-01-02T00:00'
    assert next(r for r in time_rows if r['source_label_example']=='h23_24')['interval_end_confirmed']=='2025-01-02T00:00'
    summary={'created':'2026-11-14','scope':'mapping metadata only; no observation merge performed','indoor_stations':len(indoor),'unique_mapped_stations':len(maps),'ambiguous_station_matches':len(issues),'ridership_station_codes_scanned':len(set((r['ridership_line'],r['ridership_station_code']) for r in aliases)),'ridership_rows_scanned':source_rows,'outside_scope_station_codes':len(set((r['ridership_line'],r['ridership_station_code']) for r in unused)),'station_match_methods':dict(collections.Counter(r['match_method'] for r in maps)),'time_example_rows':len(time_rows),'ridership_hour_bands':len(hours),'directions':sorted(directions),'hourly_join_ready':False,'open_items':['confirm indoor hourly averaging interval anchor','confirm outdoor hourly averaging interval anchor','acquire and validate station and outdoor coordinates before outdoor assignment']}
    (OUT/'mapping_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=True,indent=2))

if __name__=='__main__':main()
