#!/usr/bin/env python3

import os
import re
import json
import unicodedata
from collections import Counter
from datetime import date


# ============================================================
# LOSSLESS_OVERLAP_SAFE_MERGE_6_2_1
# ============================================================

def _lossless_overlap_tokens_6_2_1(value):
    import re
    import unicodedata

    text = str(
        value or ""
    )

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    text = text.casefold()

    return set(
        re.findall(
            r"[a-z0-9]+",
            text,
        )
    )


def _lossless_split_sentences_6_2_1(value):
    import re

    text = str(
        value or ""
    ).strip()

    if not text:
        return []

    return [
        part.strip()
        for part in re.split(
            r"(?<=[.!?])\s+",
            text,
        )
        if part.strip()
    ]


def _lossless_merge_source_6_2_1(
    current,
    source,
):
    """
    Source-aware Lossless merge.

    1. Source already covered -> no change.
    2. Existing sentence is a shorter version of source
       -> replace it with the richer source.
    3. Distinct source information -> append normally.
    """

    current = str(
        current or ""
    ).strip()

    source = str(
        source or ""
    ).strip()

    if not source:
        return current

    if not current:
        return source

    source_tokens = (
        _lossless_overlap_tokens_6_2_1(
            source
        )
    )

    current_tokens = (
        _lossless_overlap_tokens_6_2_1(
            current
        )
    )

    if not source_tokens:
        return current

    # Already completely represented in current text.
    if source_tokens <= current_tokens:
        return current

    sentences = (
        _lossless_split_sentences_6_2_1(
            current
        )
    )

    for index, sentence in enumerate(
        sentences
    ):

        sentence_tokens = (
            _lossless_overlap_tokens_6_2_1(
                sentence
            )
        )

        if not sentence_tokens:
            continue

        # Existing sentence is strictly contained by source.
        if sentence_tokens < source_tokens:

            overlap_ratio = (
                len(sentence_tokens)
                /
                max(
                    1,
                    len(source_tokens),
                )
            )

            # High enough to identify an enriched version,
            # but conservative enough to avoid merging
            # genuinely separate sentences.
            if overlap_ratio >= 0.60:

                sentences[index] = source

                return " ".join(
                    sentences
                ).strip()

    # Genuinely distinct information.
    return (
        current
        + " "
        + source
    ).strip()


def _lossless_word_count_6_2_1(value):
    return len(
        str(
            value or ""
        ).split()
    )



# =====================================================
# SHORTAUTO PRO
# LOSSLESS SCENE COVERAGE REPAIR 6.2
# =====================================================

BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

R = os.path.join(
    BASE,
    "roteiros"
)

SCRIPT = os.path.join(
    R,
    f"short_{SHORT_ID}.txt"
)

SCENE_MAP = os.path.join(
    R,
    f"scene_map_{SHORT_ID}.json"
)

BACKUP = os.path.join(
    R,
    f"scene_map_pre_lossless_{SHORT_ID}.json"
)

REPORT = os.path.join(
    R,
    f"scene_lossless_{SHORT_ID}.json"
)


STOP = {
    "o", "a", "os", "as",
    "um", "uma", "uns", "umas",
    "de", "da", "do", "das", "dos",
    "e", "ou", "em", "no", "na",
    "nos", "nas", "por", "para",
    "com", "sem", "que", "se",
    "ao", "aos", "à", "às",
    "foi", "era", "ser", "são",
    "como", "mais", "mas",
    "the", "of", "and", "in",
    "on", "at", "to", "for",
    "from", "with"
}


# =====================================================
# IO
# =====================================================

def read(path):

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return f.read().strip()

    except Exception:

        return ""


def read_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# =====================================================
# TEXT NORMALIZATION
# =====================================================

def sem_acento(text):

    text = unicodedata.normalize(
        "NFKD",
        str(text or "")
    )

    return "".join(
        c
        for c in text
        if not unicodedata.combining(c)
    )


def tokenizar(
    text,
    remove_stop=True
):

    toks = re.findall(
        r"[a-z0-9]+",
        sem_acento(
            text
        ).lower()
    )

    if remove_stop:

        toks = [
            x
            for x in toks
            if (
                len(x) >= 2
                and x not in STOP
            )
        ]

    return toks


def token_set(text):

    return set(
        tokenizar(
            text
        )
    )


# =====================================================
# COVERAGE
# =====================================================

def coverage(
    script,
    scenes_text
):

    script_tokens = token_set(
        script
    )

    scene_tokens = token_set(
        scenes_text
    )

    if not script_tokens:

        return 1.0, set()


    missing = (
        script_tokens
        - scene_tokens
    )


    ratio = (
        len(
            script_tokens
            & scene_tokens
        )
        / len(
            script_tokens
        )
    )


    return (
        ratio,
        missing
    )


# =====================================================
# SOURCE CHUNKS
# =====================================================

