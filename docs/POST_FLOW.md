# MiniMax H3 Post Flow

The bridge now exposes a `Post Flow` engine in the main generation screen.

## Route

1. DaSiWa MiniMax H3 Hybrid v2 INT8 base model.
2. Corrected official INT8 video VAE.
3. Turbo v4 step 600 LoRA at strength `1.0`.
4. Realism People LoRA at strength `0.8`.
5. The `r34l1sm` trigger is added automatically when it is not already in the prompt.
6. Optional LMS v1.0 R64 second pass at strength `0.8`, using the first MP4 as the guide video.

The LMS pass is available only after the first pass succeeds. Connected multi-shot sequences are intentionally disabled for this route.

## Installed and verified

The corrected VAE and all three LoRAs are installed under the native model tree and verified by size and SHA-256. The old, incompatible INT8 VAE copy was removed after a successful Fused + SLA render using the new VAE.

## Remaining resource

The DaSiWa base model is pinned to Civitai version `3314675`, file `3203130`, SHA-256:

`4cb8e1eaa9c3e5c664822760890bcbe6078455401cfa43205baf322e856d25f8`

Civitai currently requires an authenticated download for this file. Until that file is downloaded and verified, the UI keeps Post Flow disabled and shows the missing-resource note. The installer can resume the verified download after access is available:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install-post-flow.ps1
```

The installer refuses to replace a running ComfyUI process and never installs an unverified model.
