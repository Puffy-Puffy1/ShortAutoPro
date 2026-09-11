#!/usr/bin/env python3

from pathlib import Path
import ast
import builtins
import hashlib
import os
import py_compile
import re
import runpy
import shutil
import subprocess
import symtable
import traceback


ROOT = Path.home() / "ShortAutoPro"

STAMP = __import__("datetime").datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

BACKUP = (
    ROOT
    / "backups"
    / f"master_repair_v1_{STAMP}"
)

BACKUP.mkdir(
    parents=True,
    exist_ok=True,
)


PASS_COUNT = 0
FAIL_COUNT = 0
WARN_COUNT = 0


def title(text):

    print()
    print("=" * 72)
    print(text)
    print("=" * 72)


def passed(name, extra=""):

    global PASS_COUNT

    PASS_COUNT += 1

    line = f"{name}=PASS"

    if extra:
        line += f" | {extra}"

    print(line)


def failed(name, extra=""):

    global FAIL_COUNT

    FAIL_COUNT += 1

    line = f"{name}=FAIL"

    if extra:
        line += f" | {extra}"

    print(line)


def warning(name, extra=""):

    global WARN_COUNT

    WARN_COUNT += 1

    line = f"{name}=WARN"

    if extra:
        line += f" | {extra}"

    print(line)


def sha256(path):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def backup_file(path):

    if not path.is_file():
        return None

    rel = path.relative_to(ROOT)

    dest = BACKUP / rel

    dest.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        path,
        dest,
    )

    return dest


# ============================================================
# 1. CRITICAL FILES
# ============================================================

title("1. CRITICAL FILE INVENTORY")

critical = [
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "visual_selection_engine_v4.py",
    "visual_scene_commit_lock_v1.py",
    "visual_must_rescue_v1.py",
    "fresh_render_guard_v1.py",
]

for name in critical:

    path = ROOT / name

    if path.is_file():

        print(
            f"FOUND={name} "
            f"bytes={path.stat().st_size} "
            f"sha256={sha256(path)}"
        )

    else:

        warning(
            "CRITICAL_FILE_MISSING",
            name,
        )


# ============================================================
# 2. BACKUP
# ============================================================

title("2. MASTER BACKUP")

for name in critical:

    path = ROOT / name

    if path.is_file():

        dest = backup_file(path)

        print(
            f"BACKUP={path.name} -> "
            f"{dest.relative_to(ROOT)}"
        )

passed(
    "MASTER_BACKUP",
    str(BACKUP.relative_to(ROOT)),
)


# ============================================================
# 3. DUPLICATE INSTALL NORMALIZER
# ============================================================

title("3. DUPLICATE INSTALL NORMALIZATION")


