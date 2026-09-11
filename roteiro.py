#!/usr/bin/env python3

import os
import sys
import time
import re
import requests
from datetime import date

from wiki_client import search as wiki_search_client
from wiki_client import extract as wiki_extract_client
from wiki_client import WikiRateLimit

from source_identity import validar_identidade


BASE = os.path.expanduser("~/ShortAutoPro")

ROTEIRO_DIR = os.path.join(
    BASE,
    "roteiros"
)

os.makedirs(
    ROTEIRO_DIR,
    exist_ok=True
)

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

GEMINI_KEY = os.getenv(
    "GEMINI_API_KEY"
)

if not GEMINI_KEY:
    sys.exit(
        "ERRO: GEMINI_API_KEY não configurada."
    )

MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite"
)

TEMA = os.getenv(
    "SHORT_TEMA",
    "mistérios, casos inexplicáveis e true crime"
)

TOPIC_FILE = os.path.join(
    BASE,
    "roteiros",
    f"topic_{SHORT_ID}.txt"
)

try:
    QTD_CENAS = int(
        os.getenv(
            "SHORT_QTD_CENAS",
            "12"
        )
    )
except ValueError:
    QTD_CENAS = 12

QTD_CENAS = max(
    6,
    min(QTD_CENAS, 20)
)

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/{MODEL}:generateContent"
)

HEADERS = {
    "Content-Type": "application/json",
    "x-goog-api-key": GEMINI_KEY
}


# =====================================================
# GEMINI
# =====================================================

def chamar_gemini(
    prompt,
    temperatura=0.5,
    tokens=1600
):

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": temperatura,
            "maxOutputTokens": tokens
        }
    }

    for tentativa in range(1, 5):

        print(
            f"Gemini tentativa {tentativa}/4..."
        )

        try:

            r = requests.post(
                GEMINI_URL,
                headers=HEADERS,
                json=payload,
                timeout=120
            )

        except Exception as e:

            if tentativa == 4:
                raise RuntimeError(
                    str(e)
                )

            time.sleep(5)
            continue

        if r.ok:

            dados = r.json()

            try:

                return (
                    dados["candidates"][0]
                    ["content"]["parts"][0]["text"]
                    .strip()
                )

            except Exception:

                raise RuntimeError(
                    "Gemini respondeu sem texto utilizável."
                )

        if (
            r.status_code
            in [429, 500, 502, 503, 504]
            and tentativa < 4
        ):

            print(
                f"Gemini HTTP {r.status_code}. "
                "Tentando novamente..."
            )

            time.sleep(8)
            continue

        raise RuntimeError(
            f"HTTP {r.status_code}: {r.text}"
        )

    raise RuntimeError(
        "Gemini não respondeu."
    )


# =====================================================
# UTILIDADES
# =====================================================

def contar_palavras(texto):

    return len(
        re.findall(
            r"\b[\wÀ-ÿ'-]+\b",
            texto,
            flags=re.UNICODE
        )
    )


def limpar_roteiro(texto):

    texto = (
        texto
        .replace("```text", "")
        .replace("```markdown", "")
        .replace("```", "")
        .strip()
    )

    texto = re.sub(
        r"^\s*?\s*roteiro\s*?\s*:?\s*",
        "",
        texto,
        flags=re.IGNORECASE
    )

    return texto.strip()


def limpar_assunto(texto):

    texto = (
        texto
        .replace("*", "")
        .replace('"', "")
        .replace("`", "")
        .strip()
    )

    texto = re.sub(
        r"^(caso|assunto)\s*:\s*",
        "",
        texto,
        flags=re.IGNORECASE
    )

    return texto.strip()


# =====================================================
# WIKIPEDIA
# =====================================================

def wiki_search(query):

    return wiki_search_client(
        query,
        limit=6
    )


def wiki_extract(title):

    return wiki_extract_client(
        title
    )


def variacoes_busca(assunto):

    candidatos = [
        assunto,

        re.sub(
            r"^(O|A|Os|As)\s+",
            "",
            assunto,
            flags=re.IGNORECASE
        ),

        re.sub(
            r"^(O|A)\s+Caso\s+",
            "",
            assunto,
            flags=re.IGNORECASE
        ),

        re.sub(
            r"^Caso\s+",
            "",
            assunto,
            flags=re.IGNORECASE
        ),

        assunto.replace(
            "Farol das ",
            "",
            1
        ),

        assunto.replace(
            "Mistério de ",
            "",
            1
        ),

        assunto.replace(
            "Mistério do ",
            "",
            1
        ),

        assunto.replace(
            "Incidente de ",
            "",
            1
        ),

        " ".join(
            assunto.split()[:6]
        )
    ]

    saida = []

    for item in candidatos:

        item = item.strip()

        if not item:
            continue

        if item.lower() in [
            x.lower()
            for x in saida
        ]:
            continue

        saida.append(
            item
        )

    return saida


