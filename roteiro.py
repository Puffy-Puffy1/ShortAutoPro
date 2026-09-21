#!/usr/bin/env python3

import json
import os
import re
import sys
import time
from datetime import date

from gemini_runtime import (
    GeminiInvalidResponse,
    GeminiTemporaryUnavailable,
    generate_text,
)

from script_fallback import build_extractive_script, build_scene_queries
from source_identity import validar_identidade
from wiki_client import WikiRateLimit
from wiki_client import extract as wiki_extract_client
from wiki_client import search as wiki_search_client

BASE = os.path.abspath(os.path.expanduser(os.getenv("SHORTAUTOPRO_BASE", "~/ShortAutoPro")))
ROTEIRO_DIR = os.path.join(BASE, "roteiros")
os.makedirs(ROTEIRO_DIR, exist_ok=True)

SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
TEMA = os.getenv("SHORT_TEMA", "mistérios, casos inexplicáveis e true crime")
TOPIC_FILE = os.path.join(ROTEIRO_DIR, f"topic_{SHORT_ID}.txt")

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except ValueError:
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

GeminiGenerationUnavailable = GeminiInvalidResponse


def chamar_gemini(prompt, temperatura=0.5, tokens=1600):
    return generate_text(
        prompt,
        temperature=temperatura,
        max_output_tokens=tokens,
        component="Script Engine",
        api_key=GEMINI_KEY,
    )


def contar_palavras(texto):
    return len(
        re.findall(
            r"\b[\wÀ-ÿ'-]+\b",
            str(texto),
            flags=re.UNICODE,
        )
    )


def limpar_roteiro(texto):
    texto = (
        str(texto)
        .replace("```text", "")
        .replace("```markdown", "")
        .replace("```", "")
        .strip()
    )
    texto = re.sub(
        r"^\s*(?:roteiro)\s*:?\s*",
        "",
        texto,
        flags=re.IGNORECASE,
    )
    return texto.strip()


def limpar_assunto(texto):
    texto = (
        str(texto)
        .replace("*", "")
        .replace('"', "")
        .replace("`", "")
        .strip()
    )
    texto = re.sub(
        r"^(caso|assunto)\s*:\s*",
        "",
        texto,
        flags=re.IGNORECASE,
    )
    return texto.strip()


def atomic_text(path, text):
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(str(text))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def wiki_search(query):
    return wiki_search_client(query, limit=6)


def wiki_extract(title):
    return wiki_extract_client(title)


def variacoes_busca(assunto):
    candidatos = [
        assunto,
        re.sub(r"^(O|A|Os|As)\s+", "", assunto, flags=re.IGNORECASE),
        re.sub(r"^(O|A)\s+Caso\s+", "", assunto, flags=re.IGNORECASE),
        re.sub(r"^Caso\s+", "", assunto, flags=re.IGNORECASE),
        assunto.replace("Farol das ", "", 1),
        assunto.replace("Mistério de ", "", 1),
        assunto.replace("Mistério do ", "", 1),
        assunto.replace("Incidente de ", "", 1),
        " ".join(assunto.split()[:6]),
    ]

    saida = []
    vistos = set()
    for item in candidatos:
        item = str(item).strip()
        key = item.casefold()
        if item and key not in vistos:
            vistos.add(key)
            saida.append(item)
    return saida


def buscar_artigo(assunto):
    """Procura até achar um artigo que também passe pelo gate de identidade."""

    for consulta in variacoes_busca(assunto):
        print(f"Buscando Wikipedia: {consulta}")
        resultados = wiki_search(consulta)
        if not isinstance(resultados, list):
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

            identidade = validar_identidade(
                assunto,
                titulo,
                texto,
            )

            print(
                "  candidato:",
                titulo,
                "->",
                "PASS" if identidade.get("valid") else "REJEITADO",
                identidade.get("reason", ""),
            )

            if not identidade.get("valid"):
                continue

            return titulo, texto, identidade

    return "", "", None


print()
print("================================")
print("PESQUISA FACTUAL GRATUITA")
print("================================")
print()

assuntos_rejeitados = []
assunto = ""
titulo = ""
fonte = ""
identidade_fonte = None
assunto_preselecionado = ""

if os.path.exists(TOPIC_FILE):
    try:
        with open(TOPIC_FILE, "r", encoding="utf-8") as f:
            assunto_preselecionado = f.read().strip()
    except Exception:
        assunto_preselecionado = ""

