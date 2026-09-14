#!/usr/bin/env python3
"""ShortAutoPro Long-form Runtime V1.

A separate, resumable 16:9 production engine for factual PT-BR long videos.
It deliberately does not stretch the Shorts pipeline. It verifies one exact
subject, creates factual chapters from the same source, generates Piper audio,
acquires reusable Wikimedia Commons visuals with attribution, renders chapters,
and concatenates them into one final H.264/AAC MP4.

External services remain free-stack oriented: Wikipedia/Wikimedia Commons,
Gemini (using the user's configured key/free quota), Piper and FFmpeg.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

import profile_runtime
import topic_engine_runtime
from wiki_client import extract as wiki_extract_client

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
RUN_ROOT = BASE / "reports" / "evolution" / "longform_runs"
MEDIA_ROOT = BASE / "longform"
DOWNLOADS = Path(os.path.expanduser("~/storage/shared/Download"))
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
USER_AGENT = "ShortAutoPro/1.0 factual-video-tool"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def slugify(value: str, limit: int = 54) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return value[:limit] or "longform"


def run_id(topic: str) -> str:
    forced = os.getenv("LONGFORM_ID", "").strip()
    if forced:
        return slugify(forced, 80)
    return datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + slugify(topic, 28)


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temp.open("w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass


def words(text: str) -> list[str]:
    return re.findall(r"\b[\wÀ-ÿ'-]+\b", str(text), flags=re.UNICODE)


def require_runtime() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe", "piper") if shutil.which(name) is None]
    if missing:
        raise SystemExit("ERRO: dependências ausentes: " + ", ".join(missing))
    if not GEMINI_KEY:
        raise SystemExit("ERRO: GEMINI_API_KEY não configurada.")


def safe_profile(name: str) -> dict[str, Any]:
    profile = profile_runtime.load_profile(name)
    language = str(profile.get("language", "pt-BR")).lower()
    if not language.startswith("pt"):
        raise SystemExit("ERRO: Long-form V1 está certificado apenas para PT-BR; perfil inglês fica para fase futura.")
    return profile


def gemini(prompt: str, temperature: float = 0.2, max_tokens: int = 2400) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_KEY}
    last = ""
    for attempt in range(1, 5):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=150)
        except Exception as exc:
            last = str(exc)
            if attempt < 4:
                time.sleep(5)
                continue
            raise RuntimeError(last)
        if response.ok:
            try:
                return str(response.json()["candidates"][0]["content"]["parts"][0]["text"]).strip()
            except Exception as exc:
                raise RuntimeError(f"Gemini respondeu sem texto utilizável: {exc}")
        last = f"HTTP {response.status_code}: {response.text[:800]}"
        if response.status_code in {429, 500, 502, 503, 504} and attempt < 4:
            time.sleep(8)
            continue
        raise RuntimeError(last)
    raise RuntimeError(last or "Gemini não respondeu")


def parse_json_response(raw: str) -> dict[str, Any]:
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        value = json.loads(raw)
    except Exception as exc:
        raise RuntimeError(f"JSON inválido da IA: {exc}")
    if not isinstance(value, dict):
        raise RuntimeError("resposta da IA não é objeto JSON")
    return value


def verify_topic(topic: str) -> tuple[dict[str, Any], str]:
    verified = topic_engine_runtime.verify_exact(topic)
    if not verified.get("valid"):
        raise RuntimeError(
            "assunto não passou pelo gate factual: "
            f"{verified.get('wiki_title') or 'sem candidato'} / {verified.get('identity_reason', '')}"
        )
    source = wiki_extract_client(str(verified["wiki_title"]))
    if len(source) < 1200:
        raise RuntimeError("fonte factual curta demais para long-form")
    return verified, source[:24000]


def build_outline(topic: str, source: str, chapters: int, minutes: int) -> list[dict[str, str]]:
    prompt = f"""
Você é editor-chefe de um documentário factual em português do Brasil.

ASSUNTO: {topic}
DURAÇÃO ALVO: {minutes} minutos
CAPÍTULOS: exatamente {chapters}

FONTE FACTUAL ÚNICA:
====================
{source}
====================

Crie uma estrutura progressiva para um vídeo longo. Cada capítulo deve cumprir
uma função diferente e evitar repetir fatos de capítulos anteriores. Use somente
informações sustentadas pela fonte. Não invente pessoas, datas, causas ou números.

