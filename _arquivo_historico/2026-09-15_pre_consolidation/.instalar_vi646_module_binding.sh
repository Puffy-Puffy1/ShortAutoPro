#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/vi646_module_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================================"
echo " VI6.46 + VI6.47 + VI6.48"
echo " MODULE-LEVEL TRANSACTIONAL BINDING"
echo " DEFAULT = LEGACY"
echo "======================================================"
echo


# =====================================================
# 0. REQUIRED
# =====================================================

REQUIRED="
video.py
gerar_short.sh
vi6_37_renderer_shadow_adapter.py
vi6_42_binding_gate.py
vi6_43_exact_binding_planner.py
"

for F in $REQUIRED
do
    if [ ! -f "$F" ]; then
        echo "ERRO: $F ausente."
        exit 2
    fi
done


R42="logs/producao/vi6_42_binding_gate_latest.json"
R43="logs/producao/vi6_43_binding_plan_latest.json"
R45="logs/producao/vi6_45_micro_render_latest.json"


for F in "$R42" "$R43" "$R45"
do
    if [ ! -f "$F" ]; then
        echo "ERRO: relatório obrigatório ausente:"
        echo "$F"
        exit 3
    fi
done


# =====================================================
# 1. BACKUP
# =====================================================

cp video.py "$BACKDIR/video.py"

for F in \
    vi6_46_transactional_binding.py \
    vi6_47_renderer_switch.py \
    vi6_48_emergency_rollback.py \
    testar_vi646_module.py
do
    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi
done


rollback() {

    echo
    echo "======================================"
    echo " VI6.46 MODULE ROLLBACK"
    echo "======================================"

    cp "$BACKDIR/video.py" video.py

    for F in \
        vi6_46_transactional_binding.py \
        vi6_47_renderer_switch.py \
        vi6_48_emergency_rollback.py \
        testar_vi646_module.py
    do

        if [ -f "$BACKDIR/$F" ]; then
            cp "$BACKDIR/$F" "$F"
        else
            rm -f "$F"
        fi

    done

    echo "video.py restaurado."
}


# =====================================================
# 2. HARD GATE CHECK BEFORE CREATING BINDING
# =====================================================

echo "===== HARD PRE-BIND GATES ====="

if ! python - <<'PY'
import hashlib
import json
import os
from pathlib import Path


base = Path.home() / "ShortAutoPro"


def load(name, key):

    path = base / "logs" / "producao" / name

    with path.open(
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)[key]


r42 = load(
    "vi6_42_binding_gate_latest.json",
    "gate"
)

r43 = load(
    "vi6_43_binding_plan_latest.json",
    "plan"
)

r45 = load(
    "vi6_45_micro_render_latest.json",
    "certification"
)


current_hash = hashlib.sha256(
    (base / "video.py").read_bytes()
).hexdigest()


blockers = []


if not r42.get(
    "next_stage_allowed"
):

    blockers.append(
        "vi642_not_ready"
    )


if r42.get(
    "status"
) not in {
    "READY_FOR_CONTROLLED_BINDING",
    "READY_WITH_WARNINGS",
}:

    blockers.append(
        "vi642_status_invalid"
    )


if r43.get(
    "status"
) != "READY_FOR_ADAPTER_PREVIEW":

    blockers.append(
        "vi643_not_ready"
    )


if r43.get(
    "strategy"
) != "MODULE_LEVEL_SCENE_FILTER_BINDING":

    blockers.append(
        "vi643_wrong_strategy"
    )


if r43.get(
    "renderer_architecture"
) != "MODULE_LEVEL_PIPELINE":

    blockers.append(
        "vi643_wrong_architecture"
    )


if not r43.get(
    "renderer_execution_line"
):

    blockers.append(
        "vi643_execution_line_missing"
    )


if (
    r43.get(
        "video_sha256"
    )
    != current_hash
):

    blockers.append(
        "video_sha_changed_since_vi643"
    )


if r45.get(
    "status"
) != "CERTIFIED":

    blockers.append(
        "vi645_not_certified"
    )


if r45.get(
    "temporary_video_deleted"
) is not True:

    blockers.append(
        "vi645_temp_cleanup_not_verified"
    )


print(
    "VI6.42:",
    r42.get(
        "status"
    )
)

print(
    "VI6.43:",
    r43.get(
        "status"
    )
)

print(
    "VI6.43 STRATEGY:",
    r43.get(
        "strategy"
    )
)