for tentativa_assunto in range(1, 5):
    rejeitados = ", ".join(assuntos_rejeitados) if assuntos_rejeitados else "nenhum"

    if tentativa_assunto == 1 and assunto_preselecionado:
        assunto = assunto_preselecionado
        print("Usando assunto do Topic Engine.")
    else:
        prompt_assunto = f"""
Escolha UM caso REAL e documentado dentro do tema:
{TEMA}

REQUISITOS:
- precisa ser real e possuir documentação pública;
- conhecido o suficiente para provavelmente possuir artigo na Wikipedia em português;
- fatos suficientes para um Short de 30 a 45 segundos;
- não invente nomes, casos ou eventos.

NÃO escolha novamente:
{rejeitados}

Responda SOMENTE com o nome do caso ou evento.
"""
        print(f"Escolhendo assunto {tentativa_assunto}/4...")
        try:
            assunto = chamar_gemini(
                prompt_assunto,
                temperatura=0.70,
                tokens=100,
            )
        except Exception as exc:
            sys.exit(f"ERRO escolhendo assunto: {exc}")

    assunto = limpar_assunto(assunto)
    if not assunto:
        assuntos_rejeitados.append("assunto_vazio")
        continue

    print(f"Assunto escolhido: {assunto}")

    try:
        titulo, fonte, identidade_fonte = buscar_artigo(assunto)
    except WikiRateLimit:
        sys.exit("ERRO: Wikipedia temporariamente limitada. Tente novamente depois.")
    except Exception as exc:
        print(f"AVISO Wikipedia: {exc}")
        titulo, fonte, identidade_fonte = "", "", None

    if fonte and titulo and identidade_fonte and identidade_fonte.get("valid"):
        print()
        print("================================")
        print("SOURCE IDENTITY GATE 4.2")
        print("================================")
        print(f"ASSUNTO: {assunto}")
        print(f"FONTE: Wikipedia - {titulo}")
        print(f"IDENTITY SCORE: {float(identidade_fonte.get('score', 0)):.3f}")
        print(f"MOTIVO: {identidade_fonte.get('reason', '')}")
        print("SOURCE IDENTITY: PASS")
        print()
        break

    print("Fonte factual válida não encontrada. Tentando outro assunto...")
    assuntos_rejeitados.append(assunto)

if not fonte:
    sys.exit("ERRO: não consegui encontrar uma fonte factual válida após 4 assuntos.")

fonte = fonte[:16000]
print(f"Contexto recuperado: {len(fonte)} caracteres")

prompt_criacao = f"""
Você é roteirista profissional de YouTube Shorts.

ASSUNTO:
{assunto}

FONTE FACTUAL:
========================
{fonte}
========================

Use SOMENTE informações sustentadas pela fonte acima.
Não invente datas, nomes, números, locais, ferimentos, causas ou acontecimentos.
Não transforme teoria ou especulação em fato.
Se o caso envolver violência, abuso ou morte, trate de forma documental e não gráfica.
Não descreva violência sexual, tortura, ferimentos ou sofrimento em detalhes explícitos.
Quando um detalhe sensível não for necessário para compreender o caso, omita-o.

ROTEIRO:
- português do Brasil;
- entre 105 e 125 palavras REAIS;
- gancho forte na primeira frase;
- ritmo rápido e frases naturais;
- fácil para voz neural;
- CTA final curto.

Depois escreva exatamente:
CENAS:

Crie exatamente {QTD_CENAS} buscas visuais em INGLÊS, uma por linha.
Cada busca deve ter 4 a 9 palavras, acompanhar a ordem da narração e representar algo concreto.
Sem logos, interface de rede social ou CTA visual com celular.
Não numere e não use colchetes.

Responda SOMENTE:
roteiro
CENAS:
busca
busca
...
"""

roteiro = None
cenas_texto = ""
ultimo_roteiro_recebido = ""
ultimas_cenas_recebidas = ""
script_degraded = False

