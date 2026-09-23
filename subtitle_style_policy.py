#!/usr/bin/env python3
"""Deterministic subtitle styling for a cleaner documentary edit.

The policy stays dependency-free and Termux-safe. It keeps subtitles readable on
small phone screens without the oversized/template-like look of fixed 3-word
blocks. It only changes presentation; it never rewrites spoken content.
"""

from __future__ import annotations

import re


DEFAULT_FONT = "DejaVu Sans"


def _clean_word(value):
    return str(value or "").strip()


def choose_group_size(words, start_index=0):
    """Choose 2-4 words while keeping each subtitle phrase visually compact."""
    remaining = [_clean_word(x) for x in words[start_index:start_index + 4]]
    remaining = [x for x in remaining if x]
    if not remaining:
        return 0

    # Two words are enough when the phrase contains long names/terms.
    if len(remaining) >= 2 and len(" ".join(remaining[:2])) >= 24:
        return 2

    # Four short words read naturally and reduce hyperactive subtitle changes.
    if len(remaining) >= 4 and len(" ".join(remaining[:4])) <= 27:
        return 4

    return min(3, len(remaining))


DANGLING_END_WORDS = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em",
    "na", "no", "nas", "nos", "para", "por", "com", "que", "se",
    "the", "a", "an", "of", "to", "for", "and", "or", "in", "on", "with",
}


def _word_norm(value):
    return re.sub(r"[^a-zà-ÿ0-9]+", "", str(value or "").casefold())


def group_timed_words(timed_words):
    """Split aligned words into compact editorial phrases without losing words."""
    result = []
    index = 0
    raw_words = [item.get("text", "") for item in timed_words]
    while index < len(timed_words):
        size = choose_group_size(raw_words, index)
        if size <= 0:
            break
        group = timed_words[index:index + size]
        if group:
            result.append(group)
        index += size

    # Avoid captions ending in weak connectors such as "que ele seria o".
    # Rebalance only adjacent groups and preserve every aligned word/timestamp.
    for i in range(len(result) - 1):
        current = result[i]
        nxt = result[i + 1]
        if not current or not nxt:
            continue
        last = _word_norm(current[-1].get("text", ""))
        if last not in DANGLING_END_WORDS:
            continue
        if len(current) < 4 and len(nxt) >= 3:
            current.append(nxt.pop(0))
        elif len(current) > 2 and len(nxt) < 4:
            # Never grow the next caption beyond the policy maximum. A 5-word
            # group makes validate_grouping() reject an otherwise lossless alignment.
            nxt.insert(0, current.pop())
    return [group for group in result if group]


def style_header(font_name=DEFAULT_FONT):
    """Return ASS header tuned for vertical documentary shorts."""
    font = str(font_name or DEFAULT_FONT).replace(",", " ").strip() or DEFAULT_FONT
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Dynamic,{font},66,&H00FFFFFF,&H00D9E7FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,4,0,2,110,110,285,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""


def highlight_text(group, active_index, cleaner):
    """Build restrained karaoke-like emphasis for one active word."""
    parts = []
    for index, item in enumerate(group):
        text = cleaner(item.get("text", ""))
        if index == active_index:
            parts.append(r"{\c&H00D9E7FF&\b1}" + text + r"{\c&HFFFFFF&\b1}")
        else:
            parts.append(text)
    return " ".join(parts)


def validate_grouping(groups, expected_count):
    flattened = [item for group in groups for item in group]
    return len(flattened) == int(expected_count) and all(2 <= len(group) <= 4 for group in groups[:-1])
