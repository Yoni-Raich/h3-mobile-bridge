# H3 model downloads

`manifests/models.json` is the source of truth. Do not download a different
file name, branch, or model revision and expect the bridge to use it.

## Recommended: download everything

Run these commands from the bridge repository root:

```powershell
Get-Content .\THIRD_PARTY_NOTICES.md
.\scripts\preflight.ps1 -Json
.\scripts\bootstrap.ps1 -Profile Full -AcceptLicenses
```

`bootstrap.ps1` does all of the following:

- downloads every entry in `manifests/models.json`;
- uses the pinned revision in the manifest;
- places each file in the configured ComfyUI model directory;
- resumes interrupted downloads through a `.part` file;
- checks the exact byte count and SHA-256 before installing the final file.

The script also installs the pinned ComfyUI and custom nodes. `-AcceptLicenses`
means that you have read and accepted the applicable upstream terms; it does
not grant a model license.

## Where files are installed

For a new portable setup, `config.example.json` uses `.runtime/models` as the
model root. If `config.local.json` contains an explicit `comfy.models` path,
bootstrap keeps that path. The folders below are relative to that model root:

| Model folder | Used for |
|---|---|
| `diffusion_models` | H3 FL2VA and REF2VA base diffusion weights |
| `text_encoders` | 32B native encoder and 4B ClipProj encoder |
| `vae` | Video and audio VAE files |
| `loras` | Turbo and Ref2VA Turbo LoRAs |
| `clip_projections` | ClipProj learned and identity-control weights |

The Turbo node grid is different: it is installed under the configured
ComfyUI root at
`custom_nodes/ComfyUI-MiniMax-H3-Turbo/h3_silu_temb_grid.safetensors`.

The bridge route uses ComfyUI on `127.0.0.1:8190`. The protected manual/native
route on `8188`, when used, is a separate process but can use the same model
root. Do not copy models into the repository or into `state/`.

## Complete model list

The `revision` column is part of the download URL. The SHA-256 value is
lowercase on purpose; PowerShell hashes are case-insensitive when compared.

