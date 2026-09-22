#!/usr/bin/env python3

import json
import os
import shutil
import sys
import time
from datetime import date

from gemini_runtime import (\n    GeminiInvalidResponse,\n    GeminiRuntimeError,\n    GeminiTemporaryUnavailable,\n    generate_text,\n)
from runtime_config import env_int

VERSION = "3.6"
if __name__ == "__main__" and "--version" in sys.argv[1:]:
    print(f"DOCUMENTARY DIRECTOR - STABLE {VERSION}")
    raise SystemExit(0)

BASE = os.path.abspath(os.path.expanduser(os.getenv("SHORTAUTOPRO_BASE", "~/ShortAutoPro")))
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())
API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
QTD_CENAS = env_int("SHORT_QTD_CENAS", 12, 6, 20)

R = os.path.join(BASE, "roteiros")
SCENE_MAP = os.path.join(R, f"scene_map_{SHORT_ID}.json")
FONTE = os.path.join(R, f"fonte_{SHORT_ID}.txt")
TOPIC_REAL = os.path.join(R, f"used_topic_{SHORT_ID}.txt")
TOPIC_FALLBACK = os.path.join(R, f"topic_{SHORT_ID}.txt")
BACKUP = os.path.join(R, f"scene_map_pre_documentary_{SHORT_ID}.json")
REPORT = os.path.join(R, f"documentary_director_{SHORT_ID}.json")

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


def extrair_objeto_json(texto):
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("resposta vazia")

    limpo = texto.strip().lstrip("\ufeff")
    fence = chr(96) * 3

    if limpo.startswith(fence):
        linhas = limpo.splitlines()
        limpo = "\n".join(linhas[1:]).strip()
        if limpo.endswith(fence):
            limpo = limpo[:-3].rstrip()

    valor = None

    try:
        valor = json.loads(limpo)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()

        # First try the first object or array embedded in surrounding prose.
        candidatos_inicio = [
            pos for pos in (limpo.find("{"), limpo.find("["))
            if pos >= 0
        ]
        for inicio in sorted(candidatos_inicio):
            try:
                valor, _ = decoder.raw_decode(limpo, inicio)
                break
            except json.JSONDecodeError:
                continue

        if valor is None:
            raise ValueError("nenhum JSON válido encontrado")

    # Gemini sometimes returns the scenes array directly even when the prompt
    # requested {"scenes":[...]}. That shape is losslessly recoverable.
    if isinstance(valor, list):
        return {
            "scenes": valor,
            "_normalized_from": "root_array",
        }

    if not isinstance(valor, dict):
        raise ValueError("JSON raiz não é objeto nem lista")

    # Common recoverable wrappers from structured-output models.
    for key in ("result", "data", "output", "response"):
        wrapped = valor.get(key)
        if isinstance(wrapped, dict) and isinstance(wrapped.get("scenes"), list):
            normalized = dict(wrapped)
            normalized["_normalized_from"] = f"wrapper:{key}"
            return normalized
        if isinstance(wrapped, list):
            return {
                "scenes": wrapped,
                "_normalized_from": f"wrapper_list:{key}",
            }

    if isinstance(valor.get("scenes"), list):
        return valor

    # Another common shape is a dict keyed by scene number.
    numeric_items = []
    for key, item in valor.items():
        if str(key).isdigit() and isinstance(item, dict):
            normalized = dict(item)
            normalized.setdefault("scene", int(key))
            numeric_items.append(normalized)
    if numeric_items:
        numeric_items.sort(key=lambda item: int(item.get("scene", 0) or 0))
        return {
            "scenes": numeric_items,
            "_normalized_from": "numeric_object",
        }

    raise ValueError("JSON válido sem campo scenes recuperável")


def numero_cena(valor):
    # bool and floating point numbers must not silently become scene IDs.
    if type(valor) is int:
        return valor
    if isinstance(valor, str) and valor.isascii() and valor.isdecimal():
        return int(valor)
    raise ValueError("numeração de cena deve ser inteira")


