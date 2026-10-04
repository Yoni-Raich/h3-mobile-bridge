$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$repo = Get-RepoRoot

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo 'scripts\validate-manifests.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Manifest validation failed.' }

$config = Get-BridgeConfig -RepoRoot $repo
$manifest = Get-JsonFile -Path (Join-Path $repo 'manifests\models.json')
$model = $manifest.models | Where-Object { $_.name -eq 'Official FL2V Turbo 4-step LoRA' }
if (-not $model) { throw 'The official FL2V Turbo LoRA is missing from manifests/models.json.' }

$targetDirectory = Resolve-ModelTargetDirectory -Model $model -Config $config
$destination = Join-Path $targetDirectory ([string]$model.filename)
$url = "$($model.source_repository)/resolve/$($model.revision)/$($model.source_path)?download=true"

Write-Host "Installing $($model.name) to $destination"
Install-VerifiedDownload -Url $url -Destination $destination -ExpectedBytes ([int64]$model.bytes) -ExpectedSha256 ([string]$model.sha256)
