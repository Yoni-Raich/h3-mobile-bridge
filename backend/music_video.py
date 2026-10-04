"""Shared configuration and media helpers for audio-locked productions."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_AUDIO_CHUNKS: tuple[dict[str, Any], ...] = (
    {"start": 0.000, "end": 8.000, "caption_text": ""},
    {"start": 8.000, "end": 13.000, "caption_text": ""},
    {"start": 13.000, "end": 19.000, "caption_text": ""},
    {"start": 19.000, "end": 24.000, "caption_text": ""},
    {"start": 24.000, "end": 30.000, "caption_text": ""},
    {"start": 30.000, "end": 35.000, "caption_text": ""},
    {"start": 35.000, "end": 40.000, "caption_text": ""},
    {"start": 40.000, "end": 45.024, "caption_text": ""},
)

DEFAULT_LIP_SYNC_PROFILE: dict[str, Any] = {
    "mode": "lip_sync",
    "megapixels": 0.6,
    "aspect_ratio": "16:9",
    "engine": "turbo",
    "turbo_profile": "v1",
    "steps": 4,
    "fallback_engine": "standard",
    "fallback_steps": 20,
    "captions": "burned_ass",
    "fps": 24,
    "profile_version": 1,
}

DEFAULT_SILENT_PROFILE: dict[str, Any] = {
    "mode": "silent",
    "profile_version": 1,
}


def normalize_production_profile(value: Any | None) -> dict[str, Any]:
    """Validate the public production profile without changing old defaults."""
    if value is None or value == {}:
        return dict(DEFAULT_SILENT_PROFILE)
    if not isinstance(value, dict):
        raise ValueError("generation_profile must be a JSON object")
    mode = str(value.get("mode") or "silent").strip().lower()
    if mode not in {"silent", "lip_sync"}:
        raise ValueError("generation_profile.mode must be silent or lip_sync")
    if mode == "silent":
        return {**DEFAULT_SILENT_PROFILE, **{
            "megapixels": float(value["megapixels"]) if value.get("megapixels") is not None else None,
            "aspect_ratio": str(value.get("aspect_ratio") or "16:9"),
        }}
    try:
        megapixels = float(value.get("megapixels", DEFAULT_LIP_SYNC_PROFILE["megapixels"]))
    except (TypeError, ValueError):
        raise ValueError("Lip-sync megapixels must be a number") from None
    if not 0.1 <= megapixels <= 2.0:
        raise ValueError("Lip-sync megapixels must be between 0.1 and 2.0")
    aspect_ratio = str(value.get("aspect_ratio") or "16:9")
    if aspect_ratio not in {"1:1", "16:9", "9:16", "4:3", "3:4"}:
        raise ValueError("Lip-sync aspect ratio is unsupported")
    engine = str(value.get("engine") or "turbo").lower()
    if engine not in {"turbo", "standard"}:
        raise ValueError("Lip-sync engine must be turbo or standard")
    turbo_profile = str(value.get("turbo_profile") or "v1").lower()
    if turbo_profile != "v1":
        raise ValueError("Lip-sync uses Turbo profile v1")
    if engine == "turbo":
        steps = 4
    else:
        steps = max(8, min(30, int(value.get("steps", 20))))
    fallback = str(value.get("fallback_engine") or "standard").lower()
    if fallback not in {"none", "standard"}:
        raise ValueError("Lip-sync fallback must be none or standard")
    captions = str(value.get("captions") or "burned_ass").lower()
    if captions not in {"none", "burned_ass"}:
        raise ValueError("Captions must be none or burned_ass")
    return {
        **DEFAULT_LIP_SYNC_PROFILE,
        "megapixels": megapixels,
        "aspect_ratio": aspect_ratio,
        "engine": engine,
        "turbo_profile": turbo_profile,
        "steps": steps,
        "fallback_engine": fallback if engine == "turbo" else "none",
        "fallback_steps": 20,
        "captions": captions,
    }


def _duration(path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is required for audio chunk validation")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode:
        raise RuntimeError("Could not probe audio chunk: " + result.stderr[-1200:])
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError("Audio chunk has no readable duration") from exc


def normalize_audio_chunks(raw: Any, total_duration: float) -> list[dict[str, Any]]:
    """Accept AGY's plan only when it covers the source safely.

    A malformed or incomplete agent response falls back to the deterministic
    eight-shot plan. The fallback is recorded by the caller in the timeline.
    """
    candidates = raw
    if isinstance(raw, dict) and not isinstance(raw.get("audio_chunks"), list):
        # AGY responses may wrap the structured payload under content/analysis.
        pending = list(raw.values())
        candidates = None
        while pending:
            value = pending.pop(0)
            if isinstance(value, dict):
                if isinstance(value.get("audio_chunks"), list):
                    candidates = value["audio_chunks"]
                    break
                pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)
    elif isinstance(raw, dict):
        candidates = raw.get("audio_chunks")
    if not isinstance(candidates, list) or not candidates:
        candidates = list(DEFAULT_AUDIO_CHUNKS)
        source = "deterministic_default"
    else:
        source = "agy"
    parsed: list[dict[str, Any]] = []
    try:
        for item in candidates:
            if not isinstance(item, dict):
                raise ValueError
            start = float(item.get("start", item.get("audio_start")))
            end = float(item.get("end", item.get("audio_end")))
            if end <= start or end - start < 5.0 or end - start > 10.0:
                raise ValueError
            parsed.append({
                "start": round(start, 3),
                "end": round(end, 3),
                "caption_text": str(item.get("caption_text") or item.get("lyrics") or "").strip(),
                "title": str(item.get("title") or f"Shot {len(parsed) + 1}"),
                "visual_beat": str(item.get("visual_beat") or item.get("visual") or "").strip(),
            })
        parsed.sort(key=lambda item: item["start"])
        if abs(parsed[0]["start"]) > 0.05 or abs(parsed[-1]["end"] - total_duration) > 0.12:
            raise ValueError
        for previous, current in zip(parsed, parsed[1:]):
            if abs(previous["end"] - current["start"]) > 0.05:
                raise ValueError
    except (TypeError, ValueError):
        parsed = [dict(item) for item in DEFAULT_AUDIO_CHUNKS]
        source = "deterministic_default"
    parsed[-1]["end"] = round(total_duration, 3)
    for index, item in enumerate(parsed, 1):
        item["index"] = index
        item["duration"] = round(item["end"] - item["start"], 3)
    return [{"source": source, **item} for item in parsed]


def split_audio_chunks(
    source: Path,
    chunks: list[dict[str, Any]],
    audio_dir: Path,
    comfy_input: Path,
    production_id: str,
) -> list[dict[str, Any]]:
    """Create exact PCM chunks and copies that LoadAudio can see."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to split the song")
    audio_dir.mkdir(parents=True, exist_ok=True)
    comfy_input.mkdir(parents=True, exist_ok=True)
    result: list[dict[str, Any]] = []
    for item in chunks:
        index = int(item["index"])
        target = audio_dir / f"chunk_{index:02d}.wav"
        input_name = f"production_{production_id}_audio_{index:02d}.wav"
        input_target = comfy_input / input_name
        duration = float(item["duration"])
        command = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{float(item['start']):.6f}", "-i", str(source),
            "-t", f"{duration:.6f}", "-ar", "48000", "-ac", "2",
            "-c:a", "pcm_s16le", str(target),
        ]
        if not target.exists():
            completed = subprocess.run(command, capture_output=True, text=True, timeout=300)
            if completed.returncode or not target.exists():
                raise RuntimeError(f"Could not create audio chunk {index}: {completed.stderr[-2000:]}")
        actual = _duration(target)
        if actual < max(0.1, duration - 0.12):
            raise RuntimeError(f"Audio chunk {index} is too short: {actual:.3f}s vs {duration:.3f}s")
        if not input_target.exists() or input_target.stat().st_size != target.stat().st_size:
            shutil.copy2(target, input_target)
        result.append({
            **item,
            "audio_chunk_path": str(target),
            "audio_chunk_name": input_name,
            "actual_duration": round(actual, 6),
        })
    return result


def _ass_time(seconds: float) -> str:
    total_cs = max(0, round(float(seconds) * 100))
    hours, remainder = divmod(total_cs, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, centis = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def write_ass_captions(entries: list[dict[str, Any]], target: Path) -> Path:
    """Write a simple Hebrew-safe ASS subtitle file."""
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 832", "PlayResY: 480",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]", "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Arial,24,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80101010,0,0,0,0,100,100,0,0,1,2,0,2,36,36,28,1", "",
        "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for entry in entries:
        text = str(entry.get("caption_text") or "").strip()
        if not text:
            continue
        text = text.replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")
        lines.append(
            f"Dialogue: 0,{_ass_time(entry['start'])},{_ass_time(entry['end'])},Default,,0,0,0,,{text}"
        )
    target.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return target


def write_json(value: Any, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
