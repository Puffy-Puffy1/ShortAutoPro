#!/usr/bin/env python3

import os
import sys
import json
import re
import time
import shutil
import requests
from datetime import date


BASE = os.path.expanduser("~/ShortAutoPro")

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
)

MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite"
)

MAPA = os.path.join(
    BASE,
    "roteiros",
    f"scene_map_{SHORT_ID}.json"
)

BACKUP = os.path.join(
    BASE,
    "roteiros",
    f"scene_map_pre_visual_{SHORT_ID}.json"
)

REPORT = os.path.join(
    BASE,
    "roteiros",
    f"visual_director_{SHORT_ID}.json"
)


if not os.path.exists(MAPA):
    sys.exit(
        f"ERRO: scene_map não encontrado:\n{MAPA}"
    )


if not API_KEY:
    sys.exit(
        "ERRO: GEMINI_API_KEY não configurada."
    )


# =====================================================
# LEITURA
# =====================================================

try:

    with open(
        MAPA,
        "r",
        encoding="utf-8"
    ) as f:

        original = json.load(f)

except Exception as e:

    sys.exit(
        f"ERRO lendo scene_map: {e}"
    )


cenas_originais = original.get(
    "scenes",
    []
)


if len(cenas_originais) != 12:

    sys.exit(
        f"ERRO: esperado 12 cenas; "
        f"recebido {len(cenas_originais)}."
    )


# Backup automático antes de qualquer alteração.

shutil.copy2(
    MAPA,
    BACKUP
)


# =====================================================
# NORMALIZAÇÃO
# =====================================================

def texto_limpo(texto):

    return " ".join(
        str(texto)
        .replace("\n", " ")
        .split()
    )


def lista_limpa(valor):

    if not isinstance(
        valor,
        list
    ):
        return []

    saida = []

    for item in valor:

        item = texto_limpo(
            item
        ).lower()

        if (
            item
            and item not in saida
        ):
            saida.append(
                item
            )

    return saida


def tokens(texto):

    return set(
        re.findall(
            r"[a-z0-9]+",
            str(texto).lower()
        )
    )


# =====================================================
# OBJETOS VISUAIS IMPORTANTES
# =====================================================

OBJETOS = {
    "avião": "airplane",
    "aviao": "airplane",
    "aeronave": "airplane",

    "helicóptero": "helicopter",
    "helicoptero": "helicopter",

    "navio": "ship",
    "barco": "boat",

    "carro": "car",
    "veículo": "vehicle",
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
    "relatório": "document",
    "relatorio": "document",

    "câmera": "security camera",
    "camera": "security camera",

    "polícia": "police",
    "policia": "police",

    "corpo": "body",

    "rugby": "rugby team",
}


def objetos_do_segmento(
    segmento
):

    lower = str(
        segmento
    ).lower()

    saida = []

    for pt, en in OBJETOS.items():

        if pt in lower:

            if en not in saida:
                saida.append(
                    en
                )

    return saida


# =====================================================
# DETECTOR DE PLANO
# =====================================================

SHOT_TERMS = {
    "aerial",
    "close up",
    "wide shot",
    "medium shot",
    "portrait",
    "interior",
    "exterior",
    "overhead",
    "macro",
    "silhouette",
    "document",
    "security footage",
    "drone",
    "landscape"
}


def detectar_plano(
    query
):

    q = str(
        query
    ).lower()

    encontrados = [
        x
        for x in SHOT_TERMS
        if x in q
    ]

    if encontrados:
        return encontrados[0]

    return "generic"


# =====================================================
# SCORE LOCAL DO MAPA
# =====================================================


# =====================================================
# DOCUMENTARY INTEGRITY GUARD 3.1.1
# =====================================================

TERMOS_RETRATO = {
    "portrait",
    "headshot",
    "face",
    "man portrait",
    "woman portrait"
}


def segmento_tem_nome_proprio(
    segmento
):

    palavras = str(
        segmento
    ).split()

    maiusculas = [
        p.strip(".,;:!?()[]")
        for p in palavras
        if (
            len(p) > 2
            and p[:1].isupper()
        )
    ]

    # Ignora primeira palavra da frase.
    return len(
        maiusculas
    ) >= 2


