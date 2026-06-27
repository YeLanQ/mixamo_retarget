param()

$ErrorActionPreference = "Stop"
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Read version from manifest
$Version = "0.0.0"
$ManifestFile = Join-Path $SourceDir "blender_manifest.toml"
if (Test-Path $ManifestFile) {
    $Content = Get-Content $ManifestFile -Raw
    if ($Content -match '(?m)^version\s*=\s*"([^"]+)"') {
        $Version = $Matches[1]
    }
}

$Timestamp = Get-Date -Format "yyyyMMdd"
$ZipFilename = "mixamo_retarget_${Version}_${Timestamp}.zip"
$ZipPath = Join-Path $SourceDir $ZipFilename

Write-Host "========================================"
Write-Host " Mixamo Retarget Package Builder"
Write-Host "========================================"
Write-Host ""
Write-Host "Version: $Version"
Write-Host "Output: $ZipFilename"
Write-Host ""

if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}

$FilesToInclude = @(
    "__init__.py",
    "blender_manifest.toml",
    "operators.py",
    "panels.py",
    "properties.py",
    "retarget.py",
    "ui_list.py"
)

$TempDir = Join-Path $SourceDir "temp_package"
if (Test-Path $TempDir) {
    Remove-Item $TempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $TempDir | Out-Null
$TempAddonDir = Join-Path $TempDir "mixamo_retarget"
New-Item -ItemType Directory -Path $TempAddonDir | Out-Null

Write-Host "Copying files..."
foreach ($File in $FilesToInclude) {
    $SourceFile = Join-Path $SourceDir $File
    $DestFile = Join-Path $TempAddonDir $File
    if (Test-Path $SourceFile) {
        Copy-Item $SourceFile $DestFile
        Write-Host "  Added: $File"
    } else {
        Write-Host "  Warning: $File not found, skipping"
    }
}

Write-Host ""
Write-Host "Creating zip archive..."
Compress-Archive -Path $TempAddonDir -DestinationPath $ZipPath -Force

Remove-Item $TempDir -Recurse -Force

if (Test-Path $ZipPath) {
    $FileSize = (Get-Item $ZipPath).Length
    $SizeKB = [math]::Round($FileSize / 1024, 1)

    Write-Host ""
    Write-Host "========================================"
    Write-Host " Package created successfully!"
    Write-Host "========================================"
    Write-Host ""
    Write-Host "File: $ZipFilename"
    Write-Host "Size: $SizeKB KB"
    Write-Host ""
    Write-Host "To install in Blender:"
    Write-Host "1. Edit > Preferences > Add-ons > Install from Disk"
    Write-Host "2. Select: $ZipFilename"
    Write-Host "3. Enable 'Mixamo Retarget'"
} else {
    Write-Host ""
    Write-Host "ERROR: Failed to create zip file!"
}

Write-Host ""
