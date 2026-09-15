#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

echo
echo "======================================"
echo " VI6.7 RETRIEVAL INTELLIGENCE"
echo " INSTALAÇÃO OFFLINE"
echo "======================================"
echo

# =====================================================
# PRÉ-CHECK
# =====================================================

if [ ! -f vi6_6_active_brain.py ]; then
    echo "ERRO: vi6_6_active_brain.py não encontrado."
    echo "VI6.6 Standalone precisa existir primeiro."
    echo "NENHUMA ALTERAÇÃO FOI FEITA."
    exit 2
fi

if ! grep -q 'supervisionar_vi6_6' midia.py; then
    echo "ERRO: VI6.6 não está integrado ao midia.py."
    echo "NENHUMA ALTERAÇÃO FOI FEITA."
    exit 3
fi

STAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p backups/stable_release_ready

BACKUP_MIDIA="backups/stable_release_ready/midia_pre_vi67_${STAMP}.py"

cp midia.py "$BACKUP_MIDIA" || exit 1

OLD_PLANNER=""

if [ -f vi6_7_retrieval_planner.py ]; then

    OLD_PLANNER="backups/stable_release_ready/vi6_7_retrieval_planner_${STAMP}.py"

    cp vi6_7_retrieval_planner.py \
       "$OLD_PLANNER"
fi


rollback() {

    echo
    echo "======================================"
    echo " VI6.7 ROLLBACK"
    echo "======================================"

    cp "$BACKUP_MIDIA" midia.py

    if [ -n "$OLD_PLANNER" ] && \
       [ -f "$OLD_PLANNER" ]; then

        cp "$OLD_PLANNER" \
           vi6_7_retrieval_planner.py

    else

        rm -f vi6_7_retrieval_planner.py
    fi

    rm -f testar_vi67_offline.py

    echo "Projeto restaurado."
}


# =====================================================
# RETRIEVAL PLANNER 6.7
# =====================================================

cat > vi6_7_retrieval_planner.py <<'PY'
#!/usr/bin/env python3

import copy
import os
import re


# =====================================================
# VISUAL INTELLIGENCE 6.7
# RETRIEVAL INTELLIGENCE
#
# Atua ANTES da busca de mídia.
#
# Objetivos:
#
# - transformar query genérica em query factual;
# - preservar identidade do caso;
# - preservar números importantes;
# - preservar anos importantes;
# - reforçar entidades nomeadas;
# - evitar retratos genéricos;
# - evitar lugares genéricos;
# - priorizar evidência nas cenas factuais;
# - não estragar cenas contextuais boas;
# - não modificar texto narrado.
#
# NÃO chama APIs.
# NÃO baixa.
# NÃO renderiza.
# =====================================================


VERSION = "6.7"


STOP = {

    "the",
    "and",
    "for",
    "with",
    "from",
    "into",
    "this",
    "that",
    "real",

    "uma",
    "um",

    "de",
    "da",
    "do",
    "das",
    "dos",

    "em",
    "no",
    "na",
    "nos",
    "nas",

    "com",
    "para",
    "por",

    "foto",
    "imagem",
    "video",
    "vídeo",

    "image",
    "photo",

    "real",
    "true",

    "story",
    "historia",
    "história"
}


GENERIC_VISUAL = {

    "man",
    "woman",
    "person",
    "people",
    "family",
    "child",
    "girl",
    "boy",

    "homem",
    "mulher",
    "pessoa",
    "pessoas",
    "familia",
    "família",
    "crianca",
    "criança",
    "menina",
    "menino",

    "city",
    "street",
    "building",
    "room",

    "cidade",
    "rua",
    "predio",
    "prédio",
    "sala",

    "dark",
    "mystery",
    "shadow",

    "escuro",
    "misterio",
    "mistério",
    "sombra"
}


def _s(value):

    return str(
        value or ""
    ).strip()