def proteger_retrato_generico(
    segmento,
    query,
    must_have
):

    q = str(
        query
    ).lower()

    if not segmento_tem_nome_proprio(
        segmento
    ):
        return (
            query,
            must_have,
            False
        )


    if not any(
        termo in q
        for termo in TERMOS_RETRATO
    ):

        return (
            query,
            must_have,
            False
        )


    nova_query = (
        "vintage archival case documents "
        "and partially visible old photograph"
    )

    novo_must = [
        "document",
        "photograph"
    ]


    return (
        nova_query,
        novo_must,
        True
    )


def avaliar_cena(
    cena
):

    segmento = texto_limpo(
        cena.get(
            "segment",
            ""
        )
    )

    query = texto_limpo(
        cena.get(
            "query",
            ""
        )
    )

    must = lista_limpa(
        cena.get(
            "must_have",
            []
        )
    )

    avoid = lista_limpa(
        cena.get(
            "avoid",
            []
        )
    )


    score = 100
    problemas = []


    if not segmento:

        score -= 50
        problemas.append(
            "segmento_vazio"
        )


    if len(query.split()) < 4:

        score -= 25
        problemas.append(
            "query_generica"
        )


    if not must:

        score -= 25
        problemas.append(
            "sem_must"
        )


    objetos = objetos_do_segmento(
        segmento
    )


    if objetos:

        must_text = " ".join(
            must
        )

        encontrados = sum(
            1
            for obj in objetos
            if obj in must_text
        )


        if encontrados == 0:

            score -= 30

            problemas.append(
                "objeto_principal_ausente"
            )


    if len(avoid) == 0:

        score -= 5

        problemas.append(
            "sem_avoid"
        )


    return {
        "score":
            max(
                0,
                score
            ),

        "problems":
            problemas,

        "objects":
            objetos,

        "shot":
            detectar_plano(
                query
            )
    }


# =====================================================
# MAPA PARA GEMINI
# =====================================================

entrada = []


for cena in cenas_originais:

    avaliacao = avaliar_cena(
        cena
    )

    entrada.append(
        {
            "scene":
                cena.get(
                    "scene"
                ),

            "segment":
                texto_limpo(
                    cena.get(
                        "segment",
                        ""
                    )
                ),

            "current_query":
                texto_limpo(
                    cena.get(
                        "query",
                        ""
                    )
                ),

            "current_must":
                lista_limpa(
                    cena.get(
                        "must_have",
                        []
                    )
                ),

            "current_avoid":
                lista_limpa(
                    cena.get(
                        "avoid",
                        []
                    )
                ),

            "local_score":
                avaliacao[
                    "score"
                ],

            "local_problems":
                avaliacao[
                    "problems"
                ]
        }
    )


# =====================================================
# GEMINI
# =====================================================

URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/{MODEL}:generateContent"
)

HEADERS = {
    "Content-Type":
        "application/json",

    "x-goog-api-key":
        API_KEY
}