for tentativa in range(1, 4):
    print(f"Gerando roteiro inicial ({tentativa}/3)...")
    try:
        bruto = chamar_gemini(
            prompt_criacao,
            temperatura=0.50,
            tokens=1600,
        )
    except GeminiTemporaryUnavailable as exc:
        print(
            "SAP_SCRIPT_AI=UNAVAILABLE "
            f"{type(exc).__name__}:{str(exc)[:220]}"
        )
        roteiro = build_extractive_script(fonte)
        if not roteiro:
            sys.exit(
                "ERRO: Gemini indisponível e fallback factual local não conseguiu "
                "atingir 105-125 palavras sem cortar afirmações."
            )
        cenas_texto = build_scene_queries(assunto, QTD_CENAS, clean_topic=limpar_assunto)
        script_degraded = True
        print(
            "SAP_SCRIPT_FALLBACK=SOURCE_EXTRACTIVE_OK "
            f"words={contar_palavras(roteiro)}"
        )
        break
    except GeminiGenerationUnavailable as exc:
        print(
            "SAP_SCRIPT_AI=INVALID_RESPONSE "
            f"{type(exc).__name__}:{str(exc)[:220]}"
        )
        roteiro = build_extractive_script(fonte)
        if not roteiro:
            sys.exit(
                "ERRO: resposta Gemini inválida e fallback factual local "
                "não conseguiu atingir 105-125 palavras."
            )
        cenas_texto = build_scene_queries(assunto, QTD_CENAS, clean_topic=limpar_assunto)
        script_degraded = True
        print(
            "SAP_SCRIPT_FALLBACK=SOURCE_EXTRACTIVE_OK "
            f"words={contar_palavras(roteiro)}"
        )
        break
    except Exception as exc:
        print(
            "SAP_SCRIPT_AI=ERROR "
            f"{type(exc).__name__}:{str(exc)[:220]}"
        )
        roteiro = build_extractive_script(fonte)
        if not roteiro:
            sys.exit(f"ERRO gerando roteiro: {exc}")
        cenas_texto = build_scene_queries(assunto, QTD_CENAS, clean_topic=limpar_assunto)
        script_degraded = True
        print(
            "SAP_SCRIPT_FALLBACK=SOURCE_EXTRACTIVE_OK "
            f"words={contar_palavras(roteiro)}"
        )
        break

    bruto = (
        bruto.replace("```text", "")
        .replace("```markdown", "")
        .replace("```", "")
        .strip()
    )

    if "CENAS:" not in bruto:
        print("Formato inválido. Tentando novamente...")
        continue

    r, c = bruto.split("CENAS:", 1)
    r = limpar_roteiro(r)
    ultimo_roteiro_recebido = r
    ultimas_cenas_recebidas = c
    qtd = contar_palavras(r)
    print(f"Palavras recebidas: {qtd}")

    if 105 <= qtd <= 125:
        roteiro = r
        cenas_texto = c
        break

if not roteiro and not script_degraded:
    if not ultimo_roteiro_recebido:
        sys.exit("ERRO: Gemini não retornou roteiro reparável.")

    print("Tentativas normais ficaram fora do limite. Executando reparo final...")
    prompt_reparo = f"""
Reescreva o roteiro abaixo mantendo SOMENTE os mesmos fatos.

ROTEIRO:
{ultimo_roteiro_recebido}

REGRAS OBRIGATÓRIAS:
- entre 108 e 122 palavras REAIS;
- preserve fatos, gancho e CTA;
- não adicione informação;
- corte redundâncias;
- português do Brasil;
- responda SOMENTE com o roteiro final.
"""

    reparado = ""
    try:
        reparado = limpar_roteiro(
            chamar_gemini(
                prompt_reparo,
                temperatura=0.10,
                tokens=700,
            )
        )
    except Exception as exc:
        print(
            "SAP_SCRIPT_REPAIR=AI_FAIL "
            f"{type(exc).__name__}:{str(exc)[:220]}"
        )
        reparado = build_extractive_script(fonte)
        if reparado:
            script_degraded = True
            cenas_texto = build_scene_queries(assunto, QTD_CENAS, clean_topic=limpar_assunto)

    qtd_reparada = contar_palavras(reparado)
    print(f"Palavras após reparo: {qtd_reparada}")
    if not 105 <= qtd_reparada <= 125:
        reparado = build_extractive_script(fonte)
        if not reparado:
            sys.exit(
                f"ERRO: reparo final ainda fora do limite: {qtd_reparada} palavras "
                "e fallback factual indisponível."
            )
        script_degraded = True
        cenas_texto = build_scene_queries(assunto, QTD_CENAS, clean_topic=limpar_assunto)
        print(
            "SAP_SCRIPT_REPAIR=SOURCE_EXTRACTIVE_RECOVERY "
            f"words={contar_palavras(reparado)}"
        )

    roteiro = reparado
    if not cenas_texto:
        cenas_texto = ultimas_cenas_recebidas

