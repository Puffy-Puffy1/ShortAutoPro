#!/usr/bin/env python3

import json
import os
import shutil
import sys
import time
from datetime import date

import requests

BASE = os.path.abspath(os.path.expanduser(os.getenv("SHORTAUTOPRO_BASE", "~/ShortAutoPro")))
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())
API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
try:
    GEMINI_TIMEOUT = float(os.getenv("SAP_GEMINI_TIMEOUT", "75") or 75)
except (TypeError, ValueError):
    GEMINI_TIMEOUT = 75.0
GEMINI_TIMEOUT = max(20.0, min(GEMINI_TIMEOUT, 120.0))

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except ValueError:
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

R = os.path.join(BASE, "roteiros")
SCENE_MAP = os.path.join(R, f"scene_map_{SHORT_ID}.json")
FONTE = os.path.join(R, f"fonte_{SHORT_ID}.txt")
TOPIC_REAL = os.path.join(R, f"used_topic_{SHORT_ID}.txt")
TOPIC_FALLBACK = os.path.join(R, f"topic_{SHORT_ID}.txt")
BACKUP = os.path.join(R, f"scene_map_pre_documentary_{SHORT_ID}.json")
REPORT = os.path.join(R, f"documentary_director_{SHORT_ID}.json")

if not API_KEY:
    sys.exit("ERRO: GEMINI_API_KEY não configurada.")
if not os.path.isfile(SCENE_MAP):
    sys.exit(f"ERRO: scene_map ausente: {SCENE_MAP}")


