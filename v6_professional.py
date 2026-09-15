#!/usr/bin/env python3
"""Professional final renderer for ShortAutoPro.

Keeps the stable V6 technical contract while applying the professional edit
plan: restrained hook emphasis, profile-specific finish, deterministic music,
curated-SFX-first sound design and configured final loudness/true peak.
"""

from __future__ import annotations

import glob
import hashlib
import json
import math
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
VIDEO_BASE = BASE / "temp" / SHORT_ID / "video_sem_audio.mp4"
AUDIO = BASE / "audios" / f"short_{SHORT_ID}.mp3"
ASS_ORIGINAL = BASE / "videos" / f"short_{SHORT_ID}.ass"
PRO_PLAN = BASE / "roteiros" / f"pro_edit_plan_{SHORT_ID}.json"
TEMP = BASE / "temp" / SHORT_ID
ASS_RETENTION = TEMP / "legenda_professional.ass"
MUSIC_DIR = BASE / "musicas"
SFX_DIR = BASE / "sfx"
GENERATED_SFX = TEMP / "professional_hook_impact.wav"
OUTPUT = BASE / "videos" / f"short_v6_{SHORT_ID}.mp4"

TEMP.mkdir(parents=True, exist_ok=True)
MUSIC_DIR.mkdir(parents=True, exist_ok=True)
SFX_DIR.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"ERRO V6 PROFESSIONAL: plano inválido: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("ERRO V6 PROFESSIONAL: plano precisa ser objeto JSON")
    return data


def safe_float(value: Any, default: float, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        number = default
    if not math.isfinite(number):
        number = default
    return max(low, min(high, number))


def duration(path: Path) -> float:
    try:
        raw = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ], text=True, timeout=45).strip()
        value = float(raw)
    except Exception as exc:
        raise SystemExit(f"ERRO V6 PROFESSIONAL: duração inválida de {path}: {exc}") from exc
    if not math.isfinite(value) or value <= 0:
        raise SystemExit(f"ERRO V6 PROFESSIONAL: duração não positiva: {path}")
    return value


def escape_ass(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def deterministic_pick(paths: list[str], salt: str) -> str | None:
    if not paths:
        return None
    ordered = sorted(paths)
    digest = hashlib.sha256(salt.encode("utf-8", errors="ignore")).digest()
    index = int.from_bytes(digest[:8], "big") % len(ordered)
    return ordered[index]


def media_files(folder: Path) -> list[str]:
    result: list[str] = []
    for pattern in ("*.mp3", "*.wav", "*.m4a", "*.aac", "*.ogg"):
        result.extend(glob.glob(str(folder / pattern)))
    return sorted(set(result))


def prepare_caption_ass(pop_scale: int) -> Path:
    text = ASS_ORIGINAL.read_text(encoding="utf-8", errors="strict")
    yellow = r"{\c&H00FFFF&\b1}"
    pop = (
        r"{\c&H00FFFF&\b1"
        rf"\fscx{pop_scale}\fscy{pop_scale}"
        r"\t(0,110,\fscx100\fscy100)}"
    )
    normal = r"{\c&HFFFFFF&\b1}"
    normal_reset = r"{\c&HFFFFFF&\b1\fscx100\fscy100}"
    text = text.replace(yellow, pop).replace(normal, normal_reset)

    # First caption gets restrained emphasis, not the old large 112% template punch.
    lines = text.splitlines()
    first = True
    output_lines: list[str] = []
    for line in lines:
        if first and line.startswith("Dialogue:"):
            parts = line.split(",", 9)
            if len(parts) == 10:
                parts[9] = r"{\fscx106\fscy106\bord3\shad2}" + parts[9] + r"{\fscx100\fscy100}"
                line = ",".join(parts)
                first = False
        output_lines.append(line)
    ASS_RETENTION.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    return ASS_RETENTION


def generate_optional_sfx() -> str | None:
    if os.getenv("SAP_PRO_ALLOW_GENERATED_SFX", "0") != "1":
        return None
    try:
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=62:sample_rate=48000:duration=0.55",
            "-af", "volume=0.45,lowpass=f=180,afade=t=in:st=0:d=0.01,afade=t=out:st=0.12:d=0.40",
            "-c:a", "pcm_s16le", str(GENERATED_SFX),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=45)
    except Exception:
        return None
    return str(GENERATED_SFX) if GENERATED_SFX.is_file() else None


