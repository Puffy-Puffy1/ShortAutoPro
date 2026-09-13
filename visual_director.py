#!/usr/bin/env python3

import json
import os
import re
import shutil
import sys
import time
import unicodedata
from datetime import date

import requests

BASE = os.path.expanduser("~/ShortAutoPro")
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())
API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except ValueError:
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

R = os.path.join(BASE, "roteiros")
MAPA = os.path.join(R, f"scene_map_{SHORT_ID}.json")
BACKUP = os.path.join(R, f"scene_map_pre_visual_{SHORT_ID}.json")
REPORT = os.path.join(R, f"visual_director_{SHORT_ID}.json")

if not os.path.isfile(MAPA):
    sys.exit(f"ERRO: scene_map não encontrado: {MAPA}")
if not API_KEY:
    sys.exit("ERRO: GEMINI_API_KEY não configurada.")


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


def texto_limpo(texto):
    return " ".join(str(texto or "").replace("\n", " ").split())


def lista_limpa(valor, limite=10):
    if not isinstance(valor, list):
        return []
    saida = []
    vistos = set()
    for item in valor:
        item = texto_limpo(item).lower()
        key = item.casefold()
        if item and key not in vistos:
            vistos.add(key)
            saida.append(item)
    return saida[:limite]


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower()


def tokens(texto):
    return set(re.findall(r"[a-z0-9]+", normalizar(texto)))


try:
    with open(MAPA, "r", encoding="utf-8") as f:
        original = json.load(f)
except Exception as exc:
    sys.exit(f"ERRO lendo scene_map: {exc}")

if not isinstance(original, dict):
    sys.exit("ERRO: scene_map não é objeto JSON.")
cenas_originais = original.get("scenes", [])
if not isinstance(cenas_originais, list):
    sys.exit("ERRO: campo scenes inválido.")
cenas_originais = [x for x in cenas_originais if isinstance(x, dict)]
if len(cenas_originais) != QTD_CENAS:
    sys.exit(
        f"ERRO: esperado {QTD_CENAS} cenas; recebido {len(cenas_originais)}."
    )

esperado = list(range(1, QTD_CENAS + 1))
numeros = []
for index, cena in enumerate(cenas_originais, start=1):
    try:
        numeros.append(int(cena.get("scene")))
    except (TypeError, ValueError):
        sys.exit(f"ERRO: cena original {index} sem número válido.")
if numeros != esperado:
    sys.exit("ERRO: numeração original das cenas não é sequencial.")

shutil.copy2(MAPA, BACKUP)

OBJETOS = {
    "aviao": "airplane",
    "aeronave": "airplane",
    "helicoptero": "helicopter",
    "navio": "ship",
    "barco": "boat",
    "carro": "car",
    "veiculo": "vehicle",
    "hotel": "hotel",
    "elevador": "elevator",
    "tanque": "water tank",
    "montanha": "mountain",
    "montanhas": "mountains",
    "neve": "snow",
    "floresta": "forest",
    "caverna": "cave",
    "documento": "document",
    "relatorio": "document",
    "camera": "security camera",
    "policia": "police",
    "corpo": "body",
    "rugby": "rugby team",
}


def objetos_do_segmento(segmento):
    seg_tokens = tokens(segmento)
    saida = []
    for termo, ingles in OBJETOS.items():
        termo_tokens = tokens(termo)
        if termo_tokens and termo_tokens <= seg_tokens and ingles not in saida:
            saida.append(ingles)
    return saida


SHOT_TERMS = [
    "security footage", "close up", "wide shot", "medium shot", "aerial",
    "portrait", "interior", "exterior", "overhead", "macro", "silhouette",
    "document", "drone", "landscape",
]


def detectar_plano(query):
    q = texto_limpo(query).lower()
    for termo in SHOT_TERMS:
        if re.search(r"(?<![a-z0-9])" + re.escape(termo) + r"(?![a-z0-9])", q):
            return termo
    return "generic"


def segmento_tem_nome_proprio(segmento):
    palavras = re.findall(r"\b[A-ZÀ-Ý][A-Za-zÀ-ÿ'-]{2,}\b", str(segmento))
    return len(palavras) >= 2


