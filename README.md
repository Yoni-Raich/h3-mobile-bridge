# H3 Mobile Bridge

Portable private bridge for local MiniMax H3 video generation on Windows 10/11
x64 with an NVIDIA GPU. The bridge stays on `127.0.0.1`; Tailscale Serve gives
private HTTPS access only to devices allowed in the current user's tailnet.

## Quick start

```powershell
git clone https://github.com/shambik/comfy-mobile-bridge.git comfy-mobile-bridge
Set-Location .\comfy-mobile-bridge
.\scripts\preflight.ps1 -Json
Get-Content .\THIRD_PARTY_NOTICES.md
.\scripts\bootstrap.ps1 -Profile Full -AcceptLicenses
.\scripts\start.ps1
.\scripts\doctor.ps1 -Deep
```

The bootstrap downloads pinned ComfyUI, custom nodes, Python packages, FFmpeg
checks, Tailscale checks, and external model files. It never stores models,
runtime files, state, logs, or local configuration in Git.

For the exact file list, destinations, pinned revisions, download sources, and
SHA-256 checks, see [`docs/MODEL_DOWNLOADS.md`](docs/MODEL_DOWNLOADS.md).

## GPU conflict warning

The app checks for `FortniteClient-Win64-Shipping.exe` and displays a warning
when Fortnite is running, because it can compete with ComfyUI for GPU memory
and make a generation appear stuck. The warning does not close Fortnite.

The app's ComfyUI stop control stops only the ComfyUI process tree; it keeps
the mobile bridge running so the UI and logs remain available.

For Ref2VA Turbo, bootstrap also downloads and verifies the dedicated
`minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors` LoRA. If an
existing ComfyUI installation is configured in `config.local.json`, bootstrap
preserves its root, Python, models, and media-directory paths instead of
switching them to the portable layout.

The optional DaSiWa Post Flow is available in the generation UI. It combines
the DaSiWa base, corrected INT8 VAE, Turbo v4, Realism People, and an optional
LMS second pass. See [`docs/POST_FLOW.md`](docs/POST_FLOW.md) for the pinned
files and installation status.

## Requirements

- Windows 10/11 x64.
- NVIDIA GPU with at least 8 GiB VRAM, 32 GiB RAM, and 100 GB free disk.
- Git, Python 3.12, Node.js 22, FFmpeg/ffprobe, and Tailscale.
- A Tailscale login for the user who owns this computer. Do not use another
  person's tailnet or hostname.
- License review for downloaded model and node files before bootstrap.

## What bootstrap creates

```text
.runtime/
├── comfyui/
├── models/
├── python/
└── downloads/
state/
├── input/
├── output/
└── logs/
config.local.json
```

The local configuration is generated from `config.example.json`. It contains
the current machine's paths and detected Tailscale hostname and is ignored.

## Ports and private access

- Bridge: `127.0.0.1:8787`.
- ComfyUI: `127.0.0.1:8190`.
- Tailscale Serve: HTTPS to the bridge inside the current tailnet.
- Funnel is never enabled.

Use `.\scripts\doctor.ps1 -Deep` to check listeners, Serve, nodes, files,
hashes, and API health. Use `.\scripts\stop.ps1` to stop only processes
started by this bridge.

For complete Windows setup and phone-access instructions, see
[`docs/TAILSCALE.md`](docs/TAILSCALE.md).

## Development

```powershell
npm ci
npm run build
python -m unittest discover -s tests -p "test_*.py"
```

The bridge supports text-to-video, first/last-frame video, reference video,
native stereo audio, Turbo, Standard, Spectrum, and the optional ClipProj
encoder. Turbo remains the default profile. No paid API nodes and no
SageAttention are part of this release.

## Studio asset library

Generated videos can be assigned to a Studio project and optional subfolder,
either before generation or afterward from the result card. These UI actions
create, move, rename, and delete the corresponding files on disk under the
canonical `state/projects/<project>/<folder>/` structure. Existing unassigned
videos remain in the configured ComfyUI output directory until organized.

See [`docs/ASSET_LIBRARY.md`](docs/ASSET_LIBRARY.md) for the filesystem rules,
safety checks, and configuration.

## Agent Production Studio POC

The **Production** page adds a responsive production council made up of the
user, Codex, and AGY. It supports persistent projects, autonomous or
interactive planning, model and reasoning selection, selectable production
skills, user messages and decisions, and pause/stop/resume checkpoints. Codex
and AGY run through the locally authenticated CLIs; their credentials never
enter the browser.