def _flatten(value):

    if value is None:
        return ""


    if isinstance(
        value,
        dict
    ):

        return " ".join(
            _flatten(x)
            for x in value.values()
        )


    if isinstance(
        value,
        (
            list,
            tuple,
            set
        )
    ):

        return " ".join(
            _flatten(x)
            for x in value
        )


    return _s(
        value
    )


def _tokens(text):

    return [

        token

        for token in re.findall(
            r"[a-zà-ÿ0-9]+",
            _s(text).lower()
        )

        if (
            len(token) >= 2
            and token not in STOP
        )
    ]


def _unique(items):

    out = []
    seen = set()


    for item in items:

        item = _s(item)

        if not item:
            continue


        key = item.lower()


        if key in seen:
            continue


        seen.add(key)

        out.append(item)


    return out


def _years(text):

    return _unique(
        re.findall(
            r"\b(?:18|19|20)\d{2}\b",
            _s(text)
        )
    )


def _identity_labels(text):

    text = _s(text)


    labels = []


    patterns = (

        r"\b(?:Flight|flight|Voo|voo)\s*[-#:]?\s*[A-Za-z]{0,3}\d{1,5}\b",

        r"\b(?:Flight|flight|Voo|voo)\s*[-#:]?\s*\d{1,5}\b",

        r"\b(?:Case|case|Caso|caso)\s*[-#:]?\s*\d{1,6}\b",

        r"\b(?:Room|room|Quarto|quarto)\s*[-#:]?\s*\d{1,6}\b",

        r"\b(?:MH|QZ|AF|AA|UA|BA|TW|PA)\s*-?\s*\d{2,5}\b"
    )


    for pattern in patterns:

        labels.extend(
            re.findall(
                pattern,
                text
            )
        )


    return _unique(
        labels
    )


def _must_list(cena):

    raw = (
        cena.get(
            "must_have"
        )
        or cena.get(
            "must"
        )
        or []
    )


    if isinstance(
        raw,
        str
    ):

        raw = [
            raw
        ]


    if not isinstance(
        raw,
        (
            list,
            tuple,
            set
        )
    ):

        return []


    return _unique(
        raw
    )


def _scene_text(cena):

    return " ".join(

        _flatten(
            cena.get(field)
        )

        for field in (

            "segmento",
            "segment",

            "texto",
            "text",

            "narracao",
            "narração",

            "visual_query",
            "query",

            "must_have",
            "must",

            "subject",
            "topic",

            "visual_intent",
            "intent",

            "visual_mode"
        )
    )


def _visual_query(cena):

    return _s(
        cena.get(
            "visual_query"
        )
        or cena.get(
            "query"
        )
    )


def _role(cena):

    text = " ".join(
        [
            _s(
                cena.get(
                    "visual_mode"
                )
            ),
            _s(
                cena.get(
                    "visual_intent"
                )
            ),
            _s(
                cena.get(
                    "intent"
                )
            )
        ]
    ).lower()


    if "cta" in text:

        return "CTA"


    if any(
        x in text
        for x in (
            "document",
            "evidence",
            "archive",
            "arquivo",
            "newspaper",
            "case_file"
        )
    ):

        return "EVIDENCE"


    if any(
        x in text
        for x in (
            "portrait",
            "person",
            "people",
            "character"
        )
    ):

        return "PERSON"


    if any(
        x in text
        for x in (
            "location",
            "place",
            "architecture",
            "map",
            "transport"
        )
    ):

        return "PLACE"


    if any(
        x in text
        for x in (
            "object",
            "product",
            "medicine",
            "package",
            "packaging"
        )
    ):

        return "OBJECT"


    return "CONTEXT"


def _clean_anchor(value):

    value = _s(value)


    value = re.sub(
        r"\s+",
        " ",
        value
    )


    return value.strip()