def normalize_install(path):

    src = path.read_text(
        encoding="utf-8",
    )

    tree = ast.parse(src)

    defs = [
        n
        for n in tree.body
        if (
            isinstance(n, ast.FunctionDef)
            and n.name == "install"
        )
    ]

    print()
    print(f"FILE={path.name}")
    print(f"INSTALL_COUNT_BEFORE={len(defs)}")

    if len(defs) <= 1:

        print("NORMALIZE_NEEDED=NO")

        return True


    # --------------------------------------------------------
    # Procura referências executadas no nível do módulo.
    # Não altera referências dentro de funções/classes,
    # pois ali o nome é resolvido em runtime.
    # --------------------------------------------------------

    refs = []


    class Visitor(ast.NodeVisitor):

        def __init__(self):
            self.runtime_depth = 0

        def visit_FunctionDef(self, node):

            # Defaults/decorators são avaliados no módulo,
            # mas referência a install nesses locais é rara.
            #
            # Auditamos explicitamente e abortamos se houver.
            header_nodes = (
                list(node.decorator_list)
                +
                list(node.args.defaults)
                +
                [
                    x
                    for x in node.args.kw_defaults
                    if x is not None
                ]
            )

            for h in header_nodes:

                for x in ast.walk(h):

                    if (
                        isinstance(x, ast.Name)
                        and
                        isinstance(x.ctx, ast.Load)
                        and
                        x.id == "install"
                    ):

                        raise RuntimeError(
                            "install usado em "
                            f"default/decorator line={x.lineno}"
                        )

            # Corpo executa depois; mantém nome canônico.
            return

        def visit_AsyncFunctionDef(self, node):
            return

        def visit_ClassDef(self, node):
            return

        def visit_Lambda(self, node):
            return

        def visit_Name(self, node):

            if (
                isinstance(node.ctx, ast.Load)
                and
                node.id == "install"
            ):

                refs.append(
                    node
                )


    try:

        Visitor().visit(tree)

    except RuntimeError as exc:

        print(
            f"NORMALIZE=HOLD reason={exc}"
        )

        return False


    # --------------------------------------------------------
    # Cada install ganha identidade própria.
    # --------------------------------------------------------

    def_names = {
        node.lineno:
            f"_install_stage_preserved_{i}"
        for i, node in enumerate(
            defs,
            start=1,
        )
    }


    replacements = {}


    def add_replacement(
        line_index,
        start,
        end,
        value,
    ):

        replacements.setdefault(
            line_index,
            [],
        ).append(
            (
                start,
                end,
                value,
            )
        )


    lines = src.splitlines(
        keepends=True,
    )


    # Renomeia definições.
    for node in defs:

        li = node.lineno - 1

        line = lines[li]

        match = re.search(
            r"\bdef\s+install\s*\(",
            line,
        )

        if not match:

            print(
                f"NORMALIZE=HOLD "
                f"unexpected def line={node.lineno}"
            )

            return False

        name_start = line.find(
            "install",
            match.start(),
        )

        add_replacement(
            li,
            name_start,
            name_start + len("install"),
            def_names[node.lineno],
        )


    # --------------------------------------------------------
    # Reescreve somente referências executadas no módulo
    # para a versão de install que existia naquela linha.
    # --------------------------------------------------------

    for ref in refs:

        previous = [
            d
            for d in defs
            if d.lineno < ref.lineno
        ]

        if not previous:

            print(
                f"NORMALIZE=HOLD "
                f"install reference before definition "
                f"line={ref.lineno}"
            )

            return False


        visible = previous[-1]

        new_name = def_names[
            visible.lineno
        ]


        li = ref.lineno - 1

        start = ref.col_offset

        end = getattr(
            ref,
            "end_col_offset",
            start + len("install"),
        )


        # Proteção contra offsets inesperados.
        segment = lines[li][start:end]

        if segment != "install":

            pos = lines[li].find(
                "install",
                max(0, start - 3),
            )

            if pos < 0:

                print(
                    "NORMALIZE=HOLD "
                    f"cannot resolve reference "
                    f"line={ref.lineno}"
                )

                return False

            start = pos
            end = pos + len("install")


        add_replacement(
            li,
            start,
            end,
            new_name,
        )


    # Aplica da direita para a esquerda.
    for li, reps in replacements.items():

        line = lines[li]

        for start, end, value in sorted(
            reps,
            key=lambda x: x[0],
            reverse=True,
        ):

            line = (
                line[:start]
                +
                value
                +
                line[end:]
            )

        lines[li] = line


    active_name = def_names[
        defs[-1].lineno
    ]


    new_src = "".join(lines)


    new_src += (
        "\n\n"
        "# SHORTAUTOPRO CANONICAL INSTALL ALIAS V1\n"
        f"install = {active_name}\n"
    )


    # Parse antes de salvar.
    ast.parse(
        new_src
    )


    path.write_text(
        new_src,
        encoding="utf-8",
    )


    # Reaudita.
    verify = ast.parse(
        new_src
    )

    canonical_defs = [
        n
        for n in verify.body
        if (
            isinstance(n, ast.FunctionDef)
            and
            n.name == "install"
        )
    ]

    preserved = [
        n.name
        for n in verify.body
        if (
            isinstance(n, ast.FunctionDef)
            and
            n.name.startswith(
                "_install_stage_preserved_"
            )
        )
    ]


    print(
        f"INSTALL_COUNT_AFTER="
        f"{len(canonical_defs)}"
    )

    print(
        "PRESERVED_STAGES="
        +
        ",".join(preserved)
    )

    print(
        f"CANONICAL_ALIAS={active_name}"
    )


    # Não queremos mais def install();
    # o símbolo install agora é alias explícito.
    if preserved:

        print(
            "DUPLICATE_INSTALL_NORMALIZATION=PASS"
        )

        return True


    return False


for filename in (
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
):

    path = ROOT / filename

    if not path.is_file():

        warning(
            "INSTALL_NORMALIZER_FILE_MISSING",
            filename,
        )

        continue


    try:

        backup_file(path)

        ok = normalize_install(
            path
        )

        if ok:
            passed(
                "INSTALL_NORMALIZER",
                filename,
            )
        else:
            warning(
                "INSTALL_NORMALIZER_HOLD",
                filename,
            )

    except Exception as exc:

        failed(
            "INSTALL_NORMALIZER",
            f"{filename}: {type(exc).__name__}: {exc}",
        )

        traceback.print_exc()


