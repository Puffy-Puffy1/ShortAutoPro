#!/usr/bin/env python3

import json
import math
import os
import re
import sys
import time
from datetime import date

import requests

from runtime_config import env_float, env_int
from source_identity import validar_identidade
from topic_memory import encontrar_duplicata, normalizar as normalizar_memoria
from topic_reserve import melhor_reserva
from wiki_client import WikiRateLimit
from wiki_client import extract as wiki_extract_client
from wiki_client import search as wiki_search_client

BASE = os.path.abspath(os.path.expanduser(os.getenv("SHORTAUTOPRO_BASE", "~/ShortAutoPro")))
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())
TEMA = os.getenv("SHORT_TEMA", "mistérios, casos inexplicáveis e true crime")
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_TIMEOUT = env_float("SAP_GEMINI_TIMEOUT", 28.0, 8.0, 60.0)
GEMINI_ATTEMPTS_PER_MODEL = env_int("SAP_TOPIC_MODEL_ATTEMPTS", 2, 1, 3)

# High-demand 503s are model-local/capacity-local failures. Do not hammer the
# same endpoint three times for 75 seconds each; rotate across stable fallback
# models and keep a final non-LLM recovery path.
_default_model_chain = [
    MODEL,
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
]
_model_chain_env = os.getenv("GEMINI_MODEL_CHAIN", "").strip()
MODEL_CHAIN = []
for _model in (
    [x.strip() for x in _model_chain_env.split(",") if x.strip()]
    if _model_chain_env
    else _default_model_chain
):
    if _model not in MODEL_CHAIN:
        MODEL_CHAIN.append(_model)
HISTORICO = os.path.join(BASE, "historico_assuntos.json")
SAIDA = os.path.join(BASE, "roteiros", f"topic_{SHORT_ID}.txt")
VERIFICACAO = os.path.join(BASE, "roteiros", f"topic_verified_{SHORT_ID}.json")
REJEITADOS_RUNTIME = os.path.join(BASE, "roteiros", f"topic_rejected_{SHORT_ID}.json")
os.makedirs(os.path.dirname(SAIDA), exist_ok=True)

if not API_KEY:
    sys.exit("ERRO: GEMINI_API_KEY não configurada.")


def normalizar(texto):
    texto = str(texto).lower()
    texto = re.sub(r"[^\wÀ-ÿ]+", " ", texto)
    return " ".join(texto.split())


