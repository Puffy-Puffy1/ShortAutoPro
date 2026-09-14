#!/usr/bin/env python3

import json
import math
import os
import re
import tempfile
from datetime import date
from pathlib import Path

from source_identity import detectar_alias


BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro")))
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
R = BASE / "roteiros"

PUBLISH_TXT = R / f"publish_{SHORT_ID}.txt"
PUBLISH_JSON = R / f"publish_{SHORT_ID}.json"
SCRIPT = R / f"short_{SHORT_ID}.txt"
SOURCE = R / f"fonte_{SHORT_ID}.txt"
TOPIC_REAL = R / f"used_topic_{SHORT_ID}.txt"
TOPIC = R / f"topic_{SHORT_ID}.txt"
REPORT = R / f"publish_integrity_{SHORT_ID}.json"


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def read_json(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def atomic_json(path: Path, payload: dict) -> None:
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


def expandir_texto(text):
    texto = str(text or "").replace("_", " ")
    texto = re.sub(r"([a-zà-ÿ0-9])([A-ZÀ-Ý])", r"\1 \2", texto)
    texto = re.sub(r"([A-Za-zÀ-ÿ])(\d)", r"\1 \2", texto)
    texto = re.sub(r"(\d)([A-Za-zÀ-ÿ])", r"\1 \2", texto)
    return texto


def tokens(text):
    stop = {
        "o", "a", "os", "as", "um", "uma", "de", "da", "do", "das", "dos",
        "e", "em", "no", "na", "nos", "nas", "para", "por", "com", "sem",
        "caso", "desaparecimento",
    }
    out = set()
    for item in re.findall(r"[a-z0-9à-ÿ]+", expandir_texto(text).lower()):
        if item in stop:
            continue
        if item.isdigit():
            if len(item) >= 2:
                out.add(item)
        elif len(item) >= 3:
            out.add(item)
    return out


def numeric_tokens(text):
    """Extract standalone and alphanumeric numeric identity consistently."""
    expanded = expandir_texto(text)
    return set(re.findall(r"\b\d+(?:[.,]\d+)?\b", expanded))


def overlap(base, target):
    return 0.0 if not base else len(base & target) / len(base)


def parse_publish_text(text: str):
    lines = text.splitlines()
    title = ""

    for index, line in enumerate(lines):
        header = line.strip().upper().replace("Í", "I")
        if header in {"TITULO:", "TITLE:"}:
            for next_line in lines[index + 1:]:
                next_line = next_line.strip()
                if next_line:
                    title = next_line
                    break
            if title:
                break

    description = ""
    match = re.search(
        r"DESCRI(?:ÇÃO|CAO):\s*(.*?)\s*HASHTAGS:",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if match:
        description = match.group(1).strip()

    hashtag_block = ""
    match = re.search(
        r"HASHTAGS:\s*(.*?)(?=\n\s*(?:COMENT[ÁA]RIO\s+FIXADO|CR[ÉE]DITOS\s+DE\s+M[ÍI]DIA):|\Z)",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if match:
        hashtag_block = match.group(1)

    hashtags = re.findall(r"#[A-Za-zÀ-ÿ0-9_]+", hashtag_block)
    unique = []
    seen = set()
    for tag in hashtags:
        key = tag.casefold()
        if key not in seen:
            seen.add(key)
            unique.append(tag)

    return title, description, unique


def audit(publish_text, publish_json, script, source, topic):
    critical = []
    warnings = []
    strengths = []

    if not publish_text:
        critical.append("publish_file_missing_or_empty")
    if not isinstance(publish_json, dict):
        critical.append("publish_json_missing_or_invalid")
        publish_json = {}
    if not script:
        critical.append("script_missing_or_empty")
    if not source:
        critical.append("source_missing_or_empty")
    if not topic:
        critical.append("topic_missing")

    title, desc, hashtags = parse_publish_text(publish_text)

    if not title:
        critical.append("selected_title_missing")
    elif not 20 <= len(title) <= 100:
        critical.append(f"title_length_invalid={len(title)}")
    elif 35 <= len(title) <= 70:
        strengths.append("title_length_ok")
    else:
        warnings.append(f"title_length_suboptimal={len(title)}")

    if not desc:
        critical.append("description_missing")
    elif not 80 <= len(desc) <= 700:
        critical.append(f"description_length_invalid={len(desc)}")
    else:
        strengths.append("description_present")

    if len(hashtags) != 5:
        critical.append(f"hashtags_count={len(hashtags)}")
    elif not any(tag.casefold() == "#shorts" for tag in hashtags):
        critical.append("shorts_hashtag_missing")
    else:
        strengths.append("hashtags_ok")

    json_title = str(publish_json.get("chosen_title", "") or "").strip()
    json_desc = str(publish_json.get("description", "") or "").strip()
    json_tags = publish_json.get("hashtags")

    if not json_title:
        critical.append("publish_json_title_missing")
    elif title and json_title != title:
        critical.append("publish_txt_json_title_mismatch")

    if not json_desc:
        critical.append("publish_json_description_missing")
    elif desc and json_desc != desc:
        critical.append("publish_txt_json_description_mismatch")

    if not isinstance(json_tags, list):
        critical.append("publish_json_hashtags_invalid")
    elif hashtags:
        normalized_json_tags = [str(x).strip().casefold() for x in json_tags]
        normalized_txt_tags = [x.casefold() for x in hashtags]
        if normalized_json_tags != normalized_txt_tags:
            critical.append("publish_txt_json_hashtags_mismatch")

    score_raw = publish_json.get("publish_score")
    if (
        isinstance(score_raw, bool)
        or not isinstance(score_raw, (int, float))
        or not math.isfinite(float(score_raw))
    ):
        critical.append("publish_score_invalid")
    elif float(score_raw) < 60:
        critical.append(f"publish_score_low={float(score_raw):.1f}")

    base_numbers = numeric_tokens(script + "\n" + source + "\n" + topic)
    publish_number_text = title + "\n" + desc + "\n" + " ".join(hashtags)
    publish_numbers = numeric_tokens(publish_number_text)
    new_numbers = publish_numbers - base_numbers
    if new_numbers:
        critical.append("unsupported_numbers=" + ",".join(sorted(new_numbers)))

    topic_tokens = tokens(topic)
    body_tokens = tokens(title + " " + desc)
    hashtag_tokens = tokens(" ".join(hashtags))
    publish_tokens = body_tokens | hashtag_tokens

    body_overlap = overlap(topic_tokens, body_tokens)
    hashtag_overlap = overlap(topic_tokens, hashtag_tokens)
    topic_overlap = overlap(topic_tokens, publish_tokens)

    topic_alias = detectar_alias(topic)
    publish_alias = detectar_alias(
        title + " " + desc + " " + " ".join(hashtags) + " "
        + expandir_texto(" ".join(hashtags))
    )
    alias_match = False

    if topic_alias and publish_alias:
        if topic_alias != publish_alias:
            critical.append(f"publish_alias_conflict:{topic_alias}!={publish_alias}")
        else:
            alias_match = True
            topic_overlap = max(topic_overlap, 1.0)
            strengths.append("publish_known_alias_match")

    if not topic_tokens and not alias_match:
        critical.append("topic_identity_not_measurable")
    elif topic_overlap == 0:
        critical.append("publish_topic_mismatch")
    elif topic_overlap < 0.40:
        warnings.append(f"weak_topic_alignment={topic_overlap:.2f}")
    else:
        strengths.append(f"topic_alignment={topic_overlap:.2f}")

    if body_overlap == 0 and hashtag_overlap > 0:
        strengths.append("topic_anchor_from_hashtags")

    return {
        "status": "BLOCK" if critical else "PASS",
        "title": title,
        "description_chars": len(desc),
        "hashtags": hashtags,
        "topic_alignment": round(topic_overlap, 3),
        "body_topic_alignment": round(body_overlap, 3),
        "hashtag_topic_alignment": round(hashtag_overlap, 3),
        "topic_alias": topic_alias,
        "publish_alias": publish_alias,
        "new_numbers": sorted(new_numbers),
        "critical": critical,
        "warnings": warnings,
        "strengths": strengths,
    }


def main() -> int:
    publish_text = read_text(PUBLISH_TXT)
    publish_json = read_json(PUBLISH_JSON)
    script = read_text(SCRIPT)
    source = read_text(SOURCE)
    topic = read_text(TOPIC_REAL) or read_text(TOPIC)

    result = audit(
        publish_text,
        publish_json,
        script,
        source,
        topic,
    )
    report = {
        "short_id": SHORT_ID,
        "version": "5.3.2",
        "topic": topic,
        **result,
    }

    try:
        atomic_json(REPORT, report)
    except Exception as exc:
        print(f"ERRO: falha gravando publish integrity report: {exc}")
        return 1

    print()
    print("================================")
    print("PUBLISH INTEGRITY GATE 5.3.2")
    print("================================")
    print()
    print(f"Título: {result['title'] or 'AUSENTE'}")
    print(f"Alinhamento com assunto: {result['topic_alignment'] * 100:.0f}%")
    print(f"Hashtags: {len(result['hashtags'])}")
    print()

    for item in result["warnings"]:
        print(f"AVISO: {item}")

    if result["critical"]:
        print()
        for item in result["critical"]:
            print(f"ERRO: {item}")
        print()
        print("PUBLISH INTEGRITY: BLOCK")
        return 1

    print()
    print("PUBLISH INTEGRITY: PASS")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
