$ErrorActionPreference = "Stop"

# This produces a full local test build, including a copy of your
# real eso.db, so you can run and sanity-check the packaged app
# yourself before handing it off.
#
# If you're zipping up dist\BFF\ to send to someone else to test:
# DELETE dist\BFF\data\eso.db from the copy you send first, and give
# them FOR_YOUR_TESTER.md instead so they drop in their own.

$ProjectRoot = Split-Path $PSScriptRoot -Parent
$DistRoot = Join-Path $ProjectRoot "dist"
$BuildRoot = Join-Path $ProjectRoot "build"
$PackageRoot = Join-Path $DistRoot "BFF"
$ExeName = "FoundryDock.exe"

Write-Host ""
Write-Host "========================================"
Write-Host " BFF TEST BUILD"
Write-Host "========================================"
Write-Host ""

# Clean previous PyInstaller output
if (Test-Path $DistRoot) {
    Remove-Item $DistRoot -Recurse -Force
}

if (Test-Path $BuildRoot) {
    Remove-Item $BuildRoot -Recurse -Force
}

# Build the application
Write-Host "Building $ExeName..."
pyinstaller --clean "$PSScriptRoot\BFF.spec"

# Make the writable data directory
$DataRoot = Join-Path $PackageRoot "data"

New-Item -ItemType Directory -Force -Path $DataRoot | Out-Null

# Copy the database OUTSIDE PyInstaller's _internal directory
$SourceDatabase = Join-Path $ProjectRoot "data\eso.db"
$TargetDatabase = Join-Path $DataRoot "eso.db"

if (-not (Test-Path $SourceDatabase)) {
    throw "Source database not found: $SourceDatabase"
}

Copy-Item $SourceDatabase $TargetDatabase -Force

Write-Host ""
Write-Host "Database copied to:"
Write-Host $TargetDatabase

# Copy every top-level data file the app reads at runtime --
# json/txt/md files only. Excludes eso.db (handled separately
# above/below) and create_canonical_identity_schema.py (a dev-only
# script, not something the running app imports), and never touches
# the data\normalized\ or data\uesp\ subfolders.
$SourceDataDir = Join-Path $ProjectRoot "data"

Get-ChildItem -Path $SourceDataDir -File |
    Where-Object { $_.Extension -notin ".py", ".db" } |
    Copy-Item -Destination $DataRoot -Force

Write-Host "Data files copied."

# Verify the important files
$BuiltExe = Join-Path $DistRoot $ExeName

if (-not (Test-Path $BuiltExe)) {
    throw "PyInstaller did not create $ExeName at: $BuiltExe"
}

# Create the final distribution directory
New-Item -ItemType Directory -Force -Path $PackageRoot | Out-Null

# Move the executable into the final distribution
Move-Item $BuiltExe (Join-Path $PackageRoot $ExeName) -Force

if (-not (Test-Path $TargetDatabase)) {
    throw "eso.db was not copied into the distribution."
}

Write-Host ""
Write-Host "========================================"
Write-Host " BUILD COMPLETE"
Write-Host "========================================"
Write-Host ""
Write-Host "Distribution:"
Write-Host $PackageRoot
Write-Host ""
Write-Host "Executable:"
Write-Host (Join-Path $PackageRoot $ExeName)
Write-Host ""
Write-Host "Database:"
Write-Host $TargetDatabase
Write-Host ""