def carregar_historico():
    if not os.path.exists(HISTORICO):
        return []
    try:
        with open(HISTORICO, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception as exc:
        sys.exit(
            "ERRO: histórico de assuntos inválido; seleção bloqueada para evitar repetição: "
            f"{exc}"
        )
    if not isinstance(dados, list):
        sys.exit(
            "ERRO: histórico de assuntos não é uma lista; seleção bloqueada para evitar repetição."
        )
    return dados


def nota_segura(valor):
    try:
        nota = float(valor)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(nota):
        return 0.0
    return max(0.0, min(nota, 10.0))


def atomic_text(path, text):
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def atomic_json(path, data):
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


historico = carregar_historico()


def carregar_rejeitados_runtime():
    try:
        with open(REJEITADOS_RUNTIME, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    items = data.get("topics", []) if isinstance(data, dict) else []
    return [
        str(item.get("topic", "")).strip()
        for item in items
        if isinstance(item, dict) and str(item.get("topic", "")).strip()
    ]


rejeitados_runtime = carregar_rejeitados_runtime()
rejeitados_runtime_norm = {normalizar_memoria(x) or x.casefold() for x in rejeitados_runtime}


def wiki_search(query):
    return wiki_search_client(query, limit=5)


def wiki_extract(title):
    return wiki_extract_client(title)


def variacoes_busca(nome):
    candidatos = [
        nome,
        re.sub(r"^(O|A|Os|As)\s+", "", nome, flags=re.IGNORECASE),
        re.sub(r"^(O|A)\s+Caso\s+", "", nome, flags=re.IGNORECASE),
        re.sub(r"^Caso\s+", "", nome, flags=re.IGNORECASE),
    ]
    saida = []
    vistos = set()
    for item in candidatos:
        item = item.strip()
        key = item.casefold()
        if item and key not in vistos:
            vistos.add(key)
            saida.append(item)
    return saida


def verificar_wikipedia(nome):
    stop_titulo = {
        "o", "a", "os", "as", "de", "da", "do", "das", "dos", "e", "em",
        "no", "na", "caso", "incidente", "desaparecimento", "misterio", "mistério",
    }

    for consulta in variacoes_busca(nome):
        resultados = wiki_search(consulta)
        if not resultados:
            continue
        for resultado in resultados:
            if not isinstance(resultado, dict):
                continue
            titulo = str(resultado.get("title", "")).strip()
            if not titulo:
                continue
            texto = wiki_extract(titulo)
            if len(texto) < 700:
                continue

            nome_tokens = {
                x for x in normalizar(nome).split() if x not in stop_titulo
            }
            titulo_tokens = {
                x for x in normalizar(titulo).split() if x not in stop_titulo
            }
            if not nome_tokens:
                continue

            comuns = nome_tokens & titulo_tokens
            inter = len(comuns)
            semelhanca = inter / len(nome_tokens)

            if len(nome_tokens) == 1:
                if inter != 1:
                    continue
            else:
                if inter < 2 or semelhanca < 0.45:
                    continue

            identidade = validar_identidade(nome, titulo, texto)
            if not identidade.get("valid"):
                continue

            return {
                "ok": True,
                "wiki_title": titulo,
                "chars": len(texto),
                "similarity": round(semelhanca, 3),
                "identity_score": round(float(identidade.get("score", 0.0)), 3),
                "identity_reason": identidade.get("reason", ""),
            }

    return {
        "ok": False,
        "wiki_title": "",
        "chars": 0,
        "similarity": 0,
        "identity_score": 0.0,
        "identity_reason": "no_valid_source",
    }


PALAVRAS_VISUAIS = {
    "hotel", "elevator", "elevador", "aircraft", "avião", "aviao", "ship", "navio",
    "forest", "floresta", "mountain", "montanha", "island", "ilha", "ocean", "oceano",
    "snow", "neve", "police", "polícia", "policia", "house", "casa", "road", "estrada",
    "train", "trem", "car", "carro", "building", "prédio", "predio", "water", "água",
    "agua", "room", "quarto", "cave", "caverna", "desert", "deserto",
}

PALAVRAS_HOOK = {
    "desapareceu", "desaparecimento", "sumiu", "morreu", "morte", "encontrado",
    "encontrada", "mistério", "misterio", "sem", "nunca", "último", "ultimo", "corpo",
    "tripulação", "tripulacao", "avião", "aviao", "navio", "ilha", "hotel", "elevador", "neve",
}


def score_visual_nome(nome):
    hits = len(set(normalizar(nome).split()) & PALAVRAS_VISUAIS)
    return min(10.0, 5.0 + hits * 1.5)


def score_hook_nome(nome):
    hits = len(set(normalizar(nome).split()) & PALAVRAS_HOOK)
    return min(10.0, 5.0 + hits * 1.2)


def score_documentacao(chars):
    if chars >= 12000:
        return 10.0
    if chars >= 8000:
        return 9.5
    if chars >= 5000:
        return 9.0
    if chars >= 3000:
        return 8.0
    if chars >= 1800:
        return 7.0
    if chars >= 1000:
        return 6.0
    return 5.0


def score_titulo(similarity):
    return max(0.0, min(10.0, similarity * 10))


def score_novidade(nome):
    if not historico:
        return 10.0
    dup = encontrar_duplicata(nome, historico, limite=1.1)
    sim = float(dup.get("similarity", 0) or 0)
    return max(0.0, 10.0 - sim * 10)


class GeminiTemporarilyUnavailable(RuntimeError):
    pass


def _gemini_url(model):
    return (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + str(model)
        + ":generateContent"
    )


HEADERS = {"Content-Type": "application/json", "x-goog-api-key": API_KEY}


def _extract_gemini_text(dados):
    candidates = dados.get("candidates", []) if isinstance(dados, dict) else []
    for candidate in candidates if isinstance(candidates, list) else []:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content", {})
        parts = content.get("parts", []) if isinstance(content, dict) else []
        chunks = [
            str(part.get("text", "") or "").strip()
            for part in parts
            if isinstance(part, dict) and str(part.get("text", "") or "").strip()
        ]
        if chunks:
            return "\n".join(chunks).strip()

    feedback = dados.get("promptFeedback", {}) if isinstance(dados, dict) else {}
    reason = (
        str(feedback.get("blockReason", "") or "")
        if isinstance(feedback, dict)
        else ""
    ) or "no_usable_candidates"
    raise RuntimeError(f"Gemini sem candidato utilizável: {reason}")


def chamar_gemini(prompt):
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.65, "maxOutputTokens": 1800},
    }
    transient_errors = []
    total_models = len(MODEL_CHAIN)

    for model_index, model in enumerate(MODEL_CHAIN, start=1):
        url = _gemini_url(model)

        for tentativa in range(1, GEMINI_ATTEMPTS_PER_MODEL + 1):
            print(
                "Topic Engine model "
                f"{model_index}/{total_models}={model} "
                f"tentativa {tentativa}/{GEMINI_ATTEMPTS_PER_MODEL}..."
            )

            try:
                r = requests.post(
                    url,
                    headers=HEADERS,
                    json=payload,
                    timeout=GEMINI_TIMEOUT,
                )
            except requests.Timeout as exc:
                transient_errors.append(f"{model}:timeout:{exc}")
                print(f"Topic Engine: timeout em {model}; failover preparado.")
                if tentativa < GEMINI_ATTEMPTS_PER_MODEL:
                    time.sleep(1.5 * tentativa)
                    continue
                break
            except requests.RequestException as exc:
                transient_errors.append(f"{model}:network:{exc}")
                print(f"Topic Engine: erro de rede em {model}; failover preparado.")
                if tentativa < GEMINI_ATTEMPTS_PER_MODEL:
                    time.sleep(1.5 * tentativa)
                    continue
                break

            if r.ok:
                try:
                    dados = r.json()
                except Exception as exc:
                    transient_errors.append(f"{model}:invalid_json:{exc}")
                    if tentativa < GEMINI_ATTEMPTS_PER_MODEL:
                        time.sleep(1)
                        continue
                    break

                try:
                    texto = _extract_gemini_text(dados)
                except RuntimeError as exc:
                    transient_errors.append(f"{model}:empty:{exc}")
                    if tentativa < GEMINI_ATTEMPTS_PER_MODEL:
                        time.sleep(1)
                        continue
                    break

                print(f"TOPIC_ENGINE_MODEL_OK={model}")
                return texto

            status = int(r.status_code or 0)
            body = str(r.text or "")[:500]

            if status in {429, 500, 502, 503, 504}:
                transient_errors.append(f"{model}:HTTP_{status}:{body}")
                print(
                    "TOPIC_ENGINE_TRANSIENT="
                    f"model={model} status={status} "
                    "action=MODEL_FAILOVER"
                )

                # 503/504 usually indicate capacity/service trouble. Repeating
                # the same model immediately adds latency without resilience.
                if status in {503, 504}:
                    break

                if tentativa < GEMINI_ATTEMPTS_PER_MODEL:
                    wait = 2
                    if status == 429:
                        try:
                            wait = int(r.headers.get("Retry-After") or wait)
                        except (TypeError, ValueError):
                            wait = 2
                        wait = max(1, min(wait, 12))
                    time.sleep(wait)
                    continue
                break

            # Permanent/request errors should not be retried on this model.
            raise RuntimeError(f"HTTP {status} em {model}: {body}")

    detail = " | ".join(transient_errors[-6:]) or "sem detalhe"
    raise GeminiTemporarilyUnavailable(
        "todos os modelos temporariamente indisponíveis: " + detail
    )


