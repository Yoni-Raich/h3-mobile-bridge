param([switch]$SkipCivitai)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$repo = Get-RepoRoot
$config = Get-BridgeConfig -RepoRoot $repo

foreach ($port in @(8188, 8190)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "ComfyUI is listening on $port. Stop it before replacing or adding Post Flow files."
    }
}

$modelRoot = $config.Models
$vaeDestination = Join-Path $modelRoot 'vae\minimax_h3_video_vae_int8_convrot.safetensors'
$downloads = @(
    [pscustomobject]@{
        Name = 'official corrected INT8 video VAE'
        Url = 'https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_video_vae_int8_convrot.safetensors?download=true'
        Destination = "$vaeDestination.post-new"
        Bytes = 2811065184
        Sha256 = '52a2c8c73583c86e4f41cdcce3a6ad0ea562987bc0bf3d60a0cef5f5c8e60c0e'
    },
    [pscustomobject]@{
        Name = 'Turbo v4 step 600 pruned ComfyUI LoRA'
        Url = 'https://huggingface.co/drbaph/MiniMax-H3-Turbo-Lora-ComfyUI/resolve/main/minimax_h3_turbo_v4_step600_ema_pruned_comfyui.safetensors?download=true'
        Destination = Join-Path $modelRoot 'loras\minimax_h3_turbo_v4_step600_ema_pruned_comfyui.safetensors'
        Bytes = 620285592
        Sha256 = '7098acf3ee75028fd9fcd948f50fcc8d995057fabb76f86bd3ca2c0ffc58e409'
    },
    [pscustomobject]@{
        Name = 'Realism People LoRA'
        Url = 'https://huggingface.co/fal/MiniMax-H3-Realism-People-LoRA/resolve/main/h3-realism-people-t2v-i2v-r2v.safetensors?download=true'
        Destination = Join-Path $modelRoot 'loras\h3-realism-people-t2v-i2v-r2v.safetensors'
        Bytes = 131229656
        Sha256 = 'acc529601d2da117fb81179e76c56e488a3beab1171659d305f04fa3655b787e'
    },
    [pscustomobject]@{
        Name = 'LMS v1.0 rank 64 LoRA'
        Url = 'https://huggingface.co/Alissonerdx/Minimax-H3-ComfyUI/resolve/main/loras/minimax_h3_lms_v1.0_r64.safetensors?download=true'
        Destination = Join-Path $modelRoot 'loras\minimax_h3_lms_v1.0_r64.safetensors'
        Bytes = 1239664536
        Sha256 = '16f3195bc6bffa431c0598dc2031e520ba058b4fcbc9f104db9e3fdfdeacf60c'
    }
)

foreach ($item in $downloads) {
    Write-Host "Installing $($item.Name)..."
    Install-VerifiedDownload -Url $item.Url -Destination $item.Destination -ExpectedBytes $item.Bytes -ExpectedSha256 $item.Sha256
}

if (-not $SkipCivitai) {
    $civitai = [pscustomobject]@{
        Name = 'DaSiWa MiniMax H3 Hybrid v2 INT8'
        Url = 'https://civitai.com/api/download/models/3314675?fileId=3203130'
        Destination = Join-Path $modelRoot 'diffusion_models\DasiwaMinimaxH3_dasiwaHybridV2_3203130.safetensors'
        Bytes = 20967669160
        Sha256 = '4cb8e1eaa9c3e5c664822760890bcbe6078455401cfa43205baF322e856d25f8'.ToLowerInvariant()
    }
    Write-Host "Installing $($civitai.Name)..."
    Install-VerifiedDownload -Url $civitai.Url -Destination $civitai.Destination -ExpectedBytes $civitai.Bytes -ExpectedSha256 $civitai.Sha256
}

if (Test-Path -LiteralPath $vaeDestination -PathType Leaf) {
    $oldHash = (Get-FileHash -LiteralPath $vaeDestination -Algorithm SHA256).Hash.ToLowerInvariant()
    $expected = $downloads[0].Sha256.ToLowerInvariant()
    if ($oldHash -ne $expected) {
        $oldPath = "$vaeDestination.post-old"
        if (Test-Path -LiteralPath $oldPath -PathType Leaf) {
            throw "A previous VAE replacement file already exists: $oldPath"
        }
        Move-Item -LiteralPath $vaeDestination -Destination $oldPath
        Write-Host "Moved the old VAE to $oldPath for validation after the new file is tested."
    }
}

if (Test-Path -LiteralPath "$vaeDestination.post-new" -PathType Leaf) {
    Move-Item -LiteralPath "$vaeDestination.post-new" -Destination $vaeDestination
}

Write-Host 'Post Flow downloads are installed and verified.'