# ============================================================
# 4. VSE4 GEO ENGINE FIX
# ============================================================

title("4. VSE4 GEOGRAPHIC HARD-MISMATCH REPAIR")

vse = ROOT / "visual_selection_engine_v4.py"


def replace_function(
    source,
    name,
    replacement,
):

    tree = ast.parse(
        source
    )

    matches = [
        node
        for node in tree.body
        if (
            isinstance(node, ast.FunctionDef)
            and
            node.name == name
        )
    ]

    if len(matches) != 1:

        raise RuntimeError(
            f"{name} definition count="
            f"{len(matches)}"
        )


    node = matches[0]

    lines = source.splitlines(
        keepends=True,
    )

    return (
        "".join(
            lines[:node.lineno - 1]
        )
        +
        replacement.rstrip()
        +
        "\n"
        +
        "".join(
            lines[node.end_lineno:]
        )
    )


if vse.is_file():

    try:

        backup_file(vse)

        src = vse.read_text(
            encoding="utf-8",
        )


        # ----------------------------------------------------
        # geo_hits com boundary-safe matching.
        # Impede, por exemplo:
        # "uk" dentro de "ukraine".
        # ----------------------------------------------------

        geo_replacement = r'''
def geo_hits(text):

    normalized_text = norm(
        text
    )

    padded = (
        " "
        +
        normalized_text
        +
        " "
    )

    result = set()

    for group, aliases in GEO_GROUPS.items():

        for alias in aliases:

            normalized_alias = norm(
                alias
            )

            if not normalized_alias:
                continue

            needle = (
                " "
                +
                normalized_alias
                +
                " "
            )

            if needle in padded:

                result.add(
                    group
                )

                break

    return result
'''


        src = replace_function(
            src,
            "geo_hits",
            geo_replacement,
        )


        marker = (
            "# SHORTAUTOPRO VSE4 GEO HARD MISMATCH V4.1.4"
        )


        if marker not in src:

            tree = ast.parse(
                src
            )

            self_tests = [
                n
                for n in tree.body
                if (
                    isinstance(
                        n,
                        ast.FunctionDef,
                    )
                    and
                    n.name == "self_test"
                )
            ]

            if len(self_tests) != 1:

                raise RuntimeError(
                    "self_test definition count="
                    f"{len(self_tests)}"
                )


            insertion_line = (
                self_tests[0].lineno - 1
            )


            wrapper = r'''
# SHORTAUTOPRO VSE4 GEO HARD MISMATCH V4.1.4

_VSE4_SCORE_CANDIDATE_BEFORE_GEO_HARD = (
    score_candidate
)


_VSE4_COUNTRY_GROUPS = {
    "brazil",
    "usa",
    "united_kingdom",
    "france",
    "italy",
    "germany",
    "spain",
    "portugal",
    "japan",
    "china",
    "russia",
    "ukraine",
    "mexico",
    "argentina",
    "canada",
    "australia",
    "india",
    "south_korea",
    "egypt",
}


_VSE4_CITY_PARENT = {
    "sao_paulo": "brazil",
    "rio_de_janeiro": "brazil",
    "brasilia": "brazil",

    "new_york": "usa",
    "los_angeles": "usa",
    "washington_dc": "usa",

    "london": "united_kingdom",
    "paris": "france",
    "rome": "italy",
    "tokyo": "japan",
}


def _vse4_geo_conflict(
    scene,
    candidate,
):

    try:

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


        # Sem geografia explícita dos dois lados:
        # não fazemos hard block.
        if not scene_geo or not candidate_geo:

            return (
                False,
                "",
            )


        scene_countries = (
            scene_geo
            &
            _VSE4_COUNTRY_GROUPS
        )

        candidate_countries = (
            candidate_geo
            &
            _VSE4_COUNTRY_GROUPS
        )


        # País explicitamente diferente.
        if (
            scene_countries
            and
            candidate_countries
            and
            scene_countries.isdisjoint(
                candidate_countries
            )
        ):

            return (
                True,
                "GEO_COUNTRY_CONTRADICTION",
            )


        scene_cities = {
            item
            for item in scene_geo
            if item in _VSE4_CITY_PARENT
        }

        candidate_cities = {
            item
            for item in candidate_geo
            if item in _VSE4_CITY_PARENT
        }


        # Cena explicitamente cita uma cidade
        # e candidato explicitamente identifica outra.
        if (
            scene_cities
            and
            candidate_cities
            and
            scene_cities.isdisjoint(
                candidate_cities
            )
        ):

            return (
                True,
                "GEO_CITY_CONTRADICTION",
            )


        return (
            False,
            "",
        )


    except Exception:

        # Fail-open:
        # nunca derruba a seleção por erro do safety layer.
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

    result = (
        _VSE4_SCORE_CANDIDATE_BEFORE_GEO_HARD(
            candidate,
            scene,
            state,
            *args,
            **kwargs,
        )
    )


    if not isinstance(
        result,
        dict,
    ):

        return result


    conflict, reason = (
        _vse4_geo_conflict(
            scene,
            candidate,
        )
    )


    if not conflict:

        return result


    # Copia para não modificar estrutura compartilhada.
    result = dict(
        result
    )


    result[
        "hard_mismatch"
    ] = True

    result[
        "hard_reason"
    ] = reason

    result[
        "geo_conflict"
    ] = True


    # Hard contradiction deve ficar abaixo de
    # qualquer candidato semanticamente plausível,
    # mesmo quando o score bruto do stock provider é alto.
    try:

        old_effective = float(
            result.get(
                "effective",
                0.0,
            )
        )

    except Exception:

        old_effective = 0.0


    result[
        "effective_before_geo_hard"
    ] = old_effective


    result[
        "effective"
    ] = min(
        old_effective,
        -1000000.0,
    )


    return result
'''


            lines = src.splitlines(
                keepends=True,
            )

            src = (
                "".join(
                    lines[:insertion_line]
                )
                +
                wrapper
                +
                "\n\n"
                +
                "".join(
                    lines[insertion_line:]
                )
            )


        ast.parse(
            src
        )

        vse.write_text(
            src,
            encoding="utf-8",
        )

        passed(
            "VSE4_GEO_PATCH",
            "boundary + hard mismatch",
        )


    except Exception as exc:

        failed(
            "VSE4_GEO_PATCH",
            f"{type(exc).__name__}: {exc}",
        )

        traceback.print_exc()