def validar_resposta_documental(resposta):
    if not isinstance(resposta, dict):
        raise ValueError("raiz não é objeto JSON")
    novas = resposta.get("scenes")
    if not isinstance(novas, list):
        raise ValueError("campo scenes não é lista")
    if len(novas) != QTD_CENAS:
        raise ValueError(f"retornou {len(novas)} cenas; esperado {QTD_CENAS}")

    numeros = []
    for indice, item in enumerate(novas, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"cena {indice} não é objeto")
        try:
            numero = numero_cena(item.get("scene"))
        except (TypeError, ValueError):
            raise ValueError(f"cena {indice} sem numeração válida")
        numeros.append(numero)
        query = item.get("query")
        if not isinstance(query, str) or not 4 <= len(query.split()) <= 16:
            raise ValueError(f"cena {numero} com query inválida (4 a 16 palavras)")
        must = item.get("must_have")
        if (not isinstance(must, list) or len(must) > 3
                or any(not isinstance(term, str) or not term.strip() for term in must)):
            raise ValueError(f"cena {numero} com must_have inválido")
        avoid = item.get("avoid", [])
        if not isinstance(avoid, list) or any(not isinstance(term, str) for term in avoid):
            raise ValueError(f"cena {numero} com avoid inválido")
        if not isinstance(item.get("visual_mode"), str) or item["visual_mode"] not in MODOS_VALIDOS:
            raise ValueError(f"cena {numero} com visual_mode inválido")
        if not isinstance(item.get("shot_type"), str) or item["shot_type"] not in SHOTS_VALIDOS:
            raise ValueError(f"cena {numero} com shot_type inválido")
    esperado_local = list(range(1, QTD_CENAS + 1))
    if numeros != esperado_local:
        raise ValueError(f"numeração inválida: {numeros}; esperado {esperado_local}")
    return resposta


def texto_resposta_gemini(response):
    try:
        dados = response.json()
    except ValueError as exc:
        raise ValueError("HTTP 200 sem JSON de envelope") from exc
    if not isinstance(dados, dict):
        raise ValueError("envelope Gemini não é objeto")
    feedback = dados.get("promptFeedback")
    if isinstance(feedback, dict) and feedback.get("blockReason"):
        raise ValueError(f"prompt bloqueado: {feedback['blockReason']}")
    try:
        candidate = dados["candidates"][0]
        finish = candidate.get("finishReason")
        if finish and finish != "STOP":
            raise ValueError(f"candidate interrompido: {finish}")
        partes = candidate["content"]["parts"]
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise ValueError("resposta sem candidates/content/parts válidos") from exc
    if not isinstance(partes, list):
        raise ValueError("candidate parts não é lista")
    textos = [parte["text"] for parte in partes
              if isinstance(parte, dict) and not parte.get("thought")
              and isinstance(parte.get("text"), str)]
    # Parts can split a JSON string; inserting a newline corrupts that string.
    bruto = "".join(textos).strip()
    if not bruto:
        raise ValueError("candidate sem texto")
    return bruto


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
if any(not isinstance(cena, dict) for cena in cenas):
    sys.exit("ERRO: scene_map contém cena que não é objeto JSON.")
if len(cenas) != QTD_CENAS:
    sys.exit(
        f"ERRO: Documentary Director esperava {QTD_CENAS} cenas; encontrou {len(cenas)}."
    )

numeros_originais = []
for index, cena in enumerate(cenas, start=1):
    try:
        numero = numero_cena(cena.get("scene"))
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
- must_have: 0 a 3 conceitos realmente obrigatórios; use [] quando nenhum elemento factual específico precisar ser provado visualmente;
- avoid: 2 a 5 conceitos inadequados quando possível;
- não use o mesmo visual_mode ou shot_type mais de 2 vezes consecutivas;
- relevância factual é mais importante que movimento.

CENAS:
{json.dumps(entrada, ensure_ascii=False, indent=2)}

RESPONDA SOMENTE JSON VÁLIDO:
{{"scenes":[{{"scene":1,"visual_mode":"location","shot_type":"wide","query":"english search query","must_have":["term"],"avoid":["wrong thing"],"reason":"explicação curta"}}]}}

