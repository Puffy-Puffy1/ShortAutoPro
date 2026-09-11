#!/usr/bin/env python3

import re
import unicodedata


# =====================================================
# SHORTAUTO PRO
# CASE-ANCHORED QUERY BRIDGE 5.4.1
# CONTEXT COHERENCE
# =====================================================


STOP = {
    "the", "a", "an",
    "of", "in", "on",
    "at", "with", "and",
    "or", "to", "for",
    "from", "by",

    "o", "a", "os", "as",
    "um", "uma",
    "de", "da", "do",
    "das", "dos",
    "em", "no", "na",
    "nos", "nas",
    "com", "sem",
    "para", "por",
    "e", "ou",

    "case",
    "caso",
    "disappearance",
    "desaparecimento",
    "death",
    "morte",
    "incident",
    "incidente",
    "mystery",
    "misterio",
    "crime",
    "murder",
    "assassinato",

    "cinematic",
    "dramatic",
    "dark",
    "moody",
    "vintage",
    "historic",
    "historical",
    "archive",
    "archival",
    "shot",
    "view",
    "scene",
    "close",
    "medium",
    "wide"
}


NAMED_IGNORE = {
    "dias",
    "dia",
    "em",
    "por",
    "porque",
    "quando",
    "onde",
    "como",
    "apos",
    "após",
    "antes",
    "depois",
    "durante",
    "segundo",
    "entao",
    "então",
    "mas",
    "policia",
    "polícia"
}


CONTEXT_NOUNS = {
    "hotel",
    "airport",
    "aeroporto",
    "hospital",
    "school",
    "escola",
    "university",
    "universidade",
    "station",
    "estacao",
    "building",
    "predio",
    "street",
    "rua",
    "avenue",
    "avenida",
    "lake",
    "lago",
    "river",
    "rio",
    "mount",
    "mountain",
    "ship",
    "navio"
}


TIER_RANK = {
    "CASE": 6,
    "CASE_VISUAL": 5,
    "CONTEXT_COMBINED": 5,
    "CONTEXT": 4,
    "CONTEXT_VISUAL": 3,
    "GENERIC": 1
}


# =====================================================
# NORMALIZAÇÃO
# =====================================================

def sem_acento(texto):

    texto = unicodedata.normalize(
        "NFKD",
        str(texto or "")
    )

    return "".join(
        c
        for c in texto
        if not unicodedata.combining(c)
    )


def limpar(texto):

    toks = re.findall(
        r"[A-Za-z0-9'-]+",
        sem_acento(
            texto
        )
    )

    toks = [
        x
        for x in toks
        if x.lower() not in STOP
    ]

    return " ".join(
        toks
    ).strip()


def tokenizar_ancora(texto):

    return [
        x.lower()
        for x in re.findall(
            r"[A-Za-z0-9'-]+",
            sem_acento(
                texto
            )
        )
        if (
            x.lower() not in STOP
            and len(x) >= 2
        )
    ]


# =====================================================
# ASSUNTO
# =====================================================

def entidades_do_assunto(
    assunto
):

    return limpar(
        assunto
    )


# =====================================================
# CONCEITO VISUAL
# =====================================================

def conceito_principal(
    query,
    must_have
):

    must = [
        limpar(x)
        for x in (
            must_have
            or []
        )
        if limpar(x)
    ]


    if must:

        return " ".join(
            must[:2]
        )


    q = limpar(
        query
    )

    return " ".join(
        q.split()[:4]
    )


# =====================================================
# NAMED ENTITIES
# =====================================================

def capitalizada(
    palavra
):

    if not palavra:
        return False

    primeiro = palavra[0]

    return (
        primeiro.isalpha()
        and primeiro
        == primeiro.upper()
    )


def extrair_ancoras_nomeadas(
    texto
):

    palavras = re.findall(
        r"[A-Za-zÀ-ÿ0-9'-]+",
        str(texto or "")
    )


    encontrados = []

    i = 0


    while i < len(
        palavras
    ):

        palavra = palavras[i]


        if (
            capitalizada(
                palavra
            )
            and palavra.lower()
            not in NAMED_IGNORE
        ):

            grupo = [
                palavra
            ]

            j = i + 1


            while j < len(
                palavras
            ):

                prox = palavras[j]


                if (
                    capitalizada(
                        prox
                    )
                    and prox.lower()
                    not in NAMED_IGNORE
                ):

                    grupo.append(
                        prox
                    )

                    j += 1
                    continue


                break


            encontrados.append(
                " ".join(
                    grupo
                )
            )

            i = j

        else:

            i += 1


    return encontrados