else:

    failed(
        "VSE4_GEO_PATCH",
        "visual_selection_engine_v4.py missing",
    )


# ============================================================
# 5. FRESH RENDER GUARD
# ============================================================

title("5. FRESH RENDER GUARD HARDENING")

guard = ROOT / "fresh_render_guard_v1.py"


safe_guard = r'''#!/usr/bin/env python3

import os
from pathlib import Path


ROOT = (
    Path.home()
    / "ShortAutoPro"
)


# Arquivos que são INPUTS e jamais podem ser removidos
# pelo limpador de render.
PROTECTED_SUFFIXES = {
    ".ass",
    ".srt",
    ".vtt",

    ".mp3",
    ".wav",
    ".aac",
    ".m4a",
    ".ogg",

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


def _safe_short_id(value):

    value = str(
        value or ""
    ).strip()

    if not value:
        raise RuntimeError(
            "SHORT_ID vazio"
        )

    if (
        "/" in value
        or
        "\\" in value
        or
        ".." in value
    ):
        raise RuntimeError(
            "SHORT_ID inseguro"
        )

    return value


def clean(short_id):

    sid = _safe_short_id(
        short_id
    )

    removed = []


    # --------------------------------------------------------
    # Somente outputs finais conhecidos.
    # --------------------------------------------------------

    videos = (
        ROOT
        / "videos"
    )


    for pattern in FINAL_PATTERNS:

        path = (
            videos
            /
            pattern.format(
                sid=sid
            )
        )

        if (
            path.is_file()
            and
            path.suffix.lower()
            not in PROTECTED_SUFFIXES
        ):

            path.unlink()

            removed.append(
                str(
                    path.relative_to(
                        ROOT
                    )
                )
            )


    # --------------------------------------------------------
    # Somente MP4s intermediários explicitamente conhecidos
    # dentro do temp namespace do Short.
    # --------------------------------------------------------

    temp = (
        ROOT
        / "temp"
        / sid
    )


    if temp.is_dir():

        for path in list(
            temp.iterdir()
        ):

            if not path.is_file():
                continue


            if (
                path.suffix.lower()
                !=
                ".mp4"
            ):
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
                    "scene_render_"
                )

                or
                name.startswith(
                    "clip_"
                )

                or
                name.startswith(
                    "cena_"
                )
            )


            if not disposable:
                continue


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
    )

    removed = clean(
        sid
    )

    print(
        "FRESH_RENDER_GUARD=PASS"
    )

    print(
        f"REMOVED_COUNT={len(removed)}"
    )

    for item in removed:

        print(
            f"REMOVED={item}"
        )
'''


