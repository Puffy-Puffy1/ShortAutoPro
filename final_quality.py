#!/usr/bin/env python3

import hashlib
import json
import math
import os
import re
import tempfile
from datetime import date
from pathlib import Path

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro")))
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except (TypeError, ValueError):
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

MANIFEST = BASE / "manifests" / f"{SHORT_ID}.json"
PUBLISH = BASE / "roteiros" / f"publish_{SHORT_ID}.json"
ROTEIRO = BASE / "roteiros" / f"short_{SHORT_ID}.txt"
HOOK = BASE / "roteiros" / f"hook_{SHORT_ID}.txt"
SAIDA = BASE / "manifests" / f"{SHORT_ID}_quality.json"

MANIFEST_REQUIRED_FLAGS = (
    "video_exists",
    "scene_map_numbering_ok",
    "media_numbering_ok",
    "resolution_ok",
    "fps_ok",
    "video_codec_ok",
    "audio_exists",
    "audio_codec_ok",
    "duration_ok",
    "topic_exists",
    "hook_exists",
    "script_exists",
    "source_exists",
    "publish_exists",
    "publish_title_exists",
    "publish_description_exists",
    "publish_hashtags_ok",
    "publish_integrity_pass",
    "source_ledger_exists",
)


def file_sha256(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return ""


def ler_json(path: Path):
    if not path.is_file():
        return {}
    try:
        dados = json.loads(path.read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else {}
    except Exception:
        return {}


def ler_txt(path: Path):
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def dict_seguro(valor):
    return valor if isinstance(valor, dict) else {}


def contar_palavras(texto):
    return len(re.findall(r"\b[\wÀ-ÿ'-]+\b", str(texto), flags=re.UNICODE))


def atomic_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def avaliar(manifest, publish, roteiro, hook):
    critical = []

    if not manifest:
        critical.append("manifest_missing_or_invalid")
    elif str(manifest.get("status", "")).upper() not in {"QUALITY_PASS", "PASS"}:
        critical.append("manifest_not_quality_pass")

    if not publish:
        critical.append("publish_missing_or_invalid")
    if not roteiro:
        critical.append("script_missing_or_empty")
    if not hook:
        critical.append("hook_missing_or_empty")

    script_score = 25.0
    qtd_palavras = contar_palavras(roteiro)
    if not 105 <= qtd_palavras <= 125:
        script_score -= 12

    frases = [x.strip() for x in re.split(r"[.!?]+", roteiro) if x.strip()]
    frases_longas = sum(1 for frase in frases if contar_palavras(frase) > 24)
    script_score -= min(6, frases_longas * 2)

    abertura = " ".join(roteiro.split()[:15]).lower()
    fracas = [
        "hoje vamos",
        "neste vídeo",
        "nesse vídeo",
        "você sabia",
        "voce sabia",
        "vamos falar",
    ]
    if any(abertura.startswith(x) for x in fracas):
        script_score -= 6
    script_score = max(0, script_score)

    hook_score = 0.0
    if hook:
        palavras_hook = contar_palavras(hook)
        hook_score = 14.0
        if 7 <= palavras_hook <= 16:
            hook_score += 5
        elif palavras_hook > 22:
            hook_score -= 4

        termos_hook = [
            "nunca", "ninguém", "ninguem", "desapareceu", "morte", "corpo",
            "mistério", "misterio", "prova", "verdade", "como", "por que", "o que",
        ]
        hits = sum(1 for x in termos_hook if x in hook.lower())
        hook_score += min(hits * 2, 6)
    hook_score = max(0, min(hook_score, 25))

    quality = dict_seguro(manifest.get("quality", {}))
    video = dict_seguro(manifest.get("video", {}))
    scenes = dict_seguro(manifest.get("scenes", {}))

    for flag in MANIFEST_REQUIRED_FLAGS:
        if not quality.get(flag):
            critical.append(f"manifest_quality_failed={flag}")

    visual_score = 0.0
    if quality.get("resolution_ok"):
        visual_score += 7
    if quality.get("fps_ok"):
        visual_score += 5
    if quality.get("audio_exists"):
        visual_score += 5

    scene_count = scenes.get("count", 0)
    physical_count = scenes.get("physical_count", 0)
    if scene_count == QTD_CENAS:
        visual_score += 6
    else:
        critical.append(f"scene_count={scene_count}/{QTD_CENAS}")
    if physical_count == QTD_CENAS:
        visual_score += 7
    else:
        critical.append(f"physical_scene_count={physical_count}/{QTD_CENAS}")
    visual_score = min(visual_score, 30)

    publish_score_raw = publish.get("publish_score")
    publish_score = 0.0
    if (
        isinstance(publish_score_raw, (int, float))
        and not isinstance(publish_score_raw, bool)
        and math.isfinite(float(publish_score_raw))
    ):
        raw = max(0, min(float(publish_score_raw), 100))
        publish_score = raw / 100 * 20
        if raw < 60:
            critical.append(f"publish_score_low={raw:.1f}")
    else:
        critical.append("publish_score_invalid")

    publish_score = min(publish_score, 20)
    total = round(script_score + hook_score + visual_score + publish_score, 1)

    if total >= 85:
        nivel = "EXCELLENT"
    elif total >= 75:
        nivel = "GOOD"
    elif total >= 65:
        nivel = "ACCEPTABLE"
    else:
        nivel = "WEAK"

    aprovado = total >= 65 and not critical
    return {
        "short_id": SHORT_ID,
        "total_score": total,
        "level": nivel,
        "approved": aprovado,
        "critical": critical,
        "components": {
            "script": round(script_score, 1),
            "hook": round(hook_score, 1),
            "visual_technical": round(visual_score, 1),
            "publish": round(publish_score, 1),
        },
        "details": {
            "script_words": qtd_palavras,
            "long_sentences": frases_longas,
            "expected_scene_count": QTD_CENAS,
            "scene_count": scene_count,
            "physical_scene_count": physical_count,
            "duration_seconds": video.get("duration_seconds"),
        },
    }


def main():
    manifest = ler_json(MANIFEST)
    publish = ler_json(PUBLISH)
    roteiro = ler_txt(ROTEIRO)
    hook = ler_txt(HOOK)
    resultado = avaliar(manifest, publish, roteiro, hook)
    resultado["version"] = "FINAL_QUALITY_2.6_MANIFEST_CHAIN"
    resultado["input_identity"] = {
        "production_manifest_sha256": file_sha256(MANIFEST),
    }

    try:
        atomic_json(SAIDA, resultado)
    except Exception as exc:
        print(f"ERRO FINAL QUALITY: falha gravando relatório: {exc}")
        return 1

    print()
    print("================================")
    print("FINAL QUALITY SCORE - 2.6")
    print("================================")
    print()
    print(f"Roteiro: {resultado['components']['script']:.1f}/25")
    print(f"Hook: {resultado['components']['hook']:.1f}/25")
    print(f"Visual/Técnico: {resultado['components']['visual_technical']:.1f}/30")
    print(f"Publish: {resultado['components']['publish']:.1f}/20")
    print()
    print(f"NOTA FINAL: {resultado['total_score']:.1f}/100")
    print(f"NÍVEL: {resultado['level']}")
    print()

    if resultado["critical"]:
        for item in resultado["critical"]:
            print(f"ERRO: {item}")
        print()

    print(f"Arquivo:\n{SAIDA}")
    print()

    if not resultado["approved"]:
        print("FINAL QUALITY SCORE: BLOCK")
        print()
        return 1

    print("FINAL QUALITY SCORE: PASS")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