Responda SOMENTE JSON válido:
{{"chapters":[{{"title":"título curto","objective":"o que este capítulo explica"}}]}}
O array precisa ter exatamente {chapters} itens.
"""
    data = parse_json_response(gemini(prompt, 0.15, 1800))
    raw = data.get("chapters", [])
    if not isinstance(raw, list) or len(raw) != chapters:
        raise RuntimeError(f"outline retornou {len(raw) if isinstance(raw, list) else 0}/{chapters} capítulos")
    result = []
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise RuntimeError("capítulo inválido no outline")
        title = str(item.get("title", "")).strip()
        objective = str(item.get("objective", "")).strip()
        if not title or not objective:
            raise RuntimeError("outline contém título/objetivo vazio")
        result.append({"chapter": index, "title": title, "objective": objective})
    return result


def chapter_script(
    topic: str,
    source: str,
    chapter: dict[str, Any],
    target_words: int,
    prior: list[dict[str, str]],
) -> dict[str, Any]:
    prior_text = "\n".join(f"- {x['title']}: {x['summary']}" for x in prior[-4:]) or "nenhum"
    low = max(170, round(target_words * 0.84))
    high = min(620, round(target_words * 1.16))
    prompt = f"""
Você escreve um capítulo de documentário factual para YouTube em português do Brasil.

ASSUNTO GLOBAL: {topic}
CAPÍTULO {chapter['chapter']}: {chapter['title']}
OBJETIVO: {chapter['objective']}

RESUMOS DOS CAPÍTULOS ANTERIORES (não repita esses pontos sem necessidade):
{prior_text}

FONTE FACTUAL ÚNICA:
====================
{source}
====================

REGRAS:
- narração entre {low} e {high} palavras;
- use SOMENTE fatos sustentados pela fonte;
- não invente datas, nomes, números, causas ou citações;
- diferencie fato de hipótese;
- texto fluido, sem listas e sem CTA no meio;
- este capítulo deve conectar naturalmente com o próximo;
- crie 6 a 10 buscas visuais em inglês, concretas e documentais;
- cada busca visual deve corresponder a algo realmente mencionado/compatível com a fonte;
- evite logos, thumbnails, interfaces e imagens sensacionalistas.

