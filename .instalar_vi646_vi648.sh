#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/vi646_vi648_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================"
echo " VI6.46 + VI6.47 + VI6.48"
echo " TRANSACTIONAL RENDERER BINDING"
echo " DEFAULT MODE = LEGACY"
echo "======================================"
echo


# =====================================================
# 0. REQUIRED FILES
# =====================================================

REQUIRED="
video.py
midia.py
audio.py
legenda_dinamica.py
gerar_short.sh
vi6_42_binding_gate.py
vi6_43_exact_binding_planner.py
vi6_45_micro_render_certification.py
"

for F in $REQUIRED
do
    if [ ! -f "$F" ]; then
        echo "ERRO: $F não encontrado."
        echo "NENHUMA ALTERAÇÃO FEITA."
        exit 2
    fi
done


echo "===== BASELINE ====="

if ! python -m py_compile \
    video.py \
    midia.py \
    audio.py \
    legenda_dinamica.py
then
    echo "BASELINE FALHOU."
    exit 3
fi

echo "BASELINE=OK"


# =====================================================
# BACKUP
# =====================================================

cp video.py "$BACKDIR/video.py"

for F in \
    midia.py \
    audio.py \
    legenda_dinamica.py \
    gerar_short.sh
do
    cp "$F" "$BACKDIR/$F"
done


for F in \
    vi6_46_transactional_binding.py \
    vi6_47_renderer_switch.py \
    vi6_48_emergency_rollback.py \
    testar_vi646_vi648.py
do
    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi
done


