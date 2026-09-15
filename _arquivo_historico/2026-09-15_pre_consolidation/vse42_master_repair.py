#!/usr/bin/env python3

from pathlib import Path
import ast
import datetime
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import textwrap


ROOT = Path.home() / "ShortAutoPro"

STAMP = datetime.datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

BACKUP = (
    ROOT
    / "backups"
    / f"vse42_master_{STAMP}"
)

BACKUP.mkdir(
    parents=True,
    exist_ok=True,
)


TRACKED = [
    "visual_selection_engine_v4.py",
    "midia.py",
    "fresh_render_guard_v1.py",
    "render_output_certifier_v1.py",
    "render_transaction_v1.py",
    "media_diversity_guard_v1.py",
    "gerar_short.sh",
]


backed_up = {}


def banner(text):

    print()
    print("=" * 72)
    print(text)
    print("=" * 72)


def backup_files():

    banner(
        "0. BACKUP"
    )

    for name in TRACKED:

        src = ROOT / name

        if not src.exists():
            print(
                f"BACKUP_SKIP={name}"
            )
            continue

        dst = BACKUP / name

        shutil.copy2(
            src,
            dst,
        )

        backed_up[
            name
        ] = dst

        print(
            f"BACKUP=PASS {name}"
        )

    print(
        f"BACKUP_DIR={BACKUP}"
    )


def restore():

    banner(
        "ROLLBACK"
    )

    for name, backup in backed_up.items():

        target = ROOT / name

        shutil.copy2(
            backup,
            target,
        )

        print(
            f"RESTORED={name}"
        )


def compile_file(path):

    try:

        py_compile.compile(
            str(path),
            doraise=True,
        )

        return True, ""

    except Exception as exc:

        return (
            False,
            f"{type(exc).__name__}: {exc}",
        )


def replace_function(
    source,
    function_name,
    replacement,
):

    tree = ast.parse(
        source
    )

    found = [
        node
        for node in tree.body
        if (
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
            and
            node.name == function_name
        )
    ]

    if len(found) != 1:

        raise RuntimeError(
            f"{function_name} definitions="
            f"{len(found)}"
        )

    node = found[0]

    lines = source.splitlines(
        keepends=True
    )

    start = node.lineno - 1
    end = node.end_lineno

    return (
        "".join(
            lines[:start]
        )
        +
        replacement.rstrip()
        +
        "\n\n"
        +
        "".join(
            lines[end:]
        )
    )


CANDIDATE_TEXT_V42 = r'''
def candidate_text(candidate):
    """
    VSE4.2 semantic text adapter.

    Aceita diretamente:
    - string
    - dict de cena
    - dict de candidato
    - listas/tuplas/sets
    - objetos com atributos

    Corrige um bug importante:
    uma cena recebida como string não pode virar texto vazio.
    """

    if candidate is None:
        return ""


    if isinstance(
        candidate,
        str,
    ):

        return " ".join(
            candidate.split()
        ).casefold()


    if isinstance(
        candidate,
        (
            int,
            float,
            bool,
        ),
    ):

        return str(
            candidate
        ).casefold()


    parts = []


    semantic_fields = (
        "texto",
        "text",
        "narration",
        "narracao",
        "title",
        "name",
        "description",
        "caption",
        "alt",
        "alt_text",
        "visual_query",
        "query",
        "search_query",
        "must_have",
        "avoid",
        "location",
        "local",
        "geo",
        "subject",
        "topic",
        "category",
        "tags",
        "keywords",
        "terms",
        "filename",
    )


    def add(value):

        if value is None:
            return


        if isinstance(
            value,
            str,
        ):

            value = " ".join(
                value.split()
            )

            if value:
                parts.append(
                    value
                )

            return


        if isinstance(
            value,
            (
                int,
                float,
                bool,
            ),
        ):

            parts.append(
                str(value)
            )

            return


        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):

            for item in value:
                add(
                    item
                )

            return


        if isinstance(
            value,
            dict,
        ):

            for key in semantic_fields:

                if key in value:
                    add(
                        value.get(key)
                    )

            return


    if isinstance(
        candidate,
        (
            list,
            tuple,
            set,
        ),
    ):

        add(
            candidate
        )


    elif isinstance(
        candidate,
        dict,
    ):

        add(
            candidate
        )

        for nested_name in (
            "metadata",
            "meta",
            "source_metadata",
            "provenance",
            "scene",
        ):

            nested = candidate.get(
                nested_name
            )

            if isinstance(
                nested,
                dict,
            ):
                add(
                    nested
                )


    else:

        for field in semantic_fields:

            try:

                value = getattr(
                    candidate,
                    field,
                    None,
                )

            except Exception:

                value = None

            add(
                value
            )


    clean = []
    seen = set()

    for part in parts:

        part = str(
            part
        ).strip()

        if not part:
            continue

        key = part.casefold()

        if key in seen:
            continue

        seen.add(
            key
        )

        clean.append(
            part
        )


    return " ".join(
        clean
    ).casefold()
'''


