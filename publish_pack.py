#!/usr/bin/env python3

import json
import os
import re
import tempfile
import time
from datetime import date
from pathlib import Path

import requests


BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro")))
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()

R = BASE / "roteiros"
ROTEIRO = R / f"short_{SHORT_ID}.txt"
FONTE = R / f"fonte_{SHORT_ID}.txt"
TOPIC_REAL = R / f"used_topic_{SHORT_ID}.txt"
TOPIC_FALLBACK = R / f"topic_{SHORT_ID}.txt"
HOOK = R / f"hook_{SHORT_ID}.txt"
SAIDA_JSON = R / f"publish_{SHORT_ID}.json"
SAIDA_TXT = R / f"publish_{SHORT_ID}.txt"

EXPRESSOES_FRACAS = [
    "você não vai acreditar",
    "voce nao vai acreditar",
    "chocante demais",
    "isso vai te chocar",
    "ninguém esperava isso",
    "ninguem esperava isso",
    "a verdade absoluta",
    "segredo finalmente revelado",
    "100% comprovado",
    "prova definitiva",
]

ERROS_CONHECIDOS = {
    "mentura",
    "investigacaoo",
    "desaparecimente",
    "misterío",
    "períciaa",
    "tragically",
}


def read_required(path: Path, label: str) -> str:
    if not path.is_file():
        raise ValueError(f"{label} ausente: {path}")
    try:
        text = path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        raise ValueError(f"falha lendo {label}: {exc}") from exc
    if not text:
        raise ValueError(f"{label} vazio")
    return text


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
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


def atomic_json(path: Path, payload: dict) -> None:
    atomic_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )


def normalizar(texto):
    return " ".join(
        re.findall(
            r"[a-záàâãéêíóôõúç0-9]+",
            str(texto).lower(),
        )
    )


def palavras(texto):
    return set(normalizar(texto).split())


def score_titulo(titulo, assunto, hook, roteiro):
    titulo = str(titulo).strip()
    if not titulo:
        return -999.0

    score = 50.0
    tamanho = len(titulo)

    if 38 <= tamanho <= 62:
        score += 20
    elif 30 <= tamanho <= 70:
        score += 12
    elif tamanho > 90:
        score -= 25
    else:
        score -= 8

    lower = titulo.lower()
    for termo in EXPRESSOES_FRACAS:
        if termo in lower:
            score -= 35
    for erro in ERROS_CONHECIDOS:
        if erro in lower:
            score -= 60

    titulo_tokens = palavras(titulo)
    assunto_tokens = palavras(assunto)
    hook_tokens = palavras(hook)
    roteiro_tokens = palavras(roteiro)

    if assunto_tokens:
        overlap = len(titulo_tokens & assunto_tokens)
        if overlap >= 2:
            score += 12
        elif overlap == 1:
            score += 6

    if hook_tokens:
        score += min(len(titulo_tokens & hook_tokens) * 2, 8)

    base_tokens = assunto_tokens | hook_tokens | roteiro_tokens
    estranhas = [x for x in titulo_tokens if len(x) >= 7 and x not in base_tokens]
    if len(estranhas) >= 3:
        score -= 8

    if titulo.isupper():
        score -= 15
    if titulo.count("!") > 1:
        score -= 8
    if titulo.count("?") > 1:
        score -= 5

    return round(score, 1)


def clean_json_block(raw: str) -> str:
    text = str(raw or "").strip()
    text = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def normalize_hashtag(value: str) -> str:
    tag = re.sub(r"\s+", "", str(value or "").strip())
    if not tag:
        return ""
    if not tag.startswith("#"):
        tag = "#" + tag
    if not re.fullmatch(r"#[A-Za-zÀ-ÿ0-9_]+", tag):
        return ""
    return tag


