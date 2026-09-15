#!/usr/bin/env bash

set +e
set +u
set -o pipefail

ROOT="$HOME/ShortAutoPro"
cd "$ROOT" || {
    echo "ERRO: ShortAutoPro não encontrado."
    return 2 2>/dev/null || true
}

STAMP="$(date +%Y%m%d_%H%M%S)"
REPORT="temp/PRODUCTION_TRIAGE_V4_${STAMP}.txt"
VSE_LOG="temp/vse4_triage_${STAMP}.log"

mkdir -p temp

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

pass() {
    echo "PASS | $*"
    PASS_COUNT=$((PASS_COUNT + 1))
}

warn() {
    echo "WARN | $*"
    WARN_COUNT=$((WARN_COUNT + 1))
}

fail() {
    echo "FAIL | $*"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

section() {
    echo
    echo "======================================================================"
    echo " $*"
    echo "======================================================================"
}

# Salva tudo sem perder os contadores no shell atual.
exec > >(tee "$REPORT") 2>&1


section "SHORTAUTOPRO - PRODUCTION TRIAGE V4"

echo "DATE=$(date)"
echo "ROOT=$ROOT"
echo "REPORT=$REPORT"
echo "NETWORK_ALLOWED=NO"
echo "MEDIA_DOWNLOAD_ALLOWED=NO"
echo "RENDER_ALLOWED=NO"


# ======================================================================
# 1. PLATAFORMA
# ======================================================================

section "1. PLATFORM / TOOLS"

echo "PWD=$(pwd)"
echo "SHELL=${SHELL:-UNKNOWN}"

if command -v python >/dev/null 2>&1; then
    echo "PYTHON=$(python --version 2>&1)"
    pass "python disponível"
else
    fail "python ausente"
fi

if command -v ffmpeg >/dev/null 2>&1; then
    echo "FFMPEG=$(ffmpeg -version 2>/dev/null | head -n1)"
    pass "ffmpeg disponível"
else
    fail "ffmpeg ausente"
fi

if command -v ffprobe >/dev/null 2>&1; then
    pass "ffprobe disponível"
else
    fail "ffprobe ausente"
fi

echo
df -h . 2>/dev/null | head -n 5


# ======================================================================
# 2. ACTIVE CORE
# ======================================================================

section "2. ACTIVE CORE FILES + HASHES"

CORE_FILES=(
    midia.py
    wikimedia_source.py
    visual_selection_engine_v4.py
    media_diversity_guard_v1.py
    media_provenance_capture_v1.py
    visual_scene_commit_lock_v1.py
    visual_must_rescue_v1.py
    video.py
    v6.py
    legenda_dinamica.py
    gerar_short.sh
)

for F in "${CORE_FILES[@]}"
do
    if [ -f "$F" ]; then
        echo
        echo "FOUND=$F"
        sha256sum "$F"
        pass "core presente: $F"
    else
        echo "MISSING=$F"

        case "$F" in
            visual_must_rescue_v1.py|wikimedia_source.py)
                warn "módulo opcional/esperado ausente: $F"
                ;;
            *)
                fail "core ausente: $F"
                ;;
        esac
    fi
done


# ======================================================================
# 3. PYTHON SYNTAX - PROJECT
# ======================================================================

section "3. PYTHON SYNTAX AUDIT - ACTIVE PROJECT"

python - <<'PY'
from pathlib import Path
import ast

ROOT = Path(".")

SKIP_PARTS = {
    "backups",
    "__pycache__",
    ".git",
    "node_modules",
}

files = []

for p in ROOT.rglob("*.py"):

    if any(
        part in SKIP_PARTS
        for part in p.parts
    ):
        continue

    files.append(p)

files.sort()

bad = []

for p in files:

    try:
        src = p.read_text(
            encoding="utf-8",
            errors="replace",
        )

        ast.parse(
            src,
            filename=str(p),
        )

    except Exception as exc:

        bad.append(
            (
                str(p),
                type(exc).__name__,
                str(exc),
            )
        )

        print(
            f"PYTHON_SYNTAX_FAIL "
            f"file={p} "
            f"error={type(exc).__name__}: {exc}"
        )

print()
print(
    f"PYTHON_FILES_AUDITED={len(files)}"
)

print(
    f"PYTHON_SYNTAX_FAILURES={len(bad)}"
)

if bad:
    raise SystemExit(1)
PY

PYTHON_SYNTAX=$?

if [ "$PYTHON_SYNTAX" -eq 0 ]; then
    pass "todos os Python ativos passaram AST"
