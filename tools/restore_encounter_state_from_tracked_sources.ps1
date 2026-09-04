param(
    [string]$Database = "data\eso.db",
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

function Invoke-PythonStep {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    Write-Host ""
    Write-Host ("=" * 72)
    Write-Host $Label
    Write-Host ("=" * 72)
    & python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

function Get-AbsolutePath {
    param([Parameter(Mandatory = $true)][string]$Path)
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $Path))
}

function Backup-SqliteDatabase {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    Invoke-PythonStep $Label @(
        "-c",
        "import sqlite3,sys; src=sqlite3.connect(sys.argv[1]); dst=sqlite3.connect(sys.argv[2]); src.backup(dst); dst.close(); src.close()",
        $Source,
        $Destination
    )
}

function Invoke-CanonicalPrerequisiteBootstrap {
    param(
        [Parameter(Mandatory = $true)][string]$TargetDatabase,
        [switch]$Apply
    )

    $ParentArgs = @(
        "tools\bootstrap_boss_parent_content.py",
        "--database", $TargetDatabase,
        "--boss-dir", $BossSourceDir,
        "--content-root", $ContentRoot
    )
    if ($Apply) {
        $ParentArgs += "--apply"
    }
    Invoke-PythonStep "Bootstrap boss parent content" $ParentArgs

    $EncounterArgs = @(
        "tools\bootstrap_boss_encounter_corpus.py",
        "--database", $TargetDatabase,
        "--source-dir", $BossSourceDir
    )
    if ($Apply) {
        $EncounterArgs += "--apply"
    }
    Invoke-PythonStep "Bootstrap canonical boss encounter identities" $EncounterArgs
}

$DatabasePath = Get-AbsolutePath $Database
$ManifestPath = Join-Path $RepoRoot "data\encounter_reviews\inferred_boss_mechanics.json"
$ContentRoot = Join-Path $RepoRoot "data\eso_info"
$BossSourceDir = Join-Path $ContentRoot "bosses"
$EvidenceRoot = Join-Path $RepoRoot "data\encounter_evidence"
$BatchRoot = Join-Path $RepoRoot "data\encounter_review_batches"
$Timestamp = Get-Date -Format "yyyyMMddTHHmmss"

if (-not (Test-Path -LiteralPath $DatabasePath -PathType Leaf)) {
    throw "Database does not exist: $DatabasePath"
}
if (-not (Test-Path -LiteralPath $ContentRoot -PathType Container)) {
    throw "ESO source directory does not exist: $ContentRoot"
}
if (-not (Test-Path -LiteralPath $BossSourceDir -PathType Container)) {
    throw "Boss source directory does not exist: $BossSourceDir"
}
if (-not (Test-Path -LiteralPath $EvidenceRoot -PathType Container)) {
    throw "Encounter evidence directory does not exist: $EvidenceRoot"
}

$RequiredBatches = @(
    "trial_inferred_mechanics_manual_review.json",
    "dungeon_inferred_mechanics_review.json",
    "arena_inferred_mechanics_manual_review.json"
)
foreach ($BatchName in $RequiredBatches) {
    $BatchPath = Join-Path $BatchRoot $BatchName
    if (-not (Test-Path -LiteralPath $BatchPath -PathType Leaf)) {
        throw "Required tracked review batch is missing: $BatchPath"
    }
}

Write-Host "BFF ENCOUNTER STATE RECOVERY"
Write-Host "Repository: $RepoRoot"
Write-Host "Database:   $DatabasePath"
Write-Host ("Mode:       " + $(if ($DryRun) { "DRY RUN" } else { "APPLY" }))
Write-Host ""
Write-Host "This recovery does not reset or cherry-pick the branch."
Write-Host "It rebuilds encounter state from tracked current-branch sources only."

if ($DryRun) {
    $DryRunDatabase = Join-Path ([System.IO.Path]::GetTempPath()) "bff-encounter-recovery-$PID-$Timestamp.db"
    try {
        Backup-SqliteDatabase "Clone live SQLite database for disposable dry run" $DatabasePath $DryRunDatabase

        Write-Host ""
        Write-Host "Dry-run sandbox: $DryRunDatabase"
        Write-Host "Canonical prerequisites will be applied only to this temporary database."

        Invoke-CanonicalPrerequisiteBootstrap -TargetDatabase $DryRunDatabase -Apply

        Invoke-PythonStep "Structural encounter dry run" @(
            "tools\import_boss_encounter_structure.py",
            "--database", $DryRunDatabase,
            "--source-dir", $BossSourceDir
        )

        Invoke-PythonStep "Timeline canonical dry run" @(
            "tools\write_encounter_timeline_facts.py",
            "--database", $DryRunDatabase,
            "--evidence-root", $EvidenceRoot
        )

        Write-Host ""
        Write-Host "RESULT: PASS (dry run; live database and review manifest unchanged)"
    }
    finally {
        if (Test-Path -LiteralPath $DryRunDatabase -PathType Leaf) {
            Remove-Item -LiteralPath $DryRunDatabase -Force
            Write-Host "Removed disposable dry-run database: $DryRunDatabase"
        }
    }
    exit 0
}

$DatabaseBackup = "$DatabasePath.before-encounter-recovery.$Timestamp"
Backup-SqliteDatabase "Backup live SQLite database" $DatabasePath $DatabaseBackup
Write-Host "Recovery backup: $DatabaseBackup"

$ManifestBackup = $null
if (Test-Path -LiteralPath $ManifestPath -PathType Leaf) {
    $ManifestBackup = "$ManifestPath.before-encounter-recovery.$Timestamp"
    Copy-Item -LiteralPath $ManifestPath -Destination $ManifestBackup
    Write-Host "Review manifest backup: $ManifestBackup"
}