print(
    "TARGET EXECUTION LINE:",
    r43.get(
        "renderer_execution_line"
    )
)

print(
    "VI6.45:",
    r45.get(
        "status"
    )
)

print(
    "VIDEO SHA MATCH:",
    r43.get(
        "video_sha256"
    )
    == current_hash
)

print(
    "BLOCKERS:",
    blockers
)


if blockers:
    raise SystemExit(1)
PY
then

    echo
    echo "BINDING BLOQUEADO."
    echo "video.py ainda não foi alterado."
    exit 4
fi


echo "PRE-BIND GATES=PASS"


# =====================================================
# 3. VI6.48 EMERGENCY FALLBACK
# =====================================================

cat > vi6_48_emergency_rollback.py <<'PY'
#!/usr/bin/env python3

import json
import os

from datetime import datetime


VERSION = "6.48-module"


BASE = os.path.expanduser(
    "~/ShortAutoPro"
)


FLAG = os.path.join(
    BASE,
    "temp",
    "vi648_force_legacy.flag"
)


LOG = os.path.join(
    BASE,
    "logs",
    "producao",
    "vi6_48_emergency_latest.json"
)


def forced_legacy():

    return os.path.exists(
        FLAG
    )


def trip(reason):

    try:

        os.makedirs(
            os.path.dirname(
                FLAG
            ),
            exist_ok=True
        )


        os.makedirs(
            os.path.dirname(
                LOG
            ),
            exist_ok=True
        )


        payload = {

            "version":
                VERSION,

            "forced_legacy":
                True,

            "reason":
                str(
                    reason
                )[:400],

            "time":
                datetime.now().isoformat(
                    timespec="seconds"
                ),
        }


        with open(
            FLAG,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                payload[
                    "reason"
                ]
                + "\n"
            )


        with open(
            LOG,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                payload,
                f,
                ensure_ascii=False,
                indent=2
            )


    except Exception:

        pass


def resolve_mode(
    requested
):

    requested = str(
        requested
        or "LEGACY"
    ).strip().upper()


    if forced_legacy():

        return (
            "LEGACY",
            "emergency_force_legacy"
        )


    if requested not in {
        "LEGACY",
        "SHADOW",
        "ACTIVE",
    }:

        return (
            "LEGACY",
            "invalid_mode"
        )


    # ACTIVE ainda permanece fechado.
    if requested == "ACTIVE":

        return (
            "LEGACY",
            "active_not_authorized"
        )


    return (
        requested,
        "ok"
    )


def self_test():

    assert (
        resolve_mode(
            "LEGACY"
        )[0]
        == "LEGACY"
    )


    assert (
        resolve_mode(
            "ACTIVE"
        )[0]
        == "LEGACY"
    )


    assert (
        resolve_mode(
            "INVALID"
        )[0]
        == "LEGACY"
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.48 MODULE FAILSAFE: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK LEGACY"
    )
    print(
        "OK ACTIVE blocked"
    )
    print(
        "OK Invalid -> LEGACY"
    )
    print()


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 4. VI6.47 MODULE COMMAND SWITCH
# =====================================================

cat > vi6_47_renderer_switch.py <<'PY'
#!/usr/bin/env python3

import json
import os

from datetime import datetime


from vi6_48_emergency_rollback import (
    resolve_mode,
    trip,
)


VERSION = "6.47-module"


BASE = os.path.expanduser(
    "~/ShortAutoPro"
)


LOG = os.path.join(
    BASE,
    "logs",
    "producao",
    "vi6_47_shadow_runtime_latest.json"
)


def _requested_mode():

    return str(
        os.getenv(
            "VI647_RENDERER_MODE",
            "LEGACY"
        )
        or "LEGACY"
    ).strip().upper()


def _find_vf(
    command
):

    try:

        index = command.index(
            "-vf"
        )


        if (
            index + 1
            < len(
                command
            )
        ):

            return (
                index,
                command[
                    index + 1
                ]
            )


    except Exception:

        pass


    return (
        None,
        None
    )


def _media_branch(
    command
):

    try:

        if (
            "-loop"
            in command
            and "1"
            in command
        ):

            return "STILL"


        if (
            "-stream_loop"
            in command
        ):

            return "VIDEO"


    except Exception:

        pass


    return "UNKNOWN"