EXATAMENTE {QTD_CENAS} cenas, numeradas de 1 a {QTD_CENAS}.
"""

resposta = None
ultimo_erro = ""
ultimo_bruto = ""
historico = []

print()
print("================================")
print("DOCUMENTARY DIRECTOR - STABLE 3.6")
print("================================")
print()

max_tokens = env_int("SAP_DOCUMENTARY_MAX_TOKENS", 5000, 2000, 16000)

for tentativa in range(1, 4):
    print(f"Documentary Director contrato {tentativa}/3...")

    prompt_tentativa = prompt
    if tentativa > 1:
        prompt_tentativa += (
            "\n\nA resposta anterior foi inválida para o contrato JSON. "
            f"Motivo: {ultimo_erro}. "
            "Corrija e responda SOMENTE um objeto JSON válido, sem markdown, "
            f"com exatamente {QTD_CENAS} cenas numeradas de 1 a {QTD_CENAS}."
        )

    registro = {"attempt": tentativa}
    historico.append(registro)

    try:
        bruto = generate_text(
            prompt_tentativa,
            temperature=0.20,
            max_output_tokens=max_tokens,
            response_mime_type="application/json",
            component="Documentary Director",
            api_key=API_KEY,
        )
        ultimo_bruto = str(bruto)[:1200]
    except GeminiInvalidResponse as exc:
        ultimo_erro = f"{type(exc).__name__}: {str(exc)[:220]}"
        registro["error"] = ultimo_erro
        print(f"AVISO Documentary Director: {ultimo_erro}")
        if "MAX_TOKENS" in str(exc) and tentativa < 3:
            previous_budget = max_tokens
            max_tokens = min(16000, max_tokens * 2)
            registro["repair"] = {
                "action": "increase_output_budget",
                "from": previous_budget,
                "to": max_tokens,
            }
            print(
                "DOCUMENTARY_DIRECTOR_RETRY=TOKEN_BUDGET_REPAIR "
                f"from={previous_budget} to={max_tokens}"
            )
            continue
        # Safety/prompt blocks and other runtime-invalid envelopes are not
        # repaired by replaying the identical request.
        break
    except (GeminiTemporaryUnavailable, GeminiRuntimeError) as exc:
        ultimo_erro = f"{type(exc).__name__}: {str(exc)[:220]}"
        registro["error"] = ultimo_erro
        print(f"AVISO Documentary Director: {ultimo_erro}")
        # Transport/capacity/auth failure has already been handled by the
        # shared runtime. Preserve the existing map instead of multiplying it.
        break
    except Exception as exc:
        ultimo_erro = f"{type(exc).__name__}: {str(exc)[:220]}"
        registro["error"] = ultimo_erro
        print(f"AVISO Documentary Director: {ultimo_erro}")
        break

    try:
        normalizada = extrair_objeto_json(bruto)
        origem_normalizacao = str(normalizada.get("_normalized_from", "") or "")
        resposta = validar_resposta_documental(normalizada)
        registro["status"] = "PASS"
        if origem_normalizacao:
            registro["normalized_from"] = origem_normalizacao
            print(
                "DOCUMENTARY_JSON_NORMALIZED="
                f"{origem_normalizacao}"
            )
        break
    except ValueError as exc:
        ultimo_erro = str(exc)
        registro["error"] = ultimo_erro
        print(
            "AVISO: resposta Gemini inválida para o contrato documental: "
            f"{ultimo_erro}"
        )
        if "MAX_TOKENS" in ultimo_erro:
            max_tokens = min(16000, max_tokens * 2)
        continue

if resposta is None:
    atomic_json(
        REPORT,
        {
            "short_id": SHORT_ID,
            "version": "3.6",
            "status": "DEGRADED",
            "applied": False,
            "preserved_original_scene_map": True,
            "error": ultimo_erro or "resposta inválida",
            "raw_preview": ultimo_bruto,
            "attempts": len(historico),
            "attempt_history": historico,
        },
    )
    print(
        "DOCUMENTARY_DIRECTOR=DEGRADED_FAIL_OPEN "
        "scene_map_original=PRESERVED"
    )
    raise SystemExit(0)


novas = resposta["scenes"]

por_numero = {}
for item in novas:
    if not isinstance(item, dict):
        sys.exit("ERRO: Documentary Director retornou cena inválida.")
    try:
        numero = numero_cena(item.get("scene"))
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
    original_must = limpar_lista(cena_original.get("must_have", []), 3)
    if not must and original_must:
        must = original_must

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
    "version": "3.6",
    "applied": True,
    "expected_scenes": QTD_CENAS,
    "visual_mode_triple_repetitions": repeticoes_mode,
    "shot_triple_repetitions": repeticoes_shot,
}

atomic_json(SCENE_MAP, mapa_final)
atomic_json(REPORT, {
    "short_id": SHORT_ID,
    "version": "3.6",
    "status": "PASS",
    "attempts": len(historico),
    "attempt_history": historico,
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