Invoke-CanonicalPrerequisiteBootstrap -TargetDatabase $DatabasePath -Apply

$StructuralBackup = "$DatabasePath.before-structural-recovery.$Timestamp"
Invoke-PythonStep "Restore source-backed boss structure" @(
    "tools\import_boss_encounter_structure.py",
    "--database", $DatabasePath,
    "--source-dir", $BossSourceDir,
    "--apply",
    "--backup", $StructuralBackup
)

Invoke-PythonStep "Rebuild complete pending mechanic review manifest" @(
    "tools\review_inferred_boss_mechanics.py",
    "--source-dir", $BossSourceDir,
    "--manifest", $ManifestPath,
    "--initialize"
)

foreach ($ContentType in @("trial", "dungeon", "arena")) {
    Invoke-PythonStep "Apply conservative $ContentType review recommendations" @(
        "tools\recommend_inferred_boss_mechanics.py",
        "--source-dir", $BossSourceDir,
        "--content-root", $ContentRoot,
        "--content-type", $ContentType,
        "--manifest", $ManifestPath,
        "--apply-accepted"
    )
}

foreach ($BatchName in $RequiredBatches) {
    Invoke-PythonStep "Apply tracked review batch: $BatchName" @(
        "tools\apply_inferred_mechanic_review_batch.py",
        "--manifest", $ManifestPath,
        "--batch", (Join-Path $BatchRoot $BatchName)
    )
}

# Yesterday's final reviewed state explicitly corrected Hiath's Roll Dodge:
# the source movement flag describes the boss moving, not a player movement demand.
$Manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
$Decisions = @($Manifest.decisions)
$HiathRollDodge = @(
    $Decisions | Where-Object {
        $_.encounter_id -eq "hiath_the_battlemaster" -and
        $_.mechanic_name -eq "Roll Dodge"
    }
)
if ($HiathRollDodge.Count -ne 1) {
    throw "Expected exactly one Hiath Roll Dodge review decision; found $($HiathRollDodge.Count)"
}
if ($HiathRollDodge[0].status -ne "accepted") {
    throw "Hiath Roll Dodge is not accepted in the reconstructed review manifest"
}
$HiathRollDodge[0] | Add-Member -NotePropertyName "requirement_subjects" -NotePropertyValue ([pscustomobject]@{ movement = "boss" }) -Force
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText(
    $ManifestPath,
    (($Manifest | ConvertTo-Json -Depth 40) + "`n"),
    $Utf8NoBom
)

$Manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
$Decisions = @($Manifest.decisions)
$Accepted = @($Decisions | Where-Object { $_.status -eq "accepted" }).Count
$Rejected = @($Decisions | Where-Object { $_.status -eq "rejected" }).Count
$Pending = @($Decisions | Where-Object { $_.status -eq "pending" }).Count

Write-Host ""
Write-Host "RECONSTRUCTED REVIEW CHECKPOINT"
Write-Host "Decision rows: $($Decisions.Count)"
Write-Host "Accepted:      $Accepted"
Write-Host "Rejected:      $Rejected"
Write-Host "Pending:       $Pending"

if ($Decisions.Count -ne 109 -or $Accepted -ne 94 -or $Rejected -ne 15 -or $Pending -ne 0) {
    throw (
        "Reconstructed review totals do not match the verified 2026-09-03 checkpoint " +
        "(expected 109 decisions / 94 accepted / 15 rejected / 0 pending)."
    )
}

Invoke-PythonStep "Audit reconstructed mechanic review manifest" @(
    "tools\review_inferred_boss_mechanics.py",
    "--source-dir", $BossSourceDir,
    "--manifest", $ManifestPath
)

Invoke-PythonStep "Restore reviewed canonical mechanic facts" @(
    "tools\write_reviewed_single_source_mechanics.py",
    "--source-dir", $BossSourceDir,
    "--manifest", $ManifestPath,
    "--database", $DatabasePath,
    "--apply"
)

Invoke-PythonStep "Audit reviewed canonical mechanic persistence" @(
    "tools\audit_persisted_reviewed_single_source_mechanics.py",
    "--source-dir", $BossSourceDir,
    "--manifest", $ManifestPath,
    "--database", $DatabasePath
)

Invoke-PythonStep "Restore corroborated canonical timeline facts" @(
    "tools\write_encounter_timeline_facts.py",
    "--database", $DatabasePath,
    "--evidence-root", $EvidenceRoot,
    "--apply"
)

Invoke-PythonStep "Verify Hiath Roll Dodge requirement ownership" @(
    "tools\correct_hiath_roll_dodge_ownership.py",
    "--database", $DatabasePath,
    "--apply"
)

Write-Host ""
Write-Host ("=" * 72)
Write-Host "ENCOUNTER STATE RECOVERY COMPLETE"
Write-Host ("=" * 72)
Write-Host "Verified review checkpoint: 109 decisions / 94 accepted / 15 rejected / 0 pending"
Write-Host "Reviewed canonical mechanics: audited against reconstructed manifest"
Write-Host "Structural boss rows: independently audited by the structural importer"
Write-Host "Timeline facts: replayed through the current guarded timeline writer"
Write-Host "Hiath Roll Dodge: movement ownership verified as boss-owned"
Write-Host "Primary recovery backup: $DatabaseBackup"
if ($ManifestBackup) {
    Write-Host "Previous review manifest backup: $ManifestBackup"
}
Write-Host ""
Write-Host "RESULT: PASS"