def _shadow_log(
    command,
    context
):

    try:

        os.makedirs(
            os.path.dirname(
                LOG
            ),
            exist_ok=True
        )


        vf_index, vf = _find_vf(
            command
        )


        payload = {

            "version":
                VERSION,

            "time":
                datetime.now().isoformat(
                    timespec="seconds"
                ),

            "mode":
                "SHADOW",

            "branch":
                _media_branch(
                    command
                ),

            "command_length":
                len(
                    command
                ),

            "vf_index":
                vf_index,

            "has_vf":
                vf is not None,

            "has_zoompan":
                (
                    isinstance(
                        vf,
                        str
                    )
                    and "zoompan="
                    in vf
                ),

            "filter_preview":
                (
                    vf[:500]
                    if isinstance(
                        vf,
                        str
                    )
                    else None
                ),

            "context":
                context
                or {},

            "legacy_command_preserved":
                True,

            "command_mutated":
                False,

            "active_renderer_used":
                False,
        }


        with open(
            LOG,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                payload,
                f,
                ensure_ascii=False,
                indent=2
            )


    except Exception:

        # Telemetria jamais pode quebrar
        # o renderer legado.
        pass


def adapt_scene_command(
    command,
    context=None
):

    # Fail-safe máximo:
    # se algo não parece comando FFmpeg,
    # devolvemos exatamente o objeto recebido.
    if not isinstance(
        command,
        list
    ):

        return command


    requested = (
        _requested_mode()
    )


    try:

        mode, reason = resolve_mode(
            requested
        )


    except Exception as exc:

        trip(
            "resolve_mode:"
            + type(
                exc
            ).__name__
        )


        return command


    # =================================
    # LEGACY
    # =================================
    #
    # Não copia.
    # Não modifica.
    # Retorna o MESMO objeto.
    # =================================

    if mode == "LEGACY":

        return command


    # =================================
    # SHADOW
    # =================================
    #
    # Observa o comando real, mas
    # NÃO troca -vf.
    # =================================

    if mode == "SHADOW":

        _shadow_log(
            command,
            context
        )


        return command


    # Fail closed.
    return command


def self_test():

    original = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        "x.jpg",
        "-vf",
        "scale=1080:1920,zoompan=z='1.02'",
        "out.mp4",
    ]


    old = os.environ.get(
        "VI647_RENDERER_MODE"
    )


    try:

        os.environ[
            "VI647_RENDERER_MODE"
        ] = "LEGACY"


        out = adapt_scene_command(
            original
        )


        assert out is original


        assert out == original


        os.environ[
            "VI647_RENDERER_MODE"
        ] = "SHADOW"


        before = list(
            original
        )


        out = adapt_scene_command(
            original,
            {
                "self_test":
                    True
            }
        )


        assert out is original

        assert original == before


        os.environ[
            "VI647_RENDERER_MODE"
        ] = "ACTIVE"


        out = adapt_scene_command(
            original
        )


        assert out is original

        assert original == before


    finally:

        if old is None:

            os.environ.pop(
                "VI647_RENDERER_MODE",
                None
            )

        else:

            os.environ[
                "VI647_RENDERER_MODE"
            ] = old


    print()
    print(
        "======================================"
    )
    print(
        " VI6.47 MODULE SWITCH: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Same Command Object"
    )
    print(
        "OK LEGACY No Mutation"
    )
    print(
        "OK SHADOW No Mutation"
    )
    print(
        "OK ACTIVE Falls Back"
    )
    print()


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 5. VI6.46 TRANSACTIONAL PATCHER
# =====================================================

cat > vi6_46_transactional_binding.py <<'PY'
#!/usr/bin/env python3

import argparse
import ast
import hashlib
import json
import os

from datetime import datetime
from pathlib import Path


VERSION = "6.46-module"


BASE = Path.home() / "ShortAutoPro"


VIDEO = BASE / "video.py"


R43 = (
    BASE
    / "logs"
    / "producao"
    / "vi6_43_binding_plan_latest.json"
)


MANIFEST = (
    BASE
    / "logs"
    / "producao"
    / "vi6_46_binding_manifest_latest.json"
)


MARKER = (
    "# VI6.46 MODULE-LEVEL "
    "TRANSACTIONAL BINDING"
)


def _sha(
    path
):

    return hashlib.sha256(
        Path(
            path
        ).read_bytes()
    ).hexdigest()