def sentence_chunks(
    script
):

    # Primeiro tenta sentenças naturais.
    partes = [
        x.strip()
        for x in re.split(
            r"(?<=[.!?])\s+",
            script
        )
        if x.strip()
    ]


    # Roteiro com pouca pontuação:
    # cria blocos menores sem alterar palavras.
    if len(partes) < 6:

        palavras = script.split()

        alvo = max(
            8,
            round(
                len(palavras)
                / 12
            )
        )

        partes = []

        for i in range(
            0,
            len(palavras),
            alvo
        ):

            trecho = " ".join(
                palavras[
                    i:
                    i + alvo
                ]
            ).strip()

            if trecho:

                partes.append(
                    trecho
                )


    return partes


# =====================================================
# SCENE AFFINITY
# =====================================================

def scene_context(
    scene
):

    partes = [
        str(
            scene.get(
                "segment",
                ""
            )
        ),

        str(
            scene.get(
                "query",
                ""
            )
        ),

        str(
            scene.get(
                "visual_mode",
                ""
            )
        )
    ]


    partes.extend(
        str(x)
        for x in scene.get(
            "must_have",
            []
        )
    )


    return " ".join(
        partes
    )


def afinidade(
    trecho,
    scene,
    scene_index,
    total_scenes,
    chunk_index,
    total_chunks
):

    tt = token_set(
        trecho
    )

    st = token_set(
        scene_context(
            scene
        )
    )


    overlap = (
        len(
            tt
            & st
        )
        / max(
            1,
            len(tt)
        )
    )


    # Ajuda a preservar ordem narrativa.
    pos_scene = (
        scene_index
        / max(
            1,
            total_scenes - 1
        )
    )

    pos_chunk = (
        chunk_index
        / max(
            1,
            total_chunks - 1
        )
    )

    distancia = abs(
        pos_scene
        - pos_chunk
    )


    positional = (
        1.0
        - min(
            1.0,
            distancia
        )
    )


    return (
        overlap * 0.78
        + positional * 0.22
    )


# =====================================================
# REPAIR
# =====================================================

script = read(
    SCRIPT
)

if not script:

    raise SystemExit(
        f"ERRO: roteiro ausente: {SCRIPT}"
    )


if not os.path.exists(
    SCENE_MAP
):

    raise SystemExit(
        f"ERRO: scene_map ausente: {SCENE_MAP}"
    )


mapa = read_json(
    SCENE_MAP
)

scenes = mapa.get(
    "scenes",
    []
)


if len(scenes) != 12:

    raise SystemExit(
        f"ERRO: esperado 12 cenas, encontrado {len(scenes)}."
    )


original_text = "\n".join(
    str(
        x.get(
            "segment",
            ""
        )
    )
    for x in scenes
)


before, missing_before = coverage(
    script,
    original_text
)


print()
print("======================================")
print(" LOSSLESS SCENE COVERAGE REPAIR 6.2")
print("======================================")
print()

print(
    "SHORT_ID:",
    SHORT_ID
)

print(
    "Cobertura inicial:",
    f"{before * 100:.1f}%"
)

print(
    "Tokens ausentes:",
    len(
        missing_before
    )
)


# Não toca no mapa se já estiver ótimo.

if before >= 0.965:

    report = {
        "short_id":
            SHORT_ID,

        "coverage_before":
            round(
                before,
                4
            ),

        "coverage_after":
            round(
                before,
                4
            ),

        "changed_scenes":
            [],

        "missing_before":
            sorted(
                missing_before
            ),

        "missing_after":
            sorted(
                missing_before
            ),

        "status":
            "NO_REPAIR_NEEDED"
    }


    with open(
        REPORT,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2
        )


    print()
    print(
        "LOSSLESS REPAIR: NÃO NECESSÁRIO"
    )

    print(
        "Mapa original preservado."
    )

    raise SystemExit(
        0
    )


# =====================================================
# BACKUP
# =====================================================

with open(
    BACKUP,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        mapa,
        f,
        ensure_ascii=False,
        indent=2
    )


chunks = sentence_chunks(
    script
)

changed = []


# =====================================================
# Só adiciona chunks que carregam algum token ausente.
# =====================================================

