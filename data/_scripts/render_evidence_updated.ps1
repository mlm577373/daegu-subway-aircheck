$ErrorActionPreference = 'Stop'
$draftRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../outputs/submission_draft'))
$draftFile = Join-Path $draftRoot '대구_도시철도_미세먼지_분석근거_수정본.docx'
$renderRoot = Join-Path $draftRoot '_build/evidence_render'
New-Item -ItemType Directory -Path $renderRoot -Force | Out-Null
$pdfFile = Join-Path $renderRoot 'word_preview.pdf'
$wordApp = $null
$wordDoc = $null
try {
    $wordApp = New-Object -ComObject Word.Application
    $wordApp.Visible = $false
    $wordApp.DisplayAlerts = 0
    $wordDoc = $wordApp.Documents.Open($draftFile, $false, $true)
    $wordDoc.Repaginate()
    $wordDoc.ExportAsFixedFormat($pdfFile, 17)
    Write-Output ('Pages=' + $wordDoc.ComputeStatistics(2))
    Write-Output $pdfFile
} finally {
    if ($null -ne $wordDoc) { $wordDoc.Close(0); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($wordDoc) }
    if ($null -ne $wordApp) { $wordApp.Quit(); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($wordApp) }
}