FALLBACK_TOPIC_SEEDS = [
    "Desaparecimento de Frederick Valentich",
    "Incidente do Passo Dyatlov",
    "Sinal Wow!",
    "Monstro de Flatwoods",
    "Voo 19",
    "D. B. Cooper",
    "Caso Tamam Shud",
    "MV Joyita",
    "USS Cyclops",
    "Farol das Ilhas Flannan",
    "Colônia de Roanoke",
    "Manuscrito Voynich",
    "Cinco de Yuba County",
    "Crianças Sodder",
    "Caso das Máscaras de Chumbo",
    "Hinterkaifeck",
    "Kaspar Hauser",
    "Desaparecimento das crianças Beaumont",
]


def _fallback_candidate_score(nome, verificacao):
    return (
        score_visual_nome(nome) * 1.10
        + score_hook_nome(nome) * 1.15
        + score_documentacao(verificacao.get("chars", 0)) * 1.25
        + score_titulo(verificacao.get("similarity", 0.0)) * 0.55
        + score_novidade(nome) * 0.75
    )


def escolher_fallback_sem_llm():
    print()
    print("TOPIC_ENGINE_FALLBACK=START")

    reserva = melhor_reserva()
    if reserva:
        nome = str(reserva.get("topic", "")).strip()
        if nome:
            print(
                "TOPIC_ENGINE_FALLBACK=VERIFIED_RESERVE "
                f"topic={nome}"
            )
            return {
                "topic": nome,
                "score": float(reserva.get("score", 0.0) or 0.0),
                "wiki_title": str(reserva.get("wiki_title", "") or ""),
                "wiki_chars": 0,
                "wiki_similarity": 1.0,
                "gemini": {},
                "objective": {
                    "visual": score_visual_nome(nome),
                    "hook": score_hook_nome(nome),
                    "documentation": 0.0,
                    "title_match": 10.0,
                    "novelty": score_novidade(nome),
                },
                "reserve": True,
                "engine_fallback": "verified_reserve",
            }

    print("TOPIC_ENGINE_FALLBACK=LOCAL_WIKIPEDIA_DISCOVERY")

    melhores = []
    for nome in FALLBACK_TOPIC_SEEDS:
        duplicata = encontrar_duplicata(nome, historico, limite=0.72)
        if duplicata.get("duplicate"):
            continue

        chave = normalizar_memoria(nome) or nome.casefold()
        if chave in rejeitados_runtime_norm:
            continue

        try:
            verificacao = verificar_wikipedia(nome)
        except WikiRateLimit:
            print("TOPIC_ENGINE_FALLBACK=WIKIPEDIA_RATE_LIMIT")
            break
        except Exception as exc:
            print(
                "TOPIC_ENGINE_FALLBACK=WIKI_FAIL_OPEN "
                f"topic={nome} error={type(exc).__name__}:{str(exc)[:120]}"
            )
            continue

        if not verificacao.get("ok"):
            continue

        score = _fallback_candidate_score(nome, verificacao)
        melhores.append(
            {
                "topic": nome,
                "score": round(score, 2),
                "wiki_title": verificacao["wiki_title"],
                "wiki_chars": verificacao["chars"],
                "wiki_similarity": verificacao["similarity"],
                "gemini": {},
                "objective": {
                    "visual": score_visual_nome(nome),
                    "hook": score_hook_nome(nome),
                    "documentation": score_documentacao(verificacao["chars"]),
                    "title_match": score_titulo(verificacao["similarity"]),
                    "novelty": score_novidade(nome),
                },
                "engine_fallback": "local_wikipedia_verified",
            }
        )

        if len(melhores) >= 3:
            break

    if not melhores:
        return None

    melhores.sort(key=lambda x: x["score"], reverse=True)
    selected = melhores[0]
    print(
        "TOPIC_ENGINE_FALLBACK=LOCAL_VERIFIED_OK "
        f"topic={selected['topic']}"
    )
    return selected


