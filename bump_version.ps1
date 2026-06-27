param(
    [string]$NewVersion = "",
    [switch]$Patch,
    [switch]$Minor,
    [switch]$Major,
    [switch]$Commit
)

$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ManifestFile = Join-Path $SourceDir "blender_manifest.toml"
$InitFile = Join-Path $SourceDir "__init__.py"

# Read current version from manifest
$ManifestContent = Get-Content $ManifestFile -Raw
$CurrentVersion = "0.0.0"
if ($ManifestContent -match 'version\s*=\s*"([^"]+)"') {
    $CurrentVersion = $Matches[1]
}

Write-Host "========================================"
Write-Host " Mixamo Retarget Version Bumper"
Write-Host "========================================"
Write-Host ""
Write-Host "Current version: $CurrentVersion"

# Parse current version
$VerParts = $CurrentVersion.Split('.')
$MajorVer = [int]$VerParts[0]
$MinorVer = [int]$VerParts[1]
$PatchVer = [int]$VerParts[2]

if ($NewVersion -ne "") {
    # Validate format X.Y.Z
    if ($NewVersion -notmatch '^\d+\.\d+\.\d+$') {
        Write-Host "ERROR: Version must be in X.Y.Z format (e.g. 1.2.3)"
        exit 1
    }
    $TargetVersion = $NewVersion
} elseif ($Major) {
    $TargetVersion = "$($MajorVer + 1).0.0"
} elseif ($Minor) {
    $TargetVersion = "$MajorVer.$($MinorVer + 1).0"
} else {
    # Default: patch bump
    $TargetVersion = "$MajorVer.$MinorVer.$($PatchVer + 1)"
}

Write-Host "Target version: $TargetVersion"
Write-Host ""

# Update blender_manifest.toml
$ManifestContent = $ManifestContent -replace '(version\s*=\s*")[^"]+(")', "`${1}$TargetVersion`${2}"
$ManifestContent | Set-Content $ManifestFile -NoNewline
Write-Host "  Updated: blender_manifest.toml"

# Update __init__.py
$VerTuple = $TargetVersion -replace '\.', ', '
$InitContent = Get-Content $InitFile -Raw
$InitContent = $InitContent -replace '("version":\s*\()[\d,\s]+(\))', "`${1}$VerTuple`${2}"
$InitContent | Set-Content $InitFile -NoNewline
Write-Host "  Updated: __init__.py"

Write-Host ""
Write-Host "Version bumped: $CurrentVersion -> $TargetVersion"

if ($Commit) {
    git -C $SourceDir add "blender_manifest.toml" "__init__.py"
    git -C $SourceDir commit -m "Bump version to $TargetVersion"
    Write-Host "  Committed."
}

Write-Host ""
