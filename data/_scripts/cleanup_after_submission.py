"""Inventory, back up and verify exact cleanup targets. Deletion is native PowerShell."""
from pathlib import Path
import hashlib,json,zipfile,datetime,shutil
R=Path(__file__).resolve().parents[2]
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
A=R/'outputs/_archive'/('post_submission_'+stamp+'.zip')
final_names=['보고서.pptx','분석근거_정리본.docx','시각화_인터랙티브지도.html','공모전_붙임1-5_수정본.docx']
finaldir=R/'최종제출본';finaldir.mkdir(exist_ok=True)
protected={}
for name in final_names:
 src=R/'outputs/submission_draft'/name
 assert src.is_file(),src
 dst=finaldir/name
 assert not dst.exists(),dst
 shutil.copy2(src,dst);assert H(src)==H(dst)
 protected[str(dst.relative_to(R))]=H(dst)
# Keep only the most recent authoring source and the exact inputs it requires.
B=R/'outputs/submission_draft/_build'
keep={'build_deck_design_v6.mjs','content.json','forms_extracted.txt','forms_sources.json','notice_extracted.txt','risk_map_noto.png','user_limitations.json','news/sbs_page.png','news/yeongnam_page.png'}
targets={}
def add(p,reason):
 if p.is_file():targets[p]=reason
 elif p.is_dir():
  for f in p.rglob('*'):
   if f.is_file():targets[f]=reason
for p in (R/'outputs/submission_draft').iterdir():
 if p.name!='_build':add(p,'previous deliverable or verified copy in final folder')
for p in B.rglob('*'):
 if p.is_file() and p.relative_to(B).as_posix() not in keep:add(p,'obsolete authoring version or render preview')
for name in ['basic_patterns','extended_factors','factor_analysis','inspection_candidates']:add(R/'outputs'/name,'exploratory analysis superseded by final management and operation analysis')
for p in R.glob('.chart-data-*'):add(p,'temporary chart workbook staging')
for p in [R/'subway_air_check',R/'data/_work',R/'data/_tools',R/'통합분석보고서.md']:add(p,'early probe, temporary database, utility staging or previous report')
for p in R.rglob('__pycache__'):
 if '.git' not in p.parts:add(p,'Python cache')
old_scripts=['analyze_basic_patterns.py','analyze_extended_factors.py','analyze_management_conditions.py','analyze_station_factors.py','audit_consistent_weather.py','baseline_report.py','build_submission_drafts.py','build_unified_report.py','check_compression.py','check_excel_endpoint.py','check_recent_validation.py','collect_consistent_weather.py','collect_kma_hourly.py','collect_probe.py','explore_final_insights.py','finalize_factor_analysis.py','management_condition_report.py','management_map_report.py','polish_deck_v4.py','probe_extended_factors.py','probe_files.py','recheck_empty.py','render_contest_forms.ps1','render_factor_overview.py','render_submission_word.ps1','retire_later_results.py','revise_deck_flow.py','revise_deck_v3.py','select_inspection_candidates.py','test_representative_hypotheses.py','update_news_and_evidence.py','validate_extended_factors.py','validate_recent_candidates.py','extract_contest_notice.py','extract_contest_forms.py']
for name in old_scripts:add(R/'data/_scripts'/name,'superseded draft generation or exploratory script')
for p in (R/'outputs/_submission_draft_validation').glob('*'):
 if p.name!='deck_validation_v6.json':add(p,'previous deck validation')
# Preserve checksums of every surviving original file to catch unexpected changes.
survivors={str(p.relative_to(R)):H(p) for p in R.rglob('*') if p.is_file() and '.git' not in p.parts and '_archive' not in p.parts and p not in targets}
records=[]
with zipfile.ZipFile(A,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p,reason in sorted(targets.items()):
  rel=p.relative_to(R).as_posix(); digest=H(p)
  z.write(p,rel);records.append({'path':rel,'bytes':p.stat().st_size,'sha256':digest,'reason':reason})
 z.writestr('ARCHIVE_MANIFEST.json',json.dumps(records,ensure_ascii=False,indent=2))
with zipfile.ZipFile(A) as z:
 assert z.testzip() is None
 for v in records:assert hashlib.sha256(z.read(v['path'])).hexdigest()==v['sha256']
manifest={'archive':str(A.relative_to(R)),'files':records,'survivors':survivors,'final_files':protected,'total_bytes':sum(v['bytes'] for v in records)}
(R/'outputs/post_submission_cleanup.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'files':len(records),'original_MB':round(manifest['total_bytes']/1048576,1),'archive_MB':round(A.stat().st_size/1048576,1),'archive':str(A.relative_to(R))},ensure_ascii=True))
