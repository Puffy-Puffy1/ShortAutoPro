#!/usr/bin/env python3

import re
import unicodedata
from difflib import SequenceMatcher


def normalize_word(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return "".join(re.findall(r"[a-z0-9]+", text.casefold()))


def _positional_centers(count, whisper_centers, start_ms, end_ms):
    if count <= 0:
        return []
    if not whisper_centers:
        if count == 1:
            return [(start_ms + end_ms) / 2.0]
        span = max(1.0, end_ms - start_ms)
        return [start_ms + span * i / (count - 1) for i in range(count)]
    if count == 1:
        return [whisper_centers[len(whisper_centers) // 2]]

    out = []
    last = len(whisper_centers) - 1
    for i in range(count):
        pos = i / (count - 1) * last
        left = int(pos)
        right = min(left + 1, last)
        fraction = pos - left
        out.append(
            whisper_centers[left] * (1.0 - fraction)
            + whisper_centers[right] * fraction
        )
    return out


def align_word_timings(original_words, whisper_words, start_ms=None, end_ms=None):
    """Align original script words to Whisper words by textual content.

    whisper_words items must contain text/start/end in milliseconds. The
    function returns (timed_words, method, similarity_ratio).
    """
    original_words = [str(x) for x in original_words]
    clean_whisper = []
    for item in whisper_words:
        if not isinstance(item, dict):
            continue
        try:
            start = int(item.get("start"))
            end = int(item.get("end"))
        except (TypeError, ValueError):
            continue
        text = str(item.get("text", "")).strip()
        if not text or end <= start:
            continue
        clean_whisper.append({"text": text, "start": start, "end": end})

    if not original_words:
        return [], "EMPTY", 0.0
    if not clean_whisper:
        raise ValueError("Whisper não forneceu palavras temporizadas")

    if start_ms is None:
        start_ms = clean_whisper[0]["start"]
    if end_ms is None:
        end_ms = clean_whisper[-1]["end"]
    start_ms = int(start_ms)
    end_ms = int(end_ms)
    if end_ms <= start_ms:
        raise ValueError("intervalo temporal inválido")

    orig_norm = [normalize_word(x) for x in original_words]
    whisper_norm = [normalize_word(x["text"]) for x in clean_whisper]
    centers_w = [(x["start"] + x["end"]) / 2.0 for x in clean_whisper]

    matcher = SequenceMatcher(None, orig_norm, whisper_norm, autojunk=False)
    ratio = matcher.ratio()
    anchors = {}

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for oi, wi in zip(range(i1, i2), range(j1, j2)):
                anchors[oi] = centers_w[wi]
        elif tag == "replace" and i2 > i1 and j2 > j1:
            # Replacement blocks can be transcription variants. Preserve the
            # local timing span but do not claim exact lexical equality.
            olen = i2 - i1
            wlen = j2 - j1
            for offset, oi in enumerate(range(i1, i2)):
                pos = (offset + 0.5) / olen * wlen - 0.5
                pos = max(0.0, min(pos, wlen - 1))
                left = int(pos)
                right = min(left + 1, wlen - 1)
                frac = pos - left
                anchors[oi] = (
                    centers_w[j1 + left] * (1.0 - frac)
                    + centers_w[j1 + right] * frac
                )

    # If recognition differs too much, positional mapping is safer than
    # trusting weak lexical anchors.
    if ratio < 0.20 or len(anchors) < max(2, len(original_words) // 8):
        centers = _positional_centers(
            len(original_words), centers_w, start_ms, end_ms
        )
        method = "POSITIONAL_FALLBACK"
    else:
        centers = [None] * len(original_words)
        for idx, value in anchors.items():
            centers[idx] = value

        known = sorted(anchors)
        for i in range(len(centers)):
            if centers[i] is not None:
                continue
            left_candidates = [x for x in known if x < i]
            right_candidates = [x for x in known if x > i]
            left_idx = left_candidates[-1] if left_candidates else None
            right_idx = right_candidates[0] if right_candidates else None

            if left_idx is None and right_idx is None:
                centers[i] = _positional_centers(
                    len(original_words), centers_w, start_ms, end_ms
                )[i]
            elif left_idx is None:
                # Interpolate from audio start to first textual anchor.
                span = right_idx + 1
                frac = (i + 1) / span
                centers[i] = start_ms * (1.0 - frac) + centers[right_idx] * frac
            elif right_idx is None:
                span = len(original_words) - left_idx
                frac = (i - left_idx) / span
                centers[i] = centers[left_idx] * (1.0 - frac) + end_ms * frac
            else:
                frac = (i - left_idx) / (right_idx - left_idx)
                centers[i] = (
                    centers[left_idx] * (1.0 - frac)
                    + centers[right_idx] * frac
                )
        method = "CONTENT_ALIGNMENT"

    # Enforce monotonic centers. Whisper occasionally emits overlapping or
    # repeated timestamps for punctuation/subword artifacts.
    centers[0] = max(float(start_ms), min(float(end_ms), float(centers[0])))
    for i in range(1, len(centers)):
        centers[i] = max(float(centers[i]), centers[i - 1] + 1.0)
    if centers[-1] > end_ms:
        centers = _positional_centers(
            len(original_words), centers_w, start_ms, end_ms
        )
        method = "POSITIONAL_FALLBACK"

    timed = []
    for i, word in enumerate(original_words):
        if i == 0:
            start = start_ms
        else:
            start = int((centers[i - 1] + centers[i]) / 2.0)

        if i == len(original_words) - 1:
            end = end_ms
        else:
            end = int((centers[i] + centers[i + 1]) / 2.0)

        start = max(start_ms, start)
        end = min(end_ms, max(end, start + 40))
        if end <= start:
            end = min(end_ms, start + 40)
        timed.append({"text": word, "start": int(start), "end": int(end)})

    return timed, method, float(ratio)
