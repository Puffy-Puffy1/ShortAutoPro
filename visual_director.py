#!/usr/bin/env python3
"""AI Visual Director — structured, factual scene contract for ShortAutoPro.

The director never rewrites narration. It enriches each approved scene with
search and editorial metadata consumed by media selection, continuity, motion,
retention and QA.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import time
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

from gemini_runtime import generate_text

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
R = BASE / "roteiros"
MAPA = R / f"scene_map_{SHORT_ID}.json"
BACKUP = R / f"scene_map_pre_visual_{SHORT_ID}.json"
REPORT = R / f"visual_director_{SHORT_ID}.json"

try:
    QTD_CENAS = max(6, min(20, int(os.getenv("SHORT_QTD_CENAS", "12"))))
except ValueError:
    QTD_CENAS = 12

ALLOWED_SHOTS = {"wide", "medium", "close_up", "detail", "overhead", "aerial", "portrait", "document"}
ALLOWED_MOVES = {"none", "hold", "pan_left", "pan_right", "zoom_in", "zoom_out", "parallax", "native"}


def clean(value: Any) -> str:
    return " ".join(str(value or "").replace("\n", " ").split())


def clean_list(value: Any, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = clean(item).lower()
        if text and text.casefold() not in seen:
            seen.add(text.casefold())
            out.append(text)
    return out[:limit]


def norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", clean(value))
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def tokens(value: Any) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", norm(value)) if len(x) >= 3}


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_map() -> dict[str, Any]:
    if not MAPA.is_file():
        raise ValueError(f"scene_map não encontrado: {MAPA}")
    data = json.loads(MAPA.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("scene_map não é objeto JSON")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != QTD_CENAS:
        raise ValueError(f"scene_map precisa ter {QTD_CENAS} cenas")
    for idx, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict) or int(scene.get("scene", 0) or 0) != idx:
            raise ValueError(f"cena {idx} inválida")
    return data


def local_contract(scene: dict[str, Any]) -> dict[str, Any]:
    segment = clean(scene.get("segment"))
    query = clean(scene.get("query"))
    must = clean_list(scene.get("must_have"), 4)
    avoid = clean_list(scene.get("avoid"), 6)
    if not must:
        # Safe fallback must never promote arbitrary narration words into hard
        # acquisition requirements. Hard MUSTs are factual contracts and should
        # exist only when a previous verified stage explicitly supplied them.
        must = []
    fallback_subject = clean(scene.get("main_subject")) or clean(scene.get("environment")) or "documentary context"
    return {
        "scene": int(scene["scene"]),
        "segment": segment,
        "main_subject": fallback_subject,
        "environment": clean(scene.get("environment") or scene.get("setting")),
        "location": clean(scene.get("location")),
        "era": clean(scene.get("era")),
        "emotion": clean(scene.get("emotion") or scene.get("mood")) or "neutral",
        "shot_type": clean(scene.get("shot_type")) or "medium",
        "movement": clean(scene.get("movement")) or "hold",
        "must_have": must,
        "avoid": avoid,
        "query": query or "documentary context archival visual",
        "alt_queries": clean_list(scene.get("alt_queries"), 3),
        "protected_zone": clean(scene.get("protected_zone")) or "center",
        "reason": "deterministic fallback",
    }


def build_prompt(scenes: list[dict[str, Any]]) -> str:
    seed = [local_contract(scene) for scene in scenes]
    return f"""
Você é o Diretor Visual factual do ShortAutoPro para documentários verticais.
Receba EXATAMENTE {QTD_CENAS} cenas já aprovadas. NÃO reescreva `segment` e NÃO invente pessoas, locais, datas, objetos, crimes, causas ou evidências.

Para cada cena, devolva:
- main_subject: assunto/objeto principal visível e factual;
- environment: ambiente visual; location apenas se sustentado;
- era: época apenas quando sustentada, senão string vazia;
- emotion: atmosfera editorial, não alegação factual;
- shot_type: wide|medium|close_up|detail|overhead|aerial|portrait|document;
- movement: none|hold|pan_left|pan_right|zoom_in|zoom_out|parallax|native;
- must_have: 1–4 elementos obrigatórios sustentados;
- avoid: 2–6 elementos que causariam representação errada/genérica;
- query: busca principal em inglês, 5–14 palavras;
- alt_queries: 2–3 buscas alternativas em inglês, semanticamente equivalentes;
- protected_zone: center|top|bottom|left|right, onde assunto importante tende a ficar;
- reason: justificativa curta.

PRIORIDADES:
1) evidência documental real e identidade correta;
2) significado completo da frase, nunca correspondência de palavra isolada;
3) manter personagem/local/época entre cenas quando a narrativa continua no mesmo contexto;
4) variar enquadramento e movimento sem transformar documento/foto histórica em efeito artificial;
5) proibir stock lifestyle genérico quando não representa de fato a cena;
6) pessoas reais específicas não podem virar retratos genéricos;
7) teoria/paranormal deve permanecer visualmente ambígua.

ENTRADA:
{json.dumps(seed, ensure_ascii=False, indent=2)}

