"""Current-data associations and explicitly unverified inspection hypotheses.

Dependencies: numpy, pandas, Pillow. No causal or out-of-sample claims.
"""
from pathlib import Path
import json, html
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/factor_analysis'
for folder in ['tables','figures','station_reports']:
    (OUT/folder).mkdir(parents=True,exist_ok=True)
SID='analysis_station_id'
SOURCE='https://www.canada.ca/en/health-canada/services/publications/healthy-living/guidance-improving-subway-air-quality.html'
checks=['표본·모형·가설 구분 원칙 기록','전체 역 공통 패턴·조건 고려 모형 분석','후보 17개 역별 관계와 불확실성 분석','시각화·역별 진단표·점검 가설 작성','수치·모형·그림·산출물 검증']
def progress(n,msg):
    t=f'# 현재 작업: 공통 요인·후보 역별 관계 분석과 점검 가설 정리\n\n- 상태: 진행 중\n- 진행: {n} / 5단계 완료\n- 현재 단계: {msg}\n- task.md는 로컬 진행 확인용이며 별도 커밋·푸시하지 않는다.\n- 추가 수집·Git 업로드 없음\n\n## 체크리스트\n\n'
    t+='\n'.join(f'- [{"x" if i<n else " "}] {s}' for i,s in enumerate(checks))
    t+='\n\n## 산출물\n\n- outputs/factor_analysis/plan.md\n- outputs/factor_analysis/report.md\n- outputs/factor_analysis/station_reports/\n- outputs/factor_analysis/figures/\n- outputs/factor_analysis/tables/\n'
    (ROOT/'task.md').write_text(t,encoding='utf-8-sig')
def save(df,name): df.to_csv(OUT/'tables'/f'{name}.csv',index=False,encoding='utf-8-sig')
def md(df,cols=None):
    cols=cols or list(df.columns)
    out='| '+' | '.join(cols)+' |\n|'+'|'.join(['---']*len(cols))+'|\n'
    for _,r in df.iterrows():
        out+='| '+' | '.join('평가 불가' if pd.isna(r[k]) else f'{r[k]:.3f}' if isinstance(r[k],(float,np.floating)) else str(r[k]).replace('|','/') for k in cols)+' |\n'
    return out
progress(1,'분석 계획 기록 완료; 2022~2024년 표본 구성 중')
cols=[SID,'line','station_name','date','hour','indoor_pm25','indoor_quality_flag','outdoor_pm25','board_alight_count','outdoor_station_name','outdoor_distance_km']
parts=[]
for year in [2022,2023,2024]:
    p=pd.read_csv(ROOT/f'data/merged/merged_hourly_{year}.csv',usecols=cols)
    parts.append(p); print('read',year,len(p),flush=True)