The POC carries a project through song analysis, joint treatment/storyboard
consultation, reference planning, executable shot prompts, silent ComfyUI
generation, per-attempt Codex + AGY review, bounded regeneration, hard-cut
assembly, original-song attachment, final joint review, and explicit user
approval. Production jobs use the existing ComfyUI queue and the workflow's
own duration and resolution calculator nodes; existing Studio behavior is
unchanged. Restart recovery preserves shot attempts and can reattach to an
already queued job or resume review of a completed clip.

Reference development produces an executable reference package. Codex then
uses its authenticated built-in ImageGen tool to create project-bound stills;
AGY inspects each actual image and Codex reviews AGY's findings before the
still is registered for I2V/R2V. Users can also upload their own images,
videos, and audio, assign them per shot, edit a shot, and retry only that shot
plus any dependent sequential shots. Sequential I2V shots use the previous
accepted last frame; independent I2V shots use an assigned opening image.

The Reference Media panel also supports manual still generation. Auto mode
tries Codex ImageGen and falls back to AGY ImageGen; either provider can be
selected directly. Multiple productions can advance concurrently (three by
default through `agents.production_concurrency`), while the global ComfyUI
queue intentionally keeps GPU video generation serialized.

The producer seat can run through either Codex CLI or AGY CLI. Its model list
comes from the selected authenticated runtime rather than a hardcoded UI list.
The media producer stays on AGY because audio/video inspection is required.
Productions can be reconfigured while inactive, duplicated with their shot
plan and remapped references, archived, exported, or deleted. Completed jobs
from the regular generation page can be imported into a production.

See [`docs/architecture/agent-production-studio.md`](docs/architecture/agent-production-studio.md)
and [`todo/agent-production-studio-plan.md`](todo/agent-production-studio-plan.md).

## Local Qwen Image Studio

The Image Gen page supports the regular Qwen-Image-2.1 GGUF and the optional
Viggle Turbo Q4_K_M GGUF. Turbo uses exactly 4 steps, CFG 1.0, an empty
negative prompt, and the existing Euler/simple sampler settings. Install the
verified Turbo weight with `scripts/install-qwen-image-turbo.ps1`; the model
file is pinned by size and SHA-256 in `manifests/models.json`.

The Viggle Turbo checkpoint is a preview derived from Qwen Image 2.1. Review
the Qwen Research License in `THIRD_PARTY_NOTICES.md` before using or
redistributing the weights.

Read `.agents/skills/h3-environment-bootstrap/SKILL.md` before setup and
`.agents/skills/h3-mobile-bridge-codebase/SKILL.md` before code changes.
Read `.agents/skills/git-standards/SKILL.md` before Git work and
`.agents/skills/release-process/SKILL.md` before releases.

## Speed and Turbo profiles

Two opt-in settings came out of a measured review on an RTX 4060 8GB with 32GB
RAM. They are single-machine results, not guarantees for other hardware.

- **Triton backend.** Set `comfy.enable_triton_backend` to `true` in
  `config.local.json` to launch ComfyUI with `--enable-triton-backend`. The same
  0.6MP, 56-frame, four-step render took 177s without it and 106-118s with it.
- **Official Turbo profile.** `turbo_profile=official` uses the Comfy-Org
  four-step 768p FL2V Turbo LoRA with Euler, the simple scheduler and video/audio
  shift 6/3, at exactly four steps. Install the pinned file with
  `scripts/install-official-turbo.ps1`. Against Turbo v4 on one 141-frame shot it
  took 301s versus 332s and produced more motion. Across 46 shots of a full music
  video at 1056x608 the median was 160s per shot, about 2.2s per frame.
- **Lip-sync.** The Studio defaults lip-sync to Turbo v1 with Native AudioLock at
  four steps. A 6.6s clip at 0.6MP took about 6 minutes, versus about 23 minutes
  on the Standard 20-step route. The uploaded audio is kept unchanged. Mouth
  accuracy was judged by eye, not measured.

`app.allowed_hosts` in `config.local.json` adds extra host names, such as a LAN
address, to the allowed list.

The Studio UI is mobile-first: bottom navigation, Create / Queue / Library views,
one-tap quality presets and a System page for ComfyUI power, hardware meters and
logs.

## Proof boundaries

CI proves source build and tests. A hash report proves a downloaded file. API
health proves the bridge is responding. `ffprobe` and a full FFmpeg decode
prove media validity. GPU generation and second-device Tailscale access are
separate clean-machine acceptance proofs.

See `THIRD_PARTY_NOTICES.md` for upstream code, node, model, and license links.
