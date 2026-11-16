$ErrorActionPreference = 'Stop'
$draftRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../outputs/submission_draft'))
$draftFile = Join-Path $draftRoot '공모전_붙임1-5_수정본.docx'
$renderRoot = Join-Path $draftRoot '_build/forms_v2_render'
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
