<#
.SYNOPSIS
  Headless FJ Commandline driver for the FlowJo comparison sweep.

.DESCRIPTION
  See flowjo_sweep_RUNBOOK.md, step 5, for the one-time GUI setup this
  depends on (flowjo_sweep_template.wsp must already exist with the 3 gate
  variants x 3 Cell Cycle model configs and a Table Editor table marked for
  command-line batch export).

  Reference: https://flowjo.com/docs/flowjo10/advanced-features/fj-commandline
    First argument must be one of: .wspt / .wsp / .acs / .txt (sample list).
    -save         saves the workspace after processing (recomputed gates/stats).
    -batchTable   exports Table Editor tables using their assigned settings.
    -outputFolder destination for the exported table(s).
    -verbose      prints extended execution details.

.NOTES
  PowerShell equivalent of flowjo_sweep_run.bat, with clearer error reporting.
  $FlowJoExe still needs the real FlowJo 11.2 install path (vXX below is a
  placeholder). $Workspace/$OutputFolder default to sit next to the 30 FCS
  files at $DataFolder -- save flowjo_sweep_template.wsp there in step 8 of
  the runbook, or pass -Workspace/-OutputFolder to override.
#>
param(
    [string]$FlowJoExe = "C:\Program Files\FlowJo vXX\FlowJo64.exe",
    [string]$DataFolder = "C:\Users\lapt3u\Downloads\archivedwl-864",
    [string]$Workspace = "$DataFolder\flowjo_sweep_template.wsp",
    [string]$OutputFolder = "$DataFolder\exports"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $FlowJoExe)) {
    Write-Error "FlowJo executable not found: $FlowJoExe`nPass -FlowJoExe or edit the default at the top of this script."
    exit 1
}
if (-not (Test-Path -LiteralPath $Workspace)) {
    Write-Error "Workspace not found: $Workspace`nComplete flowjo_sweep_RUNBOOK.md steps 1-4 first, saving to this path."
    exit 1
}
if (-not (Test-Path -LiteralPath $DataFolder)) {
    Write-Error "Data folder not found: $DataFolder"
    exit 1
}
if (-not (Test-Path -LiteralPath $OutputFolder)) {
    New-Item -ItemType Directory -Path $OutputFolder | Out-Null
}

$savedWsp = Join-Path $OutputFolder "flowjo_sweep_output.wsp"

Write-Host "Running FlowJo headlessly against $DataFolder ..."
& $FlowJoExe $Workspace $DataFolder -save $savedWsp -batchTable -outputFolder $OutputFolder -verbose

if ($LASTEXITCODE -ne 0) {
    Write-Error "FlowJo exited with code $LASTEXITCODE. Check $OutputFolder for partial output and review the -verbose output above."
    exit $LASTEXITCODE
}

Write-Host "Done. Exported table(s) should be in $OutputFolder."
Write-Host "Next: copy $OutputFolder back to the Linux dev box and run"
Write-Host "  python3 tests/validation/driving_code/flowjo_sweep_parse_export.py --exports-dir <path>"