def validate_payload(data, assunto, hook, roteiro):
    if not isinstance(data, dict):
        raise ValueError("Publish Pack deve ser objeto JSON")

    raw_titles = data.get("titles")
    if not isinstance(raw_titles, list):
        raise ValueError("titles deve ser lista")

    titles = []
    seen = set()
    for value in raw_titles:
        title = str(value or "").strip()
        key = title.casefold()
        if not title or key in seen:
            continue
        if not 20 <= len(title) <= 100:
            continue
        seen.add(key)
        titles.append(title)

    if len(titles) < 3:
        raise ValueError("menos de 3 títulos únicos e válidos")
    titles = titles[:3]

    ranking = [
        {
            "title": title,
            "score": score_titulo(title, assunto, hook, roteiro),
        }
        for title in titles
    ]
    ranking.sort(key=lambda x: x["score"], reverse=True)

    best_score = float(ranking[0]["score"])
    if best_score < 60:
        raise ValueError(f"qualidade de título insuficiente: {best_score:.1f}")

    description = str(data.get("description", "") or "").strip()
    if not 80 <= len(description) <= 350:
        raise ValueError(
            f"descrição fora do limite seguro: {len(description)} caracteres"
        )

    raw_hashtags = data.get("hashtags")
    if not isinstance(raw_hashtags, list):
        raise ValueError("hashtags deve ser lista")

    hashtags = []
    seen_tags = set()
    for value in raw_hashtags:
        tag = normalize_hashtag(value)
        if not tag:
            continue
        key = tag.casefold()
        if key in seen_tags:
            continue
        seen_tags.add(key)
        hashtags.append(tag)

    if not any(x.casefold() == "#shorts" for x in hashtags):
        hashtags.insert(0, "#Shorts")

    final_tags = []
    seen_tags = set()
    for tag in hashtags:
        key = tag.casefold()
        if key in seen_tags:
            continue
        seen_tags.add(key)
        final_tags.append(tag)

    if len(final_tags) != 5:
        raise ValueError(
            f"Publish Pack deve ter exatamente 5 hashtags únicas; recebeu {len(final_tags)}"
        )

    pinned = str(data.get("pinned_comment", "") or "").strip()
    if not 5 <= len(pinned) <= 240:
        raise ValueError("comentário fixado ausente ou fora do limite")

    quality = "HIGH" if best_score >= 75 else "MEDIUM"

    return {
        "titles": titles,
        "title_ranking": ranking,
        "chosen_title": ranking[0]["title"],
        "publish_quality": quality,
        "publish_score": best_score,
        "description": description,
        "hashtags": final_tags,
        "pinned_comment": pinned,
    }


def chamar_gemini(prompt: str, api_key: str) -> str:
    if not MODEL:
        raise RuntimeError("GEMINI_MODEL vazio")

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{MODEL}:generateContent"
    )
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.45,
            "maxOutputTokens": 1300,
        },
    }

    wait = 4
    for attempt in range(1, 4):
        print(f"Publish Pack tentativa {attempt}/3...")
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=100,
            )
        except Exception as exc:
            if attempt == 3:
                raise RuntimeError(str(exc)) from exc
            time.sleep(wait)
            wait = min(wait * 2, 16)
            continue

        if response.ok:
            try:
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as exc:
                raise RuntimeError("Resposta Gemini inválida.") from exc
            text = str(text or "").strip()
            if not text:
                raise RuntimeError("Resposta Gemini vazia.")
            return text

        if response.status_code in {429, 500, 502, 503, 504} and attempt < 3:
            time.sleep(wait)
            wait = min(wait * 2, 20)
            continue

        raise RuntimeError(f"Gemini HTTP {response.status_code}")

    raise RuntimeError("Gemini não respondeu.")


