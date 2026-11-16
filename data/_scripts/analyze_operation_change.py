"""Quasi-experimental timetable-change associations; no source apportionment claims."""
from pathlib import Path
import json,math
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/operation_change';T=OUT/'tables'
T.mkdir(parents=True,exist_ok=True);SID='analysis_station_id'
CHANGE=pd.Timestamp('2024-10-07');SPECIAL=['2022-11-17','2023-11-16','2024-11-14']
def save(df,name):df.to_csv(T/f'{name}.csv',index=False,encoding='utf-8-sig')
def bh(p):
    a=np.asarray(p,float);out=np.full(len(a),np.nan);ii=np.where(np.isfinite(a))[0]
    if len(ii):
        ix=ii[np.argsort(a[ii])];out[ix]=np.minimum(1,np.minimum.accumulate((a[ix]*len(ix)/np.arange(1,len(ix)+1))[::-1])[::-1])
    return out
def absorb(matrix,groups):
    z=matrix.copy();codes=[]
    for g in groups:
        c,_=pd.factorize(g);counts=np.bincount(c);codes.append((c,counts))
    for iteration in range(200):
        prev=z.copy()
        for c,n in codes:
            for j in range(z.shape[1]):z[:,j]-=(np.bincount(c,weights=z[:,j])/n)[c]
        if np.max(np.abs(z-prev))<1e-9:break
    return z,iteration+1,sum(len(n) for c,n in codes)
def regress(y,X,groups,cluster):
    z,it,fe=absorb(np.column_stack([y,X]),groups);yy=z[:,0];xx=z[:,1:]
    keep=np.sqrt(np.mean(xx*xx,axis=0))>1e-10
    if not keep[0]:return None
    a=xx[:,keep];bread=np.linalg.pinv(a.T@a,rcond=1e-11);b=bread@(a.T@yy);res=yy-a@b
    c,_=pd.factorize(cluster);G=c.max()+1
    scores=np.zeros((G,a.shape[1]));np.add.at(scores,c,a*res[:,None])
    if G<2:raise ValueError('Need at least two calendar-week clusters')
    correction=G/(G-1)*len(y)/max(1,len(y)-fe-a.shape[1])
    cov=bread@(scores.T@scores)@bread*correction
    se=np.sqrt(np.maximum(np.diag(cov),0));full=np.full(X.shape[1],np.nan);fs=full.copy();full[keep]=b;fs[keep]=se
    error=float(np.max(np.abs(a.T@res))/max(1,len(y)))
    return {'beta':full,'se':fs,'n':len(y),'clusters':int(G),'iterations':it,'normal_error':error,'resid':res,'xx':xx,'yy':yy,'cluster':np.asarray(cluster),'fe':fe}
def reportfit(result,columns,station,config,g):
    if result is None:return None
    coef=result['beta'][0];se=result['se'][0]
    p=math.erfc(abs(coef/se)/math.sqrt(2)) if se>0 else np.nan
    out={SID:station,'config':config,'n':result['n'],'clusters':result['clusters'],'effect_per_scheduled_train':coef,'se':se,'ci_low':coef-1.96*se,'ci_high':coef+1.96*se,'p_normal':p,'normal_error':result['normal_error'],'absorb_iterations':result['iterations'],'days_2024_pre':g[g.year.eq(2024)&~g.post].date.nunique(),'days_2024_post':g[g.year.eq(2024)&g.post].date.nunique()}
    if 'outdoor10' in columns:
        j=columns.index('outdoor10');out.update(outdoor_10_to_20=result['beta'][j],outdoor_se=result['se'][j])
    return out

