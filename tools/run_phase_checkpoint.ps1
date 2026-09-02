[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TestTarget,
    [string]$Branch = "phase8"
)

$ErrorActionPreference = "Stop"
git status --short
git switch $Branch
git pull origin $Branch
pytest $TestTarget -q
$focusedExit = $LASTEXITCODE
pytest -q
$fullExit = $LASTEXITCODE
if ($focusedExit -ne 0 -or $fullExit -ne 0) { exit 1 }