prompt = f"""
Você é diretor visual profissional de vídeos documentais
verticais para YouTube Shorts.

Você receberá EXATAMENTE 12 cenas.

Sua função NÃO é alterar o roteiro.

Sua função é melhorar SOMENTE:

query
must_have
avoid

OBJETIVO:

Cada mídia encontrada deve representar visualmente
a frase narrada naquele momento.

REGRAS IMPORTANTES:

1. Identifique primeiro o OBJETO PRINCIPAL da frase.

Exemplo:

"O avião transportava uma equipe de rugby."

ERRADO:
rugby players running

CERTO:
vintage passenger airplane carrying rugby team

O AVIÃO é o objeto principal.
Rugby é contexto secundário.

2. must_have deve conter os elementos mais importantes.

3. avoid deve bloquear resultados visualmente errados.

4. Não invente pessoas, objetos ou locais que não
estejam justificados pela frase.

5. Não transformar teoria em fato.

5B. NÃO ACRESCENTE NOVOS FATOS.

Você pode tornar a busca mais visual e específica,
mas não pode adicionar conteúdo que não esteja
presente no segmento ou na direção recebida.

Exemplos proibidos:

- adicionar "political opinion" se a frase só fala
  de um jornal;
- adicionar crime, suspeito, arma, sangue ou causa
  quando isso não aparece no segmento;
- adicionar nacionalidade, profissão ou identidade
  não sustentada.

O Visual Director deve REFINAR a representação,
não reinterpretar o fato.

5C. PESSOAS REAIS E RETRATOS.

Quando a cena mencionar uma pessoa real específica:

- não procure um retrato genérico que possa parecer
  ser a pessoa real;
- prefira documento, fotografia antiga parcialmente
  visível, silhueta, arquivo, jornal ou contexto;
- só use "portrait of man/woman" se o segmento estiver
  falando genericamente de uma pessoa e não de uma
  identidade específica;
- não invente aparência física.

Quando a frase envolver alegação, teoria, relato não confirmado,
paranormal, UFO ou causa controversa:

- NÃO represente a alegação como fato visual;
- prefira luzes, sombras, ambiente, céu, documentos ou testemunho contextual;
- não use disco voador, alienígena, fantasma ou entidade visível,
  salvo se o roteiro estiver falando explicitamente de uma representação fictícia;
- termos como "UFO", "alien spacecraft", "ghost" e "paranormal entity"
  não devem aparecer na query como objeto factual;
- use formulações ambíguas como "unidentified light",
  "mysterious light", "shadow" ou "unexplained object in distance".

6. Para fatos históricos, prefira aparência compatível
com a época quando isso for relevante.

7. Buscas devem estar EM INGLÊS porque serão usadas
em bancos de mídia.

8. Cada query deve conter de 5 a 12 palavras.

9. must_have deve conter entre 1 e 3 itens.

10. avoid deve conter entre 2 e 4 itens.

11. Varie visualmente as cenas.

Evite sequência como:

mountain landscape
mountain landscape
mountain landscape
mountain landscape

Prefira alternar quando fizer sentido:

wide environment
object close-up
people/context
document/evidence
environment
rescue/action

12. Relevância é mais importante que movimento.

13. Não use nomes de pessoas como principal termo
de busca quando bancos de mídia provavelmente não
terão a pessoa real. Use representação contextual.

14. Preserve EXATAMENTE os números das cenas.

CENAS ATUAIS:

{json.dumps(
    entrada,
    ensure_ascii=False,
    indent=2
)}

RESPONDA SOMENTE JSON VÁLIDO:

{{
  "scenes": [
    {{
      "scene": 1,
      "query": "english visual search",
      "must_have": [
        "object"
      ],
      "avoid": [
        "wrong object",
        "wrong environment"
      ],
      "shot_type": "wide shot",
      "reason": "short explanation"
    }}
  ]
}}

EXATAMENTE 12 cenas.
Sem markdown.
Sem comentários fora do JSON.
"""


payload = {
    "contents": [
        {
            "parts": [
                {
                    "text":
                        prompt
                }
            ]
        }
    ],

    "generationConfig": {
        "temperature":
            0.25,

        "maxOutputTokens":
            4500
    }
}


resposta = None


print()
print("================================")
print("VISUAL DIRECTOR PASS - STABLE 3.0")
print("================================")
print()


for tentativa in range(
    1,
    4
):

    print(
        f"Visual Director tentativa "
        f"{tentativa}/3..."
    )


    try:

        r = requests.post(
            URL,
            headers=HEADERS,
            json=payload,
            timeout=120
        )

    except Exception as e:

        if tentativa == 3:

            sys.exit(
                f"ERRO Visual Director: {e}"
            )

        time.sleep(
            4
        )

        continue


    if r.ok:

        try:

            resposta = (
                r.json()
                ["candidates"][0]
                ["content"]
                ["parts"][0]
                ["text"]
                .strip()
            )

            break

        except Exception:

            pass


    if (
        r.status_code
        in [
            429,
            500,
            502,
            503,
            504
        ]
        and tentativa < 3
    ):

        time.sleep(
            6
        )

        continue


    sys.exit(
        f"ERRO Visual Director HTTP "
        f"{r.status_code}"
    )


if not resposta:

    sys.exit(
        "ERRO: Visual Director sem resposta."
    )


resposta = (
    resposta
    .replace(
        "```json",
        ""
    )
    .replace(
        "```",
        ""
    )
    .strip()
)


try:

    novo = json.loads(
        resposta
    )

except Exception:

    sys.exit(
        "ERRO: Visual Director retornou "
        "JSON inválido."
    )


novas_cenas = novo.get(
    "scenes",
    []
)


# =====================================================
# VALIDAÇÃO RÍGIDA
# =====================================================

if len(
    novas_cenas
) != 12:

    sys.exit(
        f"ERRO: Visual Director retornou "
        f"{len(novas_cenas)} cenas."
    )


por_numero = {}


for item in novas_cenas:

    if not isinstance(
        item,
        dict
    ):

        continue


    try:

        numero = int(
            item.get(
                "scene"
            )
        )

    except Exception:

        continue


    por_numero[
        numero
    ] = item