if guard.is_file():

    try:

        current = guard.read_text(
            encoding="utf-8",
        )


        unsafe = (
            'rglob("*")' in current
            or
            "rglob('*')" in current
            or
            "name contains SHORT_ID" in current
        )


        # Instalamos a versão segura também quando
        # não conseguimos identificar claramente a versão.
        if (
            "PROTECTED_SUFFIXES" not in current
            or
            unsafe
        ):

            backup_file(
                guard
            )

            guard.write_text(
                safe_guard,
                encoding="utf-8",
            )

            passed(
                "FRESH_RENDER_GUARD_PATCH",
                "safe allowlist installed",
            )

        else:

            passed(
                "FRESH_RENDER_GUARD_PATCH",
                "already hardened",
            )


    except Exception as exc:

        failed(
            "FRESH_RENDER_GUARD_PATCH",
            str(exc),
        )

else:

    warning(
        "FRESH_RENDER_GUARD",
        "module missing",
    )


# ============================================================
# 6. ROOT PYTHON COMPILE
# ============================================================

title("6. ROOT PYTHON COMPILE")

python_fail = []


for path in sorted(
    ROOT.glob("*.py")
):

    try:

        py_compile.compile(
            str(path),
            doraise=True,
        )

        print(
            f"PY_COMPILE=PASS | {path.name}"
        )

    except Exception as exc:

        python_fail.append(
            path.name
        )

        print(
            f"PY_COMPILE=FAIL | "
            f"{path.name} | {exc}"
        )


if python_fail:

    failed(
        "ROOT_PYTHON_COMPILE",
        ",".join(python_fail),
    )

else:

    passed(
        "ROOT_PYTHON_COMPILE",
        f"{len(list(ROOT.glob('*.py')))} files",
    )


# ============================================================
# 7. SHELL SYNTAX
# ============================================================

title("7. SHELL SYNTAX")

shell_fail = []


for path in sorted(
    ROOT.glob("*.sh")
):

    result = subprocess.run(
        [
            "bash",
            "-n",
            str(path),
        ],
        capture_output=True,
        text=True,
    )


    if result.returncode == 0:

        print(
            f"SHELL_SYNTAX=PASS | {path.name}"
        )

    else:

        shell_fail.append(
            path.name
        )

        print(
            f"SHELL_SYNTAX=FAIL | {path.name}"
        )

        if result.stderr:
            print(
                result.stderr.strip()
            )


if shell_fail:

    failed(
        "ROOT_SHELL_SYNTAX",
        ",".join(shell_fail),
    )

else:

    passed(
        "ROOT_SHELL_SYNTAX"
    )


# ============================================================
# 8. DUPLICATE TOP-LEVEL FUNCTION AUDIT
# ============================================================

title("8. DUPLICATE TOP-LEVEL FUNCTION AUDIT")

duplicate_files = {}


for path in sorted(
    ROOT.glob("*.py")
):

    try:

        tree = ast.parse(
            path.read_text(
                encoding="utf-8",
            )
        )

    except Exception:

        continue


    names = {}


    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            names.setdefault(
                node.name,
                [],
            ).append(
                node.lineno
            )


    dup = {
        name: lines
        for name, lines in names.items()
        if len(lines) > 1
    }


    if dup:

        duplicate_files[
            path.name
        ] = dup


        for name, lines in dup.items():

            print(
                f"DUPLICATE_DEF "
                f"file={path.name} "
                f"name={name} "
                f"lines={lines}"
            )


if duplicate_files:

    warning(
        "DUPLICATE_TOP_LEVEL_DEFS",
        f"{len(duplicate_files)} files",
    )

else:

    passed(
        "DUPLICATE_TOP_LEVEL_DEFS",
        "none",
    )


# ============================================================
# 9. VSE4 TRUE GLOBAL AUDIT
# ============================================================

title("9. VSE4 TRUE GLOBAL AUDIT")


