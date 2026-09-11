#!/usr/bin/env python3

import os
import json
import glob

from topic_memory import encontrar_duplicata
from source_identity import validar_identidade


BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

ROTEIROS = os.path.join(
    BASE,
    "roteiros"
)

HISTORICO = os.path.join(
    BASE,
    "historico_assuntos.json"
)

INDEX = os.path.join(
    BASE,
    "topic_index.json"
)


# =====================================================
# HISTÓRICO
# =====================================================

def carregar_historico():

    if not os.path.exists(
        HISTORICO
    ):
        return []

    try:

        with open(
            HISTORICO,
            "r",
            encoding="utf-8"
        ) as f:

            dados = json.load(f)

        if isinstance(
            dados,
            list
        ):
            return dados

    except Exception:
        pass

    return []


# =====================================================
# ÍNDICE CENTRAL
# =====================================================

def carregar_do_indice():

    if not os.path.exists(
        INDEX
    ):
        return []

    try:

        with open(
            INDEX,
            "r",
            encoding="utf-8"
        ) as f:

            dados = json.load(f)

    except Exception:

        return []


    topics = dados.get(
        "topics",
        []
    )

    if not isinstance(
        topics,
        list
    ):
        return []


    historico = carregar_historico()

    saida = []


    for item in topics:

        if not isinstance(
            item,
            dict
        ):
            continue


        nome = str(
            item.get(
                "topic",
                ""
            )
        ).strip()

        if not nome:
            continue


        # Nunca confiar apenas no campo "used"
        # salvo no índice. Conferimos novamente
        # com o histórico atual.

        duplicata = encontrar_duplicata(
            nome,
            historico,
            limite=0.72
        )

        if duplicata[
            "duplicate"
        ]:
            continue


        wiki_title = str(
            item.get(
                "wiki_title",
                ""
            )
        ).strip()

        if not wiki_title:
            continue


        identidade = validar_identidade(
            nome,
            wiki_title
        )

        if not identidade[
            "valid"
        ]:

            continue


        try:

            score = float(
                item.get(
                    "score",
                    0
                )
            )

        except Exception:

            score = 0.0


        saida.append(
            {
                "topic":
                    nome,

                "wiki_title":
                    wiki_title,

                "score":
                    score,

                "source":
                    "topic_index"
            }
        )


    saida.sort(
        key=lambda x: x[
            "score"
        ],
        reverse=True
    )

    return saida


# =====================================================
# FALLBACK ANTIGO
# =====================================================

def carregar_dos_verified():

    historico = carregar_historico()

    arquivos = glob.glob(
        os.path.join(
            ROTEIROS,
            "topic_verified_*.json"
        )
    )

    candidatos = {}


    for arquivo in arquivos:

        try:

            with open(
                arquivo,
                "r",
                encoding="utf-8"
            ) as f:

                dados = json.load(f)

        except Exception:

            continue


        ranking = (
            dados.get(
                "ranking"
            )
            or dados.get(
                "approved"
            )
            or []
        )


        if not isinstance(
            ranking,
            list
        ):
            continue


        for item in ranking:

            if not isinstance(
                item,
                dict
            ):
                continue


            nome = str(
                item.get(
                    "topic",
                    ""
                )
            ).strip()

            if not nome:
                continue


            wiki_title = str(
                item.get(
                    "wiki_title",
                    ""
                )
            ).strip()

            if not wiki_title:
                continue


            duplicata = encontrar_duplicata(
                nome,
                historico,
                limite=0.72
            )

            if duplicata[
                "duplicate"
            ]:
                continue


            try:

                score = float(
                    item.get(
                        "score",
                        0
                    )
                )

            except Exception:

                score = 0.0


            chave = nome.lower()


            atual = candidatos.get(
                chave
            )


            if (
                atual is None
                or score > atual[
                    "score"
                ]
            ):

                candidatos[
                    chave
                ] = {
                    "topic":
                        nome,

                    "wiki_title":
                        wiki_title,

                    "score":
                        score,

                    "source":
                        os.path.basename(
                            arquivo
                        )
                }


    saida = list(
        candidatos.values()
    )

    saida.sort(
        key=lambda x: x[
            "score"
        ],
        reverse=True
    )

    return saida


# =====================================================
# RESERVA
# =====================================================

def carregar_reserva():

    # Primeiro tenta o índice central.
    candidatos = carregar_do_indice()

    if candidatos:

        return candidatos


    # Se índice estiver ausente,
    # vazio ou corrompido,
    # mantém compatibilidade com
    # os arquivos antigos.

    return carregar_dos_verified()


def melhor_reserva():

    candidatos = carregar_reserva()

    if not candidatos:
        return None

    return candidatos[0]


# =====================================================
# TESTE
# =====================================================

if __name__ == "__main__":

    candidatos = carregar_reserva()

    print()
    print("==============================")
    print("VERIFIED TOPIC RESERVE 2.2.6")
    print("==============================")
    print()


    if not candidatos:

        print(
            "Nenhum tema de reserva disponível."
        )

        raise SystemExit(0)


    for numero, item in enumerate(
        candidatos[:20],
        start=1
    ):

        print(
            f"{numero:02d}. "
            f"{item['topic']}"
        )

        print(
            f"    Wikipedia: "
            f"{item['wiki_title']}"
        )

        print(
            f"    score: "
            f"{item['score']:.1f}"
        )

        print(
            f"    origem: "
            f"{item.get('source', '?')}"
        )

        print()


    print(
        "MELHOR RESERVA:"
    )

    print(
        candidatos[0][
            "topic"
        ]
    )

    print()
