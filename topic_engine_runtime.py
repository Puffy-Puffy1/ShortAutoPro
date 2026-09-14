#!/usr/bin/env python3
"""Runtime selector for automatic or exact ShortAutoPro topics.

With no SHORT_TOPIC_EXACT this delegates untouched to topic_engine.py.
With SHORT_TOPIC_EXACT it verifies the requested real-world subject against
Wikipedia/source identity and writes the same topic artifacts expected by the
rest of the pipeline. Exact mode never bypasses factual verification.
"""

from __future__ import annotations

import json
import os
import runpy
import sys
from datetime import date
from pathlib import Path

from source_identity import validar_identidade
from topic_memory import encontrar_duplicata
from wiki_client import WikiRateLimit
from wiki_client import extract as wiki_extract_client
from wiki_client import search as wiki_search_client

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())
EXACT = os.getenv("SHORT_TOPIC_EXACT", "").strip()
ALLOW_REPEAT = os.getenv("SHORT_ALLOW_REPEAT_TOPIC", "0").strip() == "1"
HISTORY = BASE / "historico_assuntos.json"
TOPIC_OUT = BASE / "roteiros" / f"topic_{SHORT_ID}.txt"
VERIFY_OUT = BASE / "roteiros" / f"topic_verified_{SHORT_ID}.json"


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def load_history() -> list[dict]:
    if not HISTORY.is_file():
        return []
    try:
        data = json.loads(HISTORY.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"ERRO: histórico inválido; exact topic bloqueado: {exc}")
    if not isinstance(data, list):
        raise SystemExit("ERRO: histórico inválido; exact topic bloqueado.")
    return [item for item in data if isinstance(item, dict)]


def candidates(topic: str) -> list[str]:
    values = [topic]
    lower = topic.lower()
    for prefix in ("o caso ", "a caso ", "caso ", "mistério de ", "misterio de ", "incidente de "):
        if lower.startswith(prefix):
            values.append(topic[len(prefix):].strip())
    values.append(" ".join(topic.split()[:7]))
    out: list[str] = []
    seen = set()
    for item in values:
        key = item.casefold().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def verify_exact(topic: str) -> dict:
    best = None
    for query in candidates(topic):
        results = wiki_search_client(query, limit=6)
        if not isinstance(results, list):
            continue
        for result in results:
            if not isinstance(result, dict):
                continue
            title = str(result.get("title", "")).strip()
            if not title:
                continue
            text = wiki_extract_client(title)
            if len(text) < 700:
                continue
            identity = validar_identidade(topic, title, text)
            score = float(identity.get("score", 0.0) or 0.0)
            if best is None or score > best["identity_score"]:
                best = {
                    "topic": topic,
                    "wiki_title": title,
                    "wiki_chars": len(text),
                    "identity_score": round(score, 4),
                    "identity_reason": identity.get("reason", ""),
                    "valid": bool(identity.get("valid")),
                }
            if identity.get("valid"):
                return best
    return best or {
        "topic": topic,
        "wiki_title": "",
        "wiki_chars": 0,
        "identity_score": 0.0,
        "identity_reason": "no_valid_source",
        "valid": False,
    }


def exact_mode() -> int:
    history = load_history()
    if not ALLOW_REPEAT:
        duplicate = encontrar_duplicata(EXACT, history, limite=0.72)
        if duplicate.get("duplicate"):
            raise SystemExit(
                "ERRO: assunto exato já utilizado ou muito semelhante: "
                f"{duplicate.get('topic', '?')} (similaridade={duplicate.get('similarity', 0)})"
            )

    print()
    print("================================")
    print("EXACT TOPIC ENGINE - VERIFIED 1.0")
    print("================================")
    print(f"Assunto solicitado: {EXACT}")
    print("Verificando fonte pública e identidade...")

    try:
        verified = verify_exact(EXACT)
    except WikiRateLimit:
        raise SystemExit("ERRO: Wikipedia temporariamente limitada.")
    except Exception as exc:
        raise SystemExit(f"ERRO verificando assunto exato: {exc}")

    if not verified.get("valid"):
        raise SystemExit(
            "ERRO: assunto exato não passou pelo gate factual. "
            f"Melhor candidato={verified.get('wiki_title') or 'nenhum'}; "
            f"motivo={verified.get('identity_reason')}"
        )

    selected = {
        "topic": EXACT,
        "score": 100.0,
        "wiki_title": verified["wiki_title"],
        "wiki_chars": verified["wiki_chars"],
        "wiki_similarity": verified["identity_score"],
        "exact": True,
        "objective": {
            "visual": 0.0,
            "hook": 0.0,
            "documentation": 10.0,
            "title_match": round(verified["identity_score"] * 10, 2),
            "novelty": 10.0 if not history else 8.0,
        },
        "gemini": {},
    }
    report = {
        "short_id": SHORT_ID,
        "mode": "exact_verified",
        "selected": selected,
        "ranking": [selected],
        "verification": [verified],
        "allow_repeat": ALLOW_REPEAT,
    }
    atomic_text(TOPIC_OUT, EXACT)
    atomic_json(VERIFY_OUT, report)

    print(f"Wikipedia: {verified['wiki_title']}")
    print(f"Identity score: {verified['identity_score']:.3f}")
    print("EXACT TOPIC: PASS")
    print()
    return 0


def main() -> int:
    if EXACT:
        return exact_mode()
    target = BASE / "topic_engine.py"
    if not target.is_file():
        raise SystemExit(f"ERRO: topic_engine.py não encontrado: {target}")
    runpy.run_path(str(target), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