usados = [
    str(item.get("topic", ""))
    for item in historico[-60:]
    if isinstance(item, dict) and str(item.get("topic", "")).strip()
]
usados_texto = "\n".join(f"- {x}" for x in usados) if usados else "nenhum"

prompt = f"""
Você é pesquisador de temas para YouTube Shorts.

Tema do canal:
{TEMA}

Gere EXATAMENTE 10 candidatos de casos REAIS.

IMPORTANTE:
- apenas casos documentados;
- não combine casos diferentes;
- não invente nomes, crimes ou desaparecimentos;
- prefira casos conhecidos com artigo provável na Wikipedia;
- evite assuntos já utilizados;
- varie países, épocas e tipos de mistério;
- priorize histórias com começo forte e bons elementos visuais;
- prefira casos que possam ser narrados de forma documental e não gráfica;
- evite temas cujo núcleo dependa de violência sexual contra menores, tortura gráfica ou detalhes explícitos de sofrimento.

ASSUNTOS JÁ UTILIZADOS:
{usados_texto}

Para cada candidato dê notas de 0 a 10:
curiosity, visual, documentation, retention, comment_potential.

RESPONDA SOMENTE EM JSON, sem markdown e sem explicações:
{{"topics":[{{"topic":"nome exato","curiosity":0,"visual":0,"documentation":0,"retention":0,"comment_potential":0}}]}}
Exatamente 10 itens.
"""