else
    fail "há arquivos Python com erro de sintaxe"
fi


# ======================================================================
# 4. SHELL SYNTAX
# ======================================================================

section "4. SHELL SYNTAX AUDIT"

SHELL_TOTAL=0
SHELL_BAD=0

while IFS= read -r F
do
    SHELL_TOTAL=$((SHELL_TOTAL + 1))

    bash -n "$F" 2>/dev/null

    S=$?

    if [ "$S" -ne 0 ]; then
        echo "SHELL_SYNTAX_FAIL=$F"
        SHELL_BAD=$((SHELL_BAD + 1))
    fi

done < <(
    find . \
        -type f \
        -name '*.sh' \
        ! -path './backups/*' \
        ! -path './.git/*' \
        2>/dev/null |
    sort
)

echo "SHELL_FILES_AUDITED=$SHELL_TOTAL"
echo "SHELL_SYNTAX_FAILURES=$SHELL_BAD"

if [ "$SHELL_BAD" -eq 0 ]; then
    pass "shell syntax"
else
    fail "$SHELL_BAD scripts shell quebrados"
fi


# ======================================================================
# 5. VSE4 STATIC STRUCTURE
# ======================================================================

section "5. VSE4 STATIC STRUCTURE"

if [ -f visual_selection_engine_v4.py ]; then

python - <<'PY'
from pathlib import Path
import ast
import collections

p = Path(
    "visual_selection_engine_v4.py"
)

src = p.read_text(
    encoding="utf-8",
    errors="replace",
)

tree = ast.parse(src)

funcs = [
    n.name
    for n in tree.body
    if isinstance(
        n,
        ast.FunctionDef,
    )
]

counts = collections.Counter(
    funcs
)

duplicates = {
    name: count
    for name, count in counts.items()
    if count > 1
}

required = {
    "norm",
    "objget",
    "provider",
    "source_group",
    "media_type",
    "candidate_key",
    "base_score",
    "must_tier",
    "flatten_candidates",
    "concept_hits",
    "geo_hits",
    "candidate_text",
    "tokens",
    "score_candidate",
    "self_test",
}

missing = sorted(
    required - set(funcs)
)

print(
    f"VSE4_FUNCTIONS={len(funcs)}"
)

print(
    "VSE4_MISSING_REQUIRED="
    +
    (
        ",".join(missing)
        if missing
        else "NONE"
    )
)

print(
    "VSE4_DUPLICATE_FUNCTIONS="
    +
    (
        repr(duplicates)
        if duplicates
        else "NONE"
    )
)

if missing:
    raise SystemExit(1)
PY

VSE_STRUCTURE=$?

if [ "$VSE_STRUCTURE" -eq 0 ]; then
    pass "VSE4 estrutura básica completa"
else
    fail "VSE4 com funções obrigatórias ausentes"
fi

else
    fail "visual_selection_engine_v4.py ausente"
fi


# ======================================================================
# 6. VSE4 TRUE GLOBAL AUDIT
# ======================================================================

section "6. VSE4 UNRESOLVED GLOBAL AUDIT"

if [ -f visual_selection_engine_v4.py ]; then

python - <<'PY'
from pathlib import Path
import symtable
import builtins

src = Path(
    "visual_selection_engine_v4.py"
).read_text(
    encoding="utf-8",
    errors="replace",
)

table = symtable.symtable(
    src,
    "visual_selection_engine_v4.py",
    "exec",
)

defined = set()

for symbol in table.get_symbols():

    if (
        symbol.is_assigned()
        or symbol.is_imported()
        or symbol.is_namespace()
    ):
        defined.add(
            symbol.get_name()
        )

allowed = (
    set(dir(builtins))
    |
    {
        "__name__",
        "__file__",
        "__package__",
        "__spec__",
        "__loader__",
        "__cached__",
    }
)

unresolved = set()


def walk(scope):

    for child in scope.get_children():

        for symbol in child.get_symbols():

            name = symbol.get_name()

            if not symbol.is_referenced():
                continue

            if not symbol.is_global():
                continue

            if name in defined:
                continue

            if name in allowed:
                continue

            unresolved.add(name)

        walk(child)


walk(table)

print(
    "TRUE_UNRESOLVED_GLOBALS="
    +
    (
        ",".join(sorted(unresolved))
        if unresolved
        else "NONE"
    )
)

if unresolved:
    raise SystemExit(1)
PY

GLOBAL_STATUS=$?