d=pd.concat(parts,ignore_index=True); del parts
dt=pd.to_datetime(d.date)
d['month']=dt.dt.month.astype('int8'); d['weekday']=dt.dt.dayofweek.astype('int8'); d['year']=dt.dt.year.astype('int16')
d['day_idx']=dt.to_numpy(dtype='datetime64[D]').astype('int64').astype('int32')
d['week_idx']=((d.day_idx+3)//7).astype('int32')
assert d.day_idx.nunique()==d.date.nunique() and d.week_idx.nunique()>150
missing_dates=pd.date_range('2022-01-01','2024-12-31').difference(pd.DatetimeIndex(dt.unique()))
save(pd.DataFrame({'date':missing_dates.astype(str),'status':'no merged rows at any station; not imputed'}),'all_station_absent_dates')
d['value']=d.indoor_pm25.where(d.indoor_quality_flag.eq('status_blank_unverified') & np.isfinite(d.indoor_pm25) & d.indoor_pm25.ge(0))
d['use_valid']=d.value.notna() & d.hour.between(5,23) & d.board_alight_count.notna() & np.isfinite(d.board_alight_count) & d.board_alight_count.ge(0)
d['out_valid']=d.use_valid & d.outdoor_pm25.notna() & np.isfinite(d.outdoor_pm25) & d.outdoor_pm25.ge(0)
meta=d[[SID,'line','station_name']].drop_duplicates().sort_values(['line',SID]).set_index(SID)
candidates=pd.read_csv(ROOT/'outputs/inspection_candidates/tables/candidate_reasons.csv').set_index(SID)
assert len(candidates)==17
raw=d.groupby(SID).value.agg(n='count',mean='mean',median='median').join(meta)
raw['base_n']=d.groupby(SID).use_valid.sum(); raw['external_n']=d.groupby(SID).out_valid.sum()
raw['base_coverage']=raw.base_n/(1096*19); raw['external_coverage']=raw.external_n/(1096*19)
raw['outdoor_station']=d.groupby(SID).outdoor_station_name.first(); raw['outdoor_distance_km']=d.groupby(SID).outdoor_distance_km.first()
save(raw.reset_index(),'sample_coverage')
for key in ['hour','month','weekday','year']:
    save(d.groupby([SID,key]).value.agg(n='count',mean='mean',median='median').reset_index().merge(meta.reset_index(),on=SID),'raw_'+key)
base=d[d.use_valid].copy()
external=d[d.out_valid].copy()
# Require at least 75% of all source-hour opportunities for both model variants.
base_ids=raw.index[raw.base_coverage.ge(.75)].tolist()
ext_ids=raw.index[raw.external_coverage.ge(.75)].tolist()
base=base[base[SID].isin(base_ids)]
external=external[external[SID].isin(ext_ids)]
assert set(ext_ids)<=set(base_ids)

def specification(ext):
    names=['log2_usage_plus1']
    groups={'이용 규모':['log2_usage_plus1']}
    if ext:
        names+=['outdoor_per10','outdoor_hinge20_per10','outdoor_hinge40_per10']
        groups['실외 농도']=names[1:].copy()
    for key,values,label in [('hour',range(6,24),'시간대'),('month',range(2,13),'월'),('weekday',range(1,7),'요일'),('year',[2023,2024],'연도')]:
        nm=[f'{key}_{i}' for i in values]; names+=nm; groups[label]=nm
    return names,groups
def design(g,ext):
    arr=[np.log2(g.board_alight_count.to_numpy(float)+1)]
    if ext:
        o=g.outdoor_pm25.to_numpy(float)
        arr += [o/10,np.maximum(o-20,0)/10,np.maximum(o-40,0)/10]
    for key,values in [('hour',range(6,24)),('month',range(2,13)),('weekday',range(1,7)),('year',[2023,2024])]:
        a=g[key].to_numpy(); arr += [(a==i).astype(float) for i in values]
    return np.column_stack(arr)
def scores(X,res,clusters):
    _,idx=np.unique(clusters,return_inverse=True)
    sc=np.column_stack([np.bincount(idx,weights=X[:,j]*res) for j in range(X.shape[1])])
    return sc
def cov_cluster(X,res,clusters,bread,dfparams):
    sc=scores(X,res,clusters); G=len(sc); n=len(res)
    correction=G/max(G-1,1)*(n-1)/max(n-dfparams,1)
    cov=bread@(sc.T@sc)@bread*correction
    return (cov+cov.T)/2,G
def fit_stats(A,z,yy):
    bread=np.linalg.pinv(A,rcond=1e-11); b=bread@z
    rss=max(float(yy-2*b@z+b@A@b),0)
    return b,bread,rss
def partials(A,z,yy,rss,names,groups):
    rows=[]
    for label,features in groups.items():
        keep=[i for i,x in enumerate(names) if x not in features]
        _,_,red=fit_stats(A[np.ix_(keep,keep)],z[keep],yy)
        value=(red-rss)/red if red>1e-8 else np.nan
        rows.append((label,float(value),float(red-rss)))
    return rows
def contrast(b,cov,vector):
    effect=float(vector@b); se=float(np.sqrt(max(vector@cov@vector,0)))
    return effect,effect-1.96*se,effect+1.96*se,se
def contrast_vectors(names,ext):
    vectors={}
    v=np.zeros(len(names)); v[names.index('log2_usage_plus1')]=1; vectors['승하차+1 두 배']=v
    if ext:
        v=np.zeros(len(names)); v[names.index('outdoor_per10')]=1; vectors['실외 10→20']=v
        v=v.copy(); v[names.index('outdoor_hinge20_per10')]=1; vectors['실외 20→30']=v
        v=v.copy(); v[names.index('outdoor_hinge40_per10')]=1; vectors['실외 40→50']=v
    return vectors

coef_rows=[]; effect_rows=[]; partial_rows=[]; fit_rows=[]; adjusted_rows=[]; profiles=[]; bins=[]
local={}; global_models={}; max_orth=0
def analyze(frame,ext,label):
    global max_orth
    names,groups=specification(ext); p=len(names)
    A=np.zeros((p,p)); z=np.zeros(p); yy=0.; N=0; means={}; global_x=np.zeros(p)
    for code,g in frame.groupby(SID,sort=True):
        X=design(g,ext); y=g.value.to_numpy(float); n=len(y)
        xm=X.mean(axis=0); ym=float(y.mean()); Xc=X-xm; yc=y-ym
        A+=Xc.T@Xc; z+=Xc.T@yc; yy+=yc@yc; N+=n; global_x+=X.sum(axis=0)
        means[code]=(xm,ym,n)
    beta,bread,rss=fit_stats(A,z,yy)
    global_x/=N
    week_scores={}; day_scores={}; local_results={}
    for code,g in frame.groupby(SID,sort=True):
        X=design(g,ext); y=g.value.to_numpy(float); xm,ym,n=means[code]
        Xc=X-xm; yc=y-ym; res=yc-Xc@beta
        for key,target in [('week_idx',week_scores),('day_idx',day_scores)]:
            cl=g[key].to_numpy(); unique=np.unique(cl); sc=scores(Xc,res,cl)
            for i,cluster in enumerate(unique): target[cluster]=target.get(cluster,np.zeros(p))+sc[i]
        adjusted_rows.append({'model':label,SID:code,'n':n,'observed_mean':ym,'adjusted_mean_common_covariates':ym-xm@beta+global_x@beta})
        XX=np.column_stack([np.ones(n),X]); ln=['intercept']+names
        LA=XX.T@XX; lz=XX.T@y; lyy=float(y@y)
        lb,lbread,lrss=fit_stats(LA,lz,lyy); lres=y-XX@lb
        cov,G=cov_cluster(XX,lres,g.week_idx.to_numpy(),lbread,len(ln))
        dcov,days=cov_cluster(XX,lres,g.day_idx.to_numpy(),lbread,len(ln))
        yc_wins=np.minimum(y,np.quantile(y,.995)); wb=lbread@(XX.T@yc_wins)
        cond=float(np.linalg.cond(LA)); rank=int(np.linalg.matrix_rank(LA))
        orth=float(np.max(np.abs(XX.T@lres))/max(n,1)); max_orth=max(max_orth,orth)
        fit_rows.append({'model':label,'scope':code,'n':n,'rank':rank,'parameters':len(ln),'condition_XtX':cond,'weeks':G,'r2':1-lrss/max(float(((y-y.mean())**2).sum()),1e-9),'orthogonality_error_per_row':orth})
        for j,name in enumerate(ln):
            se=np.sqrt(max(cov[j,j],0)); coef_rows.append({'model':label,'scope':code,'term':name,'coefficient':lb[j],'weekly_se':se,'ci_low':lb[j]-1.96*se,'ci_high':lb[j]+1.96*se,'daily_se':np.sqrt(max(dcov[j,j],0))})
        for name,v in contrast_vectors(ln,ext).items():
            e,lo,hi,se=contrast(lb,cov,v); de,dlo,dhi,dse=contrast(lb,dcov,v)
            effect_rows.append({'model':label,'scope':code,'contrast':name,'effect':e,'ci_low':lo,'ci_high':hi,'weekly_se':se,'daily_se':dse,'daily_ci_low':dlo,'daily_ci_high':dhi,'winsor_effect':float(v@wb),'n':n})
        for factor,value,delta in partials(LA,lz,lyy,lrss,ln,groups):
            partial_rows.append({'model':label,'scope':code,'factor':factor,'partial_r2':value,'rss_reduction':delta})
        for key,levels in [('hour',range(5,24)),('month',range(1,13)),('weekday',range(7)),('year',[2022,2023,2024])]:
            idx=[j for j,name in enumerate(ln) if name.startswith(key+'_')]
            average=float(XX[:,idx].mean(axis=0)@lb[idx])
            for level in levels:
                term=f'{key}_{level}'; v=np.zeros(len(ln))
                if term in ln: v[ln.index(term)]=1
                e,lo,hi,se=contrast(lb,cov,v)
                profiles.append({'model':label,SID:code,'factor':key,'level':level,'effect_vs_reference':e,'ci_low':lo,'ci_high':hi,'adjusted_level_station_reference':ym+e-average,'n_at_level':int(g[key].eq(level).sum())})
        if ext:
            oi=[ln.index(x) for x in ['outdoor_per10','outdoor_hinge20_per10','outdoor_hinge40_per10']]
            comp=XX[:,oi]@lb[oi]; adjusted=y-(XX@lb)+comp+ym-float(comp.mean())
            binned=pd.DataFrame({'bin':np.floor(g.outdoor_pm25.to_numpy()/5)*5,'adjusted_y':adjusted,'raw_y':y})
            bb=binned.groupby('bin').agg(n=('raw_y','size'),adjusted_mean=('adjusted_y','mean'),raw_mean=('raw_y','mean')).reset_index()
            for _,r in bb.iterrows(): bins.append({'model':label,SID:code,'factor':'outdoor',**r.to_dict()})
        li=ln.index('log2_usage_plus1'); comp=XX[:,li]*lb[li]
        adjusted=y-(XX@lb)+comp+ym-float(comp.mean())
        ub=np.floor(np.log2(g.board_alight_count.to_numpy()+1)*2)/2
        bb=pd.DataFrame({'bin':ub,'adjusted_y':adjusted,'raw_y':y}).groupby('bin').agg(n=('raw_y','size'),adjusted_mean=('adjusted_y','mean'),raw_mean=('raw_y','mean')).reset_index()
        for _,r in bb.iterrows(): bins.append({'model':label,SID:code,'factor':'usage',**r.to_dict()})
        local_results[code]={'names':ln,'beta':lb,'cov':cov,'n':n,'outdoor_p05':float(g.outdoor_pm25.quantile(.05)) if ext else None,'outdoor_p95':float(g.outdoor_pm25.quantile(.95)) if ext else None,'usage_p05':float(g.board_alight_count.quantile(.05)),'usage_p95':float(g.board_alight_count.quantile(.95))}
    G=len(week_scores); D=len(day_scores)
    sc=np.stack(list(week_scores.values())); ds=np.stack(list(day_scores.values()))
    cov=bread@(sc.T@sc)@bread*(G/(G-1))*((N-1)/(N-p-len(means)))
    dcov=bread@(ds.T@ds)@bread*(D/(D-1))*((N-1)/(N-p-len(means)))
    for j,name in enumerate(names):
        se=np.sqrt(max(cov[j,j],0)); coef_rows.append({'model':label,'scope':'ALL','term':name,'coefficient':beta[j],'weekly_se':se,'ci_low':beta[j]-1.96*se,'ci_high':beta[j]+1.96*se,'daily_se':np.sqrt(max(dcov[j,j],0))})
    for name,v in contrast_vectors(names,ext).items():
        e,lo,hi,se=contrast(beta,cov,v); _,dlo,dhi,dse=contrast(beta,dcov,v)
        effect_rows.append({'model':label,'scope':'ALL','contrast':name,'effect':e,'ci_low':lo,'ci_high':hi,'weekly_se':se,'daily_se':dse,'daily_ci_low':dlo,'daily_ci_high':dhi,'winsor_effect':np.nan,'n':N})
    for factor,value,delta in partials(A,z,yy,rss,names,groups): partial_rows.append({'model':label,'scope':'ALL','factor':factor,'partial_r2':value,'rss_reduction':delta})
    fit_rows.append({'model':label,'scope':'ALL','n':N,'rank':int(np.linalg.matrix_rank(A)),'parameters':p,'condition_XtX':float(np.linalg.cond(A)),'weeks':G,'r2':1-rss/yy,'orthogonality_error_per_row':float(np.max(np.abs(A@beta-z))/N)})
    global_models[label]={'names':names,'beta':beta,'cov':cov,'n':N,'stations':len(means),'within_r2':1-rss/yy,'weeks':G}
    local[label]=local_results
    print('fit',label,N,'rows',len(means),'stations',flush=True)

analyze(base,False,'base_57')
progress(2,'57개 역 공통·역별 기본 모형 완료; 실외 포함 확장 모형 분석 중')
analyze(external,True,'outdoor_matched')
# Same paired sample without outdoor separates sample changes from variable adjustment.
analyze(external,False,'base_same_paired_sample')
progress(3,'공통 모형과 역별 관계·불확실성 완료; 진단표·가설 작성 중')
coef=pd.DataFrame(coef_rows); effects=pd.DataFrame(effect_rows); partial=pd.DataFrame(partial_rows)
fits=pd.DataFrame(fit_rows); adj=pd.DataFrame(adjusted_rows).merge(meta.reset_index(),on=SID)
prof=pd.DataFrame(profiles); bin_table=pd.DataFrame(bins)
for df,name in [(coef,'coefficients'),(effects,'effect_contrasts'),(partial,'conditional_partial_r2'),(fits,'model_fit'),(adj,'adjusted_station_levels'),(prof,'adjusted_profiles'),(bin_table,'partial_adjustment_bins')]: save(df,name)
# Full-day descriptors retained separately from source-hour regression.
descriptors=[]
for code,g in d.groupby(SID):
    night=g[g.hour.between(0,4)].value; daytime=g[g.hour.between(5,23)].value
    low=g[g.outdoor_pm25.le(10) & g.value.notna()]
    descriptors.append({SID:code,'night_n':int(night.count()),'night_mean':night.mean(),'source_hours_mean':daytime.mean(),'low_outdoor_n':len(low),'low_outdoor_indoor_median':low.value.median(),'low_outdoor_gap_median':(low.value-low.outdoor_pm25).median()})
desc=pd.DataFrame(descriptors).set_index(SID); save(desc.reset_index(),'full_day_descriptors')

# Drawing primitives, without executing the earlier analysis.
source=(ROOT/'data/_scripts/analyze_basic_patterns.py').read_text(encoding='utf-8')
exec(source[source.index('class Canvas:'):source.index('def color(')])
def linepanel(canvas,x,y,w,h,title,xvals,yvals,lower=None,upper=None,xticklabels=None,points=True):
    canvas.text(x,y,title,17)
    xx=np.asarray(xvals,float); yy=np.asarray(yvals,float)
    finite=np.isfinite(xx)&np.isfinite(yy)
    if not finite.any(): canvas.text(x+30,y+60,'자료 부족',15); return
    xx=xx[finite]; yy=yy[finite]
    lo=np.asarray(lower,float)[finite] if lower is not None else yy
    hi=np.asarray(upper,float)[finite] if upper is not None else yy
    xmin,xmax=float(xx.min()),float(xx.max()); ymin,ymax=float(min(lo.min(),yy.min())),float(max(hi.max(),yy.max()))
    if xmax==xmin: xmax+=1
    margin=max((ymax-ymin)*.12,1); ymin-=margin; ymax+=margin
    a,b=x+60,x+w-15; top,bot=y+42,y+h-45
    def sx(v):return a+(v-xmin)/(xmax-xmin)*(b-a)
    def sy(v):return bot-(v-ymin)/(ymax-ymin)*(bot-top)
    for v in np.linspace(ymin,ymax,5):
        canvas.line(a,sy(v),b,sy(v),'#eeeeee'); canvas.text(x+3,sy(v)-9,f'{v:.1f}',12)
    for i,(vx,vy) in enumerate(zip(xx,yy)):
        if i: canvas.line(sx(xx[i-1]),sy(yy[i-1]),sx(vx),sy(vy),'#167daa',2)
        if lower is not None: canvas.line(sx(vx),sy(lo[i]),sx(vx),sy(hi[i]),'#93bdd6',2)
        canvas.dot(sx(vx),sy(vy),'#167daa',3)
    tick_idx=np.unique(np.linspace(0,len(xx)-1,min(7,len(xx))).astype(int))
    for j in tick_idx:
        lab=xticklabels[j] if xticklabels is not None else f'{xx[j]:g}'
        canvas.text(sx(xx[j])-8,bot+10,lab,12)
    canvas.text(x,y+h-20,'µg/m³',12)

def effectrow(code,contrast_name,model='outdoor_matched'):
    return effects[(effects.scope.eq(code)) & effects.model.eq(model) & effects.contrast.eq(contrast_name)].iloc[0]
def effectstr(row): return f'{row.effect:+.2f} µg/m³ (주 군집 95% 근사구간 {row.ci_low:+.2f}~{row.ci_high:+.2f})'
def direction(row):
    if row.ci_low>0:return '양의 관계가 관찰됨(인과 미확인)'
    if row.ci_high<0:return '음의 관계가 관찰됨(인과 미확인)'
    return '구간이 0을 포함해 방향이 불확실함'
hypotheses=[]; station_summary=[]
for code,cand in candidates.iterrows():
    title=f'{cand.line} {cand.station_name}'; model='outdoor_matched' if code in local['outdoor_matched'] else 'base_57'
    L=local[model][code]; sub=prof[prof[SID].eq(code)&prof.model.eq(model)]
    hour=sub[sub.factor.eq('hour')].sort_values('level'); month=sub[sub.factor.eq('month')].sort_values('level')
    dow=sub[sub.factor.eq('weekday')].sort_values('level'); years=sub[sub.factor.eq('year')].sort_values('level')
    peak=hour.loc[hour.adjusted_level_station_reference.idxmax()]; trough=hour.loc[hour.adjusted_level_station_reference.idxmin()]
    peakmonth=month.loc[month.adjusted_level_station_reference.idxmax()]; lowmonth=month.loc[month.adjusted_level_station_reference.idxmin()]
    u=effectrow(code,'승하차+1 두 배',model)
    o=effectrow(code,'실외 10→20') if model=='outdoor_matched' else None
    o2=effectrow(code,'실외 20→30') if o is not None else None
    current_adj=adj[adj.model.eq(model)&adj[SID].eq(code)].adjusted_mean_common_covariates.iloc[0]
    rawcorr=external[external[SID].eq(code)][['value','outdoor_pm25','board_alight_count']].corr() if o is not None else None
    hourgap=float(peak.adjusted_level_station_reference-trough.adjusted_level_station_reference)
    monthgap=float(peakmonth.adjusted_level_station_reference-lowmonth.adjusted_level_station_reference)
    station_summary.append({SID:code,'line':cand.line,'station_name':cand.station_name,'model':model,'n':L['n'],'outdoor_10_20':o.effect if o is not None else np.nan,'outdoor_10_20_low':o.ci_low if o is not None else np.nan,'outdoor_10_20_high':o.ci_high if o is not None else np.nan,'usage_doubling':u.effect,'usage_low':u.ci_low,'usage_high':u.ci_high,'peak_hour':int(peak.level),'trough_hour':int(trough.level),'hour_span':hourgap,'peak_month':int(peakmonth.level),'trough_month':int(lowmonth.level),'month_span':monthgap,'adjusted_mean_common_covariates':current_adj,'raw_indoor_outdoor_correlation':rawcorr.loc['value','outdoor_pm25'] if o is not None else np.nan,'raw_indoor_usage_correlation':rawcorr.loc['value','board_alight_count'] if o is not None else np.nan})
    evidence_o=(f'실외 10→20 대비 {effectstr(o)}; {direction(o)}. 20→30 대비 {effectstr(o2)}. 관측 실외 5~95백분위 {L["outdoor_p05"]:.1f}~{L["outdoor_p95"]:.1f}.' if o is not None else '실외 측정소 배정이 없어 평가 불가.')
    evidence_internal=f'24시간 기술통계에서 실외≤10인 표본 {int(desc.loc[code,"low_outdoor_n"]):,}개에서 실내 중앙값 {desc.loc[code,"low_outdoor_indoor_median"]:.2f}; 실내-실외 차이 중앙값 {desc.loc[code,"low_outdoor_gap_median"]:.2f} µg/m³. 이 값은 조건 미조정 기술통계.'
    evidence_time=f'다른 변수를 고정한 시간대 패턴은 {int(peak.level):02d}시 최대, {int(trough.level):02d}시 최소, 차이 {hourgap:.2f} µg/m³. 최대·최소는 같은 자료에서 탐색한 값으로 차이의 확정 검정은 아님.'
    evidence_usage=f'승하차+1 두 배 대비 {effectstr(u)}; {direction(u)}. 승하차 5~95백분위 {L["usage_p05"]:.0f}~{L["usage_p95"]:.0f}건/시간.'
    evidence_season=f'월 조정 패턴은 {int(peakmonth.level)}월 최대, {int(lowmonth.level)}월 최소, 범위 {monthgap:.2f} µg/m³. 월 최대·최소도 탐색적 선택.'
    year24=years[years.level.eq(2024)].iloc[0]
    evidence_change=f'2024년-2022년 조정 대비 {year24.effect_vs_reference:+.2f} µg/m³ (주 군집 95% 근사구간 {year24.ci_low:+.2f}~{year24.ci_high:+.2f}). 연도 차이는 특정 교체 사건을 확인한 것이 아님.'
    proxy=f'연결 실외 측정소 {raw.loc[code,"outdoor_station"]}, 거리 {raw.loc[code,"outdoor_distance_km"]:.2f} km. 역 입구·흡기구 농도는 관측하지 않음.'
    hs=[
        ('외부 오염 유입 또는 공통 기상 영향',evidence_o,'통계 관계는 평가 가능; 유입 경로는 미검증','실외와 실내가 함께 변해도 기상·운영 같은 공통 요인 때문일 수 있음','흡기구·출입구·실외 동시 측정, 풍향·풍속·환기 가동 기록','실외 고농도 사건 전후와 시간 지연을 비교하고 환기 상태별 반응을 확인'),
        ('내부 마모·쌓인 먼지의 재비산 또는 공기 교환 부족',evidence_internal,'기전 미검증 가설','실외 관측소 대표성·기기 편향·기존 먼지 잔류도 같은 패턴을 만듦','터널·승강장 입자 성분(철 등), 청소 기록, 환기 풍량, 열차·제동 기록','청소·환기 전후 및 비슷한 조건의 비교 역과 비교; 성분자료로 발생원 확인'),
        ('시간대별 운행·환기·청소 주기 차이',evidence_time,'시간대 관계는 평가 가능; 세부 기전 미검증','승객·열차·환기가 시간대별로 함께 바뀌며 실제 측정 구간도 불확실','시간별 열차 도착·환기 스케줄·청소·유지보수 기록','관측 최고·최저 시간대에 현장 동시 측정하고 운행·환기 변경 전후 비교'),
        ('승객 이동 재비산 또는 열차 운행과 이용량의 동반 변화',evidence_usage,'조건부 관계는 평가 가능; 승객의 인과효과 미검증','승하차는 플랫폼 체류 인원이 아니며 열차 횟수·공휴일을 통제하지 못함','승강장 체류·혼잡도·열차 횟수·공휴일·환승 흐름','같은 시간대·실외 조건에서 이용이 다른 날 비교하고 열차 횟수를 추가 조정'),
        ('계절별 환기 운영·습도·실내 입자 거동 변화',evidence_season,'월별 관계는 평가 가능; 계절 기전 미검증','실외 반응의 계절 차이·습도에 따른 측정 특성·운행 변화가 경쟁 설명','실내외 온습도·냉난방·환기·필터 교체 기록','계절별 실외 반응과 습도 보정 후 월별 패턴이 유지되는지 확인'),
        ('시설 운영·청소·측정기 보정 또는 교체의 장기 변화',evidence_change,'연도별 관계는 평가 가능; 사건·기전 미검증','설비 개선 외에 이용 회복·외부 환경·센서 변화·누락 시기 차이도 가능','측정기 점검·보정·이전·교체, 시설 공사·필터·청소 이력','변경 날짜가 확보되면 전후 단절·비교 역 차이를 분석; 교정기와 병행 측정'),
        ('선택 실외 측정소의 공간 대표성 부족',proxy,'현재 자료로 검증 불가한 측정·공간 가설','실제 내부 발생 차이와 실외 대리변수 오차를 현재 자료만으로 분리 불가','역 흡기구 측정, 다른 근접 실외 측정소와 풍향 자료','실외 측정소를 바꾼 민감도와 흡기구 실측을 비교')]
    for k,(hyp,ev,status,alternative,needed,method) in enumerate(hs,1):
        hypotheses.append({SID:code,'line':cand.line,'station_name':cand.station_name,'hypothesis_id':f'{code}_H{k:02d}','hypothesis':hyp,'station_evidence':ev,'status':status,'competing_explanation':alternative,'required_data':needed,'verification':method,'mechanism_source':SOURCE})
    c=Canvas(1450,980,title+' | 조건을 함께 고려한 패턴','2022~2024, 05~23시 | 인과효과가 아닌 조건부 관계 | 시간·월 패널은 역별 평균 조건에서의 조정 수준')
    linepanel(c,20,100,690,355,'시간대별 조정 수준',hour.level,hour.adjusted_level_station_reference)
    linepanel(c,740,100,690,355,'월별 조정 수준',month.level,month.adjusted_level_station_reference)
    ob=bin_table[bin_table[SID].eq(code)&bin_table.model.eq(model)&bin_table.factor.eq('outdoor')&bin_table.n.ge(30)&bin_table['bin'].le(80)].sort_values('bin')
    if len(ob): linepanel(c,20,490,690,350,'실외 농도 구간별: 다른 변수 조정 (구간 n≥30)',ob['bin']+2.5,ob.adjusted_mean)
    else:c.text(25,540,'실외 비교 평가 불가',17)
    ub=bin_table[bin_table[SID].eq(code)&bin_table.model.eq(model)&bin_table.factor.eq('usage')&bin_table.n.ge(30)].sort_values('bin')
    linepanel(c,740,490,690,350,'승하차 구간별: 다른 변수 조정 (구간 n≥30)',ub['bin']+.25,ub.adjusted_mean)
    c.text(25,850,'왼쪽 아래 가로축: 실외 PM2.5 µg/m³ (5단위 구간 중심). 오른쪽 아래: log2(승하차+1), 1 증가 시 약 두 배.',14)
    c.text(25,880,'아래 패널은 부분 조정한 관측 구간 평균이므로 직선·단조 패턴을 강제하지 않음. 인접 점 연결은 시계열이 아님.',14)
    c.text(25,910,f'모형 표본 n={L["n"]:,} | 실내 상태 공백의 정상 의미 미확인 | 시간 표기는 same_label_v1 가정',14)
    c.save('station_'+code)
    factors=partial[partial.model.eq(model)&partial.scope.eq(code)][['factor','partial_r2']].sort_values('partial_r2',ascending=False)
    eff=effects[effects.model.eq(model)&effects.scope.eq(code)][['contrast','effect','ci_low','ci_high','winsor_effect','daily_se','weekly_se']]
    text=f'''# {title}: 관계 분석과 점검 가설

## 선정 배경과 표본

기존 후보 선정 이유: {cand.reasons}. 이번 분석에서 후보를 다시 선정하지 않았다. 비교기간 2022~2024년, 회귀는 05~23시 동시 관측 {L['n']:,}개. 실내·승하차 관측률 {raw.loc[code,'base_coverage']:.2%}, 실외 포함 관측률 {raw.loc[code,'external_coverage']:.2%}. 상태 공백의 공식 정상 의미는 미확인이다.

## 자료에서 확인되는 관계

- {evidence_o}
- {evidence_usage}
- {evidence_time}
- {evidence_season}
- {evidence_change}
- {evidence_internal}
- 00~04시 유효 관측 {int(desc.loc[code,'night_n']):,}개, 평균 {desc.loc[code,'night_mean']:.2f} µg/m³. 이 시간대는 회귀에 포함하지 않았으며 영업·비영업 상태를 확인한 구분도 아니다.
- {proxy}

![역별 조정 패턴](../figures/station_{code}.png)

## 대비와 불확실성

{md(eff)}

effect·ci_low·ci_high는 µg/m³. 주별 군집 95% 근사구간이며 다중비교 보정·인과 식별 결과가 아니다. winsor_effect는 해당 역 실내 상위 0.5%를 제한했을 때 같은 표본으로 재적합한 값이다. daily_se는 하루 군집, weekly_se는 주 군집의 표준오차다. 표본 밖의 농도 대비나 사용량 두 배 변화로 외삽하지 않는다.

## 현재 모형의 조건부 추가 설명력

{md(factors)}

부분 R²는 다른 변수가 있을 때 해당 묶음을 추가한 표본 내 설명력이다. 상관된 변수 사이에서 순위가 달라질 수 있고, 합이 100%가 되지 않으며 발생원 기여율이 아니다. 이용량의 설명력이 작아도 많은 사람이 이용하는 관리상 중요성은 사라지지 않는다.

## 점검할 가설

'''
    for k,(hyp,ev,status,alternative,needed,method) in enumerate(hs,1):
        text+=f'### H{k:02d}. {hyp}\n\n- 구분: **{status}**\n- 이 역의 관측 근거: {ev}\n- 경쟁 설명: {alternative}\n- 추가로 필요한 자료: {needed}\n- 검증 방법: {method}\n\n'
    text+=f'가능한 기전의 일반적 근거: [Health Canada 지하철 공기질 지침]({SOURCE}). 이 지침이 이 역의 원인을 입증하는 것은 아니다.\n\n'
    text+='## 현장 점검에서의 해석\n\n자료상 시간대·월 패턴과 실외 반응을 우선 확인하고, 기기 검증과 운영 기록 대조를 함께 진행하는 것이 적절하다. 환기 불량·제동 마모·청소 부족 등은 후보 가설이며 이 역에서 실제 발생했다고 확인한 사실이 아니다. 실외 차이·조정 잔여 차이를 내부 발생량으로 바꾸어 해석하지 않는다.\n'
    (OUT/'station_reports'/f'{code}.md').write_text(text,encoding='utf-8-sig')

hyp=pd.DataFrame(hypotheses); station_summary=pd.DataFrame(station_summary)
save(hyp,'hypotheses'); save(station_summary,'candidate_factor_summary')
# Cross-station intervals. Include zero and every interval endpoint in the axis.
c=Canvas(1500,850,'후보 역별 실외·이용 규모와의 조건부 관계','점: 추정 대비 / 선: 주 군집 95% 근사구간 | 서로 다른 역별 모형 | 원인·관리 우선순위가 아님')
for panel,(contrast_name,title) in enumerate([('실외 10→20','실외 PM2.5 10→20 µg/m³ 대비'),('승하차+1 두 배','승하차+1 두 배 대비')]):
    x,y,w=panel*745+20,140,710
    ed=effects[effects.model.eq('outdoor_matched')&effects.scope.isin(candidates.index)&effects.contrast.eq(contrast_name)].set_index('scope').reindex(candidates.index)
    low=min(0,float(ed.ci_low.min())); high=max(0,float(ed.ci_high.max())); pad=max((high-low)*.1,.3); low-=pad; high+=pad
    a,b=x+185,x+w-15
    def sx(v): return a+(v-low)/(high-low)*(b-a)
    c.text(x,100,title,18)
    for tick in np.linspace(low,high,6):
        c.line(sx(tick),y-3,sx(tick),y+17*34,'#eeeeee'); c.text(sx(tick)-8,y+17*34+10,f'{tick:.1f}',13)
    c.line(sx(0),y-3,sx(0),y+17*34,'#999999',2)
    for j,(code,row) in enumerate(ed.iterrows()):
        yy=y+j*34+12; m=meta.loc[code]
        c.text(x,yy-10,f'{m.line} {m.station_name}',14)
        c.line(sx(row.ci_low),yy,sx(row.ci_high),yy,'#7da5bd',3); c.dot(sx(row.effect),yy,'#167daa',5)
c.text(25,790,'단위: µg/m³. 승하차 관계는 시간대·월·요일·연도·실외 농도를 고려했으나 열차 운행·환기·기상은 통제하지 못함.',14)
c.save('01_candidate_effects')

global_effect=effects[effects.scope.eq('ALL')]
global_partial=partial[partial.scope.eq('ALL')]
base_effect=effectrow('ALL','승하차+1 두 배','base_57')
ext_effect=effectrow('ALL','승하차+1 두 배')
same_effect=effectrow('ALL','승하차+1 두 배','base_same_paired_sample')
out_effect=effectrow('ALL','실외 10→20')
out_mid=effectrow('ALL','실외 20→30')
def sign_label(row):return '양' if row.ci_low>0 else '음' if row.ci_high<0 else '불확실'
candidate_usage=effects[effects.model.eq('outdoor_matched')&effects.scope.isin(candidates.index)&effects.contrast.eq('승하차+1 두 배')]
pos=int(candidate_usage.ci_low.gt(0).sum()); neg=int(candidate_usage.ci_high.lt(0).sum()); uncertain=17-pos-neg
winsor_flips=effects[effects.scope.ne('ALL') & effects.winsor_effect.notna() & (np.sign(effects.effect)!=np.sign(effects.winsor_effect))]
save(winsor_flips,'winsor_direction_changes')
links='\n'.join(f'- [{r.line} {r.station_name}](station_reports/{code}.md)' for code,r in candidates.iterrows())
report=f'''# 전체 역 공통 관계와 후보 역별 점검 가설

## 핵심 결과

2022~2024년 전체 57개 지점의 공통 관계를 분석하고, 기존 후보 17개 역 각각의 진단표를 작성했다. 후보를 다시 선정하거나 원인을 확정하지 않았다. **실외·이용량·시간·월·요일·연도를 함께 고려한 관계**와 **미검증 기전 가설**을 구분했다.

- 전체 공통 확장 모형의 실외 10→20 µg/m³ 대비: **{effectstr(out_effect)}**.
- 실외 20→30 µg/m³ 대비: **{effectstr(out_mid)}**. 실외 농도 구간에 따라 기울기가 다르게 허용된 결과다.
- 전체 공통 확장 모형의 승하차+1 두 배 대비: **{effectstr(ext_effect)}**. 승객 이동의 인과효과가 아니며 열차 횟수·환기 등과 분리되지 않는다.
- 후보 역별 이용량 대비의 주 군집 근사구간이 양수인 역 {pos}개, 음수 {neg}개, 0을 포함하는 역 {uncertain}개. 다중비교를 보정한 발견 개수가 아니므로 유의성 순위로 사용하지 않는다.
- 역마다 시간대·월·실외 반응이 다르다. 개별 진단표에 수치와 경쟁 설명을 제시했다. 조정 후 차이를 환기 불량 또는 내부 발생량으로 바로 해석할 수 없다.

## 표본과 공통 모형

24시간 기술통계는 57개 지점을 모두 포함했다. 승하차가 원자료에 없는 00~04시는 회귀에서 제외하고 0으로 채우지 않았다. 기본 모형 {global_models['base_57']['stations']}개 지점 {global_models['base_57']['n']:,}개 시간 표본, 실외 포함 확장 모형 {global_models['outdoor_matched']['stations']}개 지점 {global_models['outdoor_matched']['n']:,}개 표본이다. 현충로·율하는 실외 비교를 할 수 없어 기본 모형에만 포함했다. 사용 표본·관측률은 sample_coverage.csv에 있다.

실내 수치는 0 이상 유한 숫자 + 상태 공백인 잠정 표본이다. 상태 공백이 공식 정상인지 확인되지 않았다. same_label_v1 시간 구간 가정, 실외 위치 대표성, 누락 변수와 관측 누락의 편향은 남는다. 비교기간 1,096일 중 전체 역의 결합 행이 모두 없는 날짜 {len(missing_dates)}일({', '.join(missing_dates.astype(str))})은 보간하지 않았다. 관측률 분모는 결측일을 포함한 전체 달력 시간이며 all_station_absent_dates.csv에 기록했다. 이 부재의 원인이 기기인지 수집 시스템인지는 확정하지 않는다.

전체 모형은 역 고정효과, 시간대·월·요일·연도 범주, log2(승하차+1)를 사용한다. 확장 모형은 실외 농도에 20·40 µg/m³ 꺾임을 둔다. 월은 계절을 더 세밀하게 조정하는 변수다. 역별 모형은 같은 구조의 계수가 역마다 달라지도록 별도 적합했다.

실외 추가와 표본 변경을 구분하려고 확장 모형과 정확히 같은 표본에 실외를 빼고 다시 적합했다. 승하차+1 두 배 대비는 전체 기본 표본 {effectstr(base_effect)}, 같은 실외 동시 표본에서 실외 미포함 {effectstr(same_effect)}, 실외 포함 {effectstr(ext_effect)}다. 이 비교는 실외 조정의 영향을 보여주지만 누락 요인 제거를 보장하지 않는다.

{md(global_effect[['model','contrast','effect','ci_low','ci_high','daily_se','weekly_se','n']])}

## 무엇이 모형 안에서 추가 설명력을 갖는가

{md(global_partial[['model','factor','partial_r2']])}

부분 R²는 다른 묶음을 둔 상태에서 해당 묶음을 뺐을 때 늘어나는 잔차 제곱합을 기준으로 계산했다. 역 고정효과를 제거한 자료 내 공통 관계의 설명력이며 **발생원 기여율이나 원인 중요도 비율이 아니다**. 변수들이 관련되어 있으므로 합이 100%가 되지 않는다. 표본 내 within R²는 기본 {global_models['base_57']['within_r2']:.3f}, 확장 {global_models['outdoor_matched']['within_r2']:.3f}이며 예측 검증 성능으로 제시하지 않는다.

## 후보 역별 결과

![실외 및 이용량과의 역별 조건부 관계](figures/01_candidate_effects.png)

다음 표의 시간대·월 최대/최소는 동일 자료에서 탐색해 고른 것이다. 범위는 개별 대비의 확정 검정 결과가 아니다. 기울기와 조정 수준의 단위는 µg/m³다.

{md(station_summary[['line','station_name','outdoor_10_20','usage_doubling','peak_hour','trough_hour','hour_span','peak_month','trough_month','month_span']])}

{links}

## 점검 가설과 확인 순서

17개 역에 각 7개씩, 총 {len(hyp)}개 가설 기록을 만들었다. 가설 유형은 외부 유입/공통 기상, 내부 마모·재비산/잔류, 운행·환기 시간 주기, 이용·열차 동반 변화, 계절 운영/습도, 장기 설비·측정 변화, 실외 측정소 대표성이다. 유형은 공통이지만 **역별 실제 수치·최대 시간대·계절·구간·거리**를 근거로 다르게 정리했다. 이 중 어떤 시설이 실제로 불량하다고 확인한 것은 없다.

1. 측정기·단위·시각·점검 이력부터 대조한다. 농도 차이가 측정 차이인지 확인한다.
2. 진단표에서 높은 시간대와 낮은 시간대를 골라 열차·환기·청소 기록을 대조한다.
3. 실외가 낮아도 높은 역은 내부 발생·잔류와 실외 대리변수 오차를 함께 확인한다.
4. 이용량 대비가 음수여도 승객이 먼지를 줄인다고 해석하지 않는다. 시간대별 운행·환기·주말 구성과 모형 제한을 먼저 점검한다.
5. 자료로 판별되지 않는 가설은 필요한 기록·현장 측정·비교 설계를 붙여 후속 점검 대상으로 남긴다.

기전의 일반적 근거는 [Health Canada 지침]({SOURCE})이다. 지침은 환기·여과, 마모·제동, 청소, 스크린도어 등 여러 경로를 제시하며 시설별 검증 필요성을 강조한다. 우리 역별 기전을 입증하는 근거로 인용한 것은 아니다.

## 불확실성과 민감도

- 주별 군집 강건 근사구간은 같은 주의 시공간 상관을 허용한다. 주 사이 상관·관측 누락·측정 오차를 완전히 해결하지 않는다. 하루 군집 표준오차도 표에 병기했다.
- 주 모형과 같은 표본에서 역별 실내 상위 0.5%를 제한해 재적합했다. 방향이 바뀐 역·대비·모형 조합 {len(winsor_flips)}개는 winsor_direction_changes.csv에 모두 저장했다. 작은 계수의 부호만으로 결론을 내리지 않는다.
- 후보는 같은 2022~2024년 자료로 선정되고 분석되었다. 선택 후 분석이며 독립 검증이나 인과 식별이 아니다. 향후 새로운 기간에서 재현 확인이 필요하다.
- 실외 농도별 반응의 계절·시간 상호작용, 지연 효과, 비선형 이용량, 역 주변 공사, 공휴일, 실제 열차 횟수·온습도·시설 이력은 이번 모형에 포함되지 않았다. 부분 조정 구간 그림이 선형 계수와 다르면 모형 단순화의 징후로 확인할 수 있다.
- 조정 역 평균은 확장 표본 전체의 동일한 설명변수 평균을 각 역에 적용했다. 다른 역의 이용 규모가 해당 역의 관측 범위를 벗어날 수 있고 역별 기울기가 공통이라는 가정도 있으므로 관리 순위로 쓰지 않는다.

## 산출물

- plan.md: 분석 설계.
- station_reports/: 후보 17개 역별 보고서.
- tables/hypotheses.csv: 근거·검증 상태·경쟁 설명·필요 자료·검증 방법을 가진 전체 가설.
- tables/candidate_factor_summary.csv, effect_contrasts.csv: 역별 대비와 불확실성.
- tables/coefficients.csv, conditional_partial_r2.csv, model_fit.csv: 전체·역별 모형.
- tables/adjusted_profiles.csv, partial_adjustment_bins.csv, raw_*.csv: 그림·관계의 근거.
- tables/adjusted_station_levels.csv: 동일 조건에서의 공통 모형 역 수준(별도 인과 의미 없음).
- figures/: 요약 및 역별 PNG·SVG. 한글 SVG는 Malgun Gothic 글꼴 사용.
- validation.json: 수치 검증. 재현 스크립트 data/_scripts/analyze_station_factors.py, numpy·pandas·Pillow 필요.

원본 수정·추가 데이터 수집·Git 커밋·푸시는 수행하지 않았다. task.md는 로컬 진행표로만 갱신한다.
'''
(OUT/'report.md').write_text(report,encoding='utf-8-sig')
progress(4,'17개 진단표·119개 가설·그림 작성 완료; 모형·수치·가독성 검증 중')

assert raw.n.sum()==1461049
assert len(meta)==57 and len(base_ids)==57
assert not d.duplicated([SID,'date','hour']).any()
assert fits.n.gt(fits.parameters).all()
assert (fits['rank']==fits.parameters).all()
assert max_orth<1e-5, max_orth
assert partial.partial_r2.between(-1e-7,1+1e-7).all()
assert set(candidates.index)<=set(local['outdoor_matched'])
assert len(hyp)==17*7 and hyp.hypothesis_id.is_unique
assert effects.ci_low.le(effects.effect).all() and effects.ci_high.ge(effects.effect).all()
assert global_models['base_same_paired_sample']['n']==global_models['outdoor_matched']['n']
assert raw.external_n.sum()==len(external)
assert global_models['outdoor_matched']['n']==int(fits[(fits.model.eq('outdoor_matched'))&fits.scope.ne('ALL')].n.sum())
for p in (OUT/'figures').glob('*.png'):
    with Image.open(p) as im: im.verify()
import xml.etree.ElementTree as ET
for p in (OUT/'figures').glob('*.svg'): ET.parse(p)
validation={'numeric_passed':True,'visual_review':'pending','base_stations':len(base_ids),'external_stations':len(ext_ids),'base_n':len(base),'external_n':len(external),'candidate_reports':len(list((OUT/'station_reports').glob('*.md'))),'hypotheses':len(hyp),'png_figures':len(list((OUT/'figures').glob('*.png'))),'svg_figures':len(list((OUT/'figures').glob('*.svg'))),'maximum_normal_equation_residual_per_row':max_orth,'maximum_XtX_condition':float(fits.condition_XtX.max()),'checks':['baseline count matches earlier analysis','57 station IDs','unique station-time keys','full-rank local designs','normal equation residual tolerance','partial R2 bounds','all 17 candidates have external models','paired-sample comparison uses identical n','119 unique hypothesis IDs','CI ordering','PNG decode and SVG parse']}
(OUT/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(validation,ensure_ascii=False),flush=True)
print(global_effect[['model','contrast','effect','ci_low','ci_high']].to_string(index=False),flush=True)