if vse.is_file():

    try:

        src = vse.read_text(
            encoding="utf-8",
        )

        table = symtable.symtable(
            src,
            str(vse),
            "exec",
        )


        module_defined = set()


        for symbol in table.get_symbols():

            if (
                symbol.is_assigned()
                or
                symbol.is_imported()
                or
                symbol.is_namespace()
            ):

                module_defined.add(
                    symbol.get_name()
                )


        unresolved = set()

        builtin_names = set(
            dir(builtins)
        )


        def walk(scope):

            for child in scope.get_children():

                for symbol in child.get_symbols():

                    name = symbol.get_name()

                    if not symbol.is_referenced():
                        continue

                    if not symbol.is_global():
                        continue

                    if name in module_defined:
                        continue

                    if name in builtin_names:
                        continue

                    unresolved.add(
                        name
                    )

                walk(
                    child
                )


        walk(
            table
        )


        if unresolved:

            failed(
                "VSE4_GLOBAL_AUDIT",
                ",".join(
                    sorted(unresolved)
                ),
            )

        else:

            passed(
                "VSE4_GLOBAL_AUDIT",
                "TRUE_UNRESOLVED_GLOBALS=NONE",
            )


    except Exception as exc:

        failed(
            "VSE4_GLOBAL_AUDIT",
            str(exc),
        )


# ============================================================
# 10. VSE4 SELF TEST
# ============================================================

title("10. VSE4 SELF TEST")