for chunk_index, trecho in enumerate(
    chunks
):

    chunk_tokens = token_set(
        trecho
    )


    relevantes = (
        chunk_tokens
        & missing_before
    )


    if not relevantes:
        continue


    scores = []


    for scene_index, scene in enumerate(
        scenes
    ):

        score = afinidade(
            trecho,
            scene,
            scene_index,
            len(scenes),
            chunk_index,
            len(chunks)
        )

        scores.append(
            (
                score,
                scene_index
            )
        )


    scores.sort(
        reverse=True
    )


    melhor_score, destino = scores[0]


    atual = str(
        scenes[
            destino
        ].get(
            "segment",
            ""
        )
    ).strip()


    # Evita anexar o mesmo trecho duas vezes.
    if (
        token_set(
            trecho
        )
        <= token_set(
            atual
        )
    ):

        continue


    novo_segmento = _lossless_merge_source_6_2_1(
        atual,
        trecho,
    )


    scenes[
        destino
    ][
        "segment"
    ] = novo_segmento


    scenes[
        destino
    ][
        "lossless_repair_6_2"
    ] = True


    scenes[
        destino
    ].setdefault(
        "lossless_sources_6_2",
        []
    ).append(
        trecho
    )


    changed.append(
        {
            "scene":
                destino + 1,

            "affinity":
                round(
                    melhor_score,
                    3
                ),

            "missing_tokens":
                sorted(
                    relevantes
                ),

            "source_text":
                trecho
        }
    )


# =====================================================
# FINAL COVERAGE
# =====================================================

final_text = "\n".join(
    str(
        x.get(
            "segment",
            ""
        )
    )
    for x in scenes
)


after, missing_after = coverage(
    script,
    final_text
)


# =====================================================
# FAIL SAFE
# =====================================================

if after < before:

    raise SystemExit(
        "ERRO: reparo reduziu cobertura; "
        "scene_map original preservado no backup."
    )


if after < 0.965:

    print()
    print(
        "AVISO: primeira passagem não atingiu 96.5%."
    )

    print(
        "Aplicando recuperação literal final."
    )


    # Recuperação conservadora:
    # distribui somente tokens/frases ainda ausentes.
    #
    # Cada palavra adicionada vem do roteiro original.

    palavras = script.split()


    for palavra in palavras:

        token_palavra = token_set(
            palavra
        )


        if not (
            token_palavra
            & missing_after
        ):

            continue


        # Posicionamento aproximado pelo ponto
        # da palavra no roteiro.

        try:

            pos = palavras.index(
                palavra
            )

        except Exception:

            pos = 0


        destino = min(
            11,
            int(
                (
                    pos
                    / max(
                        1,
                        len(palavras)
                    )
                )
                * 12
            )
        )


        atual = str(
            scenes[
                destino
            ].get(
                "segment",
                ""
            )
        ).strip()


        scenes[
            destino
        ][
            "segment"
        ] = (
            atual
            + " "
            + palavra
        ).strip()


        scenes[
            destino
        ][
            "lossless_repair_6_2"
        ] = True


    final_text = "\n".join(
        str(
            x.get(
                "segment",
                ""
            )
        )
        for x in scenes
    )


    after, missing_after = coverage(
        script,
        final_text
    )


# =====================================================
# WRITE
# =====================================================


# ============================================================
# LOSSLESS WORD METADATA REFRESH 6.2.1
# ============================================================

for _lossless_scene_6_2_1 in scenes:

    if not isinstance(
        _lossless_scene_6_2_1,
        dict,
    ):
        continue

    if not _lossless_scene_6_2_1.get(
        "lossless_repair_6_2"
    ):
        continue

    _lossless_scene_6_2_1[
        "words"
    ] = _lossless_word_count_6_2_1(
        _lossless_scene_6_2_1.get(
            "segment",
            "",
        )
    )

mapa[
    "scenes"
] = scenes


mapa[
    "lossless_scene_coverage_6_2"
] = {
    "coverage_before":
        round(
            before,
            4
        ),

    "coverage_after":
        round(
            after,
            4
        ),

    "changed_scenes":
        sorted(
            {
                x[
                    "scene"
                ]
                for x in changed
            }
        )
}


with open(
    SCENE_MAP,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        mapa,
        f,
        ensure_ascii=False,
        indent=2
    )


report = {
    "short_id":
        SHORT_ID,

    "coverage_before":
        round(
            before,
            4
        ),

    "coverage_after":
        round(
            after,
            4
        ),

    "changed_scenes":
        changed,

    "missing_before":
        sorted(
            missing_before
        ),

    "missing_after":
        sorted(
            missing_after
        ),

    "backup":
        BACKUP,

    "status":
        (
            "PASS"
            if after >= 0.965
            else "WARNING"
        )
}


with open(
    REPORT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        report,
        f,
        ensure_ascii=False,
        indent=2
    )


print()
print(
    "Cobertura final:",
    f"{after * 100:.1f}%"
)

print(
    "Cenas ajustadas:",
    sorted(
        {
            x[
                "scene"
            ]
            for x in changed
        }
    )
)

print(
    "Tokens ainda ausentes:",
    sorted(
        missing_after
    )
)

print()

print(
    "Backup:",
    BACKUP
)

print(
    "Relatório:",
    REPORT
)


if after < 0.965:

    print()
    print(
        "LOSSLESS REPAIR: WARNING"
    )

    raise SystemExit(
        1
    )


print()
print(
    "LOSSLESS REPAIR: PASS"
)