def _call_name(
    node
):

    if isinstance(
        node.func,
        ast.Name
    ):

        return node.func.id


    if isinstance(
        node.func,
        ast.Attribute
    ):

        parts = []

        current = node.func


        while isinstance(
            current,
            ast.Attribute
        ):

            parts.append(
                current.attr
            )

            current = (
                current.value
            )


        if isinstance(
            current,
            ast.Name
        ):

            parts.append(
                current.id
            )


        return ".".join(
            reversed(
                parts
            )
        )


    return ""


def _load_plan():

    with R43.open(
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(
            f
        )["plan"]


def _target():

    plan = _load_plan()


    line = int(
        plan[
            "renderer_execution_line"
        ]
    )


    source = VIDEO.read_text(
        encoding="utf-8"
    )


    tree = ast.parse(
        source
    )


    parent = {}


    for node in ast.walk(
        tree
    ):

        for child in ast.iter_child_nodes(
            node
        ):

            parent[
                child
            ] = node


    matches = []


    for node in ast.walk(
        tree
    ):

        if not isinstance(
            node,
            ast.Call
        ):

            continue


        if node.lineno != line:

            continue


        if (
            _call_name(
                node
            )
            != "subprocess.run"
        ):

            continue


        if not node.args:

            continue


        first = node.args[0]


        if not (
            isinstance(
                first,
                ast.Name
            )
            and first.id
            == "comando"
        ):

            continue


        matches.append(
            node
        )


    if len(
        matches
    ) != 1:

        raise RuntimeError(
            "expected_one_target_run:"
            + str(
                len(
                    matches
                )
            )
        )


    call = matches[0]


    current = call


    target_try = None


    while current in parent:

        current = parent[
            current
        ]


        if isinstance(
            current,
            ast.Try
        ):

            target_try = current

            break


    if target_try is None:

        raise RuntimeError(
            "renderer_try_not_found"
        )


    return {
        "plan":
            plan,

        "source":
            source,

        "call_line":
            call.lineno,

        "try_line":
            target_try.lineno,
    }


def precheck():

    source = VIDEO.read_text(
        encoding="utf-8"
    )


    if MARKER in source:

        return {

            "status":
                "ALREADY_BOUND",

            "video_sha256":
                _sha(
                    VIDEO
                ),
        }


    target = _target()


    plan = target[
        "plan"
    ]


    blockers = []


    if plan.get(
        "status"
    ) != "READY_FOR_ADAPTER_PREVIEW":

        blockers.append(
            "plan_not_ready"
        )


    if plan.get(
        "strategy"
    ) != "MODULE_LEVEL_SCENE_FILTER_BINDING":

        blockers.append(
            "wrong_strategy"
        )


    if plan.get(
        "video_sha256"
    ) != _sha(
        VIDEO
    ):

        blockers.append(
            "video_hash_changed"
        )


    return {

        "status":
            (
                "READY"
                if not blockers
                else "HOLD"
            ),

        "blockers":
            blockers,

        "renderer_execution_line":
            target[
                "call_line"
            ],

        "insertion_line":
            target[
                "try_line"
            ],

        "video_sha256":
            _sha(
                VIDEO
            ),
    }


def _bridge_block(
    indent
):

    i = indent


    return [

        i + MARKER,

        i + "try:",

        i + (
            "    from vi6_47_renderer_switch "
            "import adapt_scene_command "
            "as _vi647_adapt_scene_command"
        ),

        "",

        i + (
            "    comando = "
            "_vi647_adapt_scene_command("
        ),

        i + "        comando,",

        i + "        {",

        i + (
            "            \"source\": "
            "\"video.py\","
        ),

        i + (
            "            \"stage\": "
            "\"SCENE_RENDER_PRIMARY\","
        ),

        i + "        },",

        i + "    )",

        "",

        i + (
            "except Exception "
            "as _vi647_bridge_exc:"
        ),

        i + "    try:",

        i + (
            "        from "
            "vi6_48_emergency_rollback "
            "import trip as _vi648_trip"
        ),

        "",

        i + "        _vi648_trip(",

        i + (
            "            \"scene_command_bridge:\""
        ),

        i + (
            "            + type("
            "_vi647_bridge_exc"
            ").__name__"
        ),

        i + "        )",

        "",

        i + "    except Exception:",

        i + "        pass",

        "",
    ]


def bind(
    backup_path
):

    check = precheck()


    if check[
        "status"
    ] == "ALREADY_BOUND":

        return check


    if check[
        "status"
    ] != "READY":

        return check


    target = _target()


    original = VIDEO.read_bytes()


    source = original.decode(
        "utf-8"
    )


    lines = source.splitlines(
        keepends=True
    )


    insertion_line = int(
        target[
            "try_line"
        ]
    )


    original_line = (
        lines[
            insertion_line - 1
        ]
    )


    indent = (
        original_line[
            :len(
                original_line
            )
            - len(
                original_line.lstrip()
            )
        ]
    )


    block = _bridge_block(
        indent
    )


    block_text = (
        "\n".join(
            block
        )
        + "\n"
    )


    patched_lines = (
        lines[
            :insertion_line - 1
        ]
        + [
            block_text
        ]
        + lines[
            insertion_line - 1:
        ]
    )


    patched = "".join(
        patched_lines
    )


    # Sintaxe antes de tocar no original.
    ast.parse(
        patched
    )


    Path(
        backup_path
    ).write_bytes(
        original
    )


    temp = VIDEO.with_name(
        ".video.py.vi646.tmp"
    )


    temp.write_text(
        patched,
        encoding="utf-8"
    )


    os.replace(
        temp,
        VIDEO
    )


    # Validação após escrita.
    final_source = VIDEO.read_text(
        encoding="utf-8"
    )


    if final_source.count(
        MARKER
    ) != 1:

        VIDEO.write_bytes(
            original
        )

        raise RuntimeError(
            "binding_marker_invalid"
        )


    ast.parse(
        final_source
    )


    result = {

        "version":
            VERSION,

        "status":
            "BOUND_LEGACY_DEFAULT",

        "architecture":
            "MODULE_LEVEL_PIPELINE",

        "renderer_execution_line_before":
            target[
                "call_line"
            ],

        "binding_insertion_line_before":
            target[
                "try_line"
            ],

        "strategy":
            "PRE_RUN_COMMAND_ADAPTER",

        "default_mode":
            "LEGACY",

        "shadow_available":
            True,

        "active_available":
            False,

        "video_sha256_before":
            hashlib.sha256(
                original
            ).hexdigest(),

        "video_sha256_after":
            _sha(
                VIDEO
            ),

        "backup":
            str(
                backup_path
            ),

        "ffmpeg_executed":
            False,

        "video_generated":
            False,
    }


    MANIFEST.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    with MANIFEST.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "binding":
                    result,
            },
            f,
            ensure_ascii=False,
            indent=2
        )


    return result