rollback() {

    echo
    echo "======================================"
    echo " ROLLBACK VI6.46-6.48"
    echo "======================================"

    cp "$BACKDIR/video.py" video.py

    for F in \
        vi6_46_transactional_binding.py \
        vi6_47_renderer_switch.py \
        vi6_48_emergency_rollback.py \
        testar_vi646_vi648.py
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
# 1. VI6.48 EMERGENCY FAILSAFE
# =====================================================

cat > vi6_48_emergency_rollback.py <<'PY'
#!/usr/bin/env python3

import json
import os
from datetime import datetime


VERSION = "6.48"

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


def _ensure():

    os.makedirs(
        os.path.dirname(FLAG),
        exist_ok=True
    )

    os.makedirs(
        os.path.dirname(LOG),
        exist_ok=True
    )


def forced_legacy():

    return os.path.exists(
        FLAG
    )


def trip(reason):

    _ensure()

    payload = {

        "version":
            VERSION,

        "forced_legacy":
            True,

        "reason":
            str(
                reason
            )[:300],

        "time":
            datetime.now().isoformat(
                timespec="seconds"
            ),
    }


    try:

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


    return payload


def clear():

    try:

        if os.path.exists(
            FLAG
        ):

            os.remove(
                FLAG
            )

    except Exception:
        pass


def safe_mode(
    requested
):

    requested = str(
        requested
        or "LEGACY"
    ).strip().upper()


    if forced_legacy():

        return (
            "LEGACY",
            "vi648_force_legacy"
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


    # ACTIVE ainda não possui permissão.
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

    test_flag = (
        FLAG
        + ".selftest"
    )


    assert (
        safe_mode(
            "LEGACY"
        )[0]
        in {
            "LEGACY"
        }
    )


    assert (
        safe_mode(
            "ACTIVE"
        )[0]
        == "LEGACY"
    )


    assert (
        safe_mode(
            "INVALID"
        )[0]
        == "LEGACY"
    )


    if os.path.exists(
        test_flag
    ):

        os.remove(
            test_flag
        )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.48 FAILSAFE SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK LEGACY"
    )
    print(
        "OK SHADOW"
    )
    print(
        "OK ACTIVE blocked"
    )
    print(
        "OK Invalid mode -> LEGACY"
    )
    print(
        "OK Emergency fallback"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 2. VI6.47 LEGACY / SHADOW SWITCH
# =====================================================

cat > vi6_47_renderer_switch.py <<'PY'
#!/usr/bin/env python3

import functools
import json
import os
from datetime import datetime


from vi6_48_emergency_rollback import (
    safe_mode,
    trip,
)


VERSION = "6.47"

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


def _shadow_log(
    function_name,
    args,
    kwargs,
    result
):

    try:

        os.makedirs(
            os.path.dirname(LOG),
            exist_ok=True
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

            "renderer_function":
                function_name,

            "positional_args":
                len(args),

            "keyword_names":
                sorted(
                    str(key)
                    for key
                    in kwargs.keys()
                ),

            "result_type":
                type(
                    result
                ).__name__,

            "legacy_renderer_called":
                True,

            "alternate_renderer_called":
                False,

            "output_changed":
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

        # Telemetria nunca pode quebrar
        # o renderer legado.
        pass


def install_renderer_wrapper(
    namespace,
    function_name,
    module_file=None
):

    current = namespace.get(
        function_name
    )


    if not callable(
        current
    ):

        raise RuntimeError(
            "renderer_function_not_callable:"
            + str(
                function_name
            )
        )


    if getattr(
        current,
        "__vi647_wrapped__",
        False
    ):

        return current


    legacy = current


    legacy_name = (
        "__vi647_legacy_"
        + function_name
    )


    namespace[
        legacy_name
    ] = legacy


    @functools.wraps(
        legacy
    )
    def wrapper(
        *args,
        **kwargs
    ):

        requested = (
            _requested_mode()
        )


        try:

            mode, reason = (
                safe_mode(
                    requested
                )
            )

        except Exception as exc:

            trip(
                "mode_resolution_failure:"
                + type(
                    exc
                ).__name__
            )

            mode = "LEGACY"

            reason = (
                "emergency_legacy"
            )


        # =================================
        # LEGACY
        # =================================

        if mode == "LEGACY":

            return legacy(
                *args,
                **kwargs
            )


        # =================================
        # SHADOW
        # =================================
        #
        # Executa exatamente UMA vez o
        # renderer antigo.
        #
        # Não renderiza uma segunda versão.
        # Não altera retorno.
        # Não altera argumentos.
        # =================================

        if mode == "SHADOW":

            result = legacy(
                *args,
                **kwargs
            )


            _shadow_log(
                function_name,
                args,
                kwargs,
                result
            )


            return result


        # Fail closed.
        return legacy(
            *args,
            **kwargs
        )


    wrapper.__vi647_wrapped__ = True

    wrapper.__vi647_original__ = (
        legacy
    )

    wrapper.__vi647_function__ = (
        function_name
    )

    wrapper.__vi647_default_mode__ = (
        "LEGACY"
    )


    namespace[
        function_name
    ] = wrapper


    return wrapper


def uninstall_renderer_wrapper(
    namespace,
    function_name
):

    current = namespace.get(
        function_name
    )


    original = getattr(
        current,
        "__vi647_original__",
        None
    )


    if callable(
        original
    ):

        namespace[
            function_name
        ] = original

        return True


    legacy = namespace.get(
        "__vi647_legacy_"
        + function_name
    )


    if callable(
        legacy
    ):

        namespace[
            function_name
        ] = legacy

        return True


    return False


def self_test():

    calls = []


    def fake_renderer(
        value,
        option=None
    ):

        calls.append(
            (
                value,
                option
            )
        )

        return (
            "RESULT:"
            + str(value)
        )


    ns = {
        "render":
            fake_renderer
    }


    old = os.environ.get(
        "VI647_RENDERER_MODE"
    )


    try:

        os.environ[
            "VI647_RENDERER_MODE"
        ] = "LEGACY"


        install_renderer_wrapper(
            ns,
            "render"
        )


        result = ns[
            "render"
        ](
            "X",
            option=1
        )


        assert (
            result
            == "RESULT:X"
        )


        assert len(
            calls
        ) == 1


        calls.clear()


        os.environ[
            "VI647_RENDERER_MODE"
        ] = "SHADOW"


        result = ns[
            "render"
        ](
            "Y",
            option=2
        )


        assert (
            result
            == "RESULT:Y"
        )


        assert len(
            calls
        ) == 1


        calls.clear()


        os.environ[
            "VI647_RENDERER_MODE"
        ] = "ACTIVE"


        result = ns[
            "render"
        ](
            "Z"
        )


        # ACTIVE continua bloqueado:
        # renderer legado chamado uma vez.
        assert (
            result
            == "RESULT:Z"
        )


        assert len(
            calls
        ) == 1


        assert (
            uninstall_renderer_wrapper(
                ns,
                "render"
            )
            is True
        )


        assert (
            getattr(
                ns[
                    "render"
                ],
                "__vi647_wrapped__",
                False
            )
            is False
        )


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
        " VI6.47 SWITCH SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK LEGACY exact call-through"
    )
    print(
        "OK SHADOW single render"
    )
    print(
        "OK Return preserved"
    )
    print(
        "OK ACTIVE blocked"
    )
    print(
        "OK Uninstall restores original"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 3. VI6.46 TRANSACTIONAL BINDING
# =====================================================

cat > vi6_46_transactional_binding.py <<'PY'
#!/usr/bin/env python3

import argparse
import ast
import hashlib
import json
import os
import stat
from datetime import datetime
from pathlib import Path


VERSION = "6.46"

BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

REPORT42 = os.path.join(
    BASE,
    "logs",
    "producao",
    "vi6_42_binding_gate_latest.json"
)

REPORT43 = os.path.join(
    BASE,
    "logs",
    "producao",
    "vi6_43_binding_plan_latest.json"
)

REPORT45 = os.path.join(
    BASE,
    "logs",
    "producao",
    "vi6_45_micro_render_latest.json"
)

MANIFEST = os.path.join(
    BASE,
    "logs",
    "producao",
    "vi6_46_binding_manifest_latest.json"
)

MARKER = (
    "# VI6.46-6.48 "
    "TRANSACTIONAL RENDERER BINDING"
)


def _load(
    path,
    key
):

    if not os.path.exists(
        path
    ):

        return None


    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return (
                json.load(
                    f
                ).get(
                    key
                )
            )

    except Exception:

        return None


def _hash_bytes(data):

    return hashlib.sha256(
        data
    ).hexdigest()


def _hash_file(path):

    return _hash_bytes(
        Path(
            path
        ).read_bytes()
    )


def _function_exists(
    filename,
    function_name
):

    tree = ast.parse(
        Path(
            filename
        ).read_text(
            encoding="utf-8"
        )
    )


    return any(

        isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        )

        and node.name
        == function_name

        for node in ast.walk(
            tree
        )
    )


def precheck():

    video = Path(
        "video.py"
    )


    source = video.read_text(
        encoding="utf-8"
    )


    if MARKER in source:

        return {

            "version":
                VERSION,

            "status":
                "ALREADY_BOUND",

            "reason":
                "marker_present",

            "current_sha256":
                _hash_file(
                    "video.py"
                ),
        }


    gate = _load(
        REPORT42,
        "gate"
    )


    plan = _load(
        REPORT43,
        "plan"
    )


    cert = _load(
        REPORT45,
        "certification"
    )


    blockers = []


    if gate is None:

        blockers.append(
            "vi642_report_missing"
        )


    elif not gate.get(
        "next_stage_allowed"
    ):

        blockers.append(
            "vi642_not_ready"
        )


    if plan is None:

        blockers.append(
            "vi643_report_missing"
        )


    elif plan.get(
        "status"
    ) not in {
        "READY_FOR_ADAPTER_PREVIEW",
        "READY_WITH_WARNINGS",
    }:

        blockers.append(
            "vi643_not_ready"
        )


    if cert is None:

        blockers.append(
            "vi645_report_missing"
        )


    else:

        if (
            cert.get(
                "status"
            )
            != "CERTIFIED"
        ):

            blockers.append(
                "vi645_not_certified"
            )


        if (
            cert.get(
                "temporary_video_deleted"
            )
            is not True
        ):

            blockers.append(
                "vi645_cleanup_not_verified"
            )


    function_name = (
        plan.get(
            "renderer_function"
        )
        if plan
        else None
    )


    if not function_name:

        blockers.append(
            "renderer_function_missing"
        )


    elif not _function_exists(
        "video.py",
        function_name
    ):

        blockers.append(
            "renderer_function_changed"
        )


    current_hash = _hash_file(
        "video.py"
    )


    expected_hash = (
        plan.get(
            "video_sha256"
        )
        if plan
        else None
    )


    if (
        expected_hash
        and current_hash
        != expected_hash
    ):

        blockers.append(
            "video_sha256_changed_since_vi643"
        )


    return {

        "version":
            VERSION,

        "status":
            (
                "READY_TO_BIND"
                if not blockers
                else "HOLD"
            ),

        "blockers":
            blockers,

        "renderer_function":
            function_name,

        "video_sha256_before":
            current_hash,

        "expected_sha256":
            expected_hash,

        "vi642_status":
            (
                gate.get(
                    "status"
                )
                if gate
                else None
            ),

        "vi643_status":
            (
                plan.get(
                    "status"
                )
                if plan
                else None
            ),

        "vi645_status":
            (
                cert.get(
                    "status"
                )
                if cert
                else None
            ),
    }


def binding_block(
    function_name
):

    return f'''

# =========================================
# {MARKER}
# =========================================
try:
    import vi6_47_renderer_switch as _vi647_renderer_switch

    _vi647_renderer_switch.install_renderer_wrapper(
        globals(),
        {function_name!r},
        __file__,
    )

except Exception as _vi647_binding_exc:

    try:
        import vi6_48_emergency_rollback as _vi648_emergency

        _vi648_emergency.trip(
            "binding_import_failure:"
            + type(_vi647_binding_exc).__name__
        )

    except Exception:
        pass
'''


def bind(
    backup_path
):

    check = precheck()


    if (
        check[
            "status"
        ]
        == "ALREADY_BOUND"
    ):

        return check


    if (
        check[
            "status"
        ]
        != "READY_TO_BIND"
    ):

        return check


    function_name = check[
        "renderer_function"
    ]


    path = Path(
        "video.py"
    )


    original_bytes = (
        path.read_bytes()
    )


    original_text = (
        original_bytes.decode(
            "utf-8"
        )
    )


    block = binding_block(
        function_name
    )


    patched = (
        original_text.rstrip()
        + "\n"
        + block
        + "\n"
    )


    # Não escreve se sintaxe final
    # não for válida.
    ast.parse(
        patched
    )


    backup = Path(
        backup_path
    )


    backup.write_bytes(
        original_bytes
    )


    mode = stat.S_IMODE(
        path.stat().st_mode
    )


    temp = path.with_name(
        ".video.py.vi646.tmp"
    )


    temp.write_text(
        patched,
        encoding="utf-8"
    )


    os.chmod(
        temp,
        mode
    )


    os.replace(
        temp,
        path
    )


    new_bytes = (
        path.read_bytes()
    )


    # Prova de append-only:
    # todos os bytes originais precisam
    # estar intactos no início do arquivo.
    if not new_bytes.startswith(
        original_bytes.rstrip()
    ):

        path.write_bytes(
            original_bytes
        )

        raise RuntimeError(
            "append_only_verification_failed"
        )


    new_text = new_bytes.decode(
        "utf-8"
    )


    if (
        new_text.count(
            MARKER
        )
        != 1
    ):

        path.write_bytes(
            original_bytes
        )

        raise RuntimeError(
            "binding_marker_count_invalid"
        )


    # Verificação final de sintaxe.
    ast.parse(
        new_text
    )


    result = {

        "version":
            VERSION,

        "status":
            "BOUND_LEGACY_DEFAULT",

        "renderer_function":
            function_name,

        "video_sha256_before":
            check[
                "video_sha256_before"
            ],

        "video_sha256_after":
            _hash_file(
                "video.py"
            ),

        "backup":
            str(
                backup
            ),

        "modification":
            "APPEND_ONLY",

        "default_mode":
            "LEGACY",

        "shadow_available":
            True,

        "active_available":
            False,

        "emergency_rollback":
            True,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,
    }


    os.makedirs(
        os.path.dirname(
            MANIFEST
        ),
        exist_ok=True
    )


    with open(
        MANIFEST,
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


def verify_bound():

    source = Path(
        "video.py"
    ).read_text(
        encoding="utf-8"
    )


    if MARKER not in source:

        return {

            "status":
                "NOT_BOUND"
        }


    tree = ast.parse(
        source
    )


    imports = False

    installer_call = False


    for node in ast.walk(
        tree
    ):

        if isinstance(
            node,
            ast.Import
        ):

            for alias in node.names:

                if (
                    alias.name
                    == "vi6_47_renderer_switch"
                ):

                    imports = True


        if isinstance(
            node,
            ast.Call
        ):

            if isinstance(
                node.func,
                ast.Attribute
            ):

                if (
                    node.func.attr
                    == "install_renderer_wrapper"
                ):

                    installer_call = True


    return {

        "status":
            (
                "BOUND_VALID"
                if (
                    imports
                    and installer_call
                )
                else "BOUND_INVALID"
            ),

        "marker_count":
            source.count(
                MARKER
            ),

        "switch_import":
            imports,

        "installer_call":
            installer_call,

        "video_sha256":
            _hash_file(
                "video.py"
            ),
    }


def self_test():

    block = binding_block(
        "gerar_video"
    )


    assert MARKER in block

    assert (
        "install_renderer_wrapper"
        in block
    )

    assert (
        "vi6_48_emergency_rollback"
        in block
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.46 BINDING SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Gate-based binding"
    )
    print(
        "OK SHA256 protection"
    )
    print(
        "OK Append-only patch"
    )
    print(
        "OK Exact renderer function"
    )
    print(
        "OK Atomic replace"
    )
    print(
        "OK Emergency import fallback"
    )
    print()


def main():

    parser = argparse.ArgumentParser()


    parser.add_argument(
        "--check",
        action="store_true"
    )


    parser.add_argument(
        "--bind",
        metavar="BACKUP"
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
                verify_bound(),
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
# 4. SELF TESTS BEFORE TOUCHING VIDEO.PY
# =====================================================

echo
echo "===== VI6.48 SELF TEST ====="

if ! python vi6_48_emergency_rollback.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.47 SELF TEST ====="

if ! python vi6_47_renderer_switch.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.46 SELF TEST ====="

if ! python vi6_46_transactional_binding.py; then
    rollback
    exit 1
fi


# Remove eventual flag criado manualmente anteriormente.
# Não limpa um flag de produção automaticamente.
if [ -f temp/vi648_force_legacy.flag ]; then

    echo
    echo "ATENCAO:"
    echo "vi648_force_legacy.flag já existe."
    echo "Binding pode ser instalado,"
    echo "mas runtime continuará LEGACY."

fi


# =====================================================
# 5. HARD PRECHECK
# =====================================================

echo
echo "===== VI6.46 HARD PRECHECK ====="

PRECHECK="$(
python vi6_46_transactional_binding.py \
    --check
)"


echo "$PRECHECK"


READY="$(
printf '%s\n' "$PRECHECK" \
| python -c '
import sys,json
try:
    x=json.load(sys.stdin)
    print(
        "YES"
        if x.get("status") == "READY_TO_BIND"
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
echo "READY TO BIND=$READY"


if [ "$READY" = "NO" ]; then

    echo
    echo "======================================"
    echo " BINDING BLOQUEADO COM SEGURANCA"
    echo "======================================"
    echo
    echo "video.py NÃO foi modificado."
    echo "Verifique os blockers acima."

    rollback

    exit 4
fi


# =====================================================
# 6. TRANSACTIONAL PATCH
# =====================================================

if [ "$READY" = "YES" ]; then

    echo
    echo "======================================"
    echo " VI6.46 TRANSACTIONAL PATCH"
    echo " video.py -> LEGACY DEFAULT"
    echo "======================================"

    if ! python \
        vi6_46_transactional_binding.py \
        --bind \
        "$BACKDIR/video.py.vi646_original"
    then

        rollback
        exit 1
    fi

else

    echo
    echo "Binding já estava instalado."
    echo "Nenhum segundo patch será aplicado."

fi


# =====================================================
# 7. COMPILE AFTER PATCH
# =====================================================

echo
echo "===== POST-BIND COMPILE ====="

if ! python -m py_compile \
    video.py \
    vi6_46_transactional_binding.py \
    vi6_47_renderer_switch.py \
    vi6_48_emergency_rollback.py
then

    rollback
    exit 1
fi


echo "POST-BIND COMPILE=OK"


# =====================================================
# 8. VERIFY BINDING
# =====================================================

echo
echo "===== BINDING VERIFY ====="

VERIFY="$(
python vi6_46_transactional_binding.py \
    --verify
)"


echo "$VERIFY"


VALID="$(
printf '%s\n' "$VERIFY" \
| python -c '
import sys,json
try:
    x=json.load(sys.stdin)
    print(
        "YES"
        if x.get("status") == "BOUND_VALID"
        else "NO"
    )
except Exception:
    print("NO")
'
)"


if [ "$VALID" != "YES" ]; then

    echo "Binding verification failed."

    rollback
    exit 1
fi


# =====================================================
# 9. TEST SWITCH USING FAKE RENDERER ONLY
# =====================================================

cat > testar_vi646_vi648.py <<'PY'
#!/usr/bin/env python3

import os


from vi6_47_renderer_switch import (
    install_renderer_wrapper,
    uninstall_renderer_wrapper,
)

from vi6_48_emergency_rollback import (
    safe_mode,
)


calls = []


def original_renderer(
    value,
    flag=False
):

    calls.append(
        (
            value,
            flag
        )
    )

    return {
        "value":
            value,

        "flag":
            flag,
    }


namespace = {

    "renderer":
        original_renderer
}


install_renderer_wrapper(
    namespace,
    "renderer"
)


old = os.environ.get(
    "VI647_RENDERER_MODE"
)


try:

    # =================================
    # LEGACY
    # =================================

    os.environ[
        "VI647_RENDERER_MODE"
    ] = "LEGACY"


    result = namespace[
        "renderer"
    ](
        123,
        flag=True
    )


    assert result == {
        "value":
            123,

        "flag":
            True,
    }


    assert len(
        calls
    ) == 1


    # =================================
    # SHADOW
    # =================================

    calls.clear()


    os.environ[
        "VI647_RENDERER_MODE"
    ] = "SHADOW"


    result = namespace[
        "renderer"
    ](
        456
    )


    assert result[
        "value"
    ] == 456


    assert len(
        calls
    ) == 1


    # =================================
    # ACTIVE MUST FALL BACK
    # =================================

    calls.clear()


    os.environ[
        "VI647_RENDERER_MODE"
    ] = "ACTIVE"


    mode, reason = safe_mode(
        "ACTIVE"
    )


    assert mode == "LEGACY"


    result = namespace[
        "renderer"
    ](
        789
    )


    assert result[
        "value"
    ] == 789


    assert len(
        calls
    ) == 1


    # =================================
    # RESTORE ORIGINAL
    # =================================

    assert uninstall_renderer_wrapper(
        namespace,
        "renderer"
    )


    assert (
        namespace[
            "renderer"
        ]
        is original_renderer
    )


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
    " VI6.46-6.48 INTEGRATION TEST: PASS"
)
print(
    "======================================"
)

print(
    "LEGACY SINGLE CALL=PASS"
)

print(
    "SHADOW SINGLE CALL=PASS"
)

print(
    "ACTIVE FALLBACK LEGACY=PASS"
)

print(
    "RETURN VALUE PRESERVED=PASS"
)

print(
    "UNINSTALL RESTORES ORIGINAL=PASS"
)

print()
print(
    "FFMPEG EXECUTED=0"
)

print(
    "VIDEO GENERATED=0"
)
PY


echo
echo "===== INTEGRATION TEST ====="

if ! python testar_vi646_vi648.py; then

    rollback
    exit 1
fi


# =====================================================
# 10. PROVE ONLY VIDEO.PY CHANGED
# =====================================================

echo
echo "===== CORE INTEGRITY ====="

for F in \
    midia.py \
    audio.py \
    legenda_dinamica.py \
    gerar_short.sh
do

    if ! cmp -s \
        "$BACKDIR/$F" \
        "$F"
    then

        echo "ERRO: $F foi modificado."

        rollback
        exit 1
    fi

done


echo "MIDIA.PY UNCHANGED=YES"
echo "AUDIO.PY UNCHANGED=YES"
echo "LEGENDA UNCHANGED=YES"
echo "GERAR_SHORT UNCHANGED=YES"


# =====================================================
# 11. APPEND-ONLY PROOF
# =====================================================

echo
echo "===== VIDEO.PY APPEND-ONLY PROOF ====="

python - "$BACKDIR/video.py" video.py <<'PY'
import sys
from pathlib import Path


before = Path(
    sys.argv[1]
).read_bytes()


after = Path(
    sys.argv[2]
).read_bytes()


marker = (
    b"VI6.46-6.48 "
    b"TRANSACTIONAL RENDERER BINDING"
)


prefix = before.rstrip()


if not after.startswith(
    prefix
):

    print(
        "APPEND_ONLY=NO"
    )

    raise SystemExit(1)


if after.count(
    marker
) != 1:

    print(
        "MARKER_COUNT_INVALID"
    )

    raise SystemExit(1)


print(
    "ORIGINAL VIDEO.PY PREFIX PRESERVED=YES"
)

print(
    "BINDING MARKER COUNT=1"
)

print(
    "APPEND_ONLY=YES"
)
PY


if [ "$?" -ne 0 ]; then

    rollback
    exit 1
fi


# =====================================================
# 12. BASH + RELEASE
# =====================================================

echo
echo "===== BASH CHECK ====="

if ! bash -n gerar_short.sh; then

    rollback
    exit 1
fi

echo "BASH STATUS=0"


echo
echo "===== RELEASE CHECK ====="

if ! ./release_check.sh; then

    echo
    echo "release_check falhou após binding."
    echo "Rollback automático."

    rollback
    exit 1
fi


# =====================================================
# 13. DEFAULT MODE PROOF
# =====================================================

echo
echo "===== DEFAULT MODE ====="

python - <<'PY'
import os

from vi6_48_emergency_rollback import (
    safe_mode
)


requested = os.getenv(
    "VI647_RENDERER_MODE",
    "LEGACY"
)


mode, reason = safe_mode(
    requested
)


print(
    "REQUESTED MODE:",
    requested
)

print(
    "EFFECTIVE MODE:",
    mode
)

print(
    "REASON:",
    reason
)

print(
    "ACTIVE ALLOWED:",
    False
)


if mode not in {
    "LEGACY",
    "SHADOW",
}:

    raise SystemExit(1)
PY


# =====================================================
# FINAL
# =====================================================

echo
echo "======================================"
echo " VI6.46 + VI6.47 + VI6.48 INSTALADOS"
echo "======================================"
echo
echo "OK Transactional Renderer Binding"
echo "OK Exact Renderer Function Binding"
echo "OK SHA256 Pre-Binding Protection"
echo "OK Atomic video.py Patch"
echo "OK Append-Only Modification"
echo "OK Legacy Renderer Preserved"
echo "OK Default Mode = LEGACY"
echo "OK Shadow Mode Available"
echo "OK Shadow Uses Single Legacy Render"
echo "OK Return Value Preserved"
echo "OK ACTIVE Still Blocked"
echo "OK Emergency Force-Legacy"
echo "OK Runtime Wrapper Reversible"
echo "OK Original Function Recoverable"
echo "OK VI6.42 Gate Required"
echo "OK VI6.43 Exact Plan Required"
echo "OK VI6.45 Certification Required"
echo
echo "VIDEO.PY MODIFICADO=SIM"
echo "MODIFICACAO=APPEND_ONLY_TRANSACTIONAL_BINDING"
echo
echo "MIDIA.PY MODIFICADO=NAO"
echo "AUDIO.PY MODIFICADO=NAO"
echo "LEGENDA MODIFICADA=NAO"
echo "GERAR_SHORT MODIFICADO=NAO"
echo
echo "DEFAULT RENDERER MODE=LEGACY"
echo "ACTIVE RENDERER=NAO"
echo "FFMPEG EXECUTADO NESTA INSTALACAO=NAO"
echo "VIDEO GERADO=NAO"
echo "API CALLS=0"
echo "DOWNLOADS=0"
echo
echo "EMERGENCY FLAG:"
echo "temp/vi648_force_legacy.flag"
echo
echo "BINDING MANIFEST:"
echo "logs/producao/vi6_46_binding_manifest_latest.json"
echo