if vse.is_file():

    result = subprocess.run(
        [
            "python",
            str(vse),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


    if result.stdout:
        print(
            result.stdout.strip()
        )

    if result.stderr:
        print(
            result.stderr.strip()
        )


    if result.returncode == 0:

        passed(
            "VSE4_SELF_TEST"
        )

    else:

        failed(
            "VSE4_SELF_TEST",
            f"status={result.returncode}",
        )


# ============================================================
# 11. DIRECT GEO CONTRADICTION TEST
# ============================================================

title("11. DIRECT GEO CONTRADICTION TEST")


try:

    ns = runpy.run_path(
        str(vse),
        run_name="vse4_master_test",
    )


    geo_hits = ns[
        "geo_hits"
    ]

    score_candidate = ns[
        "score_candidate"
    ]


    scene = (
        "Investigação em apartamento "
        "na cidade de São Paulo Brasil"
    )


    wrong = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            "Empire State Building "
            "Manhattan New York",

        "must":
            "2/2",

        "score":
            220,

        "width":
            1920,

        "height":
            1080,
    }


    correct = {
        "provider":
            "Wikimedia",

        "tipo":
            "foto",

        "title":
            "Apartment building "
            "Sao Paulo Brazil",

        "must":
            "1/2",

        "score":
            120,

        "width":
            1920,

        "height":
            1080,
    }


    print(
        "SCENE_GEO=",
        sorted(
            geo_hits(
                scene
            )
        ),
    )

    print(
        "WRONG_GEO=",
        sorted(
            geo_hits(
                wrong["title"]
            )
        ),
    )

    print(
        "CORRECT_GEO=",
        sorted(
            geo_hits(
                correct["title"]
            )
        ),
    )


    bad_result = score_candidate(
        wrong,
        scene,
        {
            "providers": [],
            "groups": [],
            "types": [],
            "keys": [],
        },
    )


    good_result = score_candidate(
        correct,
        scene,
        {
            "providers": [],
            "groups": [],
            "types": [],
            "keys": [],
        },
    )


    print(
        "WRONG_HARD_MISMATCH=",
        bad_result.get(
            "hard_mismatch"
        ),
    )

    print(
        "WRONG_REASON=",
        bad_result.get(
            "hard_reason"
        ),
    )

    print(
        "WRONG_EFFECTIVE=",
        bad_result.get(
            "effective"
        ),
    )

    print(
        "CORRECT_HARD_MISMATCH=",
        good_result.get(
            "hard_mismatch"
        ),
    )

    print(
        "CORRECT_EFFECTIVE=",
        good_result.get(
            "effective"
        ),
    )


    if (
        bad_result.get(
            "hard_mismatch"
        )
        is True
        and
        good_result.get(
            "hard_mismatch"
        )
        is False
        and
        float(
            good_result.get(
                "effective",
                -999999999,
            )
        )
        >
        float(
            bad_result.get(
                "effective",
                999999999,
            )
        )
    ):

        passed(
            "GEO_CONTRADICTION_RUNTIME"
        )

    else:

        failed(
            "GEO_CONTRADICTION_RUNTIME"
        )


except Exception as exc:

    failed(
        "GEO_CONTRADICTION_RUNTIME",
        f"{type(exc).__name__}: {exc}",
    )

    traceback.print_exc()


# ============================================================
# 12. GEO SUBSTRING REGRESSION
# ============================================================

title("12. GEO SUBSTRING REGRESSION")


try:

    ns = runpy.run_path(
        str(vse),
        run_name="vse4_geo_boundary_test",
    )

    gh = ns[
        "geo_hits"
    ]


    ukraine = set(
        gh(
            "Kyiv Ukraine conflict"
        )
    )


    print(
        "UKRAINE_GEO=",
        sorted(
            ukraine
        ),
    )


    if (
        "ukraine" in ukraine
        and
        "united_kingdom"
        not in ukraine
    ):

        passed(
            "GEO_WORD_BOUNDARY"
        )

    else:

        failed(
            "GEO_WORD_BOUNDARY",
            str(sorted(ukraine)),
        )


except Exception as exc:

    failed(
        "GEO_WORD_BOUNDARY",
        str(exc),
    )


# ============================================================
# 13. PROVIDER ACQUISITION AUDIT
# ============================================================

title("13. PROVIDER ACQUISITION AUDIT")

midia = ROOT / "midia.py"


provider_defs_needed = {
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_todos_candidatos",
}


if midia.is_file():

    try:

        src = midia.read_text(
            encoding="utf-8",
        )

        tree = ast.parse(
            src
        )


        defs = {
            node.name:
                node
            for node in tree.body
            if isinstance(
                node,
                ast.FunctionDef,
            )
        }


        missing_defs = (
            provider_defs_needed
            -
            set(defs)
        )


        if missing_defs:

            failed(
                "PROVIDER_DEFINITIONS",
                ",".join(
                    sorted(missing_defs)
                ),
            )

        else:

            passed(
                "PROVIDER_DEFINITIONS"
            )


        buscar = defs.get(
            "buscar_todos_candidatos"
        )


        if buscar is not None:

            calls = set()


            for node in ast.walk(
                buscar
            ):

                if not isinstance(
                    node,
                    ast.Call,
                ):
                    continue


                fn = node.func


                if isinstance(
                    fn,
                    ast.Name,
                ):

                    calls.add(
                        fn.id
                    )


            expected_calls = {
                "pexels_video",
                "pexels_foto",
                "pixabay_video",
                "pixabay_foto",
                "coverr_video",
            }


            print(
                "PROVIDER_CALLS="
                +
                ",".join(
                    sorted(
                        calls
                        &
                        expected_calls
                    )
                )
            )


            missing_calls = (
                expected_calls
                -
                calls
            )


            if missing_calls:

                failed(
                    "PROVIDER_CALL_COVERAGE",
                    ",".join(
                        sorted(missing_calls)
                    ),
                )

            else:

                passed(
                    "PROVIDER_CALL_COVERAGE"
                )


    except Exception as exc:

        failed(
            "PROVIDER_ACQUISITION_AUDIT",
            str(exc),
        )


# ============================================================
# 14. FRESH RENDER GUARD UNIT TEST
# ============================================================

title("14. FRESH RENDER GUARD UNIT TEST")


if guard.is_file():

    sid = (
        f"MASTER_GUARD_TEST_{os.getpid()}"
    )


    test_temp = (
        ROOT
        / "temp"
        / sid
    )

    test_temp.mkdir(
        parents=True,
        exist_ok=True,
    )


    ass = (
        ROOT
        / "videos"
        / f"short_{sid}.ass"
    )

    final = (
        ROOT
        / "videos"
        / f"short_v6_{sid}.mp4"
    )

    audio = (
        test_temp
        / "test.mp3"
    )

    intermediate = (
        test_temp
        / "video_sem_audio.mp4"
    )


    try:

        ass.write_text(
            "ASS_PROTECTED",
            encoding="utf-8",
        )

        audio.write_text(
            "AUDIO_PROTECTED",
            encoding="utf-8",
        )

        final.write_text(
            "DISPOSABLE",
            encoding="utf-8",
        )

        intermediate.write_text(
            "DISPOSABLE",
            encoding="utf-8",
        )


        ns = runpy.run_path(
            str(guard),
            run_name="fresh_guard_master_test",
        )


        ns[
            "clean"
        ](
            sid
        )


        checks = {
            "ASS_PROTECTED":
                ass.exists(),

            "AUDIO_PROTECTED":
                audio.exists(),

            "FINAL_REMOVED":
                not final.exists(),

            "INTERMEDIATE_REMOVED":
                not intermediate.exists(),
        }


        for name, ok in checks.items():

            print(
                f"{name}="
                f"{'PASS' if ok else 'FAIL'}"
            )


        if all(
            checks.values()
        ):

            passed(
                "FRESH_RENDER_GUARD_RUNTIME"
            )

        else:

            failed(
                "FRESH_RENDER_GUARD_RUNTIME"
            )


    except Exception as exc:

        failed(
            "FRESH_RENDER_GUARD_RUNTIME",
            str(exc),
        )


    finally:

        try:
            ass.unlink(
                missing_ok=True
            )
        except Exception:
            pass

        try:
            final.unlink(
                missing_ok=True
            )
        except Exception:
            pass

        shutil.rmtree(
            test_temp,
            ignore_errors=True,
        )


# ============================================================
# 15. SCENE DUPLICATE AUDIT
# ============================================================

title("15. MEDIA SCENE DUPLICATE AUDIT")

image_root = (
    ROOT
    / "imagens"
)


problem_scenes = []


if image_root.is_dir():

    short_dirs = sorted(
        [
            p
            for p in image_root.glob(
                "short_*"
            )
            if p.is_dir()
        ],
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )[:10]


    for folder in short_dirs:

        print()
        print(
            f"SHORT_MEDIA_DIR={folder.name}"
        )


        for number in range(
            1,
            13,
        ):

            prefix = (
                f"scene_{number:02d}."
            )


            files = [
                p
                for p in folder.iterdir()
                if (
                    p.is_file()
                    and
                    p.name.startswith(
                        prefix
                    )
                )
            ]


            if len(files) > 1:

                item = (
                    folder.name,
                    number,
                    [
                        x.name
                        for x in files
                    ],
                )

                problem_scenes.append(
                    item
                )

                print(
                    "DUPLICATE_SCENE="
                    f"{folder.name}/scene_{number:02d} "
                    +
                    ",".join(
                        x.name
                        for x in files
                    )
                )


if problem_scenes:

    warning(
        "SCENE_DUPLICATES",
        f"{len(problem_scenes)} found; "
        "not automatically deleted",
    )

else:

    passed(
        "SCENE_DUPLICATES",
        "none in latest directories",
    )


# ============================================================
# 16. ZERO-BYTE FILE AUDIT
# ============================================================

title("16. ZERO-BYTE FILE AUDIT")

zero_files = []


for dirname in (
    "audios",
    "videos",
    "roteiros",
    "imagens",
):

    base = ROOT / dirname

    if not base.exists():
        continue


    try:

        for path in base.rglob("*"):

            if (
                path.is_file()
                and
                path.stat().st_size == 0
            ):

                zero_files.append(
                    path
                )


                if len(
                    zero_files
                ) <= 100:

                    print(
                        "ZERO_BYTE="
                        +
                        str(
                            path.relative_to(
                                ROOT
                            )
                        )
                    )

    except Exception:
        pass


if zero_files:

    warning(
        "ZERO_BYTE_FILES",
        str(len(zero_files)),
    )

else:

    passed(
        "ZERO_BYTE_FILES",
        "none",
    )


# ============================================================
# 17. VSE4 INTEGRATION VISIBILITY
# ============================================================

title("17. VSE4 INTEGRATION VISIBILITY")


integration_files = [
    ROOT / "midia.py",
    ROOT / "media_diversity_guard_v1.py",
]


bridge_hits = []


for path in integration_files:

    if not path.is_file():
        continue


    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )


    if (
        "visual_selection_engine_v4"
        in text
    ):

        bridge_hits.append(
            path.name
        )


