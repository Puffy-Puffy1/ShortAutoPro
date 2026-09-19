#!/usr/bin/env python3
"""Professional caption post-director for ShortAutoPro.

Works on the already aligned ASS produced by legenda_dinamica.py. It never
rewrites spoken words or timing identity; it only applies profile typography,
safe-zone margins and at most one semantic-looking visual line break for long
phrases. A report makes the transformation auditable.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
PROFILE = os.getenv("SAP_CHANNEL_PROFILE", "default").strip() or "default"
ASS = BASE / "videos" / f"short_{SHORT_ID}.ass"
AUDIT_ASS = BASE / "temp" / SHORT_ID / f"short_{SHORT_ID}.ass"
REPORT = BASE / "roteiros" / f"pro_caption_{SHORT_ID}.json"

PRESETS: dict[str, dict[str, Any]] = {
    "default": {
        "font_size": 69,
        "outline": 4,
        "shadow": 0,
        "margin_l": 120,
        "margin_r": 120,
        "margin_v": 330,
        "break_chars": 29,
    },
    "true_crime": {
        "font_size": 69,
        "outline": 4,
        "shadow": 0,
        "margin_l": 125,
        "margin_r": 125,
        "margin_v": 335,
        "break_chars": 28,
    },
    "cinepulsar": {
        "font_size": 70,
        "outline": 4,
        "shadow": 1,
        "margin_l": 110,
        "margin_r": 110,
        "margin_v": 320,
        "break_chars": 30,
    },
    "psicotoon": {
        "font_size": 69,
        "outline": 4,
        "shadow": 1,
        "margin_l": 115,
        "margin_r": 115,
        "margin_v": 325,
        "break_chars": 29,
    },
}

TAG_RE = re.compile(r"\{[^}]*\}")
WORD_RE = re.compile(r"\b[\wÀ-ÿ'-]+\b", flags=re.UNICODE)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def visible_text(text: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub("", text).replace(r"\N", " ")).strip()


def visible_words(text: str) -> list[str]:
    return WORD_RE.findall(visible_text(text))


def ass_time(value: str) -> float | None:
    try:
        hours, minutes, tail = value.strip().split(":")
        seconds, cent = tail.split(".")
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(cent) / 100.0
    except Exception:
        return None


def replace_dynamic_style(line: str, preset: dict[str, Any]) -> str:
    if not line.startswith("Style: Dynamic,"):
        return line
    parts = line.split(",")
    # ASS V4+ style has 23 fields after the `Style:` name prefix here.
    if len(parts) < 23:
        raise ValueError("linha Style: Dynamic inesperada")
    parts[2] = str(int(preset["font_size"]))
    parts[16] = str(int(preset["outline"]))
    parts[17] = str(int(preset["shadow"]))
    parts[19] = str(int(preset["margin_l"]))
    parts[20] = str(int(preset["margin_r"]))
    parts[21] = str(int(preset["margin_v"]))
    return ",".join(parts)


def token_boundaries(text: str) -> list[tuple[int, int]]:
    """Return visible word spans in the raw ASS text, skipping override tags."""
    spans: list[tuple[int, int]] = []
    index = 0
    while index < len(text):
        if text[index] == "{":
            end = text.find("}", index + 1)
            if end < 0:
                break
            index = end + 1
            continue
        match = WORD_RE.search(text, index)
        if not match:
            break
        # Ignore matches that start inside a tag by checking unmatched braces.
        prefix = text[: match.start()]
        if prefix.rfind("{") > prefix.rfind("}"):
            index = match.end()
            continue
        spans.append((match.start(), match.end()))
        index = match.end()
    return spans


def add_balanced_break(text: str, threshold: int) -> tuple[str, bool]:
    if r"\N" in text:
        return text, False
    plain = visible_text(text)
    words = visible_words(text)
    if len(plain) <= threshold or len(words) < 4:
        return text, False
    spans = token_boundaries(text)
    if len(spans) < 4:
        return text, False

    # Break before the word nearest the visual midpoint, avoiding a one-word line.
    total_chars = max(1, len(plain))
    best_index = None
    best_distance = 10**9
    for word_index in range(2, len(spans) - 1):
        raw_pos = spans[word_index][0]
        left_visible = visible_text(text[:raw_pos])
        distance = abs(len(left_visible) - total_chars / 2)
        if distance < best_distance:
            best_distance = distance
            best_index = word_index
    if best_index is None:
        return text, False
    raw_pos = spans[best_index][0]
    while raw_pos > 0 and text[raw_pos - 1].isspace():
        raw_pos -= 1
    return text[:raw_pos].rstrip() + r"\N" + text[raw_pos:].lstrip(), True


def transform(content: str, profile: str) -> tuple[str, dict[str, Any]]:
    preset = PRESETS.get(profile, PRESETS["default"])
    source_lines = content.splitlines()
    output: list[str] = []
    style_found = False
    events = 0
    breaks = 0
    max_words = 0
    max_lines = 1
    rapid_events = 0
    durations: list[float] = []
    before_visible: list[str] = []
    after_visible: list[str] = []

    for line in source_lines:
        if line.startswith("Style: Dynamic,"):
            line = replace_dynamic_style(line, preset)
            style_found = True
        if line.startswith("Dialogue:"):
            parts = line.split(",", 9)
            if len(parts) != 10:
                raise ValueError("evento Dialogue inválido")
            before = visible_text(parts[9])
            before_visible.append(before)
            parts[9], changed = add_balanced_break(parts[9], int(preset["break_chars"]))
            breaks += int(changed)
            after = visible_text(parts[9])
            after_visible.append(after)
            if before != after:
                raise ValueError("Caption Director alterou palavras visíveis")
            count = len(visible_words(parts[9]))
            max_words = max(max_words, count)
            lines_count = parts[9].count(r"\N") + 1
            max_lines = max(max_lines, lines_count)
            if lines_count > 2:
                raise ValueError("evento de legenda excedeu duas linhas")
            start = ass_time(parts[1])
            end = ass_time(parts[2])
            if start is not None and end is not None and end > start:
                event_duration = end - start
                durations.append(event_duration)
                if event_duration < 0.07:
                    rapid_events += 1
            line = ",".join(parts)
            events += 1
        output.append(line)

    if not style_found:
        raise ValueError("Style: Dynamic não encontrado")
    if events == 0:
        raise ValueError("nenhum evento de legenda encontrado")
    if before_visible != after_visible:
        raise ValueError("sequência visível de legendas mudou")

    rapid_ratio = rapid_events / events if events else 0.0
    avg_duration = sum(durations) / len(durations) if durations else 0.0
    score = 100.0
    if max_words > 7:
        score -= min(30.0, (max_words - 7) * 5.0)
    if max_lines > 2:
        score -= 40.0
    if rapid_ratio > 0.20:
        score -= min(15.0, (rapid_ratio - 0.20) * 50.0)
    score = round(max(0.0, score), 1)

    report = {
        "short_id": SHORT_ID,
        "version": "PRO_CAPTION_1.1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "profile": profile,
        "status": "PASS" if score >= 88.0 else "REVIEW",
        "score": score,
        "events": events,
        "balanced_breaks_added": breaks,
        "max_words_per_event": max_words,
        "max_lines": max_lines,
        "rapid_events_under_70ms": rapid_events,
        "rapid_ratio": round(rapid_ratio, 4),
        "average_event_duration": round(avg_duration, 4),
        "style": preset,
        "content_preserved": True,
    }
    return "\n".join(output) + "\n", report


def main() -> int:
    try:
        if not ASS.is_file():
            raise ValueError(f"ASS ausente: {ASS}")
        original = ASS.read_text(encoding="utf-8")
        transformed, report = transform(original, PROFILE)
        atomic_write(ASS, transformed)
        atomic_write(AUDIT_ASS, transformed)
        atomic_json(REPORT, report)
    except Exception as exc:
        print(f"ERRO PROFESSIONAL CAPTION DIRECTOR: {exc}")
        return 1

    print("\n================================")
    print("PROFESSIONAL CAPTION DIRECTOR 1.1")
    print("================================")
    print(f"Perfil: {PROFILE}")
    print(f"Score: {report['score']}/100 | status={report['status']}")
    print(f"Eventos: {report['events']} | breaks={report['balanced_breaks_added']}")
    print(f"Máx. palavras: {report['max_words_per_event']} | linhas: {report['max_lines']}")
    print(f"Conteúdo preservado: {report['content_preserved']}")
    print("PROFESSIONAL CAPTION DIRECTOR: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