def verify():

    source = VIDEO.read_text(
        encoding="utf-8"
    )


    ast.parse(
        source
    )


    return {

        "status":
            (
                "BOUND_VALID"
                if source.count(
                    MARKER
                ) == 1
                else "INVALID"
            ),

        "marker_count":
            source.count(
                MARKER
            ),

        "has_adapter":
            (
                "adapt_scene_command"
                in source
            ),

        "has_subprocess_run":
            (
                "subprocess.run"
                in source
            ),

        "video_sha256":
            _sha(
                VIDEO
            ),
    }


def self_test():

    result = precheck()


    assert result[
        "status"
    ] in {
        "READY",
        "ALREADY_BOUND",
    }, result


    print()
    print(
        "======================================"
    )
    print(
        " VI6.46 MODULE PRECHECK: PASS"
    )
    print(
        "======================================"
    )


def main():

    parser = argparse.ArgumentParser()


    parser.add_argument(
        "--check",
        action="store_true"
    )


    parser.add_argument(
        "--bind"
    )


    parser.add_argument(
        "--verify",
        action="store_true"
    )


    args = parser.parse_args()


    if args.check:

        print(
            json.dumps(
                precheck(),
                ensure_ascii=False,
                indent=2
            )
        )

        return


    if args.bind:

        print(
            json.dumps(
                bind(
                    args.bind
                ),
                ensure_ascii=False,
                indent=2
            )
        )

        return


    if args.verify:

        print(
            json.dumps(
                verify(),
                ensure_ascii=False,
                indent=2
            )
        )

        return


    self_test()


if __name__ == "__main__":
    main()
PY


# =====================================================
# 6. COMPILE MODULES BEFORE TOUCHING VIDEO
# =====================================================

echo
echo "===== MODULE COMPILE ====="

if ! python -m py_compile \
    vi6_46_transactional_binding.py \
    vi6_47_renderer_switch.py \
    vi6_48_emergency_rollback.py
then

    rollback
    exit 1