print()
print("================================")
print("AUDITORIA FACTUAL")
print("================================")
print()

prompt_auditoria = f"""
Você é um auditor factual rigoroso.

FONTE:
========================
{fonte}
========================

ROTEIRO:
========================
{roteiro}
========================

Compare cada afirmação com a fonte.
- remova ou corrija informação não sustentada;
- não acrescente informação nova;
- preserve fatos documentados e atribuições;
- diferencie fato, teoria, especulação e conclusão posterior;
- preserve gancho e ritmo;
- resultado final entre 105 e 125 palavras REAIS.

Responda SOMENTE com o roteiro revisado.
"""

roteiro_auditado = roteiro if script_degraded else None

if script_degraded:
    print(
        "SAP_SCRIPT_FACT_AUDIT=SOURCE_EXTRACTIVE_BYPASS "
        "reason=script_composed_only_from_verified_source"
    )

for auditoria in range(1, 4) if not script_degraded else []:
    print(f"Auditoria {auditoria}/3...")
    try:
        revisado = limpar_roteiro(
            chamar_gemini(
                prompt_auditoria,
                temperatura=0.15,
                tokens=900,
            )
        )
    except Exception as exc:
        print(f"Falha na auditoria: {exc}")
        continue

    qtd = contar_palavras(revisado)
    print(f"Palavras após auditoria: {qtd}")
    if 105 <= qtd <= 125:
        roteiro_auditado = revisado
        break

if not roteiro_auditado:
    print(
        "SAP_SCRIPT_FACT_AUDIT=AI_EXHAUSTED "
        "action=SOURCE_EXTRACTIVE_RECOVERY"
    )
    roteiro_auditado = build_extractive_script(fonte)
    if not roteiro_auditado:
        sys.exit(
            "ERRO: auditoria factual indisponível e fallback extrativo "
            "não conseguiu produzir 105-125 palavras."
        )
    script_degraded = True
    cenas_texto = build_scene_queries(assunto, QTD_CENAS, clean_topic=limpar_assunto)

roteiro = roteiro_auditado
if script_degraded:
    print("Auditoria factual: PASS (fonte extrativa verificada)")
else:
    print("Auditoria factual: PASS")

PALAVRAS_INGLES_COMUNS = {
    "tragically", "however", "although", "meanwhile", "therefore", "apparently",
    "mysteriously", "suddenly", "eventually", "finally", "according", "despite",
    "afterwards", "later", "before", "during",
}


def detectar_ingles(texto):
    return [
        palavra
        for palavra in re.findall(r"\b[a-zA-Z]+\b", str(texto))
        if palavra.lower() in PALAVRAS_INGLES_COMUNS
    ]


ingles_detectado = detectar_ingles(roteiro)
if ingles_detectado and script_degraded:
    print(
        "SAP_SCRIPT_LANGUAGE_GUARD=DEGRADED_SKIP "
        "reason=offline_extractive_mode"
    )
elif ingles_detectado:
    print("Termos em inglês detectados: " + ", ".join(ingles_detectado))
    corrigido_final = None

    for tentativa in range(1, 3):
        prompt_idioma = f"""
Reescreva o roteiro abaixo inteiramente em português do Brasil.

ROTEIRO:
{roteiro}

REGRAS:
- preserve exatamente os mesmos fatos e sentido;
- não acrescente informação;
- traduza palavras ou expressões em inglês;
- mantenha entre 105 e 125 palavras REAIS;
- preserve gancho e CTA;
- responda SOMENTE com o roteiro corrigido.
"""
        try:
            candidato = limpar_roteiro(
                chamar_gemini(
                    prompt_idioma,
                    temperatura=0.10,
                    tokens=700,
                )
            )
        except Exception as exc:
            print(f"Falha Language Guard {tentativa}/2: {exc}")
            continue

        if 105 <= contar_palavras(candidato) <= 125 and not detectar_ingles(candidato):
            corrigido_final = candidato
            break

    if not corrigido_final:
        corrigido_final = build_extractive_script(fonte)
        if corrigido_final:
            script_degraded = True
            cenas_texto = build_scene_queries(assunto, QTD_CENAS, clean_topic=limpar_assunto)
            print("SAP_SCRIPT_LANGUAGE_GUARD=SOURCE_EXTRACTIVE_RECOVERY")
        else:
            sys.exit(
                "ERRO: Language Guard falhou e fallback factual local indisponível."
            )
    roteiro = corrigido_final
    print("Language Guard: PASS")