if [ "$GLOBAL_STATUS" -eq 0 ]; then
    pass "VSE4 sem globals ausentes"
else
    fail "VSE4 possui referências globais não resolvidas"
fi

fi


# ======================================================================
# 7. VSE4 RUNTIME SELF TEST
# ======================================================================

section "7. VSE4 SAFE RUNTIME SELF TEST"

if [ -f visual_selection_engine_v4.py ]; then

    python visual_selection_engine_v4.py \
        > "$VSE_LOG" \
        2>&1

    VSE_STATUS=$?

    echo "VSE4_SELF_TEST_STATUS=$VSE_STATUS"

    tail -n 100 "$VSE_LOG"

    if [ "$VSE_STATUS" -eq 0 ]; then
        pass "VSE4 runtime self-test"
    else
        fail "VSE4 runtime self-test"
    fi

else
    fail "VSE4 indisponível"
fi


# ======================================================================
# 8. VSE4 GEO DIRECT TEST
# ======================================================================

section "8. VSE4 GEOGRAPHY DIRECT TEST"

if [ -f visual_selection_engine_v4.py ]; then

python - <<'PY'
import runpy

ns = runpy.run_path(
    "visual_selection_engine_v4.py",
    run_name="production_geo_audit",
)

geo_hits = ns[
    "geo_hits"
]

sp = set(
    geo_hits(
        "Apartamento em São Paulo Brasil"
    )
)

ny = set(
    geo_hits(
        "Empire State Building Manhattan New York"
    )
)

print(
    "SAO_PAULO_GEO=",
    sorted(sp),
)

print(
    "NEW_YORK_GEO=",
    sorted(ny),
)

if not sp:
    print("GEO_SP_DETECTION=FAIL")
    raise SystemExit(1)

if not ny:
    print("GEO_NY_DETECTION=FAIL")
    raise SystemExit(1)

if sp == ny:
    print("GEO_DISTINCTION=FAIL")
    raise SystemExit(1)

print("GEO_DISTINCTION=PASS")
PY

GEO_STATUS=$?

if [ "$GEO_STATUS" -eq 0 ]; then
    pass "geografia São Paulo x Nova York distinguível"
else
    fail "motor geográfico"
fi

fi


# ======================================================================
# 9. MIDIA <-> VSE4 INTEGRATION
# ======================================================================

section "9. MIDIA <-> VSE4 REAL INTEGRATION"

if [ -f midia.py ]; then

    echo "--- referências VSE4 em midia.py ---"

    grep -nEi \
        'visual_selection_engine_v4|VSE4|score_candidate|hard_mismatch|rerank' \
        midia.py \
        2>/dev/null |
    head -n 120

    COUNT="$(
        grep -Eic \
        'visual_selection_engine_v4|VSE4' \
        midia.py \
        2>/dev/null
    )"

    echo "MIDIA_VSE4_REFERENCE_COUNT=$COUNT"

    if [ "$COUNT" -gt 0 ]; then
        pass "midia.py contém integração VSE4"
    else
        fail "VSE4 existe, mas midia.py não mostra integração VSE4"
    fi

else
    fail "midia.py ausente"
fi


# ======================================================================
# 10. COMMIT LOCK
# ======================================================================

section "10. SCENE COMMIT LOCK INTEGRATION"

grep -nEi \
    'visual_scene_commit_lock|SCENE_COMMIT_LOCK|commit_lock' \
    midia.py \
    media_diversity_guard_v1.py \
    visual_scene_commit_lock_v1.py \
    2>/dev/null |
head -n 200

LOCK_REFS="$(
    grep -Eic \
    'SCENE_COMMIT_LOCK|visual_scene_commit_lock' \
    midia.py \
    media_diversity_guard_v1.py \
    2>/dev/null
)"

echo "ACTIVE_COMMIT_LOCK_REFS=$LOCK_REFS"

if [ "$LOCK_REFS" -gt 0 ]; then
    pass "commit lock referenciado pelo caminho ativo"
else
    warn "commit lock não encontrado em midia/diversity guard"
fi


# ======================================================================
# 11. PROVENANCE
# ======================================================================

section "11. MEDIA PROVENANCE INTEGRATION"

grep -nEi \
    'media_provenance_capture|provenance|source_provenance' \
    midia.py \
    media_diversity_guard_v1.py \
    2>/dev/null |
head -n 160

PROV_REFS="$(
    grep -Eic \
    'media_provenance_capture|source_provenance' \
    midia.py \
    media_diversity_guard_v1.py \
    2>/dev/null
)"