def _anchor_candidates(cena):

    scene = _scene_text(
        cena
    )


    must = _must_list(
        cena
    )


    identities = _identity_labels(
        scene
    )


    years = _years(
        scene
    )


    anchors = []


    # Must-have é a fonte mais confiável.
    for value in must[:4]:

        value = _clean_anchor(
            value
        )


        tokens = _tokens(
            value
        )


        # Evita promover "dark man" etc.
        if (
            tokens
            and not all(
                token in GENERIC_VISUAL
                for token in tokens
            )
        ):

            anchors.append(
                value
            )


    anchors.extend(
        identities
    )


    anchors.extend(
        years[:2]
    )


    return _unique(
        anchors
    )


def _anchor_strength(cena):

    scene = _scene_text(
        cena
    )


    must = _must_list(
        cena
    )


    ids = _identity_labels(
        scene
    )


    years = _years(
        scene
    )


    score = 0


    if ids:
        score += 4


    if len(
        must
    ) >= 2:

        score += 3


    elif len(
        must
    ) == 1:

        score += 2


    if years:
        score += 1


    query_tokens = _tokens(
        _visual_query(
            cena
        )
    )


    non_generic = [

        t

        for t in query_tokens

        if t not in GENERIC_VISUAL
    ]


    if len(
        non_generic
    ) >= 3:

        score += 1


    return score


def _compact_query(parts):

    output = []

    seen_tokens = set()


    for part in parts:

        part = _clean_anchor(
            part
        )


        if not part:
            continue


        # Evita repetir exatamente o mesmo
        # bloco sem destruir nomes compostos.
        key = part.lower()


        if key in seen_tokens:
            continue


        seen_tokens.add(
            key
        )

        output.append(
            part
        )


    query = " ".join(
        output
    )


    # API search costuma funcionar pior
    # com consultas gigantes.
    words = query.split()


    if len(words) > 12:

        query = " ".join(
            words[:12]
        )


    return query.strip()


def _query_plan(cena):

    role = _role(
        cena
    )


    original = _visual_query(
        cena
    )


    anchors = _anchor_candidates(
        cena
    )


    strength = _anchor_strength(
        cena
    )


    queries = []


    # =================================
    # CTA
    # =================================

    if role == "CTA":

        return {

            "role":
                role,

            "strength":
                strength,

            "primary":
                original,

            "queries":
                [],

            "strategy":
                "REUSE_VERIFIED_ASSET",

            "override":
                False,

            "anchors":
                anchors
        }


    # =================================
    # EVIDENCE
    # =================================

    if role == "EVIDENCE":

        if anchors:

            queries.append(
                _compact_query(
                    anchors[:4]
                )
            )


            queries.append(
                _compact_query(
                    anchors[:3]
                    + [
                        "archive"
                    ]
                )
            )


            queries.append(
                _compact_query(
                    anchors[:3]
                    + [
                        "newspaper"
                    ]
                )
            )


            queries.append(
                _compact_query(
                    anchors[:3]
                    + [
                        "historical photograph"
                    ]
                )
            )


        if original:

            queries.append(
                original
            )


    # =================================
    # PERSON
    # =================================

    elif role == "PERSON":

        # Só faz busca específica por pessoa
        # se houver âncora real.
        if strength >= 3:

            queries.append(
                _compact_query(
                    anchors[:3]
                    + [
                        "archive photograph"
                    ]
                )
            )


            queries.append(
                _compact_query(
                    anchors[:3]
                )
            )


        if original:

            queries.append(
                original
            )


    # =================================
    # PLACE
    # =================================

    elif role == "PLACE":

        if anchors:

            queries.append(
                _compact_query(
                    anchors[:4]
                )
            )


            queries.append(
                _compact_query(
                    anchors[:3]
                    + [
                        "historical photograph"
                    ]
                )
            )


        if original:

            queries.append(
                original
            )


    # =================================
    # OBJECT
    # =================================

    elif role == "OBJECT":

        if strength >= 3:

            queries.append(
                _compact_query(
                    anchors[:3]
                )
            )


        if original:

            queries.append(
                original
            )


    # =================================
    # CONTEXT
    # =================================

    else:

        # Contexto não deve ficar
        # excessivamente estreito.
        if original:

            queries.append(
                original
            )


        if strength >= 5:

            queries.append(
                _compact_query(
                    anchors[:3]
                )
            )


    queries = _unique(
        queries
    )[:6]


    # =================================
    # PRIMARY QUERY
    # =================================

    primary = original


    override = False


    # Só substitui visual_query quando
    # realmente há âncora factual forte.
    if (
        queries
        and role in {
            "EVIDENCE",
            "PERSON",
            "PLACE"
        }
        and strength >= 4
    ):

        candidate_primary = queries[0]


        # Evita trocar por query mínima.
        if len(
            _tokens(
                candidate_primary
            )
        ) >= 2:

            primary = candidate_primary

            override = (
                primary.lower()
                != original.lower()
            )


    return {

        "role":
            role,

        "strength":
            strength,

        "primary":
            primary,

        "queries":
            queries,

        "strategy":
            (
                "DOCUMENTARY_FIRST"

                if role
                in {
                    "EVIDENCE",
                    "PERSON",
                    "PLACE"
                }

                else "BALANCED"
            ),

        "override":
            override,

        "anchors":
            anchors
    }