def extrair_contexto_especifico(
    query,
    segmento,
    entidade
):

    encontrados = []

    encontrados.extend(
        extrair_ancoras_nomeadas(
            query
        )
    )

    encontrados.extend(
        extrair_ancoras_nomeadas(
            segmento
        )
    )


    entidade_tokens = set(
        tokenizar_ancora(
            entidade
        )
    )


    candidatos = []
    vistos = set()


    for item in encontrados:

        item = " ".join(
            str(item).split()
        ).strip()


        toks = set(
            tokenizar_ancora(
                item
            )
        )


        if not toks:
            continue


        # Elisa / Lam / Elisa Lam não vira
        # contexto porque já pertence ao assunto.
        if (
            entidade_tokens
            and toks.issubset(
                entidade_tokens
            )
        ):

            continue


        # Ignora palavras isoladas genéricas.
        if (
            len(toks) == 1
            and next(
                iter(toks)
            ) in NAMED_IGNORE
        ):

            continue


        chave = frozenset(
            toks
        )


        if chave in vistos:
            continue


        vistos.add(
            chave
        )

        candidatos.append(
            item
        )


    # -----------------------------------------
    # Remove âncora pequena contida numa maior.
    #
    # "Cecil" desaparece se existir
    # "Hotel Cecil".
    # -----------------------------------------

    saida = []


    for i, item in enumerate(
        candidatos
    ):

        toks = set(
            tokenizar_ancora(
                item
            )
        )

        contida = False


        for j, outra in enumerate(
            candidatos
        ):

            if i == j:
                continue


            outros = set(
                tokenizar_ancora(
                    outra
                )
            )


            if (
                toks
                and toks < outros
            ):

                contida = True
                break


        if not contida:

            saida.append(
                item
            )


    # -----------------------------------------
    # Prioridade:
    #
    # Hotel Cecil
    # Los Angeles
    # antes de palavras soltas.
    # -----------------------------------------

    def prioridade(
        item
    ):

        toks = set(
            tokenizar_ancora(
                item
            )
        )

        tem_objeto = bool(
            toks.intersection(
                CONTEXT_NOUNS
            )
        )

        multi = (
            len(toks) >= 2
        )


        return (
            int(
                tem_objeto
            ),
            int(
                multi
            ),
            len(toks)
        )


    saida.sort(
        key=prioridade,
        reverse=True
    )


    return saida[:4]


# =====================================================
# ANCHOR GROUPS
# =====================================================

def required_hits(
    toks
):

    n = len(
        toks
    )


    if n <= 0:
        return 0


    # Nome curto:
    #
    # Los Angeles => 2/2
    # Hotel Cecil => 2/2
    # Elisa Lam   => 2/2
    if n <= 2:
        return n


    return max(
        2,
        (
            2 * n
            + 2
        ) // 3
    )


def grupo_info(
    texto
):

    toks = tokenizar_ancora(
        texto
    )


    return {
        "text":
            texto,

        "tokens":
            toks,

        "required":
            required_hits(
                toks
            )
    }


# =====================================================
# GERAR PLANOS
# =====================================================

def gerar_buscas_commons_ancoradas(
    assunto,
    query,
    must_have,
    visual_mode,
    segmento=""
):

    entidade = entidades_do_assunto(
        assunto
    )

    conceito = conceito_principal(
        query,
        must_have
    )

    contexto = extrair_contexto_especifico(
        query,
        segmento,
        entidade
    )


    registros = []
    vistos = set()


    def adicionar(
        q,
        tier,
        anchors=None
    ):

        q = " ".join(
            str(q).split()
        ).strip()


        if not q:
            return


        chave = q.lower()


        if chave in vistos:
            return


        vistos.add(
            chave
        )


        anchors = [
            x
            for x in (
                anchors
                or []
            )
            if str(x).strip()
        ]


        groups = [
            grupo_info(
                x
            )
            for x in anchors
        ]


        flat = []

        for g in groups:

            flat.extend(
                g[
                    "tokens"
                ]
            )


        registros.append(
            {
                "query":
                    q,

                "tier":
                    tier,

                "tier_rank":
                    TIER_RANK.get(
                        tier,
                        0
                    ),

                "anchor_text":
                    " | ".join(
                        anchors
                    ),

                "anchor_tokens":
                    flat,

                "anchor_required":
                    sum(
                        g[
                            "required"
                        ]
                        for g in groups
                    ),

                # 5.4.1:
                # cada grupo precisa casar.
                "anchor_groups":
                    groups
            }
        )


    # =================================
    # CASE
    # =================================

    if entidade:

        adicionar(
            f'"{entidade}"',
            "CASE",
            [
                entidade
            ]
        )


    if entidade and conceito:

        adicionar(
            f'"{entidade}" {conceito}',
            "CASE_VISUAL",
            [
                entidade
            ]
        )


    # =================================
    # CONTEXTO
    # =================================

    if len(
        contexto
    ) >= 2:

        a = contexto[0]
        b = contexto[1]


        adicionar(
            f'"{a}" "{b}"',
            "CONTEXT_COMBINED",
            [
                a,
                b
            ]
        )


    for item in contexto[:2]:

        adicionar(
            f'"{item}"',
            "CONTEXT",
            [
                item
            ]
        )


    if contexto and conceito:

        adicionar(
            f'"{contexto[0]}" {conceito}',
            "CONTEXT_VISUAL",
            [
                contexto[0]
            ]
        )


    # =================================
    # GENERIC
    # =================================

    if conceito:

        adicionar(
            conceito,
            "GENERIC",
            []
        )


    return registros[:8]


# =====================================================
# COMPATIBILIDADE
# =====================================================

def gerar_buscas_commons(
    assunto,
    query,
    must_have,
    visual_mode,
    segmento=""
):

    return [
        x[
            "query"
        ]
        for x
        in gerar_buscas_commons_ancoradas(
            assunto,
            query,
            must_have,
            visual_mode,
            segmento
        )
    ]


if __name__ == "__main__":

    for numero, (
        query,
        must,
        segmento,
        mode
    ) in enumerate(
        [
            (
                "los angeles city skyline historic downtown street view 2013",
                [
                    "city",
                    "street"
                ],
                "Em fevereiro de 2013, a canadense Elisa Lam desapareceu em Los Angeles.",
                "location"
            ),
            (
                "historic Cecil hotel facade exterior building downtown Los Angeles",
                [
                    "hotel",
                    "building"
                ],
                "Dias antes, a polícia divulgou imagens dela no Hotel Cecil.",
                "architecture"
            )
        ],
        1
    ):

        print()
        print(
            f"CENA TESTE {numero}"
        )


        for item in gerar_buscas_commons_ancoradas(
            "O Desaparecimento de Elisa Lam",
            query,
            must,
            mode,
            segmento
        ):

            print(
                item
            )