Responda SOMENTE JSON válido:
{{
  "narration":"texto completo",
  "summary":"resumo factual em até 35 palavras",
  "visual_queries":["query one","query two"]
}}
"""
    last_error = ""
    for attempt in range(1, 4):
        data = parse_json_response(gemini(prompt, 0.18 if attempt == 1 else 0.10, 3200))
        narration = " ".join(str(data.get("narration", "")).split())
        summary = " ".join(str(data.get("summary", "")).split())
        queries = [str(x).strip() for x in data.get("visual_queries", []) if str(x).strip()] if isinstance(data.get("visual_queries"), list) else []
        count = len(words(narration))
        if low <= count <= high and summary and 5 <= len(queries) <= 12:
            return {
                "narration": narration,
                "summary": summary,
                "visual_queries": queries[:10],
                "word_count": count,
            }
        last_error = f"palavras={count}, queries={len(queries)}, summary={'sim' if summary else 'não'}"
    raise RuntimeError("capítulo fora do contrato após 3 tentativas: " + last_error)


def ext_value(meta: dict[str, Any], key: str) -> str:
    value = meta.get(key, {}) if isinstance(meta, dict) else {}
    if isinstance(value, dict):
        value = value.get("value", "")
    return html.unescape(re.sub(r"<[^>]+>", "", str(value or ""))).strip()


def commons_candidates(query: str) -> list[dict[str, Any]]:
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": "6",
        "gsrlimit": "12",
        "prop": "imageinfo",
        "iiprop": "url|mime|size|extmetadata",
        "iiurlwidth": "1920",
    }
    response = requests.get(COMMONS_API, params=params, headers={"User-Agent": USER_AGENT}, timeout=60)
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    result = []
    for page in pages.values() if isinstance(pages, dict) else []:
        if not isinstance(page, dict):
            continue
        info_list = page.get("imageinfo", [])
        if not isinstance(info_list, list) or not info_list:
            continue
        info = info_list[0]
        if not isinstance(info, dict):
            continue
        width = int(info.get("width", 0) or 0)
        height = int(info.get("height", 0) or 0)
        mime = str(info.get("mime", ""))
        url = str(info.get("thumburl") or info.get("url") or "")
        if not url or width < 640 or height < 360 or not mime.startswith("image/"):
            continue
        meta = info.get("extmetadata", {}) if isinstance(info.get("extmetadata"), dict) else {}
        result.append({
            "title": str(page.get("title", "")).strip(),
            "url": url,
            "description_url": str(info.get("descriptionurl", "")).strip(),
            "mime": mime,
            "width": width,
            "height": height,
            "artist": ext_value(meta, "Artist"),
            "license": ext_value(meta, "LicenseShortName") or ext_value(meta, "UsageTerms"),
            "license_url": ext_value(meta, "LicenseUrl"),
            "credit": ext_value(meta, "Credit"),
        })
    result.sort(key=lambda x: (x["width"] * x["height"], bool(x["license"])), reverse=True)
    return result


def download_visuals(
    chapter_dir: Path,
    queries: list[str],
    topic: str,
    desired: int,
    used_urls: set[str],
) -> tuple[list[Path], list[dict[str, Any]]]:
    image_dir = chapter_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    images: list[Path] = []
    credits: list[dict[str, Any]] = []
    searches = list(dict.fromkeys(queries + [topic + " historical", topic + " location"]))
    for query in searches:
        if len(images) >= desired:
            break
        try:
            candidates = commons_candidates(query)
        except Exception as exc:
            print(f"  Wikimedia falhou para '{query}': {exc}")
            continue
        for candidate in candidates:
            url = candidate["url"]
            if url in used_urls:
                continue
            try:
                response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=90)
                response.raise_for_status()
            except Exception:
                continue
            suffix = ".png" if "png" in candidate["mime"] else ".jpg"
            path = image_dir / f"visual_{len(images)+1:02d}{suffix}"
            path.write_bytes(response.content)
            if path.stat().st_size < 10_000:
                path.unlink(missing_ok=True)
                continue
            used_urls.add(url)
            images.append(path)
            credit = dict(candidate)
            credit.update({"query": query, "local_file": path.name})
            credits.append(credit)
            if len(images) >= desired:
                break
    if len(images) < 3:
        raise RuntimeError(f"mídia insuficiente no Wikimedia: {len(images)}/3 mínimo")
    return images, credits


def audio_duration(path: Path) -> float:
    raw = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ], text=True, timeout=60).strip()
    value = float(raw)
    if not math.isfinite(value) or value <= 1:
        raise RuntimeError("duração de áudio inválida")
    return value


def tts_chapter(chapter_dir: Path, narration: str, profile: dict[str, Any]) -> tuple[Path, float]:
    model = str(profile.get("voice", "pt_BR-faber-medium")).strip() or "pt_BR-faber-medium"
    voice_dir = BASE / "piper" / "voice"
    if not voice_dir.is_dir():
        raise RuntimeError(f"pasta Piper ausente: {voice_dir}")
    raw = chapter_dir / "speech.raw"
    wav0 = chapter_dir / "speech_unmastered.wav"
    wav = chapter_dir / "speech.wav"
    env = os.environ.copy()
    env["PIPER_VOICE_PATH"] = str(voice_dir)
    subprocess.run(["piper", "-m", model, "-f", str(raw), "--", narration], env=env, check=True, timeout=420)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", "22050", "-ac", "1",
        "-i", str(raw), "-c:a", "pcm_s16le", str(wav0),
    ], check=True, timeout=180)
    target_lufs = float(profile.get("audio", {}).get("target_lufs", -14)) if isinstance(profile.get("audio"), dict) else -14.0
    true_peak = float(profile.get("audio", {}).get("true_peak_db", -1.5)) if isinstance(profile.get("audio"), dict) else -1.5
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(wav0),
        "-af", f"loudnorm=I={target_lufs}:LRA=7:TP={true_peak},alimiter=limit=0.95",
        "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(wav),
    ], check=True, timeout=240)
    raw.unlink(missing_ok=True)
    wav0.unlink(missing_ok=True)
    return wav, audio_duration(wav)


def ass_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    seconds -= hours * 3600
    minutes = int(seconds // 60)
    seconds -= minutes * 60
    return f"{hours}:{minutes:02d}:{seconds:05.2f}"


def ass_escape(text: str) -> str:
    return str(text).replace("\\", "").replace("{", "").replace("}", "").replace("\n", " ")


def make_ass(path: Path, narration: str, duration: float, max_words: int = 7) -> None:
    seq = words(narration)
    if not seq:
        raise RuntimeError("narração vazia para legenda")
    max_words = max(4, min(9, int(max_words)))
    per_word = duration / len(seq)
    events = []
    for start_index in range(0, len(seq), max_words):
        group = seq[start_index:start_index + max_words]
        start = start_index * per_word
        end = min(duration, (start_index + len(group)) * per_word + 0.08)
        events.append(
            f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{ass_escape(' '.join(group))}"
        )
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,DejaVu Sans,50,&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,-1,0,0,0,100,100,0,0,1,3,0,2,120,120,70,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    atomic_text(path, header + "\n".join(events) + "\n")


def ass_filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def render_chapter(chapter_dir: Path, images: list[Path], audio: Path, duration: float, ass: Path) -> Path:
    clips = chapter_dir / "clips"
    clips.mkdir(parents=True, exist_ok=True)
    visual_seconds = duration / len(images)
    clip_paths = []
    frames = max(1, math.ceil(visual_seconds * 30))
    for index, image in enumerate(images, start=1):
        clip = clips / f"clip_{index:02d}.mp4"
        zoom = "min(zoom+0.00018,1.055)" if index % 2 else "min(zoom+0.00014,1.045)"
        vf = (
            "scale=1920:1080:force_original_aspect_ratio=increase,"
            "crop=1920:1080,"
            f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps=30,"
            "format=yuv420p"
        )
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(image),
            "-vf", vf, "-t", f"{visual_seconds:.3f}", "-an", "-c:v", "libx264",
            "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-r", "30", str(clip),
        ], check=True, timeout=480)
        clip_paths.append(clip)
    concat = chapter_dir / "visuals.txt"
    atomic_text(concat, "".join(f"file '{p.as_posix()}'\n" for p in clip_paths))
    visual = chapter_dir / "visual.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-c", "copy", str(visual),
    ], check=True, timeout=240)
    output = chapter_dir / "chapter.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(visual), "-i", str(audio),
        "-vf", f"ass='{ass_filter_path(ass)}'", "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "21", "-profile:v", "high",
        "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-t", f"{duration:.3f}", "-movflags", "+faststart", str(output),
    ], check=True, timeout=900)
    if not output.is_file() or output.stat().st_size < 100_000:
        raise RuntimeError("render do capítulo não produziu MP4 válido")
    return output


def probe_video(path: Path) -> dict[str, Any]:
    raw = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=codec_name,codec_type,width,height:format=duration", "-of", "json", str(path),
    ], text=True, timeout=90)
    data = json.loads(raw)
    streams = data.get("streams", []) if isinstance(data, dict) else []
    video = next((x for x in streams if x.get("codec_type") == "video"), {})
    audio = next((x for x in streams if x.get("codec_type") == "audio"), {})
    duration = float(data.get("format", {}).get("duration", 0) or 0)
    return {
        "duration": round(duration, 2),
        "width": int(video.get("width", 0) or 0),
        "height": int(video.get("height", 0) or 0),
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
    }


def final_concat(run_dir: Path, chapter_paths: list[Path], run_name: str) -> Path:
    concat = run_dir / "chapters.txt"
    atomic_text(concat, "".join(f"file '{p.as_posix()}'\n" for p in chapter_paths))
    output = BASE / "videos" / f"long_v1_{run_name}.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-c", "copy", "-movflags", "+faststart", str(output),
    ], check=True, timeout=600)
    if not output.is_file() or output.stat().st_size < 500_000:
        raise RuntimeError("concatenação final não produziu vídeo válido")
    return output


def credits_text(credits: list[dict[str, Any]]) -> str:
    lines = ["SHORTAUTOPRO LONG-FORM — CRÉDITOS DE MÍDIA", ""]
    for index, item in enumerate(credits, start=1):
        lines.extend([
            f"{index}. {item.get('title', 'Wikimedia Commons')}",
            f"   Autor: {item.get('artist') or 'não informado'}",
            f"   Licença: {item.get('license') or 'ver página da mídia'}",
            f"   Licença URL: {item.get('license_url') or 'não informada'}",
            f"   Fonte: {item.get('description_url') or item.get('url')}",
            "",
        ])
    return "\n".join(lines)


def execute(topic: str, minutes: int, chapters: int | None, profile_name: str, existing_id: str | None = None) -> dict[str, Any]:
    require_runtime()
    profile = safe_profile(profile_name)
    minutes = max(5, min(int(minutes), 60))
    chapters = chapters or max(3, min(12, round(minutes / 2.5)))
    chapters = max(3, min(int(chapters), 12))
    rid = existing_id or run_id(topic)
    run_dir = MEDIA_ROOT / rid
    state_path = RUN_ROOT / f"{rid}.json"
    run_dir.mkdir(parents=True, exist_ok=True)

    state = {}
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            state = {}
    if state and str(state.get("topic")) != topic:
        raise RuntimeError("LONGFORM_ID existente pertence a outro tema")

    state.update({
        "version": "1.0",
        "run_id": rid,
        "topic": topic,
        "target_minutes": minutes,
        "chapter_count": chapters,
        "profile": profile_name,
        "status": "RUNNING",
        "updated_at": now_iso(),
    })
    state.setdefault("created_at", now_iso())
    state.setdefault("chapters", [])
    atomic_json(state_path, state)

    print("========================================")
    print(" SHORTAUTOPRO LONG-FORM V1")
    print("========================================")
    print(f"ID: {rid}")
    print(f"Tema: {topic}")
    print(f"Alvo: {minutes} min / {chapters} capítulos")
    print(f"Perfil: {profile_name}")
    print()

    verified, source = verify_topic(topic)
    state["source"] = verified
    atomic_text(run_dir / "source.txt", source)

    outline = state.get("outline") if isinstance(state.get("outline"), list) else None
    if not outline or len(outline) != chapters:
        outline = build_outline(topic, source, chapters, minutes)
        state["outline"] = outline
        atomic_json(state_path, state)

    total_target_words = minutes * 130
    target_words = max(190, min(520, round(total_target_words / chapters)))
    prior: list[dict[str, str]] = []
    all_credits: list[dict[str, Any]] = []
    chapter_paths: list[Path] = []
    used_urls: set[str] = set()

    existing_items = {
        int(x.get("chapter")): x for x in state.get("chapters", [])
        if isinstance(x, dict) and str(x.get("chapter", "")).isdigit()
    }

    for chapter in outline:
        index = int(chapter["chapter"])
        chapter_dir = run_dir / f"chapter_{index:02d}"
        chapter_dir.mkdir(parents=True, exist_ok=True)
        item = existing_items.get(index, {"chapter": index, "status": "PENDING"})
        output = chapter_dir / "chapter.mp4"
        chapter_json = chapter_dir / "chapter.json"
        credits_json = chapter_dir / "credits.json"

        if item.get("status") == "PASS" and output.is_file() and output.stat().st_size > 100_000 and chapter_json.is_file():
            print(f"Capítulo {index}/{chapters}: já aprovado — pulando.")
            data = json.loads(chapter_json.read_text(encoding="utf-8"))
            prior.append({"title": chapter["title"], "summary": str(data.get("summary", ""))})
            chapter_paths.append(output)
            if credits_json.is_file():
                credits = json.loads(credits_json.read_text(encoding="utf-8"))
                if isinstance(credits, list):
                    all_credits.extend(credits)
                    used_urls.update(str(x.get("url")) for x in credits if isinstance(x, dict) and x.get("url"))
            continue

        print(f"Capítulo {index}/{chapters}: {chapter['title']}")
        item.update({"status": "RUNNING", "title": chapter["title"], "started_at": now_iso()})
        existing_items[index] = item
        state["chapters"] = [existing_items[i] for i in sorted(existing_items)]
        atomic_json(state_path, state)

        try:
            data = chapter_script(topic, source, chapter, target_words, prior)
            atomic_json(chapter_json, {**chapter, **data})
            desired_images = max(4, min(8, round((minutes * 60 / chapters) / 25)))
            images, credits = download_visuals(chapter_dir, data["visual_queries"], topic, desired_images, used_urls)
            atomic_json(credits_json, credits)
            audio, duration = tts_chapter(chapter_dir, data["narration"], profile)
            caption_words = int(profile.get("captions", {}).get("max_words_per_event", 7)) if isinstance(profile.get("captions"), dict) else 7
            ass = chapter_dir / "captions.ass"
            make_ass(ass, data["narration"], duration, caption_words)
            rendered = render_chapter(chapter_dir, images, audio, duration, ass)
            probe = probe_video(rendered)
            if probe["width"] != 1920 or probe["height"] != 1080 or probe["video_codec"] != "h264" or probe["audio_codec"] != "aac":
                raise RuntimeError(f"contrato técnico do capítulo falhou: {probe}")
            item.update({
                "status": "PASS", "finished_at": now_iso(), "duration": probe["duration"],
                "word_count": data["word_count"], "media_count": len(images), "video": str(rendered),
            })
            prior.append({"title": chapter["title"], "summary": data["summary"]})
            all_credits.extend(credits)
            chapter_paths.append(rendered)
        except Exception as exc:
            item.update({"status": "FAIL", "finished_at": now_iso(), "error": f"{type(exc).__name__}: {exc}"})
            state["status"] = "PARTIAL"
            state["chapters"] = [existing_items[i] for i in sorted(existing_items)]
            state["updated_at"] = now_iso()
            atomic_json(state_path, state)
            raise

        state["chapters"] = [existing_items[i] for i in sorted(existing_items)]
        state["updated_at"] = now_iso()
        atomic_json(state_path, state)

    final = final_concat(run_dir, chapter_paths, rid)
    probe = probe_video(final)
    minimum = minutes * 60 * 0.68
    maximum = minutes * 60 * 1.35
    if not (minimum <= probe["duration"] <= maximum):
        raise RuntimeError(
            f"duração final fora da tolerância: {probe['duration']:.1f}s; esperado {minimum:.0f}-{maximum:.0f}s"
        )
    if probe["width"] != 1920 or probe["height"] != 1080 or probe["video_codec"] != "h264" or probe["audio_codec"] != "aac":
        raise RuntimeError(f"contrato técnico final falhou: {probe}")

    credits_json = run_dir / "credits.json"
    credits_txt = run_dir / "credits.txt"
    atomic_json(credits_json, all_credits)
    atomic_text(credits_txt, credits_text(all_credits))

    destination = final
    if DOWNLOADS.is_dir():
        candidate = DOWNLOADS / f"ShortAutoPro_LONG_{rid}.mp4"
        try:
            shutil.copy2(final, candidate)
            if candidate.stat().st_size > 0:
                destination = candidate
        except Exception:
            pass

    state.update({
        "status": "PASS",
        "completed_at": now_iso(),
        "updated_at": now_iso(),
        "final_video": str(final),
        "download_copy": str(destination),
        "credits_json": str(credits_json),
        "credits_txt": str(credits_txt),
        "probe": probe,
        "quality": {
            "factual_source_verified": True,
            "all_chapters_pass": all(x.get("status") == "PASS" for x in state["chapters"]),
            "attribution_count": len(all_credits),
            "technical_contract": True,
        },
    })
    atomic_json(state_path, state)
    print()
    print("LONGFORM_STATUS=PASS")
    print(f"Vídeo: {destination}")
    print(f"Duração: {probe['duration']:.1f}s")
    print(f"Créditos: {credits_txt}")
    return state


def latest_run_id() -> str | None:
    if not RUN_ROOT.is_dir():
        return None
    paths = sorted(RUN_ROOT.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return paths[0].stem if paths else None


def resume(run_name: str | None) -> dict[str, Any]:
    run_name = run_name or latest_run_id()
    if not run_name:
        raise SystemExit("ERRO: nenhum long-form salvo para retomar.")
    path = RUN_ROOT / f"{run_name}.json"
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"ERRO: estado long-form inválido: {exc}")
    return execute(
        str(state["topic"]), int(state["target_minutes"]), int(state["chapter_count"]),
        str(state.get("profile", "default")), existing_id=run_name,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="ShortAutoPro Long-form Runtime V1")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run")
    p.add_argument("--topic", required=True)
    p.add_argument("--minutes", type=int, default=15)
    p.add_argument("--chapters", type=int, default=None)
    p.add_argument("--profile", default="true_crime")
    p = sub.add_parser("resume")
    p.add_argument("--run-id", default=None)
    p = sub.add_parser("status")
    p.add_argument("--run-id", default=None)
    args = parser.parse_args()
    try:
        if args.command == "run":
            execute(args.topic.strip(), args.minutes, args.chapters, args.profile)
        elif args.command == "resume":
            resume(args.run_id)
        else:
            rid = args.run_id or latest_run_id()
            if not rid:
                print("Nenhum long-form salvo.")
                return 0
            print((RUN_ROOT / f"{rid}.json").read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"LONGFORM_ERROR={type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
