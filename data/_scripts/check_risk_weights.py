"""Weight sensitivity for the existing baseline risk index; no report edits."""
from pathlib import Path
import json,hashlib
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/management_map'
s=json.loads((OUT/'stations.json').read_text(encoding='utf-8'))
rows=[]
for r in s:
    p=next(p for p in r['periods'] if p['period']=='2022~24')
    rows.append({'id':r['analysis_station_id'],'line':r['line'],'name':r['name'],'timing':r['timing'],'score':r['risk_score'],**r['risk_components'],'rate':p['rate'],'stay':p['continuation_rate'],'overlap_rate':p['usage_high_share']})
d=pd.DataFrame(rows).set_index('id');keys=['frequency','persistence','overlap']
d['score']=d.score.round(6)
base=d.score.rank(ascending=False,method='min');top10=set(d.nlargest(10,'score').index)
scenarios=[('동일 비중',1/3,1/3,1/3),('발생 빈도 강조',.5,.25,.25),('유지 강조',.25,.5,.25),('이용 겹침 강조',.25,.25,.5)]
all_scores=[];checks=[]
for label,a,b,c in scenarios:
    sc=d[keys].mul([a,b,c]).sum(axis=1).round(6)
    checks.append({'scenario':label,'frequency_weight':a,'persistence_weight':b,'overlap_weight':c,'top10_common':len(set(sc.nlargest(10).index)&top10),'rank_correlation':float(sc.rank().corr(d.score.rank())),'tier_changes':int(((sc.ge(33).astype(int)+sc.ge(67).astype(int))!=(d.score.ge(33).astype(int)+d.score.ge(67).astype(int))).sum())})
for a in range(20,61,5):
    for b in range(20,61,5):
        c=100-a-b
        if 20<=c<=60:
            score=d[keys].mul([a/100,b/100,c/100]).sum(axis=1).round(6)
            all_scores.append(score.rename(f'{a}_{b}_{c}'))
matrix=pd.concat(all_scores,axis=1)
ranks=matrix.rank(ascending=False,method='min')
out=d.copy();out['baseline_rank']=base;out['min_rank']=ranks.min(axis=1).astype(int);out['max_rank']=ranks.max(axis=1).astype(int);out['top10_fraction']=ranks.le(10).mean(axis=1)
out.sort_values('score',ascending=False).to_csv(OUT/'risk_weight_station_sensitivity.csv',encoding='utf-8-sig')
pd.DataFrame(checks).to_csv(OUT/'risk_weight_scenarios.csv',index=False,encoding='utf-8-sig')
common=set(d.index)
overlaps=[]
for col in matrix:
    t=set(matrix[col].nlargest(10).index);common &= t;overlaps.append(len(t&top10))
result={'analysis_years':[2022,2023,2024],'grid_scenarios':len(matrix.columns),'weight_range':[.2,.6],'weight_step':.05,'baseline_top10_overlap_range':[min(overlaps),max(overlaps)],'always_top10':[{'id':i,'line':d.loc[i,'line'],'name':d.loc[i,'name']} for i in sorted(common)],'named_scenarios':checks,'limitation':'Weight sensitivity only; no proof of health risk, causality or robustness to concentration thresholds and missingness.'}
(OUT/'risk_weight_sensitivity.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False),flush=True)
print(out.sort_values('score',ascending=False)[['line','name','score','frequency','persistence','overlap','rate','stay','overlap_rate','min_rank','max_rank','timing']].head(15).to_string(),flush=True)