print()
print("================================")
print("VIRAL TOPIC ENGINE - STABLE 1.6")
print("================================")
print()
print(f"Assuntos no histórico: {len(historico)}")
print()

fallback_selected = None

try:
    bruto = chamar_gemini(prompt)
except GeminiTemporarilyUnavailable as exc:
    print(f"AVISO Topic Engine: {exc}")
    fallback_selected = escolher_fallback_sem_llm()
    if not fallback_selected:
        sys.exit(
            "ERRO Topic Engine: Gemini indisponível e nenhum fallback verificado disponível."
        )
except Exception as exc:
    # Request/configuration errors can still use a verified fallback instead of
    # blocking the whole production chain.
    print(f"AVISO Topic Engine não transitório: {exc}")
    fallback_selected = escolher_fallback_sem_llm()
    if not fallback_selected:
        sys.exit(f"ERRO Topic Engine: {exc}")

if fallback_selected:
    atomic_text(SAIDA, fallback_selected["topic"])
    atomic_json(
        VERIFICACAO,
        {
            "short_id": SHORT_ID,
            "selected": fallback_selected,
            "ranking": [fallback_selected],
            "verification": [
                {
                    "topic": fallback_selected["topic"],
                    "approved": True,
                    "reason": fallback_selected.get("engine_fallback", "fallback"),
                    "wiki_title": fallback_selected.get("wiki_title", ""),
                }
            ],
            "runtime_rejected_topics": rejeitados_runtime,
            "topic_engine_degraded": True,
        },
    )
    print()
    print("================================")
    print("TOPIC ENGINE DEGRADED MODE: OK")
    print("================================")
    print()
    print("Assunto escolhido:")
    print(fallback_selected["topic"])
    print()
    raise SystemExit(0)

bruto = bruto.replace("```json", "").replace("```", "").strip()
try:
    dados = json.loads(bruto)
