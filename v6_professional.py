#!/usr/bin/env python3
"""Professional final renderer for ShortAutoPro 3.0.

Applies profile finish, professional captions, mood-aware music, timed curated
SFX and voice-priority ducking. Final codec loudness is verified/remastered by
audio_finalizer.py after this stage.
"""
from __future__ import annotations

import glob
import hashlib
import json
import math
import os
import subprocess
import time
from datetime import date
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
VIDEO_BASE = BASE / "temp" / SHORT_ID / "video_sem_audio.mp4"
AUDIO = BASE / "audios" / f"short_{SHORT_ID}.mp3"
ASS_ORIGINAL = BASE / "videos" / f"short_{SHORT_ID}.ass"
PRO_PLAN = BASE / "roteiros" / f"pro_edit_plan_{SHORT_ID}.json"
RUNTIME = BASE / "roteiros" / f"pro_edit_runtime_{SHORT_ID}.json"
SOUND_PLAN = BASE / "roteiros" / f"sound_design_{SHORT_ID}.json"
TEMP = BASE / "temp" / SHORT_ID
ASS_RETENTION = TEMP / "legenda_professional.ass"
MUSIC_DIR = BASE / "musicas"
SFX_DIR = BASE / "sfx"
GENERATED_SFX = TEMP / "professional_hook_impact.wav"
OUTPUT = BASE / "videos" / f"short_v6_{SHORT_ID}.mp4"

for directory in (TEMP, MUSIC_DIR, SFX_DIR): directory.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, optional: bool = False) -> dict[str, Any]:
    if optional and not path.is_file(): return {}
    try: data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc: raise SystemExit(f"ERRO V6 PROFESSIONAL: plano inválido {path.name}: {exc}") from exc
    if not isinstance(data, dict): raise SystemExit(f"ERRO V6 PROFESSIONAL: {path.name} precisa ser objeto JSON")
    return data


def safe_float(value: Any, default: float, low: float, high: float) -> float:
    try: number = float(value)
    except (TypeError, ValueError, OverflowError): number = default
    if not math.isfinite(number): number = default
    return max(low, min(high, number))


def video_stream_info(path: Path) -> dict[str, Any]:
    try:
        raw = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,pix_fmt,color_range",
                "-of", "json",
                str(path),
            ],
            text=True,
            timeout=45,
        )
        data = json.loads(raw)
        streams = data.get("streams", []) if isinstance(data, dict) else []
        return streams[0] if streams and isinstance(streams[0], dict) else {}
    except Exception:
        return {}


def termux_runtime() -> bool:
    prefix = os.getenv("PREFIX", "")
    return (
        "com.termux" in prefix
        or "com.termux" in str(BASE)
        or os.getenv("TERMUX_VERSION") is not None
    )


def render_preset() -> str:
    explicit = os.getenv("SHORT_PRESET", "").strip()
    if explicit:
        return explicit
    return "veryfast" if termux_runtime() else "fast"


def render_threads() -> int:
    try:
        configured = int(os.getenv("SAP_RENDER_THREADS", "0") or 0)
    except (TypeError, ValueError):
        configured = 0
    if configured > 0:
        return max(1, min(configured, 8))
    cpu = os.cpu_count() or 4
    return max(2, min(cpu, 6))


def duration(path: Path) -> float:
    try:
        raw = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], text=True, timeout=45).strip(); value = float(raw)
    except Exception as exc: raise SystemExit(f"ERRO V6 PROFESSIONAL: duração inválida de {path}: {exc}") from exc
    if not math.isfinite(value) or value <= 0: raise SystemExit(f"ERRO V6 PROFESSIONAL: duração não positiva: {path}")
    return value


