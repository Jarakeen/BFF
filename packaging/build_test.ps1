$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path $PSScriptRoot -Parent
$DistRoot = Join-Path $ProjectRoot "dist"
$BuildRoot = Join-Path $ProjectRoot "build"
$PackageRoot = Join-Path $DistRoot "BFF"

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
Write-Host "Building BFF..."
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

# Copy builds.json if it exists
$SourceBuilds = Join-Path $ProjectRoot "data\builds.json"

if (Test-Path $SourceBuilds) {
    Copy-Item $SourceBuilds $DataRoot -Force
    Write-Host "builds.json copied."
}

# Verify the important files
$BuiltExe = Join-Path $DistRoot "BFF.exe"

if (-not (Test-Path $BuiltExe)) {
    throw "PyInstaller did not create BFF.exe at: $BuiltExe"
}

# Create the final distribution directory
New-Item -ItemType Directory -Force -Path $PackageRoot | Out-Null

# Move the executable into the final distribution
Move-Item $BuiltExe (Join-Path $PackageRoot "BFF.exe") -Force

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
Write-Host (Join-Path $PackageRoot "BFF.exe")
Write-Host ""
Write-Host "Database:"
Write-Host $TargetDatabase
Write-Host ""