def main() -> int:
    for path in (VIDEO_BASE, AUDIO, ASS_ORIGINAL, PRO_PLAN):
        if not path.is_file():
            print(f"ERRO V6 PROFESSIONAL: arquivo ausente: {path}")
            return 1

    plan = read_json(PRO_PLAN)
    finish = plan.get("finish", {}) if isinstance(plan.get("finish"), dict) else {}
    audio_policy = plan.get("audio", {}) if isinstance(plan.get("audio"), dict) else {}
    total = duration(AUDIO)

    contrast = safe_float(finish.get("contrast"), 1.035, 0.90, 1.15)
    saturation = safe_float(finish.get("saturation"), 0.99, 0.75, 1.20)
    brightness = safe_float(finish.get("brightness"), -0.004, -0.05, 0.05)
    sharpness = safe_float(finish.get("sharpness"), 0.12, 0.0, 0.30)
    hook_scale = safe_float(finish.get("hook_scale"), 1.025, 1.0, 1.06)
    pop_scale = int(safe_float(finish.get("caption_pop"), 106, 100, 112))

    target_lufs = safe_float(audio_policy.get("target_lufs", os.getenv("SAP_AUDIO_TARGET_LUFS", -14)), -14, -20, -10)
    true_peak = safe_float(audio_policy.get("true_peak_db", os.getenv("SAP_AUDIO_TRUE_PEAK_DB", -1.5)), -1.5, -6.0, -0.5)
    music_volume = safe_float(audio_policy.get("music_volume"), 0.045, 0.0, 0.15)
    limiter = max(0.5, min(0.98, 10 ** (true_peak / 20.0)))

    use_music = os.getenv("SHORT_USAR_MUSICA", "1") == "1"
    use_sfx = os.getenv("SHORT_USAR_SFX", "1") == "1"
    use_pop = os.getenv("SHORT_USAR_POP", "1") == "1"
    use_retention = os.getenv("SHORT_RETENTION_ENGINE", "1") == "1"

    ass_path = prepare_caption_ass(pop_scale if use_pop else 100)
    ass = escape_ass(ass_path)

    music = deterministic_pick(media_files(MUSIC_DIR), SHORT_ID + ":music") if use_music else None
    curated_sfx = deterministic_pick(media_files(SFX_DIR), SHORT_ID + ":sfx") if use_sfx else None
    sfx = curated_sfx or (generate_optional_sfx() if use_sfx else None)

    command = ["ffmpeg", "-y", "-i", str(VIDEO_BASE), "-i", str(AUDIO)]
    next_input = 2
    music_input = None
    sfx_input = None
    if music:
        music_input = next_input
        command.extend(["-stream_loop", "-1", "-i", music])
        next_input += 1
    if sfx:
        sfx_input = next_input
        command.extend(["-i", sfx])
        next_input += 1

    # Final hook emphasis is deliberately subtle because scene motion already exists.
    if use_retention and hook_scale > 1.0:
        extra_w = round(1080 * (hook_scale - 1.0), 3)
        extra_h = round(1920 * (hook_scale - 1.0), 3)
        zoom_w = f"'if(lt(t,0.18),1080+{extra_w}*(1-t/0.18),1080)'"
        zoom_h = f"'if(lt(t,0.18),1920+{extra_h}*(1-t/0.18),1920)'"
    else:
        zoom_w = "1080"
        zoom_h = "1920"

    video_filter = (
        "[0:v]"
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        f"scale={zoom_w}:{zoom_h}:eval=frame,"
        "crop=1080:1920,"
        f"eq=contrast={contrast:.4f}:saturation={saturation:.4f}:brightness={brightness:.4f},"
        f"unsharp=5:5:{sharpness:.4f}:5:5:0.0,"
        f"ass='{ass}'[v]"
    )

    audio_filters: list[str] = []
    if music_input is not None:
        audio_filters.append(
            "[1:a]highpass=f=70,acompressor=threshold=0.18:ratio=2.3:attack=18:release=170:makeup=1.10,"
            f"alimiter=limit={limiter:.5f},asplit=2[voice][voice_sidechain]"
        )
    else:
        audio_filters.append(
            "[1:a]highpass=f=70,acompressor=threshold=0.18:ratio=2.3:attack=18:release=170:makeup=1.10,"
            f"alimiter=limit={limiter:.5f}[voice]"
        )

    mix_inputs = ["[voice]"]
    if music_input is not None:
        fade_out = max(0.0, total - 1.4)
        audio_filters.append(
            f"[{music_input}:a]volume={music_volume:.5f},highpass=f=35,lowpass=f=15500,"
            f"afade=t=in:st=0:d=0.8,afade=t=out:st={fade_out:.3f}:d=1.4[music_pre]"
        )
        audio_filters.append(
            "[music_pre][voice_sidechain]sidechaincompress=threshold=0.032:ratio=6:attack=18:release=280:makeup=1[music]"
        )
        mix_inputs.append("[music]")

    if sfx_input is not None:
        sfx_volume = 0.10 if curated_sfx else 0.065
        audio_filters.append(
            f"[{sfx_input}:a]atrim=start=0:end=0.8,asetpts=PTS-STARTPTS,volume={sfx_volume:.3f},"
            f"afade=t=out:st=0.18:d=0.45,alimiter=limit={limiter:.5f}[sfx]"
        )
        mix_inputs.append("[sfx]")

    audio_filters.append(
        "".join(mix_inputs)
        + f"amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=2,"
        + f"loudnorm=I={target_lufs:.2f}:LRA=7:TP={true_peak:.2f},"
        + f"alimiter=limit={limiter:.5f}[a]"
    )

    filter_complex = video_filter + ";" + ";".join(audio_filters)
    try:
        OUTPUT.unlink(missing_ok=True)
    except OSError:
        pass

    command.extend([
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", os.getenv("SHORT_PRESET", "fast"),
        "-crf", os.getenv("SHORT_CRF", "20"), "-profile:v", "high", "-level", "4.1",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-t", f"{total:.6f}", "-movflags", "+faststart", str(OUTPUT),
    ])

    print("\n================================")
    print("V6 PROFESSIONAL RENDERER 1.0")
    print("================================")
    print(f"Perfil: {plan.get('profile', 'default')} | estilo: {plan.get('style', 'premium_documentary')}")
    print(f"Finish: contrast={contrast:.3f} saturation={saturation:.3f} brightness={brightness:.3f} sharp={sharpness:.3f}")
    print(f"Hook scale: {hook_scale:.3f} | caption pop: {pop_scale}%")
    print(f"Music: {'ON' if music else 'OFF'} | SFX: {'CURATED' if curated_sfx else 'GENERATED' if sfx else 'OFF'}")
    print(f"Loudness target: {target_lufs:.1f} LUFS | true peak: {true_peak:.1f} dB")
    print()

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"ERRO V6 PROFESSIONAL: ffmpeg retornou {exc.returncode}")
        return exc.returncode or 1

    if not OUTPUT.is_file() or OUTPUT.stat().st_size < 500_000:
        print("ERRO V6 PROFESSIONAL: saída ausente ou pequena demais")
        return 1

    print(f"V6 PROFESSIONAL: PASS\nArquivo: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