RESPONDA SOMENTE JSON VÁLIDO:
{{"scenes":[{{"scene":1,"main_subject":"...","environment":"...","location":"","era":"","emotion":"...","shot_type":"medium","movement":"hold","must_have":["..."],"avoid":["generic lifestyle","wrong person"],"query":"...","alt_queries":["...","..."],"protected_zone":"center","reason":"..."}}]}}
EXATAMENTE {QTD_CENAS} cenas.
"""


def call_ai(scenes: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not API_KEY:
        return None
    try:
        text = generate_text(
            build_prompt(scenes),
            temperature=0.18,
            max_output_tokens=6500,
            response_mime_type="application/json",
            component="Visual Director",
            api_key=API_KEY,
        )
        text = str(text).replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except Exception as exc:
        print(
            "VISUAL_DIRECTOR_AI=FAIL_OPEN "
            f"{type(exc).__name__}:{str(exc)[:180]}"
        )
        return None


def safe_scene(original: dict[str, Any], proposal: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    fallback = local_contract(original)
    p = proposal if isinstance(proposal, dict) else {}
    out = dict(original)

    query = clean(p.get("query"))
    if not 5 <= len(query.split()) <= 16:
        query = fallback["query"]
    must = clean_list(p.get("must_have"), 4) or fallback["must_have"]
    avoid = clean_list(p.get("avoid"), 6) or fallback["avoid"]
    shot = norm(p.get("shot_type")).replace(" ", "_")
    if shot not in ALLOWED_SHOTS:
        shot = norm(fallback["shot_type"]).replace(" ", "_")
    if shot not in ALLOWED_SHOTS:
        shot = "medium"
    movement = norm(p.get("movement")).replace(" ", "_")
    if movement not in ALLOWED_MOVES:
        movement = "hold"

    # Identity guard: AI cannot silently drop all original required anchors.
    original_must = clean_list(original.get("must_have"), 4)
    if original_must and not (tokens(" ".join(original_must)) & tokens(" ".join(must) + " " + query)):
        must = original_must
        query = fallback["query"]

    fields = {
        "main_subject": clean(p.get("main_subject")) or fallback["main_subject"],
        "environment": clean(p.get("environment")) or fallback["environment"],
        "location": clean(p.get("location")) or fallback["location"],
        "era": clean(p.get("era")) or fallback["era"],
        "emotion": clean(p.get("emotion")) or fallback["emotion"],
        "shot_type": shot,
        "movement": movement,
        "must_have": must,
        "avoid": avoid,
        "query": query,
        "alt_queries": clean_list(p.get("alt_queries"), 3),
        "protected_zone": norm(p.get("protected_zone")) if norm(p.get("protected_zone")) in {"center", "top", "bottom", "left", "right"} else "center",
    }
    if not fields["alt_queries"]:
        fields["alt_queries"] = [query]
    out.update(fields)

    completeness = sum(bool(fields[k]) for k in ("main_subject", "emotion", "shot_type", "movement", "must_have", "avoid", "query", "alt_queries"))
    score = round(100.0 * completeness / 8.0, 1)
    report = {"scene": int(original["scene"]), "contract_score": score, **fields, "reason": clean(p.get("reason"))}
    return out, report


def main() -> int:
    try:
        data = load_map()
        scenes = data["scenes"]
        shutil.copy2(MAPA, BACKUP)
        ai = call_ai(scenes)
        proposals = {}
        if isinstance(ai, dict) and isinstance(ai.get("scenes"), list):
            for item in ai["scenes"]:
                if isinstance(item, dict):
                    try:
                        proposals[int(item.get("scene"))] = item
                    except (TypeError, ValueError):
                        pass

        output_scenes: list[dict[str, Any]] = []
        reports: list[dict[str, Any]] = []
        for idx, scene in enumerate(scenes, 1):
            enriched, report = safe_scene(scene, proposals.get(idx))
            output_scenes.append(enriched)
            reports.append(report)

        if len(output_scenes) != QTD_CENAS or any(int(s.get("scene", 0)) != i for i, s in enumerate(output_scenes, 1)):
            raise ValueError("contrato visual perdeu cenas ou sequência")

        avg = round(sum(float(x["contract_score"]) for x in reports) / len(reports), 1)
        final = dict(data)
        final["scenes"] = output_scenes
        final["visual_director"] = {"version": "4.0", "structured_contract": True, "ai_used": bool(proposals), "score": avg}
        atomic_json(MAPA, final)
        atomic_json(REPORT, {"short_id": SHORT_ID, "version": "4.0", "ai_used": bool(proposals), "visual_director_score": avg, "backup": str(BACKUP), "scenes": reports})
    except Exception as exc:
        print(f"ERRO VISUAL DIRECTOR 4.0: {exc}")
        return 1

    print("\n================================")
    print("AI VISUAL DIRECTOR 4.0")
    print("================================")
    print(f"Cenas: {QTD_CENAS} | AI: {'ON' if proposals else 'SAFE FALLBACK'}")
    print(f"Visual director score: {avg}/100")
    print("VISUAL DIRECTOR: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