def escape_ass(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def deterministic_pick(paths: list[str], salt: str) -> str | None:
    if not paths: return None
    ordered = sorted(paths); digest = hashlib.sha256(salt.encode("utf-8", errors="ignore")).digest(); return ordered[int.from_bytes(digest[:8], "big") % len(ordered)]


def media_files(folder: Path) -> list[str]:
    result: list[str] = []
    for pattern in ("*.mp3", "*.wav", "*.m4a", "*.aac", "*.ogg"): result.extend(glob.glob(str(folder / pattern)))
    return sorted(set(result))


def mood_pick(paths: list[str], mood: str, salt: str) -> str | None:
    if not paths: return None
    mood_tokens = {x for x in mood.lower().replace("-", "_").split("_") if len(x) >= 3}
    aliases = {
        "tension": {"dark", "tense", "suspense", "mystery"},
        "cinematic": {"epic", "cinema", "dramatic"},
        "retro": {"retro", "vintage", "synth"},
        "curiosity": {"curious", "light", "mystery"},
        "suspense": {"suspense", "mystery", "tense"},
    }
    expanded = set(mood_tokens)
    for token in list(mood_tokens): expanded |= aliases.get(token, set())
    matching = [p for p in paths if any(token in Path(p).stem.lower() for token in expanded)]
    return deterministic_pick(matching or paths, salt + ":" + mood)


def prepare_caption_ass(pop_scale: int) -> Path:
    text = ASS_ORIGINAL.read_text(encoding="utf-8", errors="strict")
    yellow = r"{\c&H00FFFF&\b1}"; pop = r"{\c&H00FFFF&\b1" + rf"\fscx{pop_scale}\fscy{pop_scale}" + r"\t(0,110,\fscx100\fscy100)}"; normal = r"{\c&HFFFFFF&\b1}"; normal_reset = r"{\c&HFFFFFF&\b1\fscx100\fscy100}"
    text = text.replace(yellow, pop).replace(normal, normal_reset)
    lines = text.splitlines(); first = True; output_lines = []
    for line in lines:
        if first and line.startswith("Dialogue:"):
            parts = line.split(",", 9)
            if len(parts) == 10:
                parts[9] = r"{\fscx106\fscy106\bord3\shad2}" + parts[9] + r"{\fscx100\fscy100}"; line = ",".join(parts); first = False
        output_lines.append(line)
    ASS_RETENTION.write_text("\n".join(output_lines) + "\n", encoding="utf-8"); return ASS_RETENTION


def generate_optional_sfx() -> str | None:
    if os.getenv("SAP_PRO_ALLOW_GENERATED_SFX", "0") != "1": return None
    try:
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=62:sample_rate=48000:duration=0.55", "-af", "volume=0.40,lowpass=f=180,afade=t=in:st=0:d=0.01,afade=t=out:st=0.12:d=0.40", "-c:a", "pcm_s16le", str(GENERATED_SFX)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=45)
    except Exception: return None
    return str(GENERATED_SFX) if GENERATED_SFX.is_file() else None


def scene_starts(runtime: dict[str, Any]) -> dict[int, float]:
    durations = runtime.get("durations", []) if isinstance(runtime.get("durations"), list) else []
    result: dict[int, float] = {}; current = 0.0
    for index, raw in enumerate(durations, 1):
        result[index] = current
        try: current += max(0.0, float(raw))
        except Exception: pass
    return result


def curated_sfx_for(event_type: str, paths: list[str], salt: str) -> str | None:
    terms = {
        "hit_soft": {"hit", "impact", "soft"},
        "riser_hit": {"riser", "rise", "impact", "hit"},
        "subtle_tick": {"tick", "click", "subtle"},
        "resolve_soft": {"resolve", "soft", "chime"},
    }.get(event_type, {event_type})
    matching = [p for p in paths if any(t in Path(p).stem.lower() for t in terms)]
    return deterministic_pick(matching or paths, salt + ":" + event_type) if paths else None


def main() -> int:
    for path in (VIDEO_BASE, AUDIO, ASS_ORIGINAL, PRO_PLAN):
        if not path.is_file(): print(f"ERRO V6 PROFESSIONAL: arquivo ausente: {path}"); return 1

    plan = read_json(PRO_PLAN); runtime = read_json(RUNTIME, optional=True); sound = read_json(SOUND_PLAN, optional=True)
    finish = plan.get("finish", {}) if isinstance(plan.get("finish"), dict) else {}; audio_policy = plan.get("audio", {}) if isinstance(plan.get("audio"), dict) else {}
    total = duration(AUDIO)

    contrast = safe_float(finish.get("contrast"), 1.035, 0.90, 1.15); saturation = safe_float(finish.get("saturation"), 0.99, 0.75, 1.20); brightness = safe_float(finish.get("brightness"), -0.004, -0.05, 0.05); sharpness = safe_float(finish.get("sharpness"), 0.12, 0.0, 0.30); hook_scale = safe_float(finish.get("hook_scale"), 1.025, 1.0, 1.06); pop_scale = int(safe_float(finish.get("caption_pop"), 106, 100, 112))
    target_lufs = safe_float(audio_policy.get("target_lufs", os.getenv("SAP_AUDIO_TARGET_LUFS", -14)), -14, -20, -10); true_peak = safe_float(audio_policy.get("true_peak_db", os.getenv("SAP_AUDIO_TRUE_PEAK_DB", -1.5)), -1.5, -6.0, -0.5); music_volume = safe_float(sound.get("music_volume", audio_policy.get("music_volume", 0.045)), 0.045, 0.0, 0.15); duck = sound.get("ducking", {}) if isinstance(sound.get("ducking"), dict) else {}; duck_ratio = safe_float(duck.get("ratio", audio_policy.get("duck_ratio", 6)), 6, 2, 12); duck_threshold = safe_float(duck.get("threshold", 0.032), 0.032, 0.005, 0.2); duck_attack = int(safe_float(duck.get("attack_ms", 18), 18, 2, 100)); duck_release = int(safe_float(duck.get("release_ms", 300), 300, 80, 1000)); limiter = max(0.5, min(0.98, 10 ** (true_peak / 20.0)))

    use_music = os.getenv("SHORT_USAR_MUSICA", "1") == "1"; use_sfx = os.getenv("SHORT_USAR_SFX", "1") == "1"; use_pop = os.getenv("SHORT_USAR_POP", "1") == "1"; use_retention = os.getenv("SHORT_RETENTION_ENGINE", "1") == "1"
    ass_path = prepare_caption_ass(pop_scale if use_pop else 100); ass = escape_ass(ass_path)

    music_pool = media_files(MUSIC_DIR); sfx_pool = media_files(SFX_DIR); mood = str(sound.get("music_mood", audio_policy.get("music_mood", "")))
    music = mood_pick(music_pool, mood, SHORT_ID + ":music") if use_music else None
    starts = scene_starts(runtime); events = sound.get("events", []) if use_sfx and isinstance(sound.get("events"), list) else []

    command = ["ffmpeg", "-y", "-i", str(VIDEO_BASE), "-i", str(AUDIO)]; next_input = 2; music_input = None; sfx_inputs: list[tuple[int, dict[str, Any], str]] = []
    if music:
        music_input = next_input; command.extend(["-stream_loop", "-1", "-i", music]); next_input += 1
    generated = generate_optional_sfx() if use_sfx and not sfx_pool else None
    for event_index, event in enumerate(events[:6]):
        if not isinstance(event, dict): continue
        etype = str(event.get("type", "hit_soft")); picked = curated_sfx_for(etype, sfx_pool, SHORT_ID + f":sfx:{event_index}") or generated
        if not picked: continue
        sfx_inputs.append((next_input, event, picked)); command.extend(["-i", picked]); next_input += 1

    stream_info = video_stream_info(VIDEO_BASE)
    base_w = int(stream_info.get("width", 0) or 0)
    base_h = int(stream_info.get("height", 0) or 0)
    base_range = str(stream_info.get("color_range", "") or "").lower()

    if base_w == 1080 and base_h == 1920:
        base_filter = "[0:v]"
        if base_range in {"pc", "jpeg"}:
            base_filter += "scale=1080:1920:in_range=pc:out_range=tv,"
    else:
        range_args = ":in_range=pc:out_range=tv" if base_range in {"pc", "jpeg"} else ""
        base_filter = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase"
            + range_args
            + ",crop=1080:1920,"
        )

    mobile_fastpath = (
        termux_runtime()
        and os.getenv("SAP_RENDER_MOBILE_FASTPATH", "1") == "1"
    )

    if use_retention and hook_scale > 1.0 and not mobile_fastpath:
        extra_w = round(1080 * (hook_scale - 1.0), 3)
        extra_h = round(1920 * (hook_scale - 1.0), 3)
        zoom_w = f"'if(lt(t,0.18),1080+{extra_w}*(1-t/0.18),1080)'"
        zoom_h = f"'if(lt(t,0.18),1920+{extra_h}*(1-t/0.18),1920)'"
        zoom_filter = f"scale={zoom_w}:{zoom_h}:eval=frame,crop=1080:1920,"
    else:
        zoom_filter = ""

    unsharp_size = 3 if mobile_fastpath else 5
    video_filter = (
        base_filter
        + zoom_filter
        + f"eq=contrast={contrast:.4f}:saturation={saturation:.4f}:brightness={brightness:.4f},"
        + f"unsharp={unsharp_size}:{unsharp_size}:{sharpness:.4f}:{unsharp_size}:{unsharp_size}:0.0,"
        + f"ass='{ass}'[v]"
    )

    audio_filters: list[str] = []
    if music_input is not None:
        audio_filters.append("[1:a]highpass=f=70,acompressor=threshold=0.18:ratio=2.3:attack=18:release=170:makeup=1.10," + f"alimiter=limit={limiter:.5f},asplit=2[voice][voice_sidechain]")
    else:
        audio_filters.append("[1:a]highpass=f=70,acompressor=threshold=0.18:ratio=2.3:attack=18:release=170:makeup=1.10," + f"alimiter=limit={limiter:.5f}[voice]")
    mix_inputs = ["[voice]"]

    if music_input is not None:
        fade_out = max(0.0, total - 1.4); audio_filters.append(f"[{music_input}:a]volume={music_volume:.5f},highpass=f=35,lowpass=f=15500,afade=t=in:st=0:d=0.8,afade=t=out:st={fade_out:.3f}:d=1.4[music_pre]"); audio_filters.append(f"[music_pre][voice_sidechain]sidechaincompress=threshold={duck_threshold:.5f}:ratio={duck_ratio:.2f}:attack={duck_attack}:release={duck_release}:makeup=1[music]"); mix_inputs.append("[music]")

    timed_events = []
    for local_index, (input_index, event, picked) in enumerate(sfx_inputs):
        try: scene = int(event.get("scene", 1))
        except Exception: scene = 1
        start = starts.get(scene, 0.0); delay_ms = max(0, int(round(start * 1000))); label = f"sfx{local_index}"; volume = 0.085 if "riser" in str(event.get("type", "")) else 0.070
        audio_filters.append(f"[{input_index}:a]atrim=start=0:end=0.8,asetpts=PTS-STARTPTS,volume={volume:.3f},afade=t=out:st=0.25:d=0.45,adelay={delay_ms}|{delay_ms},alimiter=limit={limiter:.5f}[{label}]"); mix_inputs.append(f"[{label}]"); timed_events.append({"scene": scene, "type": event.get("type"), "start_seconds": round(start, 3), "file": Path(picked).name})

    audio_filters.append("".join(mix_inputs) + f"amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=2,loudnorm=I={target_lufs:.2f}:LRA=7:TP={true_peak:.2f},alimiter=limit={limiter:.5f}[a]")
    filter_complex = video_filter + ";" + ";".join(audio_filters)
    try: OUTPUT.unlink(missing_ok=True)
    except OSError: pass
    preset = render_preset()
    threads = render_threads()
    command.extend([
        "-filter_threads", str(threads),
        "-filter_complex_threads", str(threads),
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", os.getenv("SHORT_CRF", "20"),
        "-threads", str(threads),
        "-profile:v", "high",
        "-level", "4.1",
        "-pix_fmt", "yuv420p",
        "-color_range", "tv",
        "-r", "30",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-t", f"{total:.6f}",
        "-movflags", "+faststart",
        str(OUTPUT),
    ])

    print("\n================================\nV6 PROFESSIONAL RENDERER 2.1\n================================")
    print(f"Perfil: {plan.get('profile','default')} | estilo: {plan.get('style','premium_documentary')}")
    print(f"Music mood: {mood or 'generic'} | Music: {'ON' if music else 'OFF'} | timed SFX: {len(timed_events)}")
    print(f"Ducking: ratio={duck_ratio:.1f} attack={duck_attack}ms release={duck_release}ms")
    print(f"Pre-codec target: {target_lufs:.1f} LUFS | {true_peak:.1f} dBTP (post-AAC verified next stage)")
    print(
        f"Render preset: {preset} | threads={threads} | "
        f"mobile_fastpath={'ON' if mobile_fastpath else 'OFF'} | "
        f"base={base_w}x{base_h} range={base_range or 'unknown'}"
    )
    print()

    render_started = time.monotonic()
    try: subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc: print(f"ERRO V6 PROFESSIONAL: ffmpeg retornou {exc.returncode}"); return exc.returncode or 1
    if not OUTPUT.is_file() or OUTPUT.stat().st_size < 500_000: print("ERRO V6 PROFESSIONAL: saída ausente ou pequena demais"); return 1
    render_elapsed = time.monotonic() - render_started
    runtime["sound_render"] = {
        "version": "2.1",
        "music_mood": mood,
        "music_file": Path(music).name if music else None,
        "duck_ratio": duck_ratio,
        "timed_sfx": timed_events,
        "render_elapsed_seconds": round(render_elapsed, 3),
        "render_preset": preset,
        "render_threads": threads,
        "mobile_fastpath": mobile_fastpath,
        "base_video": {
            "width": base_w,
            "height": base_h,
            "color_range": base_range or None,
        },
    }
    try: RUNTIME.write_text(json.dumps(runtime, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception: pass
    speed_ratio = (total / render_elapsed) if render_elapsed > 0 else 0.0
    print(
        f"V6 PROFESSIONAL: PASS | render={render_elapsed:.1f}s "
        f"| speed={speed_ratio:.2f}x\nArquivo: {OUTPUT}"
    )
    return 0


if __name__ == "__main__": raise SystemExit(main())