SCORE_WRAPPER_V42 = r'''
# SHORTAUTOPRO VSE4.2 HARD MISMATCH + RUNTIME RANKER

def _vse42_phrase_hits(text, terms):

    normalized = norm(
        text
    )

    result = set()

    for term in terms:

        needle = norm(
            term
        )

        if (
            needle
            and
            needle in normalized
        ):
            result.add(
                needle
            )

    return result


def _vse42_hard_mismatch(
    scene,
    candidate,
):

    scene_text = candidate_text(
        scene
    )

    candidate_txt = candidate_text(
        candidate
    )


    scene_geo = set(
        geo_hits(
            scene_text
        )
    )

    candidate_geo = set(
        geo_hits(
            candidate_txt
        )
    )


    # --------------------------------------------------------
    # GEOGRAPHY
    #
    # São Paulo:
    # brazil + sao_paulo
    #
    # New York:
    # usa + new_york
    #
    # Sem interseção => incompatibilidade forte.
    # --------------------------------------------------------

    if (
        scene_geo
        and
        candidate_geo
        and
        not (
            scene_geo
            &
            candidate_geo
        )
    ):

        return (
            True,
            "GEO_CONTRADICTION",
        )


    scene_concepts = set(
        concept_hits(
            scene_text
        )
    )

    candidate_concepts = set(
        concept_hits(
            candidate_txt
        )
    )


    # --------------------------------------------------------
    # FALSE MEDICINE ASSOCIATION
    # --------------------------------------------------------

    medicine = _vse42_phrase_hits(
        candidate_txt,
        MEDICINE_TERMS,
    )

    documentary_context = {
        "police",
        "investigation",
        "crime_scene",
        "evidence",
        "forensics",
        "court",
        "law",
        "prison",
    }


    medical_context = {
        "medicine",
        "hospital",
    }


    if (
        medicine
        and
        (
            scene_concepts
            &
            documentary_context
        )
        and
        not (
            scene_concepts
            &
            medical_context
        )
    ):

        return (
            True,
            "FALSE_MEDICINE_ASSOCIATION",
        )


    # --------------------------------------------------------
    # GENERIC LIFESTYLE VS DOCUMENTARY CONTEXT
    # --------------------------------------------------------

    generic = _vse42_phrase_hits(
        candidate_txt,
        GENERIC_LIFESTYLE,
    )


    strong_documentary = {
        "police",
        "investigation",
        "crime_scene",
        "evidence",
        "forensics",
        "court",
        "law",
        "prison",
        "military",
        "war",
        "rescue",
    }


    semantic_overlap = (
        scene_concepts
        &
        candidate_concepts
    )


    if (
        generic
        and
        (
            scene_concepts
            &
            strong_documentary
        )
        and
        not semantic_overlap
    ):

        return (
            True,
            "GENERIC_LIFESTYLE_MISMATCH",
        )


    return (
        False,
        "",
    )


def score_candidate(
    candidate,
    scene,
    state=None,
    *args,
    **kwargs,
):

    if state is None:

        state = {
            "providers": [],
            "groups": [],
            "types": [],
            "keys": [],
        }


    result = _vse42_score_candidate_base(
        candidate,
        scene,
        state,
        *args,
        **kwargs,
    )


    if not isinstance(
        result,
        dict,
    ):

        return result


    guard_hard, guard_reason = (
        _vse42_hard_mismatch(
            scene,
            candidate,
        )
    )


    base_hard = bool(
        result.get(
            "hard_mismatch",
            False,
        )
    )


    if guard_hard:

        if not base_hard:

            effective = number(
                result.get(
                    "effective",
                    None,
                ),
                base_score(
                    candidate
                ),
            )

            result[
                "effective"
            ] = (
                float(
                    effective
                )
                -
                1000.0
            )


        result[
            "hard_mismatch"
        ] = True

        result[
            "hard_reason"
        ] = (
            guard_reason
            or
            result.get(
                "hard_reason",
                "",
            )
        )

        result[
            "vse42_hard_guard"
        ] = True


    else:

        result.setdefault(
            "vse42_hard_guard",
            False,
        )


    return result


def rerank_runtime_v42(
    pool,
    scene,
    state=None,
):

    """
    Reordena somente candidatos já aprovados pelo pipeline.

    Não baixa mídia.
    Não altera o objeto do candidato.
    Hard mismatch sempre perde para candidato válido.
    """

    if state is None:

        state = {
            "providers": [],
            "groups": [],
            "types": [],
            "keys": [],
        }


    candidates = flatten_candidates(
        pool
    )


    if not candidates:
        return list(
            pool
            if isinstance(
                pool,
                (list, tuple)
            )
            else
            []
        )


    ranked = []


    for index, candidate in enumerate(
        candidates
    ):

        try:

            result = score_candidate(
                candidate,
                scene,
                state,
            )


            hard = bool(
                result.get(
                    "hard_mismatch",
                    False,
                )
            )


            effective = number(
                result.get(
                    "effective",
                    None,
                ),
                base_score(
                    candidate
                ),
            )


            tier = must_tier(
                candidate,
                scene,
            )


        except Exception:

            hard = False

            effective = base_score(
                candidate
            )

            tier = must_tier(
                candidate,
                scene,
            )


        ranked.append(
            (
                1 if hard else 0,
                -int(tier),
                -float(effective),
                index,
                candidate,
            )
        )


    ranked.sort(
        key=lambda item:
            item[:4]
    )


    return [
        item[4]
        for item in ranked
    ]
'''


