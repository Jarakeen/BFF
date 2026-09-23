param(
    [switch]$SkipTests,
    [string]$UserDatabaseSeed = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path $PSScriptRoot -Parent
$DistRoot = Join-Path $ProjectRoot "dist"
$BuildRoot = Join-Path $ProjectRoot "build"
$SpecPath = Join-Path $PSScriptRoot "BFF.spec"
$ExeName = "FoundryDock.exe"

Push-Location $ProjectRoot
try {
    $Version = (python -c "from app_version import APP_VERSION; print(APP_VERSION)").Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($Version)) {
        throw "Could not read APP_VERSION from app_version.py"
    }
    if ($Version -notmatch '^\d+\.\d+\.\d+$') {
        throw "APP_VERSION must be semantic x.y.z; got '$Version'"
    }

    Write-Host ""
    Write-Host "========================================"
    Write-Host " FOUNDRYDOCK RELEASE $Version"
    Write-Host "========================================"
    Write-Host ""

    Write-Host "Running strict release-boundary audit..."
    python tools/audit_release_candidate.py --strict-data
    if ($LASTEXITCODE -ne 0) {
        throw "Release audit failed. Resolve every reported gate before packaging."
    }

    if (-not $SkipTests) {
        Write-Host "Running release test suite..."
        python -m pytest -q
        if ($LASTEXITCODE -ne 0) {
            throw "Tests failed. No release package was created."
        }
    }
    else {
        Write-Warning "Release tests were explicitly skipped. This build is not a validated release candidate."
    }

    if (-not (Test-Path $SpecPath)) {
        throw "PyInstaller spec not found: $SpecPath"
    }

    if (Test-Path $DistRoot) {
        Remove-Item $DistRoot -Recurse -Force
    }
    if (Test-Path $BuildRoot) {
        Remove-Item $BuildRoot -Recurse -Force
    }

    $SourceDatabase = Join-Path $ProjectRoot "data\eso.db"
    if (-not (Test-Path $SourceDatabase)) {
        throw "Source database not found: $SourceDatabase"
    }
    $ReleaseSeedRoot = Join-Path $BuildRoot "release_seed"
    $ReleaseSeedDatabase = Join-Path $ReleaseSeedRoot "eso.db"
    New-Item -ItemType Directory -Force -Path $ReleaseSeedRoot | Out-Null

    Write-Host "Creating privacy-safe release database seed..."
    python tools\build_release_database_seed.py --source $SourceDatabase --destination $ReleaseSeedDatabase
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create sanitized release database seed."
    }
    if (-not (Test-Path $ReleaseSeedDatabase)) {
        throw "Sanitized release database seed was not created: $ReleaseSeedDatabase"
    }

    # Optional prepared user database for a deliberately customized first-install
    # EXE. PyInstaller embeds it under _seed_user_data; runtime copies it only
    # when the recipient has no existing foundrydock.db.
    if (-not [string]::IsNullOrWhiteSpace($UserDatabaseSeed)) {
        $ResolvedUserDatabaseSeed = (Resolve-Path $UserDatabaseSeed).Path
        if (-not (Test-Path $ResolvedUserDatabaseSeed -PathType Leaf)) {
            throw "User database seed not found: $UserDatabaseSeed"
        }
        $PreparedUserDatabaseSeed = Join-Path $ReleaseSeedRoot "foundrydock.db"
        Copy-Item $ResolvedUserDatabaseSeed $PreparedUserDatabaseSeed -Force
        Write-Host "Prepared user database seed: $ResolvedUserDatabaseSeed"
    }
    else {
        Write-Host "Prepared user database seed: none"
    }

    Write-Host "Building $ExeName..."
    python -m PyInstaller --clean $SpecPath
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed."
    }

    $BuiltExe = Join-Path $DistRoot $ExeName
    if (-not (Test-Path $BuiltExe)) {
        throw "PyInstaller did not create $ExeName at: $BuiltExe"
    }

    $PackageName = "FoundryDock-$Version"
    $PackageRoot = Join-Path $DistRoot $PackageName
    $DataRoot = Join-Path $PackageRoot "data"
    New-Item -ItemType Directory -Force -Path $DataRoot | Out-Null
    Move-Item $BuiltExe (Join-Path $PackageRoot $ExeName) -Force

    # First install gets a writable privacy-safe DB created from canonical
    # reference data only. The frozen app embeds the same sanitized file as its
    # recovery seed. Never copy the developer's live eso.db into release output.
    Copy-Item $ReleaseSeedDatabase (Join-Path $DataRoot "eso.db") -Force

    # Runtime external data is positive-allowlisted by release_manifest.py.
    # File entries may include reviewed subdirectories such as gameplay_policy/.
    $RuntimeFiles = python -c "import runpy; m=runpy.run_path(r'packaging/release_manifest.py'); print(chr(10).join(m.get('RUNTIME_EXTERNAL_DATA_FILES', ())))"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not read runtime data file allowlist."
    }
    foreach ($Name in $RuntimeFiles) {
        $Name = $Name.Trim()
        if ([string]::IsNullOrWhiteSpace($Name)) { continue }
        $Source = Join-Path $ProjectRoot ("data\" + $Name)
        if (-not (Test-Path $Source -PathType Leaf)) {
            throw "Allowlisted runtime data file is missing: data\$Name"
        }
        $Destination = Join-Path $DataRoot $Name
        $DestinationParent = Split-Path $Destination -Parent
        if (-not [string]::IsNullOrWhiteSpace($DestinationParent)) {
            New-Item -ItemType Directory -Force -Path $DestinationParent | Out-Null
        }
        Copy-Item $Source $Destination -Force
    }

    # Canonical runtime data directories are copied recursively, preserving their
    # data-relative paths. These are reviewed application inputs, not user state.
    $RuntimeDirectories = python -c "import runpy; m=runpy.run_path(r'packaging/release_manifest.py'); print(chr(10).join(m.get('RUNTIME_EXTERNAL_DATA_DIRECTORIES', ())))"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not read runtime data directory allowlist."
    }
    foreach ($Name in $RuntimeDirectories) {
        $Name = $Name.Trim()
        if ([string]::IsNullOrWhiteSpace($Name)) { continue }
        $Source = Join-Path $ProjectRoot ("data\" + $Name)
        if (-not (Test-Path $Source -PathType Container)) {
            throw "Allowlisted runtime data directory is missing: data\$Name"
        }
        $Destination = Join-Path $DataRoot $Name
        $DestinationParent = Split-Path $Destination -Parent
        if (-not [string]::IsNullOrWhiteSpace($DestinationParent)) {
            New-Item -ItemType Directory -Force -Path $DestinationParent | Out-Null
        }
        Copy-Item $Source $Destination -Recurse -Force
    }

    # A first install starts with no developer-owned builds. Existing installs
    # keep their own file because the update archive never contains builds.json.
    $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText(
        (Join-Path $DataRoot "builds.json"),
        '{"Members": []}',
        $Utf8NoBom
    )

    # First install also starts with a clean canonical player/character/build
    # catalog. Existing installs keep their own characters.json because the
    # updater never ships or replaces user-owned identity state.
    [System.IO.File]::WriteAllText(
        (Join-Path $DataRoot "characters.json"),
        '{"schema_version": 4, "players": [], "characters": [], "builds": [], "team_assignments": []}',
        $Utf8NoBom
    )

    Write-Host "Running packaged release privacy audit..."
    python tools\audit_packaged_release_privacy.py --package-root $PackageRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Packaged release privacy audit failed. No release package will be created."
    }

    $CleanSettings = @'
{
  "EsoLogsClientId": "",
  "BuildsExportFolder": "",
  "CurrentExpeditionPath": "data/CurrentExpedition.json",
  "CurrentIncidentPath": "data/CurrentIncident.json",
  "FieldNoteCounterPath": "data/FieldNoteCounter.txt",
  "CountersFolder": "data",
  "ArchiveFolder": "Archive",
  "WeatherFolder": "data/Weather",
  "StreamEventsPath": "data/StreamEvents.json",
  "StreamSessionPath": "data/StreamSession.json",
  "BossLogPath": "Archive/BossLog.md",
  "NarratorContentPath": "data/natural_history_narrator.json",
  "AchievementRunDraftPath": "data/current_achievement_run.json",
  "BrbSceneName": "BRB",
  "EndOfStreamSceneName": "Ending",
  "ObsWebSocketHost": "127.0.0.1",
  "ObsWebSocketPort": 4455,
  "ObsWebSocketPassword": "",
  "GoogleCredentialsPath": "google_service_account.json",
  "GoogleSpreadsheetId": "",
  "GoogleSheetsPerson": "",
  "AchievementProgressPath": "data/achievement_progress.json",
  "MarkerLogPath": "data/MarkerLog.md",
  "CurrentAchievementRunPath": "data/CurrentAchievementRun.json",
  "CurrentBroadcastPath": "data/CurrentBroadcast.json",
  "SessionArchiveFolder": "Archive/Sessions",
  "BffRoot": "."
}
'@
    [System.IO.File]::WriteAllText((Join-Path $PackageRoot "settings.json"), $CleanSettings, $Utf8NoBom)

    # Optional private-repository updater access. These values are injected at
    # packaging time and are never committed to the repository or included in
    # the in-place update archive.
    $UpdateBaseUrl = if ([string]::IsNullOrWhiteSpace($env:FOUNDRYDOCK_UPDATE_BASE_URL)) { "https://bff-production-30c2.up.railway.app" } else { $env:FOUNDRYDOCK_UPDATE_BASE_URL }
    $UpdateAccessKey = $env:FOUNDRYDOCK_UPDATE_ACCESS_KEY
    if (-not [string]::IsNullOrWhiteSpace($UpdateAccessKey)) {
        $UpdateAccess = @{
            base_url = $UpdateBaseUrl.TrimEnd('/')
            access_key = $UpdateAccessKey
        } | ConvertTo-Json
        [System.IO.File]::WriteAllText(
            (Join-Path $PackageRoot "update_access.json"),
            $UpdateAccess,
            $Utf8NoBom
        )
        Write-Host "Private updater access: configured"
    }
    else {
        Write-Host "Private updater access: not configured (public GitHub release fallback)"
    }

    Copy-Item (Join-Path $ProjectRoot "RELEASE_STATUS.md") (Join-Path $PackageRoot "RELEASE_STATUS.md") -Force

    $ReadmeSource = Join-Path $PSScriptRoot "FRIEND_README.txt"
    if (Test-Path $ReadmeSource) {
        Copy-Item $ReadmeSource (Join-Path $PackageRoot "README.txt") -Force
    }

    # Versioned first-install package.
    $FirstInstallZip = Join-Path $DistRoot ("FoundryDock-$Version.zip")
    Compress-Archive -Path (Join-Path $PackageRoot "*") -DestinationPath $FirstInstallZip -CompressionLevel Optimal

    # In-place update payload: application + allowlisted runtime reference data only.
    # Never include DB, settings, builds, roster/progress/session state.
    $UpdateRoot = Join-Path $DistRoot "FoundryDock-Update"
    New-Item -ItemType Directory -Force -Path $UpdateRoot | Out-Null
    Copy-Item (Join-Path $PackageRoot $ExeName) (Join-Path $UpdateRoot $ExeName) -Force

    if ($RuntimeFiles.Count -gt 0 -or $RuntimeDirectories.Count -gt 0) {
        $UpdateDataRoot = Join-Path $UpdateRoot "data"
        New-Item -ItemType Directory -Force -Path $UpdateDataRoot | Out-Null

        foreach ($Name in $RuntimeFiles) {
            $Name = $Name.Trim()
            if ([string]::IsNullOrWhiteSpace($Name)) { continue }
            $UpdateDestination = Join-Path $UpdateDataRoot $Name
            $UpdateDestinationParent = Split-Path $UpdateDestination -Parent
            if (-not [string]::IsNullOrWhiteSpace($UpdateDestinationParent)) {
                New-Item -ItemType Directory -Force -Path $UpdateDestinationParent | Out-Null
            }
            Copy-Item (Join-Path $DataRoot $Name) $UpdateDestination -Force
        }

        foreach ($Name in $RuntimeDirectories) {
            $Name = $Name.Trim()
            if ([string]::IsNullOrWhiteSpace($Name)) { continue }
            $UpdateDestination = Join-Path $UpdateDataRoot $Name
            $UpdateDestinationParent = Split-Path $UpdateDestination -Parent
            if (-not [string]::IsNullOrWhiteSpace($UpdateDestinationParent)) {
                New-Item -ItemType Directory -Force -Path $UpdateDestinationParent | Out-Null
            }
            Copy-Item (Join-Path $DataRoot $Name) $UpdateDestination -Recurse -Force
        }
    }

    $UpdateZip = Join-Path $DistRoot "FoundryDock-update.zip"
    Compress-Archive -Path (Join-Path $UpdateRoot "*") -DestinationPath $UpdateZip -CompressionLevel Optimal
    $UpdateHash = (Get-FileHash -Path $UpdateZip -Algorithm SHA256).Hash.ToLowerInvariant()
    [System.IO.File]::WriteAllText(
        (Join-Path $DistRoot "FoundryDock-update.zip.sha256"),
        "$UpdateHash  FoundryDock-update.zip`n",
        $Utf8NoBom
    )

    Write-Host ""
    Write-Host "========================================"
    Write-Host " RELEASE BUILD COMPLETE"
    Write-Host "========================================"
    Write-Host "Version: $Version"
    Write-Host "First install: $FirstInstallZip"
    Write-Host "Update payload: $UpdateZip"
    Write-Host "Update SHA-256: $UpdateHash"
    Write-Host ""
}
finally {
    Pop-Location
}