def proteger_retrato_generico(segmento, query, must_have):
    if not segmento_tem_nome_proprio(segmento):
        return query, must_have, False
    q = texto_limpo(query).lower()
    termos = {"portrait", "headshot", "face", "man portrait", "woman portrait"}
    if not any(
        re.search(r"(?<![a-z0-9])" + re.escape(termo) + r"(?![a-z0-9])", q)
        for termo in termos
    ):
        return query, must_have, False
    return (
        "vintage archival case documents and partially visible old photograph",
        ["document", "photograph"],
        True,
    )


def avaliar_cena(cena):
    segmento = texto_limpo(cena.get("segment", ""))
    query = texto_limpo(cena.get("query", ""))
    must = lista_limpa(cena.get("must_have", []), 3)
    avoid = lista_limpa(cena.get("avoid", []), 5)
    score = 100
    problemas = []

    if not segmento:
        score -= 50
        problemas.append("segmento_vazio")
    if len(query.split()) < 4:
        score -= 25
        problemas.append("query_generica")
    if not must:
        score -= 25
        problemas.append("sem_must")

    objetos = objetos_do_segmento(segmento)
    must_text = " ".join(must)
    if objetos and not any(obj in must_text for obj in objetos):
        score -= 30
        problemas.append("objeto_principal_ausente")
    if not avoid:
        score -= 5
        problemas.append("sem_avoid")

    return {
        "score": max(0, score),
        "problems": problemas,
        "objects": objetos,
        "shot": detectar_plano(query),
    }


entrada = []
for cena in cenas_originais:
    avaliacao = avaliar_cena(cena)
    entrada.append({
        "scene": cena["scene"],
        "segment": texto_limpo(cena.get("segment", "")),
        "current_query": texto_limpo(cena.get("query", "")),
        "current_must": lista_limpa(cena.get("must_have", []), 3),
        "current_avoid": lista_limpa(cena.get("avoid", []), 5),
        "local_score": avaliacao["score"],
        "local_problems": avaliacao["problems"],
    })

prompt = f"""
Você é diretor visual profissional de vídeos documentais verticais.
Você receberá EXATAMENTE {QTD_CENAS} cenas.
Não altere o roteiro. Melhore SOMENTE query, must_have e avoid.

REGRAS:
- identifique o objeto principal da frase;
- não acrescente fatos, identidades, crimes, armas, causas ou locais não sustentados;
- pessoas reais específicas não devem ser substituídas por retratos genéricos;
- teoria/paranormal/UFO deve ser visualmente ambíguo, nunca mostrado como fato;
- query em inglês, 5 a 12 palavras;
- must_have: 1 a 3 itens;
- avoid: 2 a 4 itens quando possível;
- relevância factual acima de movimento;
- preserve exatamente os números das cenas.

CENAS:
{json.dumps(entrada, ensure_ascii=False, indent=2)}

RESPONDA SOMENTE JSON VÁLIDO:
{{"scenes":[{{"scene":1,"query":"english visual search","must_have":["object"],"avoid":["wrong object"],"shot_type":"wide shot","reason":"short explanation"}}]}}
EXATAMENTE {QTD_CENAS} cenas.
"""

URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
HEADERS = {"Content-Type": "application/json", "x-goog-api-key": API_KEY}
payload = {
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {"temperature": 0.25, "maxOutputTokens": 4500},
}

resposta = None
print()
print("================================")
print("VISUAL DIRECTOR PASS - STABLE 3.1")
print("================================")
print()

for tentativa in range(1, 4):
    print(f"Visual Director tentativa {tentativa}/3...")
    try:
        response = requests.post(
            URL,
            headers=HEADERS,
            json=payload,
            timeout=120,
        )
    except Exception as exc:
        if tentativa == 3:
            sys.exit(f"ERRO Visual Director: {exc}")
        time.sleep(4)
        continue

    if response.ok:
        try:
            resposta = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            resposta = str(resposta).strip()
            if resposta:
                break
        except Exception:
            resposta = None

    if response.status_code in {429, 500, 502, 503, 504} and tentativa < 3:
        time.sleep(6)
        continue
    sys.exit(f"ERRO Visual Director HTTP {response.status_code}")

if not resposta:
    sys.exit("ERRO: Visual Director sem resposta.")