def avaliar_qualidade_roteiro(texto):
    score = 100
    problemas = []
    qtd = contar_palavras(texto)
    if not 105 <= qtd <= 125:
        score -= 50
        problemas.append(f"palavras={qtd}")

    frases = [x.strip() for x in re.split(r"[.!?]+", texto) if x.strip()]
    longas = [f for f in frases if contar_palavras(f) > 24]
    if longas:
        score -= min(20, len(longas) * 7)
        problemas.append(f"frases_longas={len(longas)}")

    inicio = " ".join(texto.split()[:18]).lower()
    for termo in [
        "hoje vamos", "neste vídeo", "nesse vídeo", "você sabia", "voce sabia",
        "vamos falar", "essa é a história", "essa e a historia",
    ]:
        if inicio.startswith(termo):
            score -= 20
            problemas.append("abertura_fraca")
            break

    final = " ".join(texto.split()[-20:]).lower()
    sinais_cta = [
        "comente", "qual sua opinião", "qual sua opiniao", "o que você acha",
        "o que voce acha", "siga", "curta", "inscreva",
    ]
    if not any(x in final for x in sinais_cta):
        score -= 8
        problemas.append("cta_fraco_ou_ausente")

    return max(0, score), problemas


script_score, script_problemas = avaliar_qualidade_roteiro(roteiro)
print()
print("================================")
print("SCRIPT QUALITY GATE 2.3.6")
print("================================")
print(f"Score: {script_score}/100")
if script_problemas:
    print("Observações: " + ", ".join(script_problemas))
if script_score < 70:
    print("AVISO: roteiro abaixo do padrão de qualidade; o gate final decidirá a liberação.")
else:
    print("SCRIPT QUALITY: PASS")

cenas = []
for linha in str(cenas_texto).splitlines():
    linha = linha.strip()
    if not linha:
        continue
    linha = linha.lstrip("[").rstrip("]").strip()
    linha = re.sub(r"^\s*\d+[\.\)\:\-]\s*", "", linha)
    linha = re.sub(
        r"^\s*(scene|cena)\s*\d*[\.\:\-\)]*\s*",
        "",
        linha,
        flags=re.IGNORECASE,
    )
    linha = linha.strip(' "[]')
    if linha:
        cenas.append(linha)

fallback = [
    "isolated location cinematic wide shot",
    "person walking alone dramatic lighting",
    "abandoned building dark cinematic",
    "investigation documents close up",
    "search team outdoors cinematic",
    "evidence photographs dramatic lighting",
    "isolated landscape moody cinematic",
    "investigator examining evidence close up",
    "empty location dark atmospheric shot",
    "search operation cinematic wide shot",
    "case files desk dramatic lighting",
    "mysterious landscape at night cinematic",
]

indice = 0
while len(cenas) < QTD_CENAS:
    cenas.append(fallback[indice % len(fallback)])
    indice += 1
cenas = cenas[:QTD_CENAS]

bloqueadas = [
    "phone", "smartphone", "comment", "comments", "like", "subscribe",
    "social media", "typing",
]
if any(termo in cenas[-1].lower() for termo in bloqueadas):
    cenas[-1] = "mysterious location at night cinematic"

roteiro_path = os.path.join(ROTEIRO_DIR, f"short_{SHORT_ID}.txt")
cenas_path = os.path.join(ROTEIRO_DIR, f"keywords_{SHORT_ID}.txt")
fonte_path = os.path.join(ROTEIRO_DIR, f"fonte_{SHORT_ID}.txt")

atomic_text(roteiro_path, roteiro)
atomic_text(cenas_path, "\n".join(cenas))
atomic_text(
    fonte_path,
    f"ASSUNTO: {assunto}\nFONTE: Wikipedia — {titulo}\n\n{fonte}",
)

if script_degraded:
    print("SAP_SCRIPT_MODE=DEGRADED_SOURCE_EXTRACTIVE")

print()
print("================================")
print("ROTEIRO AUDITADO PRONTO!")
print("================================")
print(f"Assunto: {assunto}")
print(f"Fonte: Wikipedia - {titulo}")
print(f"Palavras: {contar_palavras(roteiro)}")
print(f"Cenas: {len(cenas)}/{QTD_CENAS}")
print()
print(f"Roteiro:\n{roteiro_path}")
print(f"Buscas visuais:\n{cenas_path}")
print(f"Fonte factual:\n{fonte_path}")
print()