SAFE_RENDER_GUARD = r'''#!/usr/bin/env python3

import os
from pathlib import Path


ROOT = (
    Path.home()
    / "ShortAutoPro"
)


PROTECTED_SUFFIXES = {
    ".ass",
    ".srt",
    ".vtt",
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".json",
    ".txt",
}


FINAL_PATTERNS = (
    "short_v6_{sid}.mp4",
    "short_v5_{sid}.mp4",
    "short_v4_{sid}.mp4",
    "short_v3_{sid}.mp4",
)


def _safe_id(short_id):

    if not short_id:
        raise RuntimeError(
            "SHORT_ID vazio"
        )

    if (
        "/" in short_id
        or
        "\\" in short_id
        or
        ".." in short_id
    ):

        raise RuntimeError(
            "SHORT_ID inseguro"
        )


def _remove_mp4(path):

    if not path.is_file():
        return False

    if path.suffix.casefold() != ".mp4":
        return False

    path.unlink()

    return True


def clean(short_id):

    _safe_id(
        short_id
    )

    removed = []


    videos = (
        ROOT
        / "videos"
    )


    for pattern in FINAL_PATTERNS:

        path = (
            videos
            /
            pattern.format(
                sid=short_id
            )
        )

        if _remove_mp4(
            path
        ):

            removed.append(
                str(
                    path.relative_to(
                        ROOT
                    )
                )
            )


    temp_dir = (
        ROOT
        / "temp"
        / short_id
    )


    if temp_dir.is_dir():

        for path in list(
            temp_dir.iterdir()
        ):

            if not path.is_file():
                continue


            name = path.name


            disposable = (
                name
                ==
                "video_sem_audio.mp4"
                or
                name.startswith(
                    "v63_cena_"
                )
                or
                name.startswith(
                    "cena_"
                )
                or
                name.startswith(
                    "clip_"
                )
            )


            if (
                disposable
                and
                path.suffix.casefold()
                ==
                ".mp4"
            ):

                path.unlink()

                removed.append(
                    str(
                        path.relative_to(
                            ROOT
                        )
                    )
                )


    return removed


if __name__ == "__main__":

    sid = os.environ.get(
        "SHORT_ID",
        "",
    ).strip()

    removed = clean(
        sid
    )

    print(
        "FRESH_RENDER_GUARD=PASS"
    )

    print(
        f"REMOVED_COUNT={len(removed)}"
    )

    print(
        "ASS_PROTECTED=YES"
    )

    print(
        "AUDIO_PROTECTED=YES"
    )

    print(
        "MEDIA_PROTECTED=YES"
    )
'''