except Exception:
    print(bruto)
    fallback_selected = escolher_fallback_sem_llm()
    if fallback_selected:
        atomic_text(SAIDA, fallback_selected["topic"])
        atomic_json(
            VERIFICACAO,
            {
                "short_id": SHORT_ID,
                "selected": fallback_selected,
                "ranking": [fallback_selected],
                "verification": [],
                "runtime_rejected_topics": rejeitados_runtime,
                "topic_engine_degraded": True,
                "degraded_reason": "invalid_llm_json",
            },
        )
        print("TOPIC_ENGINE_JSON_RECOVERY=FALLBACK_OK")
        raise SystemExit(0)
    sys.exit("ERRO: JSON inválido e fallback verificado indisponível.")

if not isinstance(dados, dict):
    sys.exit("ERRO: resposta do Topic Engine não é um objeto JSON.")
topics = dados.get("topics", [])
if not isinstance(topics, list):
    sys.exit("ERRO: campo topics inválido.")
if len(topics) < 8:
    print(
        "AVISO: poucos candidatos do modelo; "
        "ativando fallback verificado para evitar bloqueio."
    )
    fallback_selected = escolher_fallback_sem_llm()
    if fallback_selected:
        atomic_text(SAIDA, fallback_selected["topic"])
        atomic_json(
            VERIFICACAO,
            {
                "short_id": SHORT_ID,
                "selected": fallback_selected,
                "ranking": [fallback_selected],
                "verification": [],
                "runtime_rejected_topics": rejeitados_runtime,
                "topic_engine_degraded": True,
                "degraded_reason": "insufficient_llm_candidates",
            },
        )
        print("TOPIC_ENGINE_CANDIDATE_RECOVERY=FALLBACK_OK")
        raise SystemExit(0)
    sys.exit("ERRO: poucos candidatos e fallback verificado indisponível.")

aprovados = []
relatorio = []
pre_candidatos = []
vistos = set()

for item in topics:
    if not isinstance(item, dict):
        continue
    nome = str(item.get("topic", "")).strip()
    if not nome:
        continue

    chave = normalizar_memoria(nome) or nome.casefold()
    if chave in rejeitados_runtime_norm:
        relatorio.append({
            "topic": nome,
            "approved": False,
            "reason": "runtime_script_incompatible",
        })
        continue
    if chave in vistos:
        relatorio.append({"topic": nome, "approved": False, "reason": "duplicate_in_batch"})
        continue
    vistos.add(chave)

    duplicata = encontrar_duplicata(nome, historico, limite=0.72)
    if duplicata["duplicate"]:
        relatorio.append({
            "topic": nome,
            "approved": False,
            "reason": "duplicate",
            "similar_to": duplicata["topic"],
            "similarity": duplicata["similarity"],
        })
        continue

    curiosity = nota_segura(item.get("curiosity"))
    visual_gemini = nota_segura(item.get("visual"))
    documentation_gemini = nota_segura(item.get("documentation"))
    retention = nota_segura(item.get("retention"))
    comment_potential = nota_segura(item.get("comment_potential"))

    pre_score = (
        curiosity * 1.20
        + visual_gemini * 0.80
        + documentation_gemini * 1.10
        + retention * 1.30
        + comment_potential * 0.90
    )
    pre_candidatos.append({
        "nome": nome,
        "pre_score": pre_score,
        "scores": {
            "curiosity": curiosity,
            "visual": visual_gemini,
            "documentation": documentation_gemini,
            "retention": retention,
            "comment_potential": comment_potential,
        },
    })

pre_candidatos.sort(key=lambda x: x["pre_score"], reverse=True)
pre_candidatos = pre_candidatos[:5]
print("Verificando apenas os melhores candidatos na Wikipedia...")
print()