echo "ACTIVE_PROVENANCE_REFS=$PROV_REFS"

if [ "$PROV_REFS" -gt 0 ]; then
    pass "provenance integrado"
else
    warn "provenance não aparece no caminho ativo"
fi


# ======================================================================
# 12. PROVIDER DEFINITIONS
# ======================================================================

section "12. PROVIDER ACQUISITION MAP"

python - <<'PY'
from pathlib import Path
import ast

p = Path(
    "midia.py"
)

if not p.is_file():
    print("MIDIA_MISSING=YES")
    raise SystemExit(1)

src = p.read_text(
    encoding="utf-8",
    errors="replace",
)

tree = ast.parse(src)

wanted = {
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_todos_candidatos",
    "buscar_wikimedia_fotos",
}

definitions = {}

for node in tree.body:

    if (
        isinstance(node, ast.FunctionDef)
        and node.name in wanted
    ):
        definitions[node.name] = (
            node.lineno,
            node.end_lineno,
        )


for name in sorted(wanted):

    if name in definitions:

        start, end = definitions[name]

        print(
            f"PROVIDER_FUNCTION "
            f"name={name} "
            f"lines={start}-{end}"
        )

    else:

        print(
            f"PROVIDER_FUNCTION_MISSING={name}"
        )


target = None

for node in tree.body:

    if (
        isinstance(node, ast.FunctionDef)
        and node.name == "buscar_todos_candidatos"
    ):
        target = node
        break


if target:

    print()
    print(
        "BUSCAR_TODOS_CANDIDATOS_CALLS:"
    )

    for node in ast.walk(target):

        if not isinstance(node, ast.Call):
            continue

        try:
            name = ast.unparse(node.func)
        except Exception:
            name = "?"

        print(
            f"CALL line={node.lineno} "
            f"name={name}"
        )
PY

PROVIDER_MAP=$?

if [ "$PROVIDER_MAP" -eq 0 ]; then
    pass "provider acquisition map analisado"
else
    fail "não foi possível mapear providers"
fi


# ======================================================================
# 13. API CONFIG WITHOUT SECRET VALUES
# ======================================================================

section "13. API CONFIG SAFE DETECTION"

python - <<'PY'
from pathlib import Path
import os
import re

keys = [
    "PEXELS_API_KEY",
    "PIXABAY_API_KEY",
    "COVERR_API_KEY",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
]

files = [
    Path("config.env"),
    Path(".env"),
    Path("config/.env"),
]

for key in keys:

    process = bool(
        os.environ.get(key)
    )

    found = []

    for path in files:

        if not path.is_file():
            continue

        text = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        if re.search(
            rf"(?m)^\s*(?:export\s+)?"
            rf"{re.escape(key)}\s*=",
            text,
        ):
            found.append(
                str(path)
            )


    if process:

        status = "PROCESS_ENV_PRESENT"

    elif found:

        status = (
            "CONFIG_PRESENT:"
            +
            ",".join(found)
        )

    else:

        status = "NOT_FOUND"


    print(
        f"{key}={status}"
    )
PY


# ======================================================================
# 14. ENV LOADER
# ======================================================================

section "14. ENV LOADER AUDIT"

grep -nEi \
    'config\.env|\.env|load_dotenv|source .*env|PEXELS_API_KEY|PIXABAY_API_KEY|COVERR_API_KEY' \
    gerar_short.sh \
    midia.py \
    wikimedia_source.py \
    2>/dev/null |
head -n 300


# ======================================================================
# 15. NETWORK TIMEOUTS
# ======================================================================

section "15. NETWORK TIMEOUT AUDIT"

python - <<'PY'
from pathlib import Path
import ast

ROOTS = [
    Path("midia.py"),
    Path("wikimedia_source.py"),
    Path("visual_selection_engine_v4.py"),
]

network_calls = 0
missing = 0

for path in ROOTS:

    if not path.is_file():
        continue

    src = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    try:
        tree = ast.parse(src)

    except Exception as exc:

        print(
            f"PARSE_FAIL file={path} "
            f"error={exc}"
        )

        continue


    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        try:
            call = ast.unparse(node)
        except Exception:
            call = ""

        low = call.casefold()


        evidence = any(
            token in low
            for token in (
                "requests.",
                "session.get",
                "session.post",
                "httpx.",
                "urlopen(",
            )
        )

        if not evidence:
            continue


        network_calls += 1


        has_timeout = any(
            kw.arg == "timeout"
            for kw in node.keywords
        )


        if has_timeout:

            print(
                f"NETWORK_TIMEOUT_OK "
                f"file={path} "
                f"line={node.lineno}"
            )

        else:

            missing += 1

            print(
                f"NETWORK_TIMEOUT_MISSING "
                f"file={path} "
                f"line={node.lineno}"
            )


print()
print(
    f"NETWORK_CALLS_AUDITED={network_calls}"
)

print(
    f"NETWORK_TIMEOUT_MISSING={missing}"
)

if missing:
    raise SystemExit(1)
PY

TIMEOUT_STATUS=$?

if [ "$TIMEOUT_STATUS" -eq 0 ]; then
    pass "network calls auditadas possuem timeout"
else
    warn "há chamada HTTP sem timeout"
fi


# ======================================================================
# 16. HARDCODED SECRET AUDIT
# ======================================================================

section "16. HARDCODED SECRET AUDIT"

python - <<'PY'
from pathlib import Path
import ast

danger_names = (
    "api_key",
    "apikey",
    "secret",
    "token",
    "password",
    "passwd",
)

hits = []

for path in Path(".").rglob("*.py"):

    if any(
        x in path.parts
        for x in (
            "backups",
            ".git",
            "__pycache__",
            "temp",
        )
    ):
        continue


    try:
        src = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        tree = ast.parse(src)

    except Exception:
        continue


    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
            ),
        ):
            continue


        names = []


        if isinstance(
            node,
            ast.Assign,
        ):

            targets = node.targets
            value = node.value

        else:

            targets = [
                node.target
            ]

            value = node.value


        for target in targets:

            if isinstance(
                target,
                ast.Name,
            ):
                names.append(
                    target.id
                )


        if not names:
            continue


        suspicious_name = any(
            any(
                marker in name.casefold()
                for marker in danger_names
            )
            for name in names
        )


        if not suspicious_name:
            continue


        if isinstance(
            value,
            ast.Constant,
        ) and isinstance(
            value.value,
            str,
        ):

            val = value.value.strip()

            if (
                val
                and len(val) >= 12
                and not val.startswith(
                    "${"
                )
            ):

                hits.append(
                    (
                        str(path),
                        node.lineno,
                        ",".join(names),
                    )
                )


for path, line, names in hits:

    # Nunca imprime o valor.
    print(
        f"POSSIBLE_HARDCODED_SECRET "
        f"file={path} "
        f"line={line} "
        f"name={names}"
    )


print(
    f"HARDCODED_SECRET_SUSPECTS={len(hits)}"
)

if hits:
    raise SystemExit(1)
PY

SECRET_STATUS=$?

if [ "$SECRET_STATUS" -eq 0 ]; then
    pass "nenhum segredo hardcoded óbvio"
else
    warn "há possíveis secrets hardcoded; valores não foram exibidos"
fi


# ======================================================================
# 17. DANGEROUS FILE DELETION
# ======================================================================

section "17. DESTRUCTIVE FILE OPERATION AUDIT"

python - <<'PY'
from pathlib import Path
import ast

hits = []

for path in Path(".").rglob("*.py"):

    if any(
        part in path.parts
        for part in (
            "backups",
            ".git",
            "__pycache__",
        )
    ):
        continue


    try:
        tree = ast.parse(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )

    except Exception:
        continue


    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        try:
            name = ast.unparse(
                node.func
            )
        except Exception:
            continue


        if name in {
            "os.remove",
            "os.unlink",
            "shutil.rmtree",
            "Path.unlink",
        } or name.endswith(
            ".unlink"
        ):

            hits.append(
                (
                    str(path),
                    node.lineno,
                    name,
                )
            )


for path, line, name in hits:

    print(
        f"DESTRUCTIVE_CALL "
        f"file={path} "
        f"line={line} "
        f"call={name}"
    )


print(
    f"DESTRUCTIVE_CALLS_FOUND={len(hits)}"
)
PY

grep -RniE \
    'rm[[:space:]]+-rf|rm[[:space:]]+-fr' \
    --include='*.sh' \
    --exclude-dir=backups \
    --exclude-dir=.git \
    . \
    2>/dev/null |
head -n 100


# ======================================================================
# 18. SHORT_ID SELECTION
# ======================================================================

section "18. SHORT_ID RESOLUTION"

if [ -n "${SHORT_ID:-}" ]; then

    ACTIVE_SHORT_ID="$SHORT_ID"
    echo "SHORT_ID_SOURCE=ENV"

else

    ACTIVE_SHORT_ID="$(
        python - <<'PY'
from pathlib import Path

root = Path(
    "imagens"
)

dirs = [
    p
    for p in root.glob(
        "short_*"
    )
    if p.is_dir()
]

if not dirs:
    print("")
else:
    dirs.sort(
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )

    print(
        dirs[0].name.removeprefix(
            "short_"
        )
    )
PY
    )"

    echo "SHORT_ID_SOURCE=LATEST_MEDIA_DIR"

fi

echo "ACTIVE_SHORT_ID=$ACTIVE_SHORT_ID"

if [ -n "$ACTIVE_SHORT_ID" ]; then
    pass "SHORT_ID resolvido"
else
    warn "nenhum SHORT_ID encontrado"
fi


# ======================================================================
# 19. CURRENT MEDIA INTEGRITY
# ======================================================================

section "19. CURRENT 12-SCENE MEDIA INTEGRITY"

if [ -n "$ACTIVE_SHORT_ID" ]; then

    MEDIA_DIR="imagens/short_${ACTIVE_SHORT_ID}"

    echo "MEDIA_DIR=$MEDIA_DIR"

    MEDIA_TOTAL=0
    MEDIA_BAD=0

    for N in $(seq -w 1 12)
    do

        COUNT="$(
            find "$MEDIA_DIR" \
                -maxdepth 1 \
                -type f \
                -name "scene_${N}.*" \
                2>/dev/null |
            wc -l
        )"

        MEDIA_TOTAL=$((MEDIA_TOTAL + COUNT))

        if [ "$COUNT" -ne 1 ]; then

            echo "SCENE_${N}=BAD count=$COUNT"
            MEDIA_BAD=$((MEDIA_BAD + 1))

        else

            F="$(
                find "$MEDIA_DIR" \
                    -maxdepth 1 \
                    -type f \
                    -name "scene_${N}.*" \
                    2>/dev/null |
                head -n1
            )"

            BYTES="$(
                stat -c%s "$F" \
                2>/dev/null
            )"

            echo \
                "SCENE_${N}=PASS bytes=$BYTES file=$F"

        fi

    done

    echo
    echo "MEDIA_TOTAL=$MEDIA_TOTAL"
    echo "INVALID_SCENES=$MEDIA_BAD"

    if \
        [ "$MEDIA_TOTAL" -eq 12 ] &&
        [ "$MEDIA_BAD" -eq 0 ]
    then

        pass "12 cenas, uma mídia por cena"
    else
        fail "estrutura de mídia inválida"
    fi

else
    warn "media audit ignorado sem SHORT_ID"
fi


# ======================================================================
# 20. DUPLICATE MEDIA HASH
# ======================================================================

section "20. DUPLICATE MEDIA HASH AUDIT"

if \
    [ -n "$ACTIVE_SHORT_ID" ] &&
    [ -d "imagens/short_${ACTIVE_SHORT_ID}" ]
then

python - "$ACTIVE_SHORT_ID" <<'PY'
from pathlib import Path
import hashlib
import sys
import collections

sid = sys.argv[1]

root = (
    Path("imagens")
    /
    f"short_{sid}"
)

groups = collections.defaultdict(
    list
)

for p in sorted(
    root.glob(
        "scene_*.*"
    )
):

    if not p.is_file():
        continue

    h = hashlib.sha256()

    with p.open("rb") as f:

        for chunk in iter(
            lambda:
                f.read(
                    1024 * 1024
                ),
            b"",
        ):
            h.update(chunk)

    groups[
        h.hexdigest()
    ].append(
        str(p)
    )


duplicates = [
    files
    for files in groups.values()
    if len(files) > 1
]


for files in duplicates:

    print(
        "DUPLICATE_MEDIA="
        +
        " | ".join(files)
    )


print(
    f"DUPLICATE_MEDIA_GROUPS={len(duplicates)}"
)

if duplicates:
    raise SystemExit(1)
PY

DUP_STATUS=$?

if [ "$DUP_STATUS" -eq 0 ]; then
    pass "sem cenas byte-identical duplicadas"
else
    warn "existem mídias duplicadas entre cenas"
fi

fi


# ======================================================================
# 21. RENDER INPUTS
# ======================================================================

section "21. RENDER INPUT READINESS"

if [ -n "$ACTIVE_SHORT_ID" ]; then

    CHECKS=(
        "audios/short_${ACTIVE_SHORT_ID}.mp3"
        "videos/short_${ACTIVE_SHORT_ID}.ass"
        "temp/${ACTIVE_SHORT_ID}/video_sem_audio.mp4"
    )

    for F in "${CHECKS[@]}"
    do

        if [ -s "$F" ]; then
            echo \
                "RENDER_INPUT=PASS bytes=$(stat -c%s "$F") file=$F"
        else
            echo \
                "RENDER_INPUT=ABSENT file=$F"
        fi

    done


    FINAL="videos/short_v6_${ACTIVE_SHORT_ID}.mp4"

    if [ -s "$FINAL" ]; then

        echo
        echo "FINAL_VIDEO=FOUND"

        sha256sum "$FINAL"

        ffprobe \
            -v error \
            -show_entries \
stream=codec_name,codec_type,width,height,r_frame_rate \
            -show_entries \
format=duration,size,bit_rate \
            -of default=noprint_wrappers=1 \
            "$FINAL" \
            2>/dev/null

        pass "vídeo final legível"

    else

        echo "FINAL_VIDEO=ABSENT"

    fi

fi


# ======================================================================
# 22. STALE/CROSS-SHORT CACHE
# ======================================================================

section "22. STALE / SHARED CACHE AUDIT"

echo "--- MP4 diretamente em temp/ ---"

find temp \
    -maxdepth 1 \
    -type f \
    -name '*.mp4' \
    -print \
    2>/dev/null |
head -n 100


echo
echo "--- generic render filenames outside per-short temp dirs ---"

find . \
    -type f \
    \( \
        -name 'video_sem_audio.mp4' \
        -o \
        -name 'final.mp4' \
        -o \
        -name 'output.mp4' \
        -o \
        -name 'video_final.mp4' \
    \) \
    ! -path './backups/*' \
    ! -path './temp/short_*/*' \
    2>/dev/null |
head -n 150


# ======================================================================
# 23. HARD-CODED SHORT IDS / DATES
# ======================================================================

section "23. HARDCODED SHORT-ID AUDIT"

grep -RniE \
    '2026-[0-9]{2}-[0-9]{2}_[0-9]{4}|2026-[0-9]{2}-[0-9]{2}' \
    --include='*.py' \
    --include='*.sh' \
    --exclude-dir=backups \
    --exclude-dir=temp \
    --exclude-dir=.git \
    . \
    2>/dev/null |
head -n 200


# ======================================================================
# 24. BACKUP/TEMP IMPORT LEAK
# ======================================================================

section "24. ACTIVE CODE IMPORTING BACKUP/TEMP AUDIT"

python - <<'PY'
from pathlib import Path
import ast

hits = []

for path in Path(".").glob("*.py"):

    try:
        tree = ast.parse(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )

    except Exception:
        continue


    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Import,
        ):

            names = [
                x.name
                for x in node.names
            ]

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            names = [
                node.module or ""
            ]

        else:
            continue


        for name in names:

            low = name.casefold()

            if (
                "backup" in low
                or low.startswith("temp")
            ):

                hits.append(
                    (
                        str(path),
                        node.lineno,
                        name,
                    )
                )


for path, line, name in hits:

    print(
        f"SUSPICIOUS_IMPORT "
        f"file={path} "
        f"line={line} "
        f"module={name}"
    )


print(
    f"BACKUP_TEMP_IMPORTS={len(hits)}"
)

if hits:
    raise SystemExit(1)
PY

IMPORT_LEAK=$?

if [ "$IMPORT_LEAK" -eq 0 ]; then
    pass "core não importa módulos de backup/temp"
else
    warn "há imports suspeitos de backup/temp"
fi


# ======================================================================
# 25. RENDER PATH STATIC AUDIT
# ======================================================================

section "25. VIDEO/V6 SHORT_ID PATH AUDIT"

for F in video.py v6.py
do

    echo
    echo "--- $F ---"

    grep -nE \
        'SHORT_ID|video_sem_audio|short_v6_|short_.*\.ass|temp' \
        "$F" \
        2>/dev/null |
    head -n 160

done


# ======================================================================
# 26. GERAR_SHORT PIPELINE MAP
# ======================================================================

section "26. GERAR_SHORT PIPELINE MAP"

grep -nEi \
    'python .*\.py|[0-9]+/[0-9]+|midia|legenda|video|v6|whisper|render' \
    gerar_short.sh \
    2>/dev/null |
head -n 400


# ======================================================================
# 27. GIT STATUS
# ======================================================================

section "27. GIT STATUS"

if [ -d .git ] && command -v git >/dev/null 2>&1; then

    git status --short 2>/dev/null |
    head -n 300

    echo
    echo "BRANCH=$(git branch --show-current 2>/dev/null)"

else

    echo "GIT_REPOSITORY=NO"

fi


# ======================================================================
# 28. FILE SIZE ANOMALIES
# ======================================================================

section "28. ACTIVE PYTHON FILE SIZE ANOMALIES"

python - <<'PY'
from pathlib import Path

files = []

for p in Path(".").glob("*.py"):

    try:
        size = p.stat().st_size
    except Exception:
        continue

    files.append(
        (
            size,
            p.name,
        )
    )


files.sort(
    reverse=True
)


for size, name in files[:40]:

    print(
        f"{size:9d} bytes | {name}"
    )


zero = [
    name
    for size, name in files
    if size == 0
]


print()
print(
    "ZERO_BYTE_PYTHON="
    +
    (
        ",".join(zero)
        if zero
        else "NONE"
    )
)

if zero:
    raise SystemExit(1)
PY

SIZE_STATUS=$?

if [ "$SIZE_STATUS" -eq 0 ]; then
    pass "sem Python ativo vazio"
else
    fail "arquivo Python ativo com 0 bytes"
fi


# ======================================================================
# 29. RECENT ERROR LOG SCAN
# ======================================================================

section "29. RECENT PRODUCTION LOG ERROR SCAN"

python - <<'PY'
from pathlib import Path
import time
import re

root = Path(
    "logs/producao"
)

if not root.is_dir():

    print(
        "PRODUCTION_LOG_DIR=ABSENT"
    )

    raise SystemExit(0)


cutoff = (
    time.time()
    -
    7 * 24 * 3600
)

pattern = re.compile(
    r"(?i)"
    r"(traceback|"
    r"nameerror|"
    r"typeerror|"
    r"filenotfounderror|"
    r"syntaxerror|"
    r"runtimeerror|"
    r"\berro\b|"
    r"\berror\b|"
    r"\bfail(?:ed)?\b)"
)

files = [
    p
    for p in root.glob("*")
    if (
        p.is_file()
        and
        p.stat().st_mtime >= cutoff
    )
]

files.sort(
    key=lambda p:
        p.stat().st_mtime,
    reverse=True,
)

matches = 0


for p in files[:80]:

    try:
        lines = p.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()

    except Exception:
        continue


    selected = [
        line
        for line in lines
        if pattern.search(line)
    ]


    if not selected:
        continue


    print()
    print(
        f"LOG={p}"
    )

    for line in selected[-12:]:

        print(
            "  "
            +
            line[:260]
        )

        matches += 1


print()
print(
    f"RECENT_ERROR_LINES={matches}"
)
PY


# ======================================================================
# 30. FINAL SUMMARY
# ======================================================================

section "30. PRODUCTION TRIAGE SUMMARY"

echo "PASS_COUNT=$PASS_COUNT"
echo "WARN_COUNT=$WARN_COUNT"
echo "FAIL_COUNT=$FAIL_COUNT"

echo
echo "PYTHON_SYNTAX_STATUS=$PYTHON_SYNTAX"
echo "SHELL_FAILURES=$SHELL_BAD"
echo "VSE4_SELF_TEST_STATUS=${VSE_STATUS:-99}"
echo "NETWORK_TIMEOUT_STATUS=$TIMEOUT_STATUS"
echo "SECRET_AUDIT_STATUS=$SECRET_STATUS"

if [ -n "${ACTIVE_SHORT_ID:-}" ]; then
    echo "ACTIVE_SHORT_ID=$ACTIVE_SHORT_ID"
fi

echo

if [ "$FAIL_COUNT" -eq 0 ]; then

    if [ "$WARN_COUNT" -eq 0 ]; then

        echo "OVERALL_STATUS=PASS"
        echo "PRODUCTION_READINESS=GREEN"

    else

        echo "OVERALL_STATUS=PASS_WITH_WARNINGS"
        echo "PRODUCTION_READINESS=YELLOW"

    fi

else

    echo "OVERALL_STATUS=FAIL"
    echo "PRODUCTION_READINESS=RED"

fi

echo
echo "REPORT=$REPORT"
echo "NETWORK_EXECUTED=NO"
echo "MEDIA_DOWNLOADED=NO"
echo "VIDEO_RENDERED=NO"
echo "CORE_FILES_MODIFIED=NO"
echo "TERMUX_CONTINUA_ABERTO=SIM"

echo
echo "======================================================================"
echo " TRIAGE COMPLETE"
echo "======================================================================"