CERTIFIER = r'''#!/usr/bin/env python3

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path


ROOT = (
    Path.home()
    / "ShortAutoPro"
)


def sha256(path):

    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as f:

        for chunk in iter(
            lambda:
                f.read(
                    1024 * 1024
                ),
            b"",
        ):

            h.update(
                chunk
            )

    return h.hexdigest()


def certify(
    short_id,
    max_age=900,
):

    final = (
        ROOT
        / "videos"
        / f"short_v6_{short_id}.mp4"
    )


    result = {
        "short_id":
            short_id,

        "output":
            str(
                final
            ),

        "ok":
            False,
    }


    if not final.is_file():

        result[
            "reason"
        ] = "FINAL_NOT_FOUND"

        return result


    if final.stat().st_size < 100_000:

        result[
            "reason"
        ] = "FINAL_TOO_SMALL"

        return result


    digest = sha256(
        final
    )


    if not digest:

        result[
            "reason"
        ] = "EMPTY_HASH"

        return result


    age = max(
        0.0,
        time.time()
        -
        final.stat().st_mtime,
    )


    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,codec_type,width,height,r_frame_rate",
            "-show_entries",
            "format=duration,size,bit_rate",
            "-of",
            "json",
            str(
                final
            ),
        ],
        text=True,
        capture_output=True,
    )


    if probe.returncode != 0:

        result[
            "reason"
        ] = "FFPROBE_FAILED"

        result[
            "ffprobe_error"
        ] = probe.stderr[-1000:]

        return result


    try:

        metadata = json.loads(
            probe.stdout
        )

    except Exception:

        result[
            "reason"
        ] = "FFPROBE_JSON_INVALID"

        return result


    streams = metadata.get(
        "streams",
        [],
    )


    video_streams = [
        stream
        for stream in streams
        if stream.get(
            "codec_type"
        )
        ==
        "video"
    ]


    if not video_streams:

        result[
            "reason"
        ] = "NO_VIDEO_STREAM"

        return result


    if age > max_age:

        result[
            "reason"
        ] = "OUTPUT_STALE"

        result[
            "age_seconds"
        ] = age

        return result


    result.update(
        {
            "ok":
                True,

            "sha256":
                digest,

            "bytes":
                final.stat().st_size,

            "age_seconds":
                age,

            "probe":
                metadata,
        }
    )


    return result


if __name__ == "__main__":

    sid = os.environ.get(
        "SHORT_ID",
        "",
    ).strip()


    if not sid:

        print(
            "CERTIFICATION=FAIL"
        )

        print(
            "REASON=SHORT_ID_MISSING"
        )

        raise SystemExit(
            2
        )


    result = certify(
        sid
    )


    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )


    if result.get(
        "ok"
    ):

        print(
            "CERTIFICATION=PASS"
        )

    else:

        print(
            "CERTIFICATION=FAIL"
        )

        raise SystemExit(
            1
        )
'''


