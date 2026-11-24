# package.ps1 - pack everything under pack\ into BadShader.mcpack
#
# pack\ is the source of truth: manifest.json, pack_icon.png and anything else
# you put there is shipped verbatim. The only thing this script writes into
# pack\ is the freshly compiled renderer\materials\*.material.bin taken from
# build\, so the pack never carries stale shaders.
#
# Usage (from the BE folder):  powershell -ExecutionPolicy Bypass -File package.ps1

$ErrorActionPreference = 'Stop'
$be    = $PSScriptRoot
$pack  = Join-Path $be 'pack'
$mats  = Join-Path $pack 'renderer\materials'
$out   = Join-Path $be 'BadShader.mcpack'

if (-not (Test-Path $pack)) {
    Write-Output 'ERROR: pack\ not found.'
    exit 1
}
if (-not (Test-Path (Join-Path $pack 'manifest.json'))) {
    Write-Output 'ERROR: pack\manifest.json not found.'
    exit 1
}

# --- refresh compiled materials --------------------------------------------
New-Item -ItemType Directory -Force -Path $mats | Out-Null
Remove-Item (Join-Path $mats '*.material.bin') -Force -ErrorAction SilentlyContinue

$count = 0
Get-ChildItem -File (Join-Path $be 'build\*.material.bin') -ErrorAction SilentlyContinue | ForEach-Object {
    Copy-Item $_.FullName $mats -Force
    $count++
    Write-Output ('packed: ' + $_.Name)
}
if ($count -eq 0) {
    Write-Output 'ERROR: no .material.bin in build\. Run the lazurite build first.'
    exit 1
}

# --- optional per-material textures (<Material>\textures\*.png) ------------
$texDir = Join-Path $mats 'textures'
if (Test-Path $texDir) { Remove-Item $texDir -Recurse -Force }
Get-ChildItem -Path (Join-Path $be '*\textures\*.png') -ErrorAction SilentlyContinue | ForEach-Object {
    New-Item -ItemType Directory -Force -Path $texDir | Out-Null
    Copy-Item $_.FullName $texDir -Force
    Write-Output ('texture: ' + $_.Name)
}

# --- zip pack\ verbatim into BadShader.mcpack ------------------------------
$zip = Join-Path $be '_pack.zip'
if (Test-Path $zip)  { Remove-Item $zip  -Force }
if (Test-Path $out)  { Remove-Item $out  -Force }
Compress-Archive -Path (Join-Path $pack '*') -DestinationPath $zip -Force
Move-Item -Path $zip -Destination $out -Force

Write-Output ''
Write-Output ('OK: ' + $out + ' (' + (Get-Item $out).Length + ' bytes, ' + $count + ' material(s))')
