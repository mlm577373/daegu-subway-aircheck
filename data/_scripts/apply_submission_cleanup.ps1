$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..')).TrimEnd('\')
$manifestPath=Join-Path $projectRoot 'outputs/post_submission_cleanup.json'
$audit=Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$retain=@('data/_scripts/collect_probe.py','outputs/inspection_candidates/tables/all_station_metrics.csv')
$deleted=0
foreach($entry in $audit.files){
 if($entry.path -in $retain){continue}
 $target=[IO.Path]::GetFullPath((Join-Path $projectRoot $entry.path))
 if(-not $target.StartsWith($projectRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw "Outside project: $target"}
 if($target.Contains('\.git\')){throw 'Git deletion prohibited'}
 if(Test-Path -LiteralPath $target -PathType Leaf){
  $digest=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLower()
  if($digest -ne $entry.sha256){throw "Changed since backup: $target"}
  Remove-Item -LiteralPath $target -Force
  $deleted++
 }
}
# Only remove empty directories within explicitly scoped cleanup areas.
$areas=@('outputs/submission_draft','outputs/basic_patterns','outputs/extended_factors','outputs/factor_analysis','outputs/inspection_candidates','data/_work','data/_tools','data/__pycache__','subway_air_check')
$areas+=@(Get-ChildItem -LiteralPath $projectRoot -Directory -Force | Where-Object {$_.Name -like '.chart-data-*'} | ForEach-Object {$_.Name})
foreach($area in $areas){
 $folder=[IO.Path]::GetFullPath((Join-Path $projectRoot $area))
 if(-not $folder.StartsWith($projectRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid folder'}
 if(Test-Path -LiteralPath $folder){
  $dirs=@(Get-ChildItem -LiteralPath $folder -Directory -Recurse -Force | Sort-Object {$_.FullName.Length} -Descending)
  $dirs+=Get-Item -LiteralPath $folder
  foreach($dir in $dirs){if(@(Get-ChildItem -LiteralPath $dir.FullName -Force).Count -eq 0){Remove-Item -LiteralPath $dir.FullName -Force}}
 }
}
$mismatches=@()
foreach($property in $audit.survivors.PSObject.Properties){
 $target=Join-Path $projectRoot $property.Name
 if(-not(Test-Path -LiteralPath $target)){$mismatches+=$property.Name;continue}
 if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLower() -ne $property.Value){$mismatches+=$property.Name}
}
if($mismatches.Count){throw ('Survivor mismatch: '+($mismatches -join ', '))}
@{deleted_files=$deleted;retained_dependencies=$retain;verified_survivors=@($audit.survivors.PSObject.Properties).Count;archive=$audit.archive;status='pass'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $projectRoot 'outputs/post_submission_cleanup_result.json') -Encoding utf8
Write-Output "Deleted files: $deleted. All original surviving files verified."