def ler_txt(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def atomic_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def limpar(texto):
    return " ".join(str(texto or "").replace("\n", " ").split())


def limpar_lista(valor, maximo=10):
    if not isinstance(valor, list):
        return []
    saida = []
    vistos = set()
    for item in valor:
        item = limpar(item).lower()
        if not item:
            continue
        key = item.casefold()
        if key not in vistos:
            vistos.add(key)
            saida.append(item)
    return saida[:maximo]


try:
    with open(SCENE_MAP, "r", encoding="utf-8") as f:
        mapa = json.load(f)
except Exception as exc:
    sys.exit(f"ERRO lendo scene_map: {exc}")

if not isinstance(mapa, dict):
    sys.exit("ERRO: scene_map não é um objeto JSON.")

cenas = mapa.get("scenes", [])
if not isinstance(cenas, list):
    sys.exit("ERRO: campo scenes inválido.")
cenas = [x for x in cenas if isinstance(x, dict)]
if len(cenas) != QTD_CENAS:
    sys.exit(
        f"ERRO: Documentary Director esperava {QTD_CENAS} cenas; encontrou {len(cenas)}."
    )

numeros_originais = []
for index, cena in enumerate(cenas, start=1):
    try:
        numero = int(cena.get("scene"))
    except (TypeError, ValueError):
        sys.exit(f"ERRO: cena original {index} sem numeração válida.")
    numeros_originais.append(numero)

esperado = list(range(1, QTD_CENAS + 1))
if numeros_originais != esperado:
    sys.exit(
        "ERRO: numeração original das cenas não é sequencial de 1 até "
        f"{QTD_CENAS}."
    )

assunto = ler_txt(TOPIC_REAL) or ler_txt(TOPIC_FALLBACK)
fonte = ler_txt(FONTE)
if not assunto:
    sys.exit("ERRO: assunto ausente para Documentary Director.")
if not fonte:
    sys.exit("ERRO: fonte factual ausente para Documentary Director.")

shutil.copy2(SCENE_MAP, BACKUP)

MODOS_VALIDOS = {
    "location", "object", "evidence", "document", "human_context", "environment",
    "transport", "architecture", "map_context", "abstract_context",
}
SHOTS_VALIDOS = {
    "wide", "medium", "close_up", "aerial", "detail", "interior", "exterior",
    "overhead", "silhouette",
}

entrada = []
for cena in cenas:
    entrada.append({
        "scene": cena["scene"],
        "segment": limpar(cena.get("segment", "")),
        "query": limpar(cena.get("query", "")),
        "must_have": limpar_lista(cena.get("must_have", []), 3),
        "avoid": limpar_lista(cena.get("avoid", []), 5),
    })

prompt = f"""
Você é o diretor visual de um documentário factual vertical para YouTube Shorts.

ASSUNTO:
{assunto}

FONTE FACTUAL:
========================
{fonte[:14000]}
========================

Você receberá {QTD_CENAS} cenas já associadas ao roteiro.
Crie direção documental profissional SEM mudar o texto narrado e SEM inventar fatos.

Modos permitidos:
location, object, evidence, document, human_context, environment, transport,
architecture, map_context, abstract_context.

Enquadramentos permitidos:
wide, medium, close_up, aerial, detail, interior, exterior, overhead, silhouette.

REGRAS:
- represente cada frase de forma factual e concreta;
- priorize o objeto/local/documento principal da frase;
- evite pessoas aleatórias quando contexto documental for melhor;
- não invente retratos de pessoas reais;
- alegações controversas devem permanecer visualmente ambíguas;
- query em inglês, aproximadamente 5 a 13 palavras;
- must_have: 1 a 3 conceitos essenciais;
- avoid: 2 a 5 conceitos inadequados quando possível;
- não use o mesmo visual_mode ou shot_type mais de 2 vezes consecutivas;
- relevância factual é mais importante que movimento.

CENAS:
{json.dumps(entrada, ensure_ascii=False, indent=2)}

RESPONDA SOMENTE JSON VÁLIDO:
{{"scenes":[{{"scene":1,"visual_mode":"location","shot_type":"wide","query":"english search query","must_have":["term"],"avoid":["wrong thing"],"reason":"explicação curta"}}]}}

EXATAMENTE {QTD_CENAS} cenas, numeradas de 1 a {QTD_CENAS}.
"""

URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
HEADERS = {"Content-Type": "application/json", "x-goog-api-key": API_KEY}
payload = {
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {"temperature": 0.20, "maxOutputTokens": 5000},
}

bruto = None
print()
print("================================")
print("DOCUMENTARY DIRECTOR - STABLE 3.2")
print("================================")
print()

for tentativa in range(1, 4):
    print(f"Documentary Director tentativa {tentativa}/3...")
    try:
        response = requests.post(
            URL,
            headers=HEADERS,
            json=payload,
            timeout=GEMINI_TIMEOUT,
        )
    except Exception as exc:
        if tentativa == 3:
            sys.exit(f"ERRO Documentary Director: {exc}")
        time.sleep(4)
        continue

    if response.ok:
        try:
            bruto = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            bruto = str(bruto).strip()
            if bruto:
                break
        except Exception:
            bruto = None

    if response.status_code in {429, 500, 502, 503, 504} and tentativa < 3:
        time.sleep(6)
        continue

    sys.exit(f"ERRO Documentary Director HTTP {response.status_code}")

if not bruto:
    sys.exit("ERRO: Documentary Director sem resposta.")

bruto = bruto.replace("```json", "").replace("```", "").strip()
try:
    resposta = json.loads(bruto)
except Exception:
    sys.exit("ERRO: Documentary Director retornou JSON inválido.")

if not isinstance(resposta, dict):
    sys.exit("ERRO: resposta do Documentary Director não é objeto JSON.")

novas = resposta.get("scenes", [])
if not isinstance(novas, list):
    sys.exit("ERRO: campo scenes do Documentary Director não é lista.")
if len(novas) != QTD_CENAS:
    sys.exit(
        f"ERRO: Documentary Director retornou {len(novas)} cenas; esperado {QTD_CENAS}."
    )

por_numero = {}
for item in novas:
    if not isinstance(item, dict):
        sys.exit("ERRO: Documentary Director retornou cena inválida.")
    try:
        numero = int(item.get("scene"))
    except (TypeError, ValueError):
        sys.exit("ERRO: Documentary Director retornou numeração inválida.")
    if numero in por_numero:
        sys.exit(f"ERRO: cena {numero} duplicada no Documentary Director.")
    por_numero[numero] = item

if set(por_numero) != set(esperado):
    sys.exit("ERRO: Documentary Director alterou a numeração das cenas.")

resultado = []
relatorio = []

for cena_original in cenas:
    numero = int(cena_original["scene"])
    novo = por_numero[numero]

    mode = limpar(novo.get("visual_mode", "")).lower()
    if mode not in MODOS_VALIDOS:
        mode = limpar(cena_original.get("visual_mode", "")).lower()
        if mode not in MODOS_VALIDOS:
            mode = "environment"

    shot = limpar(novo.get("shot_type", "")).lower()
    if shot not in SHOTS_VALIDOS:
        shot = limpar(cena_original.get("shot_type", "")).lower()
        if shot not in SHOTS_VALIDOS:
            shot = "medium"

    query = limpar(novo.get("query", ""))
    if not 4 <= len(query.split()) <= 16:
        query = limpar(cena_original.get("query", ""))
    if not query:
        sys.exit(f"ERRO: cena {numero} ficou sem query válida.")

    must = limpar_lista(novo.get("must_have", []), 3)
    if not must:
        must = limpar_lista(cena_original.get("must_have", []), 3)
    if not must:
        sys.exit(f"ERRO: cena {numero} ficou sem must_have.")

    avoid = limpar_lista(novo.get("avoid", []), 5)
    if len(avoid) < 2:
        anterior = limpar_lista(cena_original.get("avoid", []), 5)
        if len(anterior) > len(avoid):
            avoid = anterior

    cena_final = dict(cena_original)
    cena_final.update({
        "query": query,
        "must_have": must,
        "avoid": avoid,
        "visual_mode": mode,
        "shot_type": shot,
    })
    resultado.append(cena_final)
    relatorio.append({
        "scene": numero,
        "segment": limpar(cena_original.get("segment", "")),
        "visual_mode": mode,
        "shot_type": shot,
        "query_before": limpar(cena_original.get("query", "")),
        "query_after": query,
        "must_have": must,
        "avoid": avoid,
        "reason": limpar(novo.get("reason", "")),
    })

repeticoes_mode = 0
repeticoes_shot = 0
for i in range(2, len(resultado)):
    a, b, c = resultado[i], resultado[i - 1], resultado[i - 2]
    if a.get("visual_mode") == b.get("visual_mode") == c.get("visual_mode"):
        repeticoes_mode += 1
    if a.get("shot_type") == b.get("shot_type") == c.get("shot_type"):
        repeticoes_shot += 1

mapa_final = dict(mapa)
mapa_final["scenes"] = resultado
mapa_final["documentary_director"] = {
    "version": "3.2",
    "applied": True,
    "expected_scenes": QTD_CENAS,
    "visual_mode_triple_repetitions": repeticoes_mode,
    "shot_triple_repetitions": repeticoes_shot,
}

atomic_json(SCENE_MAP, mapa_final)
atomic_json(REPORT, {
    "short_id": SHORT_ID,
    "version": "3.2",
    "topic": assunto,
    "backup": BACKUP,
    "visual_mode_triple_repetitions": repeticoes_mode,
    "shot_triple_repetitions": repeticoes_shot,
    "scenes": relatorio,
})

print()
print(f"Cenas processadas: {len(resultado)}/{QTD_CENAS}")
print(f"Repetições de 3 visual_modes: {repeticoes_mode}")
print(f"Repetições de 3 enquadramentos: {repeticoes_shot}")
print(f"Relatório: {REPORT}")
print("DOCUMENTARY DIRECTOR: OK")
print()