def buscar_artigo(assunto):

    for consulta in variacoes_busca(
        assunto
    ):

        print(
            f"Buscando Wikipedia: {consulta}"
        )

        resultados = wiki_search(
            consulta
        )

        if not resultados:
            continue

        for resultado in resultados:

            titulo = resultado.get(
                "title",
                ""
            )

            if not titulo:
                continue

            texto = wiki_extract(
                titulo
            )

            if len(texto) >= 700:

                return (
                    titulo,
                    texto
                )

    return (
        "",
        ""
    )


# =====================================================
# ESCOLHER ASSUNTO COM RETRY
# =====================================================

print()
print("================================")
print("PESQUISA FACTUAL GRATUITA")
print("================================")
print()

assuntos_rejeitados = []

assunto = ""
titulo = ""
fonte = ""

assunto_preselecionado = ""

if os.path.exists(TOPIC_FILE):

    try:

        with open(
            TOPIC_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            assunto_preselecionado = (
                f.read().strip()
            )

    except Exception:

        assunto_preselecionado = ""


for tentativa_assunto in range(
    1,
    5
):

    rejeitados = (
        ", ".join(
            assuntos_rejeitados
        )
        if assuntos_rejeitados
        else "nenhum"
    )

    prompt_assunto = f"""
Escolha UM caso REAL e documentado dentro do tema:

{TEMA}

REQUISITOS:

- precisa ser real;
- precisa possuir documentação pública;
- precisa ser conhecido o suficiente para provavelmente
  possuir artigo na Wikipedia em português;
- precisa ter fatos suficientes para um Short
  de aproximadamente 30 a 45 segundos;
- não invente nomes;
- não invente casos;
- não invente eventos.

NÃO escolha novamente:

{rejeitados}

Prefira casos conhecidos e bem documentados.

Responda SOMENTE com o nome do caso ou evento.

Sem explicação.
"""

    print()
    print(
        f"Escolhendo assunto "
        f"{tentativa_assunto}/4..."
    )

    if (
        tentativa_assunto == 1
        and assunto_preselecionado
    ):

        assunto = assunto_preselecionado

        print(
            "Usando assunto do Topic Engine."
        )

    else:

        try:

            assunto = chamar_gemini(
                prompt_assunto,
                temperatura=0.70,
                tokens=100
            )

        except Exception as e:

            sys.exit(
                f"ERRO escolhendo assunto: {e}"
            )

    assunto = limpar_assunto(
        assunto
    )

    print(
        f"Assunto escolhido: {assunto}"
    )

    titulo, fonte = buscar_artigo(
        assunto
    )


    # =====================================================
    # SOURCE IDENTITY GATE 4.0 - ROTEIRO
    # =====================================================

    if fonte and titulo:

        identidade_fonte = validar_identidade(
            assunto,
            titulo,
            fonte
        )

        print()
        print("================================")
        print("SOURCE IDENTITY GATE 4.0")
        print("================================")
        print()

        print(
            f"ASSUNTO: {assunto}"
        )

        print(
            f"FONTE ENCONTRADA: "
            f"Wikipedia — {titulo}"
        )

        print(
            f"IDENTITY SCORE: "
            f"{identidade_fonte['score']:.3f}"
        )

        print(
            f"MOTIVO: "
            f"{identidade_fonte['reason']}"
        )

        if not identidade_fonte[
            "valid"
        ]:

            print()
            print(
                "FONTE REJEITADA: "
                "não corresponde ao assunto."
            )

            print(
                "Descartando esta fonte "
                "e tentando outro assunto..."
            )

            fonte = ""
            titulo = ""

        else:

            print()
            print(
                "SOURCE IDENTITY: PASS"
            )

    if fonte:

        print()
        print(
            "Fonte factual encontrada:"
        )

        print(
            f"Wikipedia — {titulo}"
        )

        break

    print()
    print(
        "Fonte factual suficiente "
        "não encontrada."
    )

    print(
        "Descartando assunto e tentando outro..."
    )

    assuntos_rejeitados.append(
        assunto
    )


if not fonte:

    sys.exit(
        "ERRO: não consegui encontrar uma "
        "fonte factual após 4 assuntos."
    )


fonte = fonte[:16000]

print(
    f"Contexto recuperado: "
    f"{len(fonte)} caracteres"
)


# =====================================================
# GERAR ROTEIRO
# =====================================================

prompt_criacao = f"""
Você é roteirista profissional de YouTube Shorts.

ASSUNTO:

{assunto}

FONTE FACTUAL:

========================

{fonte}

========================

Use SOMENTE informações sustentadas
pela fonte acima.

CLASSIFIQUE MENTALMENTE:

FATO:
pode ser narrado diretamente.

DECLARAÇÃO HISTÓRICA:
preserve a atribuição.

TEORIA:
nunca apresente como fato.

CONCLUSÃO MODERNA:
deixe claro quando vier de investigação posterior.

REGRAS FACTUAIS:

- não invente datas;
- não invente nomes;
- não invente números;
- não invente locais;
- não invente ferimentos;
- não invente causas;
- não invente acontecimentos;
- não transforme teorias em fatos;
- não acrescente detalhes apenas por suspense.

REGRAS DO ROTEIRO:

- português do Brasil;
- entre 105 e 125 palavras REAIS;
- nunca menos de 105;
- nunca mais de 125;
- gancho forte na primeira frase;
- ritmo rápido;
- frases naturais;
- curiosidade progressiva;
- fácil para voz neural;
- CTA final curto.

Depois escreva exatamente:

CENAS:

Crie exatamente {QTD_CENAS}
buscas visuais em INGLÊS.

REGRAS:

- acompanhe a ordem da narração;
- 4 a 9 palavras;
- algo concreto e visível;
- pessoas, lugares, objetos ou ações;
- compatível com Pexels, Pixabay e Coverr;
- sem logos;
- sem interface de rede social;
- sem representar CTA com celular;
- última cena fecha visualmente a história.

Não numere.

Não use colchetes.

Responda SOMENTE:

roteiro

CENAS:
busca
busca
...
"""


roteiro = None
cenas_texto = None
ultimo_roteiro_recebido = ""
ultimas_cenas_recebidas = ""


for tentativa in range(
    1,
    4
):

    print()
    print(
        f"Gerando roteiro inicial "
        f"({tentativa}/3)..."
    )

    try:

        bruto = chamar_gemini(
            prompt_criacao,
            temperatura=0.50,
            tokens=1600
        )

    except Exception as e:

        sys.exit(
            f"ERRO gerando roteiro: {e}"
        )

    bruto = (
        bruto
        .replace("```text", "")
        .replace("```markdown", "")
        .replace("```", "")
        .strip()
    )

    if "CENAS:" not in bruto:

        print(
            "Formato inválido. "
            "Tentando novamente..."
        )

        continue

    r, c = bruto.split(
        "CENAS:",
        1
    )

    r = limpar_roteiro(
        r
    )

    qtd = contar_palavras(
        r
    )

    ultimo_roteiro_recebido = r
    ultimas_cenas_recebidas = c

    print(
        f"Palavras recebidas: {qtd}"
    )

    if 105 <= qtd <= 125:

        roteiro = r
        cenas_texto = c

        break

    print(
        "Quantidade fora do limite. "
        "Tentando novamente..."
    )


if not roteiro:

    print()
    print(
        "Tentativas normais ficaram fora do limite."
    )

    print(
        "Executando reparo final de tamanho..."
    )

    # Gera uma última versão de forma mais rígida.
    prompt_reparo = f"""
Reescreva o roteiro abaixo mantendo SOMENTE os mesmos fatos.

ROTEIRO:

{{r}}

REGRAS OBRIGATÓRIAS:

- entre 108 e 122 palavras REAIS;
- preserve os fatos;
- preserve o gancho;
- preserve o CTA;
- não adicione informação;
- não invente nada;
- corte palavras e frases redundantes;
- português do Brasil;
- responda SOMENTE com o roteiro final.
"""

    try:

        reparado = chamar_gemini(
            prompt_reparo,
            temperatura=0.10,
            tokens=700
        )

        reparado = limpar_roteiro(
            reparado
        )

        qtd_reparada = contar_palavras(
            reparado
        )

        print(
            f"Palavras após reparo: "
            f"{qtd_reparada}"
        )

        if 105 <= qtd_reparada <= 125:

            roteiro = reparado
            cenas_texto = ultimas_cenas_recebidas

        else:

            sys.exit(
                "ERRO: reparo final ainda ficou "
                f"fora do limite: {qtd_reparada} palavras."
            )

    except Exception as e:

        sys.exit(
            f"ERRO no reparo final do roteiro: {e}"
        )


# =====================================================
# AUDITORIA FACTUAL
# =====================================================

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

REGRAS:

- remova ou corrija informação não sustentada;
- não acrescente informação nova;
- preserve fatos documentados;
- preserve atribuições;
- diferencie fato, teoria e especulação;
- diferencie teoria de conclusão moderna;
- não transforme especulação em fato;
- preserve gancho e ritmo;
- resultado final entre 105 e 125 palavras REAIS.

Responda SOMENTE com o roteiro revisado.

Sem explicações.
Sem títulos.
"""


roteiro_auditado = None


for auditoria in range(
    1,
    4
):

    print(
        f"Auditoria {auditoria}/3..."
    )

    try:

        revisado = chamar_gemini(
            prompt_auditoria,
            temperatura=0.15,
            tokens=900
        )

    except Exception as e:

        print(
            f"Falha na auditoria: {e}"
        )

        continue

    revisado = limpar_roteiro(
        revisado
    )

    qtd = contar_palavras(
        revisado
    )

    print(
        f"Palavras após auditoria: {qtd}"
    )

    if 105 <= qtd <= 125:

        roteiro_auditado = revisado

        print(
            "Auditoria factual: OK"
        )

        break

    print(
        "Auditoria saiu do limite. "
        "Tentando novamente..."
    )


if roteiro_auditado:

    roteiro = roteiro_auditado

else:

    print(
        "AVISO: auditor não manteve "
        "o limite."
    )

    print(
        "Usando roteiro inicial validado."
    )



# =====================================================
# LANGUAGE GUARD 2.3.2
# =====================================================

PALAVRAS_INGLES_COMUNS = {
    "tragically",
    "however",
    "although",
    "meanwhile",
    "therefore",
    "apparently",
    "mysteriously",
    "suddenly",
    "eventually",
    "finally",
    "according",
    "despite",
    "afterwards",
    "later",
    "before",
    "during"
}


def detectar_ingles(texto):

    palavras = re.findall(
        r"\b[a-zA-Z]+\b",
        texto
    )

    encontrados = []

    for palavra in palavras:

        p = palavra.lower()

        if p in PALAVRAS_INGLES_COMUNS:
            encontrados.append(
                palavra
            )

    return encontrados


ingles_detectado = detectar_ingles(
    roteiro
)


if ingles_detectado:

    print()
    print("================================")
    print("LANGUAGE GUARD")
    print("================================")
    print()

    print(
        "Termos em inglês detectados: "
        + ", ".join(
            ingles_detectado
        )
    )

    prompt_idioma = f"""
Reescreva o roteiro abaixo inteiramente em português do Brasil.

ROTEIRO:

{roteiro}

REGRAS:

- preserve exatamente os mesmos fatos;
- preserve o mesmo sentido;
- não acrescente informação;
- não remova fatos importantes;
- traduza qualquer palavra ou expressão em inglês;
- mantenha entre 105 e 125 palavras REAIS;
- preserve gancho e CTA;
- responda SOMENTE com o roteiro corrigido.
"""

    try:

        corrigido = chamar_gemini(
            prompt_idioma,
            temperatura=0.10,
            tokens=700
        )

        corrigido = limpar_roteiro(
            corrigido
        )

        qtd_corrigida = contar_palavras(
            corrigido
        )

        ingles_restante = detectar_ingles(
            corrigido
        )

        print(
            f"Palavras após correção: "
            f"{qtd_corrigida}"
        )

        if (
            105 <= qtd_corrigida <= 125
            and not ingles_restante
        ):

            roteiro = corrigido

            print(
                "Language Guard: OK"
            )

        else:

            print(
                "AVISO: correção de idioma "
                "não passou na validação."
            )

            print(
                "Mantendo roteiro auditado."
            )

    except Exception as e:

        print(
            f"AVISO Language Guard: {e}"
        )

        print(
            "Mantendo roteiro auditado."
        )


# =====================================================
# SCRIPT QUALITY GATE 2.3.5
# =====================================================

def avaliar_qualidade_roteiro(texto):

    score = 100
    problemas = []

    qtd = contar_palavras(
        texto
    )

    if not 105 <= qtd <= 125:

        score -= 50
        problemas.append(
            f"palavras={qtd}"
        )


    frases = [
        x.strip()
        for x in re.split(
            r"[.!?]+",
            texto
        )
        if x.strip()
    ]


    # Frases muito longas prejudicam
    # TTS e ritmo de Shorts.
    longas = [
        f
        for f in frases
        if contar_palavras(f) > 24
    ]

    if longas:

        score -= min(
            20,
            len(longas) * 7
        )

        problemas.append(
            f"frases_longas={len(longas)}"
        )


    inicio = " ".join(
        texto.split()[:18]
    ).lower()


    aberturas_fracas = [
        "hoje vamos",
        "neste vídeo",
        "nesse vídeo",
        "você sabia",
        "voce sabia",
        "vamos falar",
        "essa é a história",
        "essa e a historia"
    ]


    for termo in aberturas_fracas:

        if inicio.startswith(
            termo
        ):

            score -= 20

            problemas.append(
                "abertura_fraca"
            )

            break


    # CTA final
    final = " ".join(
        texto.split()[-20:]
    ).lower()


    sinais_cta = [
        "comente",
        "qual sua opinião",
        "qual sua opiniao",
        "o que você acha",
        "o que voce acha",
        "siga",
        "curta",
        "inscreva"
    ]


    if not any(
        x in final
        for x in sinais_cta
    ):

        score -= 8
        problemas.append(
            "cta_fraco_ou_ausente"
        )


    return (
        max(
            0,
            score
        ),
        problemas
    )


script_score, script_problemas = (
    avaliar_qualidade_roteiro(
        roteiro
    )
)


print()
print("================================")
print("SCRIPT QUALITY GATE 2.3.5")
print("================================")
print()

print(
    f"Score: {script_score}/100"
)


if script_problemas:

    print(
        "Observações: "
        + ", ".join(
            script_problemas
        )
    )


if script_score < 70:

    print(
        "AVISO: roteiro abaixo do padrão."
    )

    print(
        "Mantendo o roteiro porque ele já "
        "passou pela auditoria factual."
    )

else:

    print(
        "SCRIPT QUALITY: PASS"
    )

# =====================================================
# PROCESSAR CENAS
# =====================================================

cenas = []

for linha in cenas_texto.splitlines():

    linha = linha.strip()

    if not linha:
        continue

    linha = (
        linha
        .lstrip("[")
        .rstrip("]")
        .strip()
    )

    linha = re.sub(
        r"^\s*\d+[\.\)\:\-]\s*",
        "",
        linha
    )

    linha = re.sub(
        r"^\s*(scene|cena)\s*\d*"
        r"[\.\:\-\)]*\s*",
        "",
        linha,
        flags=re.IGNORECASE
    )

    linha = linha.strip(
        ' "[]'
    )

    if linha:
        cenas.append(
            linha
        )


# =====================================================
# FALLBACK VISUAL
# =====================================================

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
    "mysterious landscape at night cinematic"
]


indice = 0

while len(cenas) < QTD_CENAS:

    cenas.append(
        fallback[
            indice
            % len(fallback)
        ]
    )

    indice += 1


cenas = cenas[:QTD_CENAS]


# =====================================================
# EVITAR ÚLTIMA CENA DE CTA
# =====================================================

bloqueadas = [
    "phone",
    "smartphone",
    "comment",
    "comments",
    "like",
    "subscribe",
    "social media",
    "typing"
]


if any(
    termo in cenas[-1].lower()
    for termo in bloqueadas
):

    cenas[-1] = (
        "mysterious location at night cinematic"
    )


# =====================================================
# SALVAR
# =====================================================

roteiro_path = os.path.join(
    ROTEIRO_DIR,
    f"short_{SHORT_ID}.txt"
)

cenas_path = os.path.join(
    ROTEIRO_DIR,
    f"keywords_{SHORT_ID}.txt"
)

fonte_path = os.path.join(
    ROTEIRO_DIR,
    f"fonte_{SHORT_ID}.txt"
)


with open(
    roteiro_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        roteiro
    )


with open(
    cenas_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "\n".join(cenas)
    )


with open(
    fonte_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        f"ASSUNTO: {assunto}\n"
    )

    f.write(
        f"FONTE: Wikipedia — {titulo}\n\n"
    )

    f.write(
        fonte
    )


# =====================================================
# RESULTADO
# =====================================================

print()
print("================================")
print("ROTEIRO AUDITADO PRONTO!")
print("================================")
print()

print(
    f"Assunto: {assunto}"
)

print(
    f"Fonte: Wikipedia — {titulo}"
)

print(
    f"Palavras: "
    f"{contar_palavras(roteiro)}"
)

print()

print(
    roteiro
)

print()
print("================================")
print("DIREÇÃO VISUAL")
print("================================")
print()


for numero, cena in enumerate(
    cenas,
    start=1
):

    print(
        f"{numero:02d}. {cena}"
    )


print()

print(
    f"Cenas: "
    f"{len(cenas)}/{QTD_CENAS}"
)

print()

print(
    f"Roteiro:\n{roteiro_path}"
)

print()

print(
    f"Buscas visuais:\n{cenas_path}"
)

print()

print(
    f"Fonte factual:\n{fonte_path}"
)

print()