print(
    "VSE4_BRIDGE_FILES="
    +
    (
        ",".join(
            bridge_hits
        )
        if bridge_hits
        else
        "NONE"
    )
)


if bridge_hits:

    passed(
        "VSE4_BRIDGE_VISIBILITY"
    )

else:

    warning(
        "VSE4_BRIDGE_VISIBILITY",
        "VSE4 certified separately but "
        "no active bridge detected",
    )


# ============================================================
# 18. FINAL CORE HASHES
# ============================================================

title("18. FINAL CORE HASHES")


for name in critical:

    path = ROOT / name

    if path.is_file():

        print(
            f"SHA256 "
            f"{sha256(path)} "
            f"{name}"
        )


# ============================================================
# 19. FINAL SUMMARY
# ============================================================

title("19. MASTER REPAIR SUMMARY")


print(
    f"PASS_COUNT={PASS_COUNT}"
)

print(
    f"WARN_COUNT={WARN_COUNT}"
)

print(
    f"FAIL_COUNT={FAIL_COUNT}"
)


if FAIL_COUNT == 0:

    print(
        "MASTER_REPAIR_STATUS=PASS"
    )

else:

    print(
        "MASTER_REPAIR_STATUS=FAIL"
    )


if WARN_COUNT:

    print(
        "REVIEW_WARNINGS=YES"
    )

else:

    print(
        "REVIEW_WARNINGS=NO"
    )


print(
    f"BACKUP_DIR="
    f"{BACKUP}"
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
    "MIDIA_RUNTIME_EXECUTED=NO"
)