def build_prompt(assunto: str, hook: str, roteiro: str, fonte: str) -> str:
    return f"""
Você cria metadados profissionais para YouTube Shorts em português do Brasil.

ASSUNTO REAL:
{assunto}

HOOK FINAL:
{hook}

ROTEIRO FINAL:
========================
{roteiro}
========================

FONTE FACTUAL:
========================
{fonte[:10000]}
========================

Use SOMENTE informações sustentadas pelo roteiro e pela fonte factual.
Não invente fatos. Não exagere conclusões. Não transforme teoria em fato.

Crie EXATAMENTE 3 títulos:
- português natural do Brasil;
- entre 35 e 70 caracteres;
- curiosidade forte, clara e factual;
- sem ALL CAPS e sem hashtag;
- no máximo 1 emoji;
- sem clickbait falso.

Descrição:
- entre 120 e 280 caracteres;
- factual;
- incentive comentário;
- não invente fatos.

Hashtags:
- EXATAMENTE 5;
- incluir #Shorts;
- relacionadas ao assunto;
- sem espaços.

Comentário fixado:
- uma pergunta curta;
- estimular opinião ou teoria;
- não pedir inscrição.

RESPONDA SOMENTE EM JSON VÁLIDO:
{{
  "titles": ["título 1", "título 2", "título 3"],
  "description": "descrição",
  "hashtags": ["#Shorts", "#Exemplo", "#Exemplo2", "#Exemplo3", "#Exemplo4"],
  "pinned_comment": "pergunta"
}}
""".strip()


def render_text(pack: dict) -> str:
    return (
        "TÍTULO:\n"
        + pack["chosen_title"]
        + "\n\nDESCRIÇÃO:\n"
        + pack["description"]
        + "\n\nHASHTAGS:\n"
        + " ".join(pack["hashtags"])
        + "\n\nCOMENTÁRIO FIXADO:\n"
        + pack["pinned_comment"]
        + "\n"
    )


def main() -> int:
    try:
        if not SHORT_ID:
            raise ValueError("SHORT_ID vazio")

        api_key = str(os.getenv("GEMINI_API_KEY", "") or "").strip()
        if not api_key:
            raise ValueError("GEMINI_API_KEY não configurada")

        roteiro = read_required(ROTEIRO, "roteiro")
        fonte = read_required(FONTE, "fonte factual")
        assunto = (
            TOPIC_REAL.read_text(encoding="utf-8").strip()
            if TOPIC_REAL.is_file()
            else ""
        )
        if not assunto and TOPIC_FALLBACK.is_file():
            assunto = TOPIC_FALLBACK.read_text(encoding="utf-8").strip()
        if not assunto:
            raise ValueError("assunto real ausente")
        hook = read_required(HOOK, "hook")

        print()
        print("================================")
        print("PUBLISH QUALITY GUARD - 2.4.0")
        print("================================")
        print()
        print(f"ID: {SHORT_ID}")
        print(f"Assunto: {assunto}")
        print()

        raw = chamar_gemini(
            build_prompt(assunto, hook, roteiro, fonte),
            api_key,
        )
        clean = clean_json_block(raw)
        try:
            data = json.loads(clean)
        except Exception as exc:
            raise ValueError("JSON inválido no Publish Pack") from exc

        pack = validate_payload(data, assunto, hook, roteiro)
        output = {
            "short_id": SHORT_ID,
            "topic": assunto,
            **pack,
        }

        atomic_json(SAIDA_JSON, output)
        atomic_text(SAIDA_TXT, render_text(output))

    except Exception as exc:
        print(f"ERRO Publish Pack: {exc}")
        return 1

    print("TÍTULOS:")
    print()
    for number, item in enumerate(output["title_ranking"], start=1):
        mark = " <-- ESCOLHIDO" if number == 1 else ""
        print(f"{number}. {item['title']}{mark}")
        print(f"   score={item['score']:.1f}")

    print()
    print(f"PUBLISH QUALITY: {output['publish_quality']}")
    print(f"PUBLISH SCORE: {output['publish_score']:.1f}")
    print()
    print("DESCRIÇÃO:")
    print(output["description"])
    print()
    print("HASHTAGS:")
    print(" ".join(output["hashtags"]))
    print()
    print("COMENTÁRIO FIXADO:")
    print(output["pinned_comment"])
    print()
    print(f"Arquivo:\n{SAIDA_TXT}")
    print()
    print("PUBLISH QUALITY GUARD: OK")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