resposta = resposta.replace("```json", "").replace("```", "").strip()
try:
    novo = json.loads(resposta)
except Exception:
    sys.exit("ERRO: Visual Director retornou JSON inválido.")

if not isinstance(novo, dict):
    sys.exit("ERRO: resposta do Visual Director não é objeto JSON.")
novas_cenas = novo.get("scenes", [])
if not isinstance(novas_cenas, list):
    sys.exit("ERRO: campo scenes do Visual Director não é lista.")
if len(novas_cenas) != QTD_CENAS:
    sys.exit(
        f"ERRO: Visual Director retornou {len(novas_cenas)} cenas; esperado {QTD_CENAS}."
    )

por_numero = {}
for item in novas_cenas:
    if not isinstance(item, dict):
        sys.exit("ERRO: Visual Director retornou cena inválida.")
    try:
        numero = int(item.get("scene"))
    except (TypeError, ValueError):
        sys.exit("ERRO: Visual Director retornou número de cena inválido.")
    if numero in por_numero:
        sys.exit(f"ERRO: cena {numero} duplicada no Visual Director.")
    por_numero[numero] = item

if set(por_numero) != set(esperado):
    sys.exit("ERRO: numeração das cenas inválida.")

resultado_cenas = []
relatorio = []

for original_scene in cenas_originais:
    numero = int(original_scene["scene"])
    melhoria = por_numero[numero]
    antes = avaliar_cena(original_scene)

    query = texto_limpo(melhoria.get("query", ""))
    must = lista_limpa(melhoria.get("must_have", []), 3)
    avoid = lista_limpa(melhoria.get("avoid", []), 5)

    if not 4 <= len(query.split()) <= 15:
        query = texto_limpo(original_scene.get("query", ""))
    if not 1 <= len(must) <= 3:
        must = lista_limpa(original_scene.get("must_have", []), 3)
    if not 1 <= len(avoid) <= 5:
        avoid = lista_limpa(original_scene.get("avoid", []), 5)

    if not query or not must:
        sys.exit(f"ERRO: cena {numero} perdeu query ou must_have.")

    query, must, retrato_protegido = proteger_retrato_generico(
        original_scene.get("segment", ""),
        query,
        must,
    )

    candidato = dict(original_scene)
    candidato.update({"query": query, "must_have": must, "avoid": avoid})
    depois = avaliar_cena(candidato)

    # O refinamento não pode piorar o score heurístico, salvo quando a
    # proteção de identidade foi acionada deliberadamente.
    reverted = False
    if depois["score"] < antes["score"] and not retrato_protegido:
        candidato = dict(original_scene)
        depois = antes
        reverted = True

    resultado_cenas.append(candidato)
    relatorio.append({
        "scene": numero,
        "before_score": antes["score"],
        "after_score": depois["score"],
        "before_query": original_scene.get("query", ""),
        "after_query": candidato.get("query", ""),
        "must_have": candidato.get("must_have", []),
        "avoid": candidato.get("avoid", []),
        "shot_type": texto_limpo(melhoria.get("shot_type", "")),
        "reason": texto_limpo(melhoria.get("reason", "")),
        "portrait_guard": retrato_protegido,
        "reverted_regression": reverted,
    })

shots = [detectar_plano(x.get("query", "")) for x in resultado_cenas]
repeticoes = sum(
    1
    for i in range(1, len(shots))
    if shots[i] == shots[i - 1] and shots[i] != "generic"
)

mapa_final = dict(original)
mapa_final["scenes"] = resultado_cenas
mapa_final["visual_director"] = {
    "version": "3.1",
    "applied": True,
    "expected_scenes": QTD_CENAS,
    "consecutive_shot_repetitions": repeticoes,
}

atomic_json(MAPA, mapa_final)
atomic_json(REPORT, {
    "short_id": SHORT_ID,
    "version": "3.1",
    "backup": BACKUP,
    "shot_repetitions": repeticoes,
    "scenes": relatorio,
})

print()
print(f"Cenas processadas: {len(resultado_cenas)}/{QTD_CENAS}")
print(f"Repetições consecutivas de plano: {repeticoes}")
print(f"Backup original: {BACKUP}")
print(f"Relatório: {REPORT}")
print("VISUAL DIRECTOR PASS: OK")