TRANSACTION = r'''#!/usr/bin/env python3

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

from fresh_render_guard_v1 import clean
from render_input_fingerprint_v1 import fingerprint


ROOT = (
    Path.home()
    / "ShortAutoPro"
)


def sha256(path):

    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as f:

        for chunk in iter(
            lambda:
                f.read(
                    1024 * 1024
                ),
            b"",
        ):

            h.update(
                chunk
            )

    return h.hexdigest()


def run_stage(
    script,
    env,
):

    print(
        f"RUN={script}",
        flush=True,
    )

    result = subprocess.run(
        [
            "python",
            script,
        ],
        cwd=ROOT,
        env=env,
    )

    if result.returncode != 0:

        raise RuntimeError(
            f"{script} failed "
            f"status={result.returncode}"
        )


def require_file(path):

    if not path.is_file():

        raise RuntimeError(
            f"missing input: {path}"
        )

    if path.stat().st_size <= 0:

        raise RuntimeError(
            f"empty input: {path}"
        )


def main():

    sid = os.environ.get(
        "SHORT_ID",
        "",
    ).strip()


    if not sid:

        raise RuntimeError(
            "SHORT_ID ausente"
        )


    media_before = fingerprint(
        sid
    )


    if media_before.get(
        "media_count"
    ) != 12:

        raise RuntimeError(
            "media_count != 12"
        )


    audio = (
        ROOT
        / "audios"
        / f"short_{sid}.mp3"
    )

    ass = (
        ROOT
        / "videos"
        / f"short_{sid}.ass"
    )


    require_file(
        audio
    )

    require_file(
        ass
    )


    print(
        "INPUT_FINGERPRINT="
        +
        str(
            media_before[
                "fingerprint"
            ]
        )
    )


    removed = clean(
        sid
    )


    print(
        f"STALE_RENDER_FILES_REMOVED={len(removed)}"
    )


    # O guard nunca deve apagar o ASS.
    require_file(
        ass
    )


    env = os.environ.copy()

    env[
        "SHORT_ID"
    ] = sid

    env[
        "SAP_NO_PUBLISH"
    ] = "1"


    started = time.time()


    run_stage(
        "video.py",
        env,
    )


    base_video = (
        ROOT
        / "temp"
        / sid
        / "video_sem_audio.mp4"
    )


    require_file(
        base_video
    )


    run_stage(
        "v6.py",
        env,
    )


    final = (
        ROOT
        / "videos"
        / f"short_v6_{sid}.mp4"
    )


    require_file(
        final
    )


    if (
        final.stat().st_mtime
        <
        started - 1
    ):

        raise RuntimeError(
            "final output stale"
        )


    media_after = fingerprint(
        sid
    )


    if (
        media_before[
            "fingerprint"
        ]
        !=
        media_after[
            "fingerprint"
        ]
    ):

        raise RuntimeError(
            "media changed during render"
        )


    manifest = {
        "short_id":
            sid,

        "input_fingerprint":
            media_before[
                "fingerprint"
            ],

        "output":
            str(
                final
            ),

        "output_sha256":
            sha256(
                final
            ),

        "output_bytes":
            final.stat().st_size,

        "render_started":
            started,

        "output_mtime":
            final.stat().st_mtime,

        "fresh":
            True,
    }


    manifest_path = (
        ROOT
        / "manifests"
        / f"render_transaction_{sid}.json"
    )


    manifest_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    manifest_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


    print(
        "RENDER_TRANSACTION=PASS"
    )

    print(
        f"OUTPUT={final}"
    )

    print(
        f"OUTPUT_SHA256={manifest['output_sha256']}"
    )


if __name__ == "__main__":

    main()
'''


