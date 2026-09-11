#!/usr/bin/env python3

import os
import json
import re
from datetime import date


# =====================================================
# SHORTAUTO PRO
# SOURCE & ATTRIBUTION MANAGER 3.7
# =====================================================

BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

CREDIT_TXT = os.path.join(
    BASE,
    "credits",
    f"short_{SHORT_ID}.txt"
)

LEDGER_JSON = os.path.join(
    BASE,
    "credits",
    f"ledger_{SHORT_ID}.json"
)

ATTRIBUTION_TXT = os.path.join(
    BASE,
    "credits",
    f"attribution_{SHORT_ID}.txt"
)

PUBLISH_JSON = os.path.join(
    BASE,
    "roteiros",
    f"publish_{SHORT_ID}.json"
)

PUBLISH_TXT = os.path.join(
    BASE,
    "roteiros",
    f"publish_{SHORT_ID}.txt"
)


os.makedirs(
    os.path.join(
        BASE,
        "credits"
    ),
    exist_ok=True
)


# =====================================================
# PARSER DOS CRÉDITOS
# =====================================================

def carregar_creditos():

    if not os.path.exists(
        CREDIT_TXT
    ):
        return []


    try:

        texto = open(
            CREDIT_TXT,
            "r",
            encoding="utf-8"
        ).read()

    except Exception:

        return []


    blocos = re.split(
        r"\n(?=SCENE\s+\d+)",
        texto.strip()
    )


    saida = []


    for bloco in blocos:

        bloco = bloco.strip()

        if not bloco:
            continue


        cena = re.search(
            r"SCENE\s+(\d+)",
            bloco
        )

        autor = re.search(
            r"Author:\s*(.*)",
            bloco
        )

        licenca = re.search(
            r"License:\s*(.*)",
            bloco
        )

        pagina = re.search(
            r"Page:\s*(.*)",
            bloco
        )


        if not pagina:
            continue


        item = {
            "scene":
                int(
                    cena.group(1)
                )
                if cena
                else 0,

            "source":
                "Wikimedia Commons",

            "author":
                autor.group(1).strip()
                if autor
                else "",

            "license":
                licenca.group(1).strip()
                if licenca
                else "",

            "page":
                pagina.group(1).strip()
        }


        saida.append(
            item
        )


    return saida


# =====================================================
# DEDUPLICAÇÃO
# =====================================================

def deduplicar(
    itens
):

    unicos = {}


    for item in itens:

        chave = (
            item.get(
                "page",
                ""
            ).strip()
        )


        if not chave:
            continue


        if chave not in unicos:

            unicos[
                chave
            ] = dict(
                item
            )

            unicos[
                chave
            ][
                "scenes"
            ] = [
                item.get(
                    "scene",
                    0
                )
            ]


        else:

            cena = item.get(
                "scene",
                0
            )

            if (
                cena
                not in unicos[
                    chave
                ][
                    "scenes"
                ]
            ):

                unicos[
                    chave
                ][
                    "scenes"
                ].append(
                    cena
                )


    return list(
        unicos.values()
    )


# =====================================================
# ATRIBUIÇÃO
# =====================================================

def precisa_atribuicao(
    licenca
):

    l = str(
        licenca
    ).lower()


    # Public Domain / CC0 não exigem
    # atribuição obrigatória, embora
    # possamos preservar a fonte no ledger.
    if (
        "public domain" in l
        or "cc0" in l
        or l.startswith("pd")
    ):

        return False


    return bool(
        l.strip()
    )


def criar_bloco(
    itens
):

    obrigatorios = [
        x
        for x in itens
        if precisa_atribuicao(
            x.get(
                "license",
                ""
            )
        )
    ]


    if not obrigatorios:
        return ""


    linhas = [
        "Créditos de mídia:"
    ]


    for item in obrigatorios:

        autor = (
            item.get(
                "author"
            )
            or "Autor não informado"
        )

        licenca = (
            item.get(
                "license"
            )
            or "Licença informada na página"
        )

        cenas = ", ".join(
            str(x)
            for x in sorted(
                item.get(
                    "scenes",
                    []
                )
            )
        )


        linhas.append(
            f"• Cenas {cenas}: "
            f"{autor} — {licenca}"
        )

        linhas.append(
            f"  {item.get('page', '')}"
        )


    return "\n".join(
        linhas
    )


# =====================================================
# EXECUÇÃO
# =====================================================

creditos = carregar_creditos()

unicos = deduplicar(
    creditos
)


ledger = {
    "short_id":
        SHORT_ID,

    "total_scene_credits":
        len(
            creditos
        ),

    "unique_assets":
        len(
            unicos
        ),

    "assets":
        unicos
}


with open(
    LEDGER_JSON,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        ledger,
        f,
        ensure_ascii=False,
        indent=2
    )


bloco = criar_bloco(
    unicos
)


with open(
    ATTRIBUTION_TXT,
    "w",
    encoding="utf-8"
) as f:

    if bloco:

        f.write(
            bloco
        )

        f.write(
            "\n"
        )


# =====================================================
# ATUALIZAR PUBLISH JSON
# =====================================================

if os.path.exists(
    PUBLISH_JSON
):

    try:

        with open(
            PUBLISH_JSON,
            "r",
            encoding="utf-8"
        ) as f:

            publish = json.load(f)


        publish[
            "media_attribution"
        ] = bloco


        publish[
            "source_ledger"
        ] = LEDGER_JSON


        with open(
            PUBLISH_JSON,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                publish,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception:

        pass


# =====================================================
# ATUALIZAR TXT PARA PUBLICAÇÃO
# =====================================================

if (
    bloco
    and os.path.exists(
        PUBLISH_TXT
    )
):

    try:

        texto = open(
            PUBLISH_TXT,
            "r",
            encoding="utf-8"
        ).read()


        marcador = (
            "\n\nCRÉDITOS DE MÍDIA:\n"
        )


        # Evita duplicação caso o módulo
        # seja executado novamente.
        if marcador in texto:

            texto = texto.split(
                marcador,
                1
            )[0]


        texto = (
            texto.rstrip()
            + marcador
            + bloco
            + "\n"
        )


        with open(
            PUBLISH_TXT,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                texto
            )

    except Exception:

        pass


# =====================================================
# TERMINAL
# =====================================================

print()
print("================================")
print("SOURCE & ATTRIBUTION MANAGER 3.7")
print("================================")
print()

print(
    f"Cenas Wikimedia: "
    f"{len(creditos)}"
)

print(
    f"Arquivos únicos: "
    f"{len(unicos)}"
)

print()


if bloco:

    print(
        "ATRIBUIÇÃO NECESSÁRIA:"
    )

    print()

    print(
        bloco
    )

else:

    if unicos:

        print(
            "Somente ativos sem atribuição "
            "obrigatória detectada "
            "(ex.: Public Domain/CC0)."
        )

    else:

        print(
            "Nenhuma mídia Wikimedia usada."
        )


print()

print(
    f"Ledger:\n{LEDGER_JSON}"
)

print()

print(
    f"Atribuição:\n{ATTRIBUTION_TXT}"
)

print()

print(
    "SOURCE LEDGER: OK"
)

print()