fi


echo "MODULE COMPILE=PASS"


# =====================================================
# 7. SELF TESTS
# =====================================================

python vi6_48_emergency_rollback.py || {
    rollback
    exit 1
}


python vi6_47_renderer_switch.py || {
    rollback
    exit 1
}


python vi6_46_transactional_binding.py || {
    rollback
    exit 1
}


# =====================================================
# 8. PRECHECK
# =====================================================

echo
echo "===== VI6.46 REAL PRECHECK ====="

CHECK="$(
python \
    vi6_46_transactional_binding.py \
    --check
)"


echo "$CHECK"


READY="$(
printf '%s\n' "$CHECK" \
| python -c '
import json,sys
try:
    x=json.load(sys.stdin)
    print(
        "YES"
        if x.get("status") == "READY"
        else (
            "ALREADY"
            if x.get("status") == "ALREADY_BOUND"
            else "NO"
        )
    )
except Exception:
    print("NO")
'
)"


echo
echo "READY=$READY"


if [ "$READY" = "NO" ]; then

    echo "Binding abortado."

    rollback
    exit 5
fi


# =====================================================
# 9. REAL TRANSACTIONAL BIND
# =====================================================

if [ "$READY" = "YES" ]; then

    echo
    echo "======================================"
    echo " APPLYING MODULE-LEVEL BINDING"
    echo "======================================"

    if ! python \
        vi6_46_transactional_binding.py \
        --bind \
        "$BACKDIR/video.py.original"
    then

        rollback
        exit 1
    fi

else

    echo "Binding já presente."
fi


# =====================================================
# 10. POST-PATCH COMPILE
# =====================================================

echo
echo "===== VIDEO.PY POST-PATCH COMPILE ====="

if ! python -m py_compile video.py; then

    rollback
    exit 1
fi


echo "VIDEO.PY COMPILE=PASS"


# =====================================================
# 11. VERIFY
# =====================================================

echo
echo "===== VI6.46 VERIFY ====="

VERIFY="$(
python \
    vi6_46_transactional_binding.py \
    --verify
)"


echo "$VERIFY"


VALID="$(
printf '%s\n' "$VERIFY" \
| python -c '
import json,sys
try:
    x=json.load(sys.stdin)
    print(
        "YES"
        if (
            x.get("status") == "BOUND_VALID"
            and x.get("marker_count") == 1
            and x.get("has_adapter")
        )
        else "NO"
    )
except Exception:
    print("NO")
'
)"


if [ "$VALID" != "YES" ]; then

    rollback
    exit 1
fi


# =====================================================
# 12. STATIC PROOF:
#     ORIGINAL RUN STILL EXISTS AFTER BRIDGE
# =====================================================

echo
echo "===== AST BINDING PROOF ====="

if ! python - <<'PY'
import ast
from pathlib import Path


source = Path(
    "video.py"
).read_text(
    encoding="utf-8"
)


tree = ast.parse(
    source
)


marker = (
    "# VI6.46 MODULE-LEVEL "
    "TRANSACTIONAL BINDING"
)


assert source.count(
    marker
) == 1


adapter_calls = 0

legacy_runs = 0


for node in ast.walk(
    tree
):

    if not isinstance(
        node,
        ast.Call
    ):
        continue


    if isinstance(
        node.func,
        ast.Name
    ):

        if (
            node.func.id
            == "_vi647_adapt_scene_command"
        ):

            adapter_calls += 1


    if isinstance(
        node.func,
        ast.Attribute
    ):

        if (
            isinstance(
                node.func.value,
                ast.Name
            )
            and node.func.value.id
            == "subprocess"
            and node.func.attr
            == "run"
        ):

            if (
                node.args
                and isinstance(
                    node.args[0],
                    ast.Name
                )
                and node.args[0].id
                == "comando"
            ):

                legacy_runs += 1


print(
    "ADAPTER CALLS:",
    adapter_calls
)

print(
    "LEGACY subprocess.run(comando):",
    legacy_runs
)


assert adapter_calls == 1

assert legacy_runs >= 1


print(
    "AST BINDING PROOF=PASS"
)
PY
then

    rollback
    exit 1
fi


# =====================================================
# 13. NO-RUNTIME INTEGRATION TEST
# =====================================================

cat > testar_vi646_module.py <<'PY'
#!/usr/bin/env python3

import os

from vi6_47_renderer_switch import (
    adapt_scene_command
)