def main():
    parts=[];meta=None
    cols=[SID,'line','station_name','date','hour','indoor_pm25','indoor_quality_flag','outdoor_pm25','board_alight_count']
    for year in [2022,2023,2024,2025,2026]:
        p=pd.read_csv(ROOT/f'data/merged/merged_hourly_{year}.csv',usecols=cols)
        p['year']=year;parts.append(p);print('read',year,len(p),flush=True)
    d=pd.concat(parts,ignore_index=True);del parts
    meta=d[[SID,'line','station_name']].drop_duplicates().set_index(SID)
    d['value']=d.indoor_pm25.where(d.indoor_quality_flag.eq('status_blank_unverified')&d.indoor_pm25.ge(0)&np.isfinite(d.indoor_pm25))
    d['date_dt']=pd.to_datetime(d.date);d['weekday']=d.date_dt.dt.weekday
    d['time']=d.date_dt+pd.to_timedelta(d.hour,unit='h')
    d['offset']=(d.date_dt-pd.to_datetime(d.year.astype(str)+'-10-07')).dt.days
    d['post']=d.offset.ge(0);d['week']=(d.date_dt.to_numpy(dtype='datetime64[D]').astype('int64')+3)//7
    coverage=d.groupby([SID,'year']).agg(returned=('value','size'),valid=('value','count'),start=('date','min'),end=('date','max')).reset_index()
    save(coverage,'source_coverage')
    spring=d[d.date_dt.dt.month.le(4)].groupby([SID,'year','hour']).agg(n=('value','count'),mean=('value','mean'),median=('value','median')).reset_index().merge(meta.reset_index(),on=SID)
    save(spring,'spring_followup_hour_profiles')
    # Date-key join avoids silently assuming changed data units or timestamps.
    weather=pd.read_csv(ROOT/'data/weather/weather_hourly_2022_2024.csv',usecols=['time_kst','temperature_c','relative_humidity_derived_pct','wind_speed_mps','weather_complete'])
    weather['time']=pd.to_datetime(weather.time_kst)
    cal=pd.read_csv(ROOT/'data/calendar/calendar_2022_2024.csv',usecols=['date','named_holiday'])
    x=d[d.year.le(2024)&d.hour.between(14,22)&d.offset.between(-70,69)].merge(weather.drop(columns='time_kst'),on='time',how='left',validate='many_to_one').merge(cal,on='date',how='left',validate='many_to_one')
    del d
    counts=pd.read_csv(ROOT/'data/timetable_change/hourly_schedule_change.csv')
    delta=counts[counts.day_type.eq('weekday')][[SID,'hour','delta']]
    for shift,label in [(0,'delta'),(-1,'delta_minus1'),(1,'delta_plus1')]:
        c=delta.rename(columns={'delta':label}).copy();c['hour']=c.hour-shift
        x=x.merge(c,on=[SID,'hour'],how='left',validate='many_to_one')
    x=x[x.weekday.lt(5)&x.named_holiday.eq(0)&~x.date.isin(SPECIAL)].copy()
    x['usage_log']=np.log1p(x.board_alight_count.where(x.board_alight_count.ge(0)))
    configs=[('raw56',56,False,False,0,2024),('adjusted56',56,True,False,0,2024),('usage56',56,True,True,0,2024),('adjusted42',42,True,False,0,2024),('adjusted70',70,True,False,0,2024),('clock_minus1',56,True,False,-1,2024),('clock_plus1',56,True,False,1,2024),('placebo2023',56,True,False,0,2023)]
    results=[];quality=[];hour_profiles=[];pools={};diagnostics=[]
    for config,width,adjust,usage,shift,eventyear in configs:
        pool=[]
        for sid,g0 in x.groupby(SID,sort=True):
            g=g0[g0.offset.between(-width,width-1)&g0.year.le(eventyear)].copy()
            need=g.value.notna()
            if adjust:need &= g.outdoor_pm25.ge(0)&g.weather_complete.fillna(False)
            if usage:need &= g.usage_log.notna()
            g=g[need].copy()
            dn=g.groupby('date').hour.transform('size');g=g[dn.ge(7)].copy()
            nc=g.groupby(['year','post']).date.nunique()
            eligible=len(nc)==(eventyear-2021)*2 and nc.min()>=15
            quality.append({SID:sid,'config':config,'n':len(g),'eligible':bool(eligible),'min_days_per_side':int(nc.min()) if len(nc) else 0})
            if not eligible:continue
            dose=g['delta' if shift==0 else 'delta_minus1' if shift==-1 else 'delta_plus1'].to_numpy(float)
            treatment=dose*g.post.to_numpy()*g.year.eq(eventyear).to_numpy()
            columns=['train_change'];arrays=[treatment]
            if adjust:
                o=g.outdoor_pm25.to_numpy(float)
                arrays.extend([o/10,np.maximum(o-20,0)/10,np.maximum(o-40,0)/10,g.temperature_c.to_numpy()/10,g.relative_humidity_derived_pct.to_numpy()/10,g.wind_speed_mps.to_numpy()])
                columns+=['outdoor10','outdoor_hinge20','outdoor_hinge40','temp10','rh10','wind']
            if usage:arrays.append(g.usage_log.to_numpy());columns+=['usage_log']
            X=np.column_stack(arrays)
            groups=[g.date,g.year.astype(str)+'_'+g.hour.astype(str),g.post.astype(int).astype(str)+'_'+g.hour.astype(str)]
            fit=regress(g.value.to_numpy(float),X,groups,g.week.to_numpy())
            if fit is None:continue
            row=reportfit(fit,columns,sid,config,g);results.append(row)
            pool.append(fit)
            if config=='adjusted56':
                for yr in [2022,2023,2024]:
                    h=g[g.year.eq(yr)].groupby(['post','hour']).agg(n=('value','count'),indoor=('value','mean'),outdoor=('outdoor_pm25','mean'),usage=('board_alight_count','mean')).reset_index()
                    h[SID]=sid;h['year']=yr;hour_profiles.append(h)
                diagnostics.append({SID:sid,'train_residual_sd':float(np.std(fit['xx'][:,0])),'normal_error':fit['normal_error'],'days':g.date.nunique()})
        # Concatenated within-station transforms, with common calendar-week clusters.
        if pool:
            xx=np.concatenate([f['xx'] for f in pool]);yy=np.concatenate([f['yy'] for f in pool])
            beta=np.linalg.pinv(xx.T@xx,rcond=1e-11)@(xx.T@yy)
            clusters,_=pd.factorize(np.concatenate([f['cluster'] for f in pool]));G=int(clusters.max()+1)
            residual=yy-xx@beta;bread=np.linalg.pinv(xx.T@xx,rcond=1e-11)
            scores=np.zeros((G,xx.shape[1]));np.add.at(scores,clusters,xx*residual[:,None])
            correction=G/(G-1)*len(yy)/max(1,len(yy)-sum(f['fe'] for f in pool)-xx.shape[1])
            cov=bread@(scores.T@scores)@bread*correction;se=float(np.sqrt(max(0,cov[0,0])))
            pools[config]={'stations':len(pool),'n':len(yy),'point_estimate':float(beta[0]),'se':se,'ci_low':float(beta[0]-1.96*se),'ci_high':float(beta[0]+1.96*se),'calendar_week_clusters':G,'inference':'common calendar-week clustered approximate normal interval; station-specific fixed effects, common covariate slopes'}
        print('fit',config,'stations',len(pool),flush=True)
    r=pd.DataFrame(results)
    for config in r.config.unique():
        idx=r.config.eq(config);r.loc[idx,'q_bh']=bh(r.loc[idx,'p_normal'])
    r=r.merge(meta.reset_index(),on=SID)
    save(r,'station_event_estimates');save(pd.DataFrame(quality),'model_coverage');save(pd.DataFrame(diagnostics),'model_diagnostics')
    save(pd.concat(hour_profiles,ignore_index=True),'matched_hour_profiles')
    (OUT/'pooled_point_estimates.json').write_text(json.dumps(pools,ensure_ascii=False,indent=2),encoding='utf-8')
    primary=r[r.config.eq('adjusted56')].copy()
    tiers=[]
    for a in primary.itertuples():
        sid=getattr(a,SID);z=r[r[SID].eq(sid)].set_index('config')
        stable=all(c in z.index and z.loc[c,'effect_per_scheduled_train']>0 for c in ['adjusted42','adjusted70','usage56','clock_minus1','clock_plus1'])
        placebo_clear=bool('placebo2023' in z.index and z.loc['placebo2023','p_normal']>.1)
        train=bool(a.q_bh<=.1 and a.effect_per_scheduled_train>0 and stable and placebo_clear)
        external=bool(np.isfinite(a.outdoor_10_to_20) and a.outdoor_10_to_20-1.96*a.outdoor_se>0)
        tiers.append({SID:sid,'line':a.line,'station_name':a.station_name,'train_change_consistent':train,'positive_in_core_sensitivities':stable,'outdoor_association_positive':external,'management_direction':'운행 관련·실외 연동 모두 추가 조사' if train and external else '운행 관련 내부 발생·재비산·열차풍 우선 조사' if train else '실외 연동·공조 운전 대조 우선, 운행 변화 근거 제한' if external else '현재 자료로 관리 원인 분류 유보','train_effect':a.effect_per_scheduled_train,'q_bh':a.q_bh,'outdoor_10_to_20':a.outdoor_10_to_20})
    save(pd.DataFrame(tiers),'management_evidence')
    summary={'primary_event':'2024-10-07','primary_years':[2022,2023,2024],'followup_years':[2025,2026],'source_periods':coverage.groupby('year').agg(start=('start','min'),end=('end','max'),valid=('valid','sum')).reset_index().to_dict('records'),'primary_stations':len(primary),'primary_positive_q10':int((primary.q_bh.le(.1)&primary.effect_per_scheduled_train.gt(0)).sum()),'primary_negative_q10':int((primary.q_bh.le(.1)&primary.effect_per_scheduled_train.lt(0)).sum()),'management_counts':pd.Series([t['management_direction'] for t in tiers]).value_counts().to_dict(),'pooled_points':pools,'max_normal_error':float(r.normal_error.max()),'model':'station-specific date FE + year-by-hour FE + shared post-by-hour FE; treatment planned hourly train-count change x post x event-year; calendar-week clustered approximate normal CIs; BH within 57-station family','limitations':['planned timetable counts, not realized train movement','not a rail-wear source-apportionment experiment','simultaneous extension trial and unobserved operation changes','outdoor linkage does not measure actual ventilation flow','spring follow-up descriptive only; post timetable continuous validity not assumed','hour-label alignment remains provisional; plus/minus hour tested']}
    (OUT/'analysis_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=True),flush=True)
if __name__=='__main__':main()