| Name | File | Target folder | Size (bytes) | SHA-256 | Source |
|---|---|---|---:|---|---|
| H3 FL2VA diffusion | `minimax_h3_fl2va_pruned_int8_convrot.safetensors` | `diffusion_models` | `20970379616` | `e889202c41dafb67b10d67b97f0d8541508036a6090af23425a5c2615d03c47a` | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3), revision `014cd40f7e177756c6b2473c0d93b1c89a790dd2` |
| H3 REF2VA diffusion | `minimax_h3_ref2va_pruned_int8_convrot.safetensors` | `diffusion_models` | `20970379616` | `9255f52b6677845ad238f20dfaafa94727053694127ab7f255c048f0f9365779` | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3), revision `014cd40f7e177756c6b2473c0d93b1c89a790dd2` |
| H3 32B text encoder | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | `text_encoders` | `15687142551` | `35a88d51044231fe332301d7a62aa81e3f2cba62febeb446e2c1e3e0ef76f2c6` | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3), revision `014cd40f7e177756c6b2473c0d93b1c89a790dd2` |
| H3 4B ClipProj encoder | `qwen3vl_4b_fp8_scaled.safetensors` | `text_encoders` | `5242467968` | `54bd5144df0bbc25dd6ccadfcb826b521445a1b06ae5a42570bdd2974ca87094` | [Comfy-Org/Krea-2](https://huggingface.co/Comfy-Org/Krea-2), revision `952f49d49653cb42e7d6cf7cbfad74738073ec7d` |
| H3 video VAE | `minimax_h3_video_vae_fp16.safetensors` | `vae` | `5207808496` | `7c1f131492e7eddacaac9069a61b81bdd39de5cc96561e677c5eab1cdce5e522` | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3), revision `014cd40f7e177756c6b2473c0d93b1c89a790dd2` |
| H3 audio VAE | `minimax_h3_audio_vae_fp32.safetensors` | `vae` | `605254808` | `8e505d95dd1561d47abd43d4238fd40d9bb1ae9e147ed0a4cba778d76ae4db48` | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3), revision `014cd40f7e177756c6b2473c0d93b1c89a790dd2` |
| Turbo v1 LoRA | `minimax_h3_turbo_4step_ema_ckpt850.safetensors` | `loras` | `779849816` | `5a6eeba171cf183020a4ad48774bb2968f29f8168afd6ec17a04987f3528b4ea` | [MiniMax-H3-Turbo-Lora](https://huggingface.co/larryvrh/MiniMax-H3-Turbo-Lora), revision `43a74557ac3f6539db8e0f2a959d03feb7a81480` |
| Turbo v4 LoRA | `minimax_h3_turbo_v4_step600_ema.safetensors` | `loras` | `779849816` | `5f3a626cd72c93a8b9318d6760c510bc5092d2ab13aaba1f932c5bab07a416d3` | [MiniMax-H3-Turbo-Lora](https://huggingface.co/larryvrh/MiniMax-H3-Turbo-Lora), revision `43a74557ac3f6539db8e0f2a959d03feb7a81480` |
| Ref2VA Turbo 4-step LoRA | `minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors` | `loras` | `1956193000` | `5b9ab5ade15d0775676d01a907268a69a1468dc6033b3b0d3ded5502f3ebb84c` | [lightx2v/Minimax-h3-Turbo](https://huggingface.co/lightx2v/Minimax-h3-Turbo), revision `5d1d4829fe614c1b93fcfd9cc7718e9ba71f73e1` |
| ClipProj learned projection | `h3_qwen3vl_4b_tap24.safetensors` | `clip_projections` | `52511480` | `f0f7ecaf4f431f62055888cbd214c607bf4215feb002ef4aa43a3ba6205ac325` | [ClipProj-MiniMax-H3](https://huggingface.co/NicoLab28/ClipProj-MiniMax-H3), revision `ef89d0fc87ec004adc3330641dd6acb79bd785a7` |
| ClipProj identity control | `h3_control_identity.safetensors` | `clip_projections` | `52511408` | `6bd90824280210c53a5a2de4ddfb6c61a6f921ea3ab5c45fbb55e977629947b9` | [ClipProj-MiniMax-H3](https://huggingface.co/NicoLab28/ClipProj-MiniMax-H3), revision `ef89d0fc87ec004adc3330641dd6acb79bd785a7` |
| ClipProj zero control | `h3_control_zero.safetensors` | `clip_projections` | `52511400` | `73842bed5a64979e639cff06e0e9fab00e124f908b8a19b85b83130ffa54e3cb` | [ClipProj-MiniMax-H3](https://huggingface.co/NicoLab28/ClipProj-MiniMax-H3), revision `ef89d0fc87ec004adc3330641dd6acb79bd785a7` |
| Turbo node SiLU timestep grid | `h3_silu_temb_grid.safetensors` | ComfyUI custom node folder | `5510600` | `30eb3c2cc7fb6b470d9717ff840d359313ac27cd64b705e32da1baa10f72d6a8` | [ComfyUI-MiniMax-H3-Turbo](https://github.com/Larryvrh/ComfyUI-MiniMax-H3-Turbo), revision `55fee864dd7b2976b1c4ce3c3d5f7968f181409f` |

## Manual download of one file

Use this only when a single file is missing. Replace the values with one row
from the table and keep the `.part` suffix until verification passes:

```powershell
$url = 'https://huggingface.co/<owner>/<repo>/resolve/<revision>/<path>?download=true'
$destination = Join-Path $modelRoot 'loras/<filename>.safetensors'
$partial = "$destination.part"
New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
curl.exe --location --fail --retry 8 --retry-delay 3 --continue-at - --output $partial $url
Get-FileHash $partial -Algorithm SHA256
Move-Item -LiteralPath $partial -Destination $destination
```

For the GitHub grid file, use this URL form instead:

```text
https://raw.githubusercontent.com/<owner>/<repo>/<revision>/<path>
```

Do not rename a file to hide a wrong hash. Delete the bad file and run
bootstrap again. A Hugging Face login or acceptance of a gated model's terms,
when requested by Hugging Face, must be done by the user in the browser.

## Verify an installed setup

The quickest complete check is:

```powershell
.\scripts\validate-manifests.ps1
.\scripts\doctor.ps1 -Deep
```

To verify one file yourself:

```powershell
Get-FileHash '<full path to the file>' -Algorithm SHA256
```

Compare the result with this document and `manifests/models.json`. For the
experimental Turbo lip-sync route, the required files are the FL2VA diffusion
model, native 32B encoder, video VAE, audio VAE, Turbo v1 LoRA, and the Turbo
node plus its SiLU grid. Standard lip-sync does not need the Turbo LoRA.