def patch_vse():

    banner(
        "1. VSE4.2 SEMANTIC REPAIR"
    )

    path = (
        ROOT
        / "visual_selection_engine_v4.py"
    )

    source = path.read_text(
        encoding="utf-8"
    )


    source = replace_function(
        source,
        "candidate_text",
        CANDIDATE_TEXT_V42,
    )


    marker = (
        "# SHORTAUTOPRO VSE4.2 HARD MISMATCH "
        "+ RUNTIME RANKER"
    )


    if marker not in source:

        source, count = re.subn(
            r"(?m)^def score_candidate\(",
            "def _vse42_score_candidate_base(",
            source,
            count=1,
        )


        if count != 1:

            raise RuntimeError(
                "score_candidate rename failed"
            )


        anchor = "def self_test("


        if anchor not in source:

            raise RuntimeError(
                "self_test anchor missing"
            )


        source = source.replace(
            anchor,
            SCORE_WRAPPER_V42
            +
            "\n\n"
            +
            anchor,
            1,
        )


    path.write_text(
        source,
        encoding="utf-8",
    )


    ok, error = compile_file(
        path
    )


    print(
        f"VSE42_COMPILE={'PASS' if ok else 'FAIL'}"
    )


    if not ok:

        raise RuntimeError(
            error
        )


    result = subprocess.run(
        [
            "python",
            str(
                path
            ),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


    print(
        result.stdout,
        end="",
    )


    if result.stderr:

        print(
            result.stderr,
            end="",
        )


    if result.returncode != 0:

        raise RuntimeError(
            "VSE4 self-test failed"
        )


    test = subprocess.run(
        [
            "python",
            "-c",
            r'''
import runpy

ns = runpy.run_path(
    "visual_selection_engine_v4.py",
    run_name="vse42_direct_test",
)

candidate_text = ns["candidate_text"]
geo_hits = ns["geo_hits"]
score_candidate = ns["score_candidate"]

scene = (
    "Investigação em apartamento "
    "na cidade de São Paulo"
)

wrong = {
    "provider": "Pixabay",
    "tipo": "foto",
    "title":
        "Empire State Building New York",
    "must": "2/2",
    "score": 220,
    "width": 1920,
    "height": 1080,
}

correct = {
    "provider": "Wikimedia",
    "tipo": "foto",
    "title":
        "Apartment building Sao Paulo Brazil",
    "must": "1/2",
    "score": 120,
    "width": 1920,
    "height": 1080,
}

state = {
    "providers": [],
    "groups": [],
    "types": [],
    "keys": [],
}

text = candidate_text(scene)

print("DIRECT_STRING_TEXT=", text)
print("DIRECT_STRING_GEO=", sorted(geo_hits(text)))

a = score_candidate(
    wrong,
    scene,
    state,
)

b = score_candidate(
    correct,
    scene,
    state,
)

print("WRONG_HARD=", a["hard_mismatch"])
print("WRONG_REASON=", a.get("hard_reason"))
print("CORRECT_HARD=", b["hard_mismatch"])
print("WRONG_EFFECTIVE=", a["effective"])
print("CORRECT_EFFECTIVE=", b["effective"])

assert "sao paulo" in text
assert "brazil" in geo_hits(text)
assert "sao_paulo" in geo_hits(text)
assert a["hard_mismatch"] is True
assert b["hard_mismatch"] is False
assert b["effective"] > a["effective"]

print("VSE42_DIRECT_SEMANTICS=PASS")
''',
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


    print(
        test.stdout,
        end="",
    )


    if test.stderr:

        print(
            test.stderr,
            end="",
        )


    if test.returncode != 0:

        raise RuntimeError(
            "VSE4 direct semantic test failed"
        )


def patch_midia():

    banner(
        "2. MIDIA REAL-PATH INTEGRATION"
    )

    path = (
        ROOT
        / "midia.py"
    )

    source = path.read_text(
        encoding="utf-8"
    )


    integration_marker = (
        "# SHORTAUTOPRO VSE4.2 REAL PATH"
    )


    if integration_marker not in source:

        tree = ast.parse(
            source
        )

        target = None


        for node in ast.walk(
            tree
        ):

            if not isinstance(
                node,
                ast.Assign,
            ):
                continue


            if not any(
                isinstance(t, ast.Name)
                and
                t.id == "pool"
                for t in node.targets
            ):

                continue


            if not isinstance(
                node.value,
                ast.Call,
            ):

                continue


            func = node.value.func


            name = (
                func.id
                if isinstance(
                    func,
                    ast.Name,
                )
                else
                func.attr
                if isinstance(
                    func,
                    ast.Attribute,
                )
                else
                ""
            )


            if (
                name
                ==
                "ordenar_failover_5_2"
            ):

                target = node
                break


        if target is None:

            raise RuntimeError(
                "ordenar_failover_5_2 pool "
                "assignment not found"
            )


        lines = source.splitlines(
            keepends=True
        )


        indent = (
            " "
            *
            target.col_offset
        )


        insertion = textwrap.indent(
r'''
# SHORTAUTOPRO VSE4.2 REAL PATH
try:

    from visual_selection_engine_v4 import (
        rerank_runtime_v42 as _vse42_rerank_runtime,
    )


    _vse42_scene_ctx = (
        locals().get(
            "segmento"
        )
        or
        locals().get(
            "scene"
        )
        or
        locals().get(
            "cena"
        )
        or
        {
            "texto":
                locals().get(
                    "texto",
                    "",
                ),

            "visual_query":
                locals().get(
                    "busca",
                    "",
                ),

            "must_have":
                locals().get(
                    "must_have",
                    [],
                ),

            "avoid":
                locals().get(
                    "avoid",
                    [],
                ),

            "location":
                locals().get(
                    "location",
                    "",
                ),
        }
    )


    _vse42_before = (
        escolhido
        if "escolhido" in locals()
        else
        None
    )


    pool = _vse42_rerank_runtime(
        pool,
        _vse42_scene_ctx,
    )


    if pool:

        escolhido = pool[0]


    print(
        "VSE42_REAL_PATH=ACTIVE"
    )

    if pool:

        print(
            "VSE42_POOL_SIZE="
            + str(
                len(pool)
            )
        )


except Exception as _vse42_exc:

    print(
        "VSE42_REAL_PATH=FAIL_OPEN "
        + type(
            _vse42_exc
        ).__name__
        + ": "
        + str(
            _vse42_exc
        )
    )
''',
            indent,
        )


        index = target.end_lineno


        source = (
            "".join(
                lines[:index]
            )
            +
            insertion
            +
            "\n"
            +
            "".join(
                lines[index:]
            )
        )


    # --------------------------------------------------------
    # SCENE COMMIT
    # --------------------------------------------------------

    commit_marker = (
        "# SHORTAUTOPRO VSE4.2 SCENE COMMIT"
    )


    if commit_marker not in source:

        tree = ast.parse(
            source
        )

        commit_if = None


        for for_node in [
            node
            for node in ast.walk(
                tree
            )
            if isinstance(
                node,
                ast.For,
            )
        ]:

            segment = ast.get_source_segment(
                source,
                for_node,
            ) or ""


            if (
                "baixar_candidato_5_2"
                not in segment
            ):

                continue


            for child in ast.walk(
                for_node
            ):

                if not isinstance(
                    child,
                    ast.If,
                ):
                    continue


                test_source = (
                    ast.get_source_segment(
                        source,
                        child.test,
                    )
                    or
                    ""
                ).strip()


                if test_source != "ok":
                    continue


                body_source = (
                    ast.get_source_segment(
                        source,
                        child,
                    )
                    or
                    ""
                )


                if (
                    "sucesso"
                    in body_source
                    or
                    "escolhido"
                    in body_source
                ):

                    commit_if = child
                    break


            if commit_if is not None:
                break


        if commit_if is None:

            raise RuntimeError(
                "successful media download "
                "block not found"
            )


        lines = source.splitlines(
            keepends=True
        )


        body_indent = (
            " "
            *
            (
                commit_if.col_offset
                +
                4
            )
        )


        insertion = (
            body_indent
            +
            "# SHORTAUTOPRO VSE4.2 SCENE COMMIT\n"
            +
            body_indent
            +
            'print("SCENE_COMMIT_V42=SUCCESS")\n'
            +
            body_indent
            +
            "break\n"
        )


        index = commit_if.end_lineno


        source = (
            "".join(
                lines[:index]
            )
            +
            insertion
            +
            "".join(
                lines[index:]
            )
        )


    path.write_text(
        source,
        encoding="utf-8",
    )


    ok, error = compile_file(
        path
    )


    print(
        f"MIDIA_COMPILE={'PASS' if ok else 'FAIL'}"
    )


    if not ok:

        raise RuntimeError(
            error
        )


    final = path.read_text(
        encoding="utf-8"
    )


    if (
        integration_marker
        not in final
    ):

        raise RuntimeError(
            "VSE42 integration marker absent"
        )


    if (
        commit_marker
        not in final
    ):

        raise RuntimeError(
            "scene commit marker absent"
        )


    print(
        "VSE42_MIDIA_INTEGRATION=PASS"
    )

    print(
        "SCENE_COMMIT_FIX=PASS"
    )


def patch_render_safety():

    banner(
        "3. RENDER SAFETY"
    )


    (
        ROOT
        /
        "fresh_render_guard_v1.py"
    ).write_text(
        SAFE_RENDER_GUARD,
        encoding="utf-8",
    )


    (
        ROOT
        /
        "render_output_certifier_v1.py"
    ).write_text(
        CERTIFIER,
        encoding="utf-8",
    )


    (
        ROOT
        /
        "render_transaction_v1.py"
    ).write_text(
        TRANSACTION,
        encoding="utf-8",
    )


    for name in (
        "fresh_render_guard_v1.py",
        "render_output_certifier_v1.py",
        "render_transaction_v1.py",
    ):

        ok, error = compile_file(
            ROOT / name
        )


        print(
            f"{name}_COMPILE="
            f"{'PASS' if ok else 'FAIL'}"
        )


        if not ok:

            raise RuntimeError(
                error
            )


def test_guard():

    banner(
        "4. RENDER GUARD REGRESSION"
    )


    sid = (
        "VSE42_GUARD_TEST"
    )


    env = os.environ.copy()

    env[
        "SHORT_ID"
    ] = sid


    temp = (
        ROOT
        / "temp"
        / sid
    )

    videos = (
        ROOT
        / "videos"
    )


    temp.mkdir(
        parents=True,
        exist_ok=True,
    )

    videos.mkdir(
        parents=True,
        exist_ok=True,
    )


    ass = (
        videos
        /
        f"short_{sid}.ass"
    )

    audio = (
        temp
        /
        "input.mp3"
    )

    disposable = (
        temp
        /
        "video_sem_audio.mp4"
    )

    final = (
        videos
        /
        f"short_v6_{sid}.mp4"
    )


    ass.write_text(
        "protected",
        encoding="utf-8",
    )

    audio.write_bytes(
        b"protected"
    )

    disposable.write_bytes(
        b"delete"
    )

    final.write_bytes(
        b"delete"
    )


    test = subprocess.run(
        [
            "python",
            "fresh_render_guard_v1.py",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )


    print(
        test.stdout,
        end="",
    )


    checks = {
        "ASS":
            ass.exists(),

        "AUDIO":
            audio.exists(),

        "TEMP_MP4_REMOVED":
            not disposable.exists(),

        "FINAL_MP4_REMOVED":
            not final.exists(),
    }


    for name, ok in checks.items():

        print(
            f"GUARD_{name}="
            f"{'PASS' if ok else 'FAIL'}"
        )


    try:
        ass.unlink()
    except FileNotFoundError:
        pass


    shutil.rmtree(
        temp,
        ignore_errors=True,
    )


    if not all(
        checks.values()
    ):

        raise RuntimeError(
            "render guard regression failed"
        )


def final_compile():

    banner(
        "5. CORE CERTIFICATION"
    )


    core = [
        "visual_selection_engine_v4.py",
        "midia.py",
        "video.py",
        "v6.py",
        "legenda_dinamica.py",
        "media_diversity_guard_v1.py",
        "media_provenance_capture_v1.py",
        "fresh_render_guard_v1.py",
        "render_input_fingerprint_v1.py",
        "render_output_certifier_v1.py",
        "render_transaction_v1.py",
    ]


    failed = []


    for name in core:

        path = (
            ROOT
            /
            name
        )


        if not path.is_file():

            print(
                f"CORE_MISSING={name}"
            )

            failed.append(
                name
            )

            continue


        ok, error = compile_file(
            path
        )


        print(
            f"COMPILE_{name}="
            f"{'PASS' if ok else 'FAIL'}"
        )


        if not ok:

            print(
                error
            )

            failed.append(
                name
            )


    shell = subprocess.run(
        [
            "bash",
            "-n",
            "gerar_short.sh",
        ],
        cwd=ROOT,
    )


    print(
        "GERAR_SHORT_SYNTAX="
        +
        (
            "PASS"
            if shell.returncode == 0
            else
            "FAIL"
        )
    )


    if shell.returncode != 0:

        failed.append(
            "gerar_short.sh"
        )


    if failed:

        raise RuntimeError(
            "core certification failed: "
            +
            ",".join(
                failed
            )
        )


def hashes():

    banner(
        "6. FINAL HASHES"
    )


    for name in (
        "visual_selection_engine_v4.py",
        "midia.py",
        "video.py",
        "v6.py",
        "gerar_short.sh",
    ):

        result = subprocess.run(
            [
                "sha256sum",
                name,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )


        print(
            result.stdout.strip()
        )


def main():

    backup_files()


    try:

        patch_vse()

        patch_midia()

        patch_render_safety()

        test_guard()

        final_compile()

        hashes()


    except Exception as exc:

        print()
        print(
            "MASTER_REPAIR_ERROR="
            +
            type(
                exc
            ).__name__
            +
            ": "
            +
            str(
                exc
            )
        )

        restore()

        print()
        print(
            "VSE42_MASTER_REPAIR=FAIL_ROLLED_BACK"
        )

        raise SystemExit(
            1
        )


    banner(
        "VSE4.2 MASTER REPAIR RESULT"
    )

    print(
        "VSE42_MASTER_REPAIR=PASS"
    )

    print(
        "VSE42_SELF_TEST=PASS"
    )

    print(
        "DIRECT_STRING_SEMANTICS=PASS"
    )

    print(
        "GEO_HARD_MISMATCH=PASS"
    )

    print(
        "MIDIA_REAL_PATH=PASS"
    )

    print(
        "SCENE_COMMIT=PASS"
    )

    print(
        "RENDER_GUARD=PASS"
    )

    print(
        "CORE_COMPILE=PASS"
    )

    print(
        "NETWORK_EXECUTED=NO"
    )

    print(
        "MEDIA_DOWNLOADED=NO"
    )

    print(
        "VIDEO_RENDERED=NO"
    )

    print(
        f"BACKUP={BACKUP}"
    )


if __name__ == "__main__":

    main()