if set(
    por_numero.keys()
) != set(
    range(
        1,
        13
    )
):

    sys.exit(
        "ERRO: numeração das cenas inválida."
    )


# =====================================================
# CONSTRUIR NOVO MAPA
# =====================================================

resultado_cenas = []

relatorio = []


for original_scene in cenas_originais:

    numero = int(
        original_scene[
            "scene"
        ]
    )

    melhoria = por_numero[
        numero
    ]


    query = texto_limpo(
        melhoria.get(
            "query",
            ""
        )
    )

    must = lista_limpa(
        melhoria.get(
            "must_have",
            []
        )
    )

    avoid = lista_limpa(
        melhoria.get(
            "avoid",
            []
        )
    )


    # ---------------------------------
    # SEGURANÇA
    # ---------------------------------

    if not (
        4
        <= len(
            query.split()
        )
        <= 15
    ):

        query = texto_limpo(
            original_scene.get(
                "query",
                ""
            )
        )


    if not (
        1
        <= len(must)
        <= 3
    ):

        must = lista_limpa(
            original_scene.get(
                "must_have",
                []
            )
        )


    if not (
        1
        <= len(avoid)
        <= 5
    ):

        avoid = lista_limpa(
            original_scene.get(
                "avoid",
                []
            )
        )


    nova_scene = dict(
        original_scene
    )


    antes = avaliar_cena(
        original_scene
    )


    query, must, retrato_protegido = (
        proteger_retrato_generico(
            original_scene.get(
                "segment",
                ""
            ),
            query,
            must
        )
    )

    nova_scene[
        "query"
    ] = query

    nova_scene[
        "must_have"
    ] = must

    nova_scene[
        "avoid"
    ] = avoid


    depois = avaliar_cena(
        nova_scene
    )


    resultado_cenas.append(
        nova_scene
    )


    relatorio.append(
        {
            "scene":
                numero,

            "before_score":
                antes[
                    "score"
                ],

            "after_score":
                depois[
                    "score"
                ],

            "before_query":
                original_scene.get(
                    "query",
                    ""
                ),

            "after_query":
                query,

            "must_have":
                must,

            "avoid":
                avoid,

            "shot_type":
                texto_limpo(
                    melhoria.get(
                        "shot_type",
                        ""
                    )
                ),

            "reason":
                texto_limpo(
                    melhoria.get(
                        "reason",
                        ""
                    )
                )
        }
    )


# =====================================================
# DIVERSIDADE DE PLANOS
# =====================================================

shots = [
    detectar_plano(
        x[
            "query"
        ]
    )
    for x in resultado_cenas
]


repeticoes = 0


for i in range(
    1,
    len(shots)
):

    if (
        shots[i]
        == shots[i - 1]
        and shots[i] != "generic"
    ):

        repeticoes += 1


# =====================================================
# SALVAR
# =====================================================

mapa_final = dict(
    original
)

mapa_final[
    "scenes"
] = resultado_cenas

mapa_final[
    "visual_director"
] = {
    "version":
        "3.0",

    "applied":
        True,

    "consecutive_shot_repetitions":
        repeticoes
}


with open(
    MAPA,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        mapa_final,
        f,
        ensure_ascii=False,
        indent=2
    )


with open(
    REPORT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        {
            "short_id":
                SHORT_ID,

            "backup":
                BACKUP,

            "shot_repetitions":
                repeticoes,

            "scenes":
                relatorio
        },
        f,
        ensure_ascii=False,
        indent=2
    )


# =====================================================
# TERMINAL
# =====================================================

print()
print("DIREÇÃO VISUAL REFINADA:")
print()


for item in relatorio:

    print(
        f"{item['scene']:02d}. "
        f"{item['after_query']}"
    )

    print(
        "    MUST: "
        + ", ".join(
            item[
                "must_have"
            ]
        )
    )

    print(
        "    AVOID: "
        + ", ".join(
            item[
                "avoid"
            ]
        )
    )

    print(
        f"    score "
        f"{item['before_score']} "
        f"-> {item['after_score']}"
    )


print()

print(
    f"Repetições consecutivas "
    f"de plano: {repeticoes}"
)

print()

print(
    f"Backup original:\n"
    f"{BACKUP}"
)

print()

print(
    f"Relatório:\n"
    f"{REPORT}"
)

print()

print(
    "VISUAL DIRECTOR PASS: OK"
)
