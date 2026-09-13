#!/usr/bin/env python3

import json
import os
import re
from datetime import date

from source_identity import detectar_alias

BASE = os.path.expanduser("~/ShortAutoPro")
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())
R = os.path.join(BASE, "roteiros")
PUBLISH = os.path.join(R, f"publish_{SHORT_ID}.txt")
SCRIPT = os.path.join(R, f"short_{SHORT_ID}.txt")
SOURCE = os.path.join(R, f"fonte_{SHORT_ID}.txt")
TOPIC_REAL = os.path.join(R, f"used_topic_{SHORT_ID}.txt")
TOPIC = os.path.join(R, f"topic_{SHORT_ID}.txt")
REPORT = os.path.join(R, f"publish_integrity_{SHORT_ID}.json")


def read(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


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
    texto = expandir_texto(text)
    saida = set()
    for x in re.findall(r"[a-z0-9à-ÿ]+", texto.lower()):
        if x in stop:
            continue
        if x.isdigit():
            if len(x) >= 2:
                saida.add(x)
        elif len(x) >= 3:
            saida.add(x)
    return saida


def calcular_overlap(base, alvo):
    if not base:
        return 0.0
    return len(base & alvo) / len(base)


publish = read(PUBLISH)
script = read(SCRIPT)
source = read(SOURCE)
topic = read(TOPIC_REAL) or read(TOPIC)

critical = []
warnings = []
strengths = []

if not publish:
    critical.append("publish_file_missing_or_empty")
if not script:
    critical.append("script_missing_or_empty")
if not topic:
    critical.append("topic_missing")

linhas = publish.splitlines()
title = ""
for i, line in enumerate(linhas):
    cabecalho = line.strip().upper().replace("Í", "I")
    if cabecalho in {"TITULO:", "TITLE:"}:
        for prox in linhas[i + 1:]:
            prox = prox.strip()
            if prox:
                title = prox
                break
        if title:
            break

if not title:
    for line in linhas:
        if "<-- ESCOLHIDO" in line:
            title = re.sub(r"^\s*\d+\.\s*", "", line)
            title = title.replace("<-- ESCOLHIDO", "").strip()
            break

desc = ""
m = re.search(
    r"DESCRI(?:ÇÃO|CAO):\s*(.*?)\s*HASHTAGS:",
    publish,
    flags=re.DOTALL | re.IGNORECASE,
)
if m:
    desc = m.group(1).strip()

hashtags = re.findall(r"#[A-Za-zÀ-ÿ0-9_]+", publish)
unique_hashtags = []
seen_hashtags = set()
for tag in hashtags:
    key = tag.casefold()
    if key not in seen_hashtags:
        seen_hashtags.add(key)
        unique_hashtags.append(tag)

if not title:
    critical.append("selected_title_missing")
else:
    if len(title) > 100:
        critical.append(f"title_too_long={len(title)}")
    elif len(title) < 20:
        warnings.append(f"title_too_short={len(title)}")
    elif len(title) >= 35:
        strengths.append("title_length_ok")

if not desc:
    critical.append("description_missing")
elif len(desc) > 700:
    warnings.append(f"description_long={len(desc)}")
else:
    strengths.append("description_present")

base_numbers = set(
    re.findall(r"\b\d+(?:[.,]\d+)?\b", script + "\n" + source + "\n" + topic)
)
publish_number_text = title + "\n" + desc + "\n" + expandir_texto(" ".join(unique_hashtags))
publish_numbers = set(re.findall(r"\b\d+(?:[.,]\d+)?\b", publish_number_text))
new_numbers = publish_numbers - base_numbers
if new_numbers:
    critical.append("unsupported_numbers=" + ",".join(sorted(new_numbers)))

topic_tokens = tokens(topic)
body_tokens = tokens(title + " " + desc)
hashtag_tokens = tokens(" ".join(unique_hashtags))
publish_tokens = body_tokens | hashtag_tokens

body_overlap = calcular_overlap(topic_tokens, body_tokens)
hashtag_overlap = calcular_overlap(topic_tokens, hashtag_tokens)
overlap = calcular_overlap(topic_tokens, publish_tokens)

topic_alias = detectar_alias(topic)
publish_alias = detectar_alias(
    title + " " + desc + " " + " ".join(unique_hashtags) + " " + expandir_texto(" ".join(unique_hashtags))
)
alias_match = False

if topic_alias and publish_alias:
    if topic_alias != publish_alias:
        critical.append(f"publish_alias_conflict:{topic_alias}!={publish_alias}")
    else:
        alias_match = True
        overlap = max(overlap, 1.0)
        strengths.append("publish_known_alias_match")

if not topic_tokens and not alias_match:
    critical.append("topic_identity_not_measurable")
elif overlap == 0:
    critical.append("publish_topic_mismatch")
elif overlap < 0.40:
    warnings.append(f"weak_topic_alignment={overlap:.2f}")
else:
    strengths.append(f"topic_alignment={overlap:.2f}")

if body_overlap == 0 and hashtag_overlap > 0:
    strengths.append("topic_anchor_from_hashtags")

if not 3 <= len(unique_hashtags) <= 7:
    warnings.append(f"hashtags={len(unique_hashtags)}")
else:
    strengths.append("hashtags_ok")

status = "BLOCK" if critical else "PASS"
report = {
    "short_id": SHORT_ID,
    "version": "5.2",
    "status": status,
    "topic": topic,
    "title": title,
    "description_chars": len(desc),
    "hashtags": unique_hashtags,
    "topic_alignment": round(overlap, 3),
    "body_topic_alignment": round(body_overlap, 3),
    "hashtag_topic_alignment": round(hashtag_overlap, 3),
    "topic_alias": topic_alias,
    "publish_alias": publish_alias,
    "new_numbers": sorted(new_numbers),
    "critical": critical,
    "warnings": warnings,
    "strengths": strengths,
}

os.makedirs(R, exist_ok=True)
with open(REPORT, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print()
print("================================")
print("PUBLISH INTEGRITY GATE 5.2")
print("================================")
print()
print(f"Título: {title or 'AUSENTE'}")
print(f"Alinhamento com assunto: {overlap * 100:.0f}%")
print(f"Hashtags: {len(unique_hashtags)}")
print()

for item in warnings:
    print(f"AVISO: {item}")

if critical:
    print()
    for item in critical:
        print(f"ERRO: {item}")
    print()
    print("PUBLISH INTEGRITY: BLOCK")
    raise SystemExit(1)

print()
print("PUBLISH INTEGRITY: PASS")
print()