photo = [
    "ffmpeg",
    "-y",
    "-loop",
    "1",
    "-i",
    "photo.jpg",
    "-vf",
    "scale=1200:2133,zoompan=z='1.02'",
    "scene.mp4",
]


video = [
    "ffmpeg",
    "-y",
    "-stream_loop",
    "-1",
    "-i",
    "clip.mp4",
    "-t",
    "4",
    "-vf",
    "scale=1080:1920",
    "scene.mp4",
]


old = os.environ.get(
    "VI647_RENDERER_MODE"
)


try:

    for mode in (
        "LEGACY",
        "SHADOW",
        "ACTIVE",
    ):

        os.environ[
            "VI647_RENDERER_MODE"
        ] = mode


        for command in (
            photo,
            video,
        ):

            snapshot = list(
                command
            )


            result = adapt_scene_command(
                command,
                {
                    "test":
                        True
                }
            )


            assert result is command

            assert command == snapshot


finally:

    if old is None:

        os.environ.pop(
            "VI647_RENDERER_MODE",
            None
        )

    else:

        os.environ[
            "VI647_RENDERER_MODE"
        ] = old


print()
print(
    "======================================"
)
print(
    " VI6.46-6.48 MODULE TEST: PASS"
)
print(
    "======================================"
)

print(
    "PHOTO COMMAND PRESERVED=YES"
)

print(
    "VIDEO COMMAND PRESERVED=YES"
)

print(
    "LEGACY NO MUTATION=YES"
)

print(
    "SHADOW NO MUTATION=YES"
)

print(
    "ACTIVE BLOCKED=YES"
)

print(
    "FFMPEG EXECUTED=0"
)

print(
    "VIDEO GENERATED=0"
)
PY


python testar_vi646_module.py || {
    rollback
    exit 1
}


# =====================================================
# 14. BASH + RELEASE
# =====================================================

echo
echo "===== BASH CHECK ====="

bash -n gerar_short.sh || {
    rollback
    exit 1
}


echo "BASH STATUS=0"


echo
echo "===== RELEASE CHECK ====="

if ! ./release_check.sh; then

    rollback
    exit 1
fi


# =====================================================
# 15. FINAL
# =====================================================

echo
echo "======================================================"
echo " VI6.46 + VI6.47 + VI6.48 MODULE BINDING INSTALLED"
echo "======================================================"

python - <<'PY'
import json
import os
from pathlib import Path


manifest = Path.home() / (
    "ShortAutoPro/logs/producao/"
    "vi6_46_binding_manifest_latest.json"
)


if manifest.exists():

    data = json.loads(
        manifest.read_text(
            encoding="utf-8"
        )
    )["binding"]


    print(
        "STATUS:",
        data.get(
            "status"
        )
    )


    print(
        "ARCHITECTURE:",
        data.get(
            "architecture"
        )
    )


    print(
        "STRATEGY:",
        data.get(
            "strategy"
        )
    )


    print(
        "ORIGINAL EXECUTION LINE:",
        data.get(
            "renderer_execution_line_before"
        )
    )


    print(
        "DEFAULT MODE:",
        data.get(
            "default_mode"
        )
    )


    print(
        "SHADOW AVAILABLE:",
        data.get(
            "shadow_available"
        )
    )


    print(
        "ACTIVE AVAILABLE:",
        data.get(
            "active_available"
        )
    )


print()
print(
    "VIDEO.PY MODIFIED=YES"
)

print(
    "MODIFICATION=PRE-RUN TRANSACTIONAL BRIDGE"
)

print(
    "LEGACY COMMAND MODIFIED=NO"
)

print(
    "DEFAULT RENDERER=LEGACY"
)

print(
    "SHADOW MUTATES COMMAND=NO"
)

print(
    "ACTIVE RENDERER=BLOCKED"
)

print(
    "FFMPEG EXECUTED DURING INSTALL=NO"
)

print(
    "VIDEO GENERATED DURING INSTALL=NO"
)

print(
    "API CALLS=0"
)

print(
    "DOWNLOADS=0"
)
PY

echo
echo "EMERGENCY FLAG:"
echo "temp/vi648_force_legacy.flag"
echo
echo "SHADOW LOG:"
echo "logs/producao/vi6_47_shadow_runtime_latest.json"
echo
echo "BINDING MANIFEST:"
echo "logs/producao/vi6_46_binding_manifest_latest.json"
echo