def _extend_avoid(
    cena,
    role
):

    current = (
        cena.get(
            "avoid"
        )
        or cena.get(
            "avoid_terms"
        )
        or []
    )


    if isinstance(
        current,
        str
    ):

        current = [
            current
        ]


    if not isinstance(
        current,
        (
            list,
            tuple,
            set
        )
    ):

        current = []


    extra = []


    if role == "PERSON":

        extra.extend(
            [
                "generic portrait",
                "random person",
                "actor",
                "reenactment"
            ]
        )


    elif role == "EVIDENCE":

        extra.extend(
            [
                "reenactment",
                "illustrative evidence",
                "generic mystery",
                "shadow suspect"
            ]
        )


    elif role == "PLACE":

        extra.extend(
            [
                "wrong city",
                "unrelated building",
                "generic location"
            ]
        )


    return _unique(
        list(current)
        + extra
    )


def aplicar_retrieval_plan_6_7(
    cena
):

    mode = _s(
        os.getenv(
            "VI67_RETRIEVAL_MODE",
            "ACTIVE"
        )
    ).upper()


    # Nunca modifica o objeto original.
    result = copy.deepcopy(
        cena
    )


    if mode == "OFF":

        return result


    plan = _query_plan(
        result
    )


    result[
        "retrieval_version"
    ] = VERSION


    result[
        "retrieval_role_6_7"
    ] = plan[
        "role"
    ]


    result[
        "retrieval_strategy_6_7"
    ] = plan[
        "strategy"
    ]


    result[
        "retrieval_anchor_strength_6_7"
    ] = plan[
        "strength"
    ]


    result[
        "retrieval_anchors_6_7"
    ] = plan[
        "anchors"
    ]


    result[
        "retrieval_queries_6_7"
    ] = plan[
        "queries"
    ]


    result[
        "retrieval_primary_query_6_7"
    ] = plan[
        "primary"
    ]


    result[
        "retrieval_query_overridden_6_7"
    ] = plan[
        "override"
    ]


    # Preserva consulta anterior para auditoria.
    if (
        "visual_query_original_6_7"
        not in result
    ):

        result[
            "visual_query_original_6_7"
        ] = _visual_query(
            result
        )


    # Override conservador.
    if (
        plan[
            "override"
        ]
        and plan[
            "primary"
        ]
    ):

        result[
            "visual_query"
        ] = plan[
            "primary"
        ]


    result[
        "avoid"
    ] = _extend_avoid(
        result,
        plan[
            "role"
        ]
    )


    return result


# =====================================================
# SELF TEST
# =====================================================

