# H3 mobile Studio verification - 2026-10-04

The local bridge uses the reviewed H3 video profiles and the new mobile UI.

## Generation settings

- Recommended Studio video: Official FL2V Turbo, Native encoder, 4 steps, 0.6 MP.
- Studio lip-sync: Turbo v1, Native AudioLock, 4 steps, 0.6 MP.
- New lip-sync productions: 0.6 MP. Explicit saved production settings are preserved.
- Resolution metadata and the UI match ComfyUI ResolutionSelector: 0.6 MP / 16:9 is 1056x608.
- Triton is opt-in in portable configuration and enabled on the reviewed local installation.
- Reference input groups use the dotted sockets exposed by the current ComfyUI nodes.

## Checks completed

- 96 isolated Python tests passed; test configuration uses separate runtime directories and ports.
- Clean worktree npm ci and npm run build passed.
- Vite updated to 6.4.3 and Nano ID to 3.3.18; npm audit reports zero known vulnerabilities.
- Browser checks at 320, 390, 720 and 1440 pixels passed without horizontal overflow or page errors.
- Create, Queue, Library, System, Images and Production views were inspected.
- Intercepted generation requests verified Official Turbo and audio-locked Turbo v1 settings.
- No GPU jobs were submitted by these browser tests. They verify configuration and UI, not new video quality.
- The ordinary ComfyUI listener responded with the Triton flag enabled. Bridge health and private proxy access returned successfully.
- SQLite was backed up before restart; existing media, models and job state were retained.
- Current source and the reachable publication history were scanned for known personal paths, private hostnames and token patterns.

## Remaining installation differences

The existing local ComfyUI checkout is newer than the portable manifest pin.
The existing local bridge configuration also enables LAN binding, while Doctor expects loopback.
Doctor therefore reports those existing differences. Its checks are not all green.
Neither the local ComfyUI checkout nor the user's existing LAN configuration was replaced during this UI update.
A full download and GPU render from the pinned portable environment on a second computer was not performed.

## Publication and rollback

The publication branch starts from the public main branch and includes a sanitized production baseline,
then separate engine, UI, database, documentation and test commits. Private local history is retained locally.
Local configuration, models, state, media and the local patch file are excluded from Git.

To roll back the interface, use the previous app revision and rebuild its frontend.
Turn off comfy.enable_triton_backend in local configuration and restart ComfyUI to disable Triton.
Choose Standard or an existing manually saved profile to use the earlier generation route.
Keep the SQLite backup when rolling back across schema changes.