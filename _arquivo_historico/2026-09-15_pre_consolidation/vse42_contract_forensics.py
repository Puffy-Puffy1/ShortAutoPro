#!/usr/bin/env python3

from pathlib import Path
import ast
import hashlib
import inspect
import os
import py_compile
import runpy
import sys
import traceback


ROOT = Path.home() / "ShortAutoPro"

MIDIA = ROOT / "midia.py"
BRIDGE = ROOT / "visual_selection_bridge_v42.py"
COMMIT = ROOT / "visual_scene_commit_lock_v1.py"

REPORT = ROOT / "temp" / "VSE42_CONTRACT_FORENSICS.txt"

REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


def emit(*args):
    text = " ".join(
        str(x)
        for x in args
    )

    print(text)

    with REPORT.open(
        "a",
        encoding="utf-8",
    ) as f:
        f.write(text + "\n")


def section(title):

    emit()
    emit("=" * 72)
    emit(title)
    emit("=" * 72)


def sha(path):

    if not path.is_file():
        return "MISSING"

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def read(path):

    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


REPORT.write_text(
    "",
    encoding="utf-8",
)


section(
    "1. FILE STATUS"
)

for path in (
    MIDIA,
    BRIDGE,
    COMMIT,
):

    emit(
        "FILE=",
        path.name,
    )

    emit(
        "EXISTS=",
        path.is_file(),
    )

    emit(
        "SHA256=",
        sha(path),
    )


section(
    "2. COMPILE"
)

compile_fail = []


for path in (
    MIDIA,
    BRIDGE,
    COMMIT,
):

    if not path.is_file():
        emit(
            f"{path.name}_COMPILE=MISSING"
        )

        compile_fail.append(
            path.name
        )

        continue

    try:

        py_compile.compile(
            str(path),
            doraise=True,
        )

        emit(
            f"{path.name}_COMPILE=PASS"
        )

    except Exception as exc:

        emit(
            f"{path.name}_COMPILE=FAIL "
            f"{type(exc).__name__}: {exc}"
        )

        compile_fail.append(
            path.name
        )


if not MIDIA.is_file() or not BRIDGE.is_file():

    section(
        "FATAL"
    )

    emit(
        "REQUIRED_FILE_MISSING=YES"
    )

    raise SystemExit(0)


midia_src = read(
    MIDIA
)

bridge_src = read(
    BRIDGE
)

midia_tree = ast.parse(
    midia_src
)

bridge_tree = ast.parse(
    bridge_src
)


section(
    "3. BRIDGE PUBLIC FUNCTIONS"
)

bridge_functions = {}


for node in bridge_tree.body:

    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    ):

        bridge_functions[
            node.name
        ] = node

        args = []

        for arg in (
            node.args.posonlyargs
            +
            node.args.args
            +
            node.args.kwonlyargs
        ):
            args.append(
                arg.arg
            )

        emit(
            f"FUNCTION={node.name} "
            f"LINE={node.lineno} "
            f"ARGS={','.join(args)}"
        )


emit(
    "BRIDGE_FUNCTION_COUNT=",
    len(
        bridge_functions
    ),
)

emit(
    "COMMIT_CANDIDATE_DEFINED=",
    "commit_candidate"
    in
    bridge_functions,
)


section(
    "4. MIDIA IMPORTS FROM VSE42 BRIDGE"
)

bridge_aliases = {}


for node in ast.walk(
    midia_tree
):

    if not isinstance(
        node,
        ast.ImportFrom,
    ):
        continue

    if node.module != "visual_selection_bridge_v42":
        continue

    for alias in node.names:

        local = (
            alias.asname
            or
            alias.name
        )

        bridge_aliases[
            local
        ] = alias.name

        emit(
            f"IMPORT line={node.lineno} "
            f"remote={alias.name} "
            f"local={local}"
        )


emit(
    "BRIDGE_IMPORTED_NAMES=",
    ",".join(
        sorted(
            set(
                bridge_aliases.values()
            )
        )
    )
    or
    "NONE",
)


missing_exports = sorted(
    {
        remote
        for remote
        in bridge_aliases.values()
        if remote
        not in
        bridge_functions
    }
)


emit(
    "MISSING_BRIDGE_EXPORTS=",
    ",".join(
        missing_exports
    )
    or
    "NONE",
)


section(
    "5. COMMIT API SEARCH"
)


def function_names(path):

    if not path.is_file():
        return set()

    tree = ast.parse(
        read(path)
    )

    return {
        node.name
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }


commit_functions = function_names(
    COMMIT
)


for name in sorted(
    commit_functions
):

    if any(
        term in name.casefold()
        for term in (
            "commit",
            "note",
            "install",
            "reset",
            "lock",
        )
    ):

        emit(
            "COMMIT_MODULE_FUNCTION=",
            name,
        )


emit(
    "COMMIT_MODULE_HAS_COMMIT_CANDIDATE=",
    "commit_candidate"
    in
    commit_functions,
)

emit(
    "COMMIT_MODULE_HAS_NOTE_COMMIT=",
    "note_commit"
    in
    commit_functions,
)


section(
    "6. VSE42 CALLS IN MIDIA"
)


def call_name(call):

    try:

        return ast.unparse(
            call.func
        )

    except Exception:

        return "UNKNOWN"


interesting_calls = []


for node in ast.walk(
    midia_tree
):

    if not isinstance(
        node,
        ast.Call,
    ):
        continue

    name = call_name(
        node
    )

    low = name.casefold()

    if (
        "vse42"
        in low
        or
        name
        in bridge_aliases
        or
        "visual_selection_bridge"
        in low
    ):

        interesting_calls.append(
            (
                node.lineno,
                name,
            )
        )


for line, name in sorted(
    interesting_calls
):

    emit(
        f"CALL line={line} "
        f"name={name}"
    )


emit(
    "VSE42_CALL_COUNT=",
    len(
        interesting_calls
    ),
)


section(
    "7. TUPLE UNPACK CONTRACTS"
)


def target_count(target):

    if isinstance(
        target,
        (
            ast.Tuple,
            ast.List,
        ),
    ):

        return len(
            target.elts
        )

    return 1


unpack_contracts = []


for node in ast.walk(
    midia_tree
):

    if not isinstance(
        node,
        (
            ast.Assign,
            ast.AnnAssign,
        ),
    ):
        continue


    value = node.value

    if not isinstance(
        value,
        ast.Call,
    ):
        continue


    name = call_name(
        value
    )

    interesting = (
        "vse42"
        in name.casefold()
        or
        name
        in bridge_aliases
    )

    if not interesting:
        continue


    if isinstance(
        node,
        ast.Assign,
    ):

        targets = node.targets

    else:

        targets = [
            node.target
        ]


    for target in targets:

        count = target_count(
            target
        )

        unpack_contracts.append(
            (
                node.lineno,
                name,
                count,
            )
        )

        emit(
            f"UNPACK line={node.lineno} "
            f"call={name} "
            f"expected_values={count}"
        )


if not unpack_contracts:

    emit(
        "UNPACK_CONTRACTS=NONE_FOUND"
    )


section(
    "8. BRIDGE RETURN SHAPES"
)


def describe_return(
    node
):

    value = node.value

    if value is None:
        return "NONE"

    if isinstance(
        value,
        ast.Tuple,
    ):

        return (
            "TUPLE:"
            +
            str(
                len(
                    value.elts
                )
            )
        )

    if isinstance(
        value,
        ast.List,
    ):

        return (
            "LIST_LITERAL:"
            +
            str(
                len(
                    value.elts
                )
            )
        )

    if isinstance(
        value,
        ast.Dict,
    ):

        return (
            "DICT_LITERAL:"
            +
            str(
                len(
                    value.keys
                )
            )
        )

    if isinstance(
        value,
        ast.Name,
    ):

        return (
            "NAME:"
            +
            value.id
        )

    if isinstance(
        value,
        ast.Call,
    ):

        try:

            return (
                "CALL:"
                +
                ast.unparse(
                    value.func
                )
            )

        except Exception:

            return "CALL"

    try:

        return (
            type(value).__name__
            +
            ":"
            +
            ast.unparse(value)[:120]
        )

    except Exception:

        return type(
            value
        ).__name__


for name, fn in sorted(
    bridge_functions.items()
):

    returns = [
        n
        for n in ast.walk(fn)
        if isinstance(
            n,
            ast.Return
        )
    ]


    if not returns:

        emit(
            f"RETURN function={name} NONE_EXPLICIT"
        )

        continue


    for ret in returns:

        emit(
            f"RETURN function={name} "
            f"line={ret.lineno} "
            f"shape={describe_return(ret)}"
        )


section(
    "9. SUSPECT CALLSITE CONTEXT"
)


lines = midia_src.splitlines()


suspect_lines = sorted(
    {
        line
        for line, _name
        in interesting_calls
    }
)


for line in suspect_lines:

    start = max(
        1,
        line - 12,
    )

    end = min(
        len(lines),
        line + 18,
    )


    emit()
    emit(
        f"--- MIDIA CONTEXT {start}-{end} "
        f"(call at {line}) ---"
    )


    for n in range(
        start,
        end + 1,
    ):

        emit(
            f"{n:05d}: "
            f"{lines[n-1]}"
        )


section(
    "10. KNOWN FAILURE LINE CONTEXT"
)


for line in (
    4539,
    4736,
    4897,
    5009,
    5012,
):

    if line > len(lines):
        continue

    start = max(
        1,
        line - 12,
    )

    end = min(
        len(lines),
        line + 18,
    )


    emit()
    emit(
        f"--- KNOWN LINE {line} ---"
    )


    for n in range(
        start,
        end + 1,
    ):

        emit(
            f"{n:05d}: "
            f"{lines[n-1]}"
        )


section(
    "11. SAFE RUNTIME BRIDGE LOAD"
)

os.environ[
    "SAP_NO_PUBLISH"
] = "1"

os.environ[
    "SAP_VSE4_DIAGNOSTIC"
] = "1"


try:

    ns = runpy.run_path(
        str(BRIDGE),
        run_name="vse42_contract_probe",
    )


    emit(
        "BRIDGE_RUNTIME_LOAD=PASS"
    )


    for name in sorted(
        bridge_functions
    ):

        obj = ns.get(
            name
        )

        if not callable(
            obj
        ):
            continue

        try:

            signature = inspect.signature(
                obj
            )

        except Exception:

            signature = "UNKNOWN"


        emit(
            f"RUNTIME_FUNCTION={name} "
            f"SIGNATURE={signature}"
        )


    emit(
        "RUNTIME_COMMIT_CANDIDATE=",
        callable(
            ns.get(
                "commit_candidate"
            )
        ),
    )


except Exception as exc:

    emit(
        "BRIDGE_RUNTIME_LOAD=FAIL"
    )

    emit(
        "ERROR=",
        type(exc).__name__,
        str(exc),
    )

    emit(
        traceback.format_exc()
    )


section(
    "12. ERROR LOG CONTRACT EXTRACTION"
)


log_dir = ROOT / "logs" / "producao"

patterns = (
    "too many values to unpack",
    "not enough values to unpack",
    "cannot import name 'commit_candidate'",
    "mídia incompleta",
)


if log_dir.is_dir():

    logs = sorted(
        log_dir.glob("*.log"),
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )[:50]


    found = 0


    for log in logs:

        try:

            content = read(
                log
            )

        except Exception:

            continue


        matches = []

        for n, text in enumerate(
            content.splitlines(),
            start=1,
        ):

            if any(
                p in text
                for p in patterns
            ):

                matches.append(
                    (
                        n,
                        text,
                    )
                )


        if matches:

            found += 1

            emit()
            emit(
                "LOG=",
                log.name,
            )

            for n, text in matches[-30:]:

                emit(
                    f"{n}: {text}"
                )


    emit(
        "LOGS_WITH_CONTRACT_ERRORS=",
        found,
    )


section(
    "13. CONTRACT DIAGNOSIS"
)


if missing_exports:

    emit(
        "DIAGNOSIS_MISSING_EXPORTS=YES"
    )

    emit(
        "MISSING=",
        ",".join(
            missing_exports
        ),
    )

else:

    emit(
        "DIAGNOSIS_MISSING_EXPORTS=NO"
    )


if (
    "commit_candidate"
    not in
    bridge_functions
):

    emit(
        "COMMIT_API_CONTRACT=FAIL"
    )

else:

    emit(
        "COMMIT_API_CONTRACT=PASS"
    )


expected_three = [
    x
    for x in unpack_contracts
    if x[2] == 3
]


emit(
    "THREE_VALUE_UNPACK_SITES=",
    len(
        expected_three
    ),
)


for line, name, count in expected_three:

    emit(
        f"EXPECTED3 line={line} "
        f"call={name}"
    )


section(
    "14. FINAL SUMMARY"
)

emit(
    "PYTHON_COMPILE_FAILURES=",
    ",".join(
        compile_fail
    )
    or
    "NONE",
)

emit(
    "BRIDGE_MISSING_EXPORTS=",
    ",".join(
        missing_exports
    )
    or
    "NONE",
)

emit(
    "COMMIT_CANDIDATE_AVAILABLE=",
    "commit_candidate"
    in
    bridge_functions,
)

emit(
    "VSE42_UNPACK_CONTRACTS=",
    len(
        unpack_contracts
    ),
)

emit(
    "REPORT=",
    REPORT,
)

emit(
    "NETWORK_CALLED_BY_AUDITOR=NO"
)

emit(
    "MEDIA_DOWNLOADED=NO"
)

emit(
    "MIDIA_MODIFIED=NO"
)

emit(
    "BRIDGE_MODIFIED=NO"
)

emit(
    "VIDEO_RENDERED=NO"
)

emit(
    "VSE42_CONTRACT_FORENSICS=COMPLETE"
)


print()
print(
    "TERMUX_CONTINUA_ABERTO=SIM"
)