for numero, pre in enumerate(pre_candidatos, start=1):
    nome = pre["nome"]
    try:
        verificacao = verificar_wikipedia(nome)
    except WikiRateLimit:
        sys.exit("ERRO: Wikipedia temporariamente limitada. Tente novamente depois.")
    except Exception as exc:
        print(f"AVISO Wikipedia: {exc}")
        continue

    if not verificacao["ok"]:
        print(f"{numero:02d}. REJEITADO (sem fonte): {nome}")
        relatorio.append({"topic": nome, "approved": False, "reason": "wikipedia_not_verified"})
        continue

    scores = pre["scores"]
    curiosity = scores["curiosity"]
    visual_gemini = scores["visual"]
    documentation_gemini = scores["documentation"]
    retention = scores["retention"]
    comment_potential = scores["comment_potential"]

    visual_obj = score_visual_nome(nome)
    hook_obj = score_hook_nome(nome)
    doc_obj = score_documentacao(verificacao["chars"])
    titulo_obj = score_titulo(verificacao["similarity"])
    novidade_obj = score_novidade(nome)

    score = (
        curiosity * 1.10
        + retention * 1.20
        + comment_potential * 0.90
        + visual_gemini * 0.55
        + documentation_gemini * 0.45
        + visual_obj * 1.10
        + hook_obj * 1.15
        + doc_obj * 1.25
        + titulo_obj * 0.55
        + novidade_obj * 0.75
    )

    aprovado = {
        "topic": nome,
        "score": round(score, 2),
        "gemini": scores,
        "objective": {
            "visual": visual_obj,
            "hook": hook_obj,
            "documentation": doc_obj,
            "title_match": titulo_obj,
            "novelty": novidade_obj,
        },
        "wiki_title": verificacao["wiki_title"],
        "wiki_chars": verificacao["chars"],
        "wiki_similarity": verificacao["similarity"],
    }
    aprovados.append(aprovado)
    relatorio.append({
        "topic": nome,
        "approved": True,
        "score": round(score, 2),
        "wiki_title": verificacao["wiki_title"],
    })

    print(f"{numero:02d}. APROVADO: {nome}")
    print(f"    score viral: {score:.1f}")
    print(f"    wiki: {verificacao['wiki_title']}")
    print(f"    contexto: {verificacao['chars']} chars")

    if len(aprovados) >= 3:
        print()
        print("Já existem 3 temas verificados. Encerrando consultas à Wikipedia.")
        break

if not aprovados:
    print()
    print("Nenhum tema novo foi aprovado.")
    print("Consultando Verified Topic Reserve...")
    reserva = melhor_reserva()
    if not reserva:
        sys.exit("ERRO: nenhum tema novo aprovado e nenhuma reserva verificada disponível.")

    print()
    print("TEMA DE RESERVA ENCONTRADO:")
    print(reserva["topic"])
    print("Wikipedia:")
    print(reserva["wiki_title"])

    aprovados = [{
        "topic": reserva["topic"],
        "score": reserva["score"],
        "wiki_title": reserva["wiki_title"],
        "wiki_chars": 0,
        "wiki_similarity": 1.0,
        "gemini": {},
        "objective": {
            "visual": 0,
            "hook": 0,
            "documentation": 0,
            "title_match": 10,
            "novelty": 10,
        },
        "reserve": True,
    }]

aprovados.sort(key=lambda x: x["score"], reverse=True)
escolhido = aprovados[0]

atomic_text(SAIDA, escolhido["topic"])
atomic_json(VERIFICACAO, {
    "short_id": SHORT_ID,
    "selected": escolhido,
    "ranking": aprovados,
    "verification": relatorio,
    "runtime_rejected_topics": rejeitados_runtime,
})

print()
print("================================")
print("RANKING VIRAL")
print("================================")
print()
for numero, item in enumerate(aprovados, start=1):
    marca = " <-- ESCOLHIDO" if numero == 1 else ""
    print(f"{numero}. {item['topic']} score={item['score']:.1f}{marca}")
    print(
        f"   visual={item['objective']['visual']:.1f} "
        f"hook={item['objective']['hook']:.1f} "
        f"doc={item['objective']['documentation']:.1f} "
        f"novidade={item['objective']['novelty']:.1f}"
    )

print()
print("Assunto escolhido:")
print(escolhido["topic"])
print()
print("VIRAL TOPIC ENGINE: OK")
print()