def self_test():

    # ---------------------------------
    # 1. Flight identity
    # ---------------------------------

    scene = {

        "visual_mode":
            "evidence",

        "visual_query":
            "old aircraft mystery",

        "must_have":
            [
                "Flight 19",
                "1945"
            ],

        "segmento":
            "Flight 19 disappeared in 1945."
    }


    x = aplicar_retrieval_plan_6_7(
        scene
    )


    assert (
        x[
            "retrieval_role_6_7"
        ]
        == "EVIDENCE"
    )


    assert (
        "Flight 19"
        in x[
            "retrieval_primary_query_6_7"
        ]
    )


    assert (
        "1945"
        in x[
            "retrieval_primary_query_6_7"
        ]
    )


    assert (
        x[
            "visual_query_original_6_7"
        ]
        == "old aircraft mystery"
    )


    # ---------------------------------
    # 2. Generic person must not become
    # fake named-person query.
    # ---------------------------------

    person = {

        "visual_mode":
            "person",

        "visual_query":
            "sad young girl portrait",

        "must_have":
            []
    }


    y = aplicar_retrieval_plan_6_7(
        person
    )


    assert (
        y[
            "retrieval_anchor_strength_6_7"
        ]
        < 4
    )


    assert (
        y[
            "retrieval_query_overridden_6_7"
        ]
        is False
    )


    assert (
        "generic portrait"
        in y[
            "avoid"
        ]
    )


    # ---------------------------------
    # 3. Named place
    # ---------------------------------

    place = {

        "visual_mode":
            "location",

        "visual_query":
            "old hotel building",

        "must_have":
            [
                "Cecil Hotel",
                "Los Angeles"
            ],

        "segmento":
            "The Cecil Hotel in Los Angeles."
    }


    z = aplicar_retrieval_plan_6_7(
        place
    )


    assert (
        "Cecil Hotel"
        in z[
            "retrieval_primary_query_6_7"
        ]
    )


    assert (
        "Los Angeles"
        in z[
            "retrieval_primary_query_6_7"
        ]
    )


    # ---------------------------------
    # 4. CTA never creates new search
    # ---------------------------------

    cta = {

        "visual_mode":
            "cta_reuse",

        "visual_query":
            "subscribe"
    }


    c = aplicar_retrieval_plan_6_7(
        cta
    )


    assert (
        c[
            "retrieval_strategy_6_7"
        ]
        == "REUSE_VERIFIED_ASSET"
    )


    assert (
        c[
            "retrieval_queries_6_7"
        ]
        == []
    )


    # ---------------------------------
    # 5. Context stays conservative
    # ---------------------------------

    context = {

        "visual_mode":
            "context",

        "visual_query":
            "pharmacy shelves medicine"
    }


    q = aplicar_retrieval_plan_6_7(
        context
    )


    assert (
        q[
            "visual_query"
        ]
        == "pharmacy shelves medicine"
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.7 RETRIEVAL SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK factual identity anchors"
    )
    print(
        "OK flight/case preservation"
    )
    print(
        "OK year preservation"
    )
    print(
        "OK evidence query planning"
    )
    print(
        "OK person generic guard"
    )
    print(
        "OK named-place precision"
    )
    print(
        "OK CTA no-search policy"
    )
    print(
        "OK conservative context"
    )
    print(
        "OK original query preserved"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# INTEGRAÇÃO ADAPTATIVA NO LOOP DE CENAS
# =====================================================

python - <<'PY'
from pathlib import Path
import re


p = Path(
    "midia.py"
)


t = p.read_text(
    encoding="utf-8"
)


if "aplicar_retrieval_plan_6_7" in t:

    print(
        "VI6.7 já está integrado."
    )

    raise SystemExit(0)


# Procuramos loops que iteram sobre `cenas`
# e têm uma variável chamada `cena`.
pattern = re.compile(
    r'''
    ^(?P<indent>[ \t]*)
    for
    [^\n:]*\bcena\b[^\n:]*
    \bin\b
    [^\n:]*\bcenas\b[^\n:]*
    :
    [ \t]*$
    ''',
    re.MULTILINE
    | re.VERBOSE
)


matches = list(
    pattern.finditer(
        t
    )
)


if not matches:

    raise SystemExit(
        "ERRO: loop principal de cenas "
        "não encontrado. "
        "midia.py NÃO foi alterado."
    )


# Escolhe apenas loop cujo bloco seguinte
# contém busca de mídia + VI6.
chosen = None


for match in matches:

    trecho = t[
        match.end():
        match.end() + 18000
    ]


    has_vi6 = (
        "vi6_audit_scene"
        in trecho
        or "VI6"
        in trecho
    )


    has_media = (
        "todos"
        in trecho
        and (
            "Pixabay"
            in trecho
            or "Wikimedia"
            in trecho
            or "buscar_"
            in trecho
        )
    )


    if (
        has_vi6
        and has_media
    ):

        chosen = match
        break


if chosen is None:

    raise SystemExit(
        "ERRO: loop de produção visual "
        "não identificado com segurança. "
        "midia.py NÃO foi alterado."
    )


indent = (
    chosen.group(
        "indent"
    )
    + "    "
)


lines = [

    "",

    "# =========================================",
    "# VI6.7 RETRIEVAL INTELLIGENCE",
    "# =========================================",

    "try:",

    "    from vi6_7_retrieval_planner import (",
    "        aplicar_retrieval_plan_6_7",
    "    )",

    "",

    "    cena = aplicar_retrieval_plan_6_7(",
    "        cena",
    "    )",

    "",

    "    if cena.get(",
    "        'retrieval_query_overridden_6_7',",
    "        False",
    "    ):",
    "        print(",
    "            '  VI6.7 RETRIEVAL:'",
    "        )",
    "        print(",
    "            f\"    ROLE=\"",
    "            f\"{cena.get('retrieval_role_6_7')}\"",
    "        )",
    "        print(",
    "            f\"    QUERY=\"",
    "            f\"{cena.get('retrieval_primary_query_6_7')}\"",
    "        )",
    "        print(",
    "            f\"    ANCHOR_STRENGTH=\"",
    "            f\"{cena.get('retrieval_anchor_strength_6_7')}\"",
    "        )",

    "",

    "except Exception as e:",

    "    print(",
    "        f\"  VI6.7 RETRIEVAL WARNING: \"",
    "        f\"{type(e).__name__}: \"",
    "        f\"{str(e)[:140]}\"",
    "    )",

    ""
]


block = "\n".join(

    (
        indent + line
        if line
        else ""
    )

    for line in lines
)


insert_at = (
    chosen.end()
)


t = (
    t[:insert_at]
    + "\n"
    + block
    + t[insert_at:]
)


p.write_text(
    t,
    encoding="utf-8"
)


print()
print(
    "OK VI6.7 inserido no loop visual"
)
PY


# =====================================================
# AUDITOR OFFLINE
# =====================================================

cat > testar_vi67_offline.py <<'PY'
#!/usr/bin/env python3

from vi6_7_retrieval_planner import (
    aplicar_retrieval_plan_6_7
)


samples = [

    {
        "name":
            "Flight 19 evidence",

        "scene":
            {
                "visual_mode":
                    "evidence",

                "visual_query":
                    "airplane ocean mystery",

                "must_have":
                    [
                        "Flight 19",
                        "1945"
                    ],

                "segmento":
                    "Flight 19 vanished in 1945."
            }
    },

    {
        "name":
            "Cecil Hotel place",

        "scene":
            {
                "visual_mode":
                    "location",

                "visual_query":
                    "old hotel",

                "must_have":
                    [
                        "Cecil Hotel",
                        "Los Angeles"
                    ],

                "segmento":
                    "The Cecil Hotel in Los Angeles."
            }
    },

    {
        "name":
            "Generic unnamed person",

        "scene":
            {
                "visual_mode":
                    "person",

                "visual_query":
                    "sad young girl portrait",

                "must_have":
                    []
            }
    },

    {
        "name":
            "Tylenol evidence",

        "scene":
            {
                "visual_mode":
                    "evidence",

                "visual_query":
                    "medicine bottle",

                "must_have":
                    [
                        "Tylenol",
                        "Chicago"
                    ],

                "segmento":
                    "The 1982 Chicago Tylenol poisonings."
            }
    },

    {
        "name":
            "CTA reuse",

        "scene":
            {
                "visual_mode":
                    "cta_reuse",

                "visual_query":
                    "subscribe"
            }
    }
]


print()
print(
    "======================================"
)
print(
    " VI6.7 OFFLINE RETRIEVAL AUDIT"
)
print(
    " SEM API / SEM DOWNLOAD / SEM VIDEO"
)
print(
    "======================================"
)


for index, sample in enumerate(
    samples,
    1
):

    result = aplicar_retrieval_plan_6_7(
        sample[
            "scene"
        ]
    )


    print()
    print(
        f"CENA TESTE {index:02d}: "
        f"{sample['name']}"
    )

    print(
        "  ROLE:",
        result.get(
            "retrieval_role_6_7"
        )
    )

    print(
        "  STRENGTH:",
        result.get(
            "retrieval_anchor_strength_6_7"
        )
    )

    print(
        "  ORIGINAL:",
        result.get(
            "visual_query_original_6_7"
        )
    )

    print(
        "  PRIMARY:",
        result.get(
            "retrieval_primary_query_6_7"
        )
    )

    print(
        "  OVERRIDE:",
        result.get(
            "retrieval_query_overridden_6_7"
        )
    )

    print(
        "  STRATEGY:",
        result.get(
            "retrieval_strategy_6_7"
        )
    )

    print(
        "  QUERIES:"
    )


    for q in result.get(
        "retrieval_queries_6_7",
        []
    ):

        print(
            "   -",
            q
        )


print()
print(
    "======================================"
)
print(
    " VI6.7 OFFLINE AUDIT COMPLETO"
)
print(
    "======================================"
)
print(
    "API CALLS: 0"
)
print(
    "DOWNLOADS: 0"
)
print(
    "VIDEOS: 0"
)
print()
PY


# =====================================================
# VALIDATION
# =====================================================

echo
echo "===== PYTHON COMPILE ====="

if ! python -m py_compile \
    vi6_7_retrieval_planner.py \
    testar_vi67_offline.py \
    vi6_6_active_brain.py \
    visual_intelligence_6.py \
    midia.py
then

    echo
    echo "COMPILE FALHOU."

    rollback

    exit 1
fi

echo "PYTHON STATUS=0"


echo
echo "===== VI6.7 SELF TEST ====="

if ! python vi6_7_retrieval_planner.py
then

    echo
    echo "VI6.7 SELF TEST FALHOU."

    rollback

    exit 1
fi


echo
echo "===== VI6.6 REGRESSION ====="

if ! python vi6_6_active_brain.py
then

    echo
    echo "VI6.6 REGRESSION FALHOU."

    rollback

    exit 1
fi


echo
echo "===== BASH CHECK ====="

if ! bash -n gerar_short.sh
then

    echo
    echo "BASH CHECK FALHOU."

    rollback

    exit 1
fi

echo "BASH STATUS=0"


echo
echo "===== RELEASE CHECK ====="

if ! ./release_check.sh
then

    echo
    echo "RELEASE CHECK FALHOU."

    rollback

    exit 1
fi


echo
echo "======================================"
echo " VI6.7 RETRIEVAL INSTALADO"
echo "======================================"
echo
echo "OK Retrieval Planner"
echo "OK Documentary-first queries"
echo "OK Identity preservation"
echo "OK Flight/Case anchors"
echo "OK Year anchors"
echo "OK Named-place precision"
echo "OK Generic-person protection"
echo "OK Evidence query expansion"
echo "OK Query budget"
echo "OK Original query preservation"
echo "OK CTA no-search strategy"
echo "OK VI6.6 regression"
echo "OK VI6.3/5.x fallback intact"
echo
echo "API CALLS=0"
echo "DOWNLOADS NOVOS=0"
echo "VIDEOS GERADOS=0"
echo


echo "======================================"
echo " AUDITORIA OFFLINE VI6.7"
echo "======================================"

python testar_vi67_offline.py

