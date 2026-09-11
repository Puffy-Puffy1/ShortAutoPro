#!/usr/bin/env python3

"""
ShortAutoPro
Visual Scene Commit Lock V2.1

Objetivo:
- cada cena aceita somente o PRIMEIRO download bem-sucedido;
- impede overwrite posterior no mesmo processo;
- remove extensão irmã antiga (.jpg/.mp4) após commit;
- mantém fail-open se não conseguir identificar a cena;
- não executa rede por conta própria.
"""

import inspect
import os
import re
from pathlib import Path


_ENABLED = (
    os.getenv(
        "SAP_SCENE_COMMIT_LOCK",
        "1",
    )
    !=
    "0"
)


_committed = set()
_wrapped_ids = set()
_return_shape = None


def reset():

    _committed.clear()


def _short_id(namespace=None):

    if isinstance(
        namespace,
        dict,
    ):

        sid = namespace.get(
            "SHORT_ID"
        )

        if sid:
            return str(sid)

    return (
        os.getenv(
            "SHORT_ID",
            ""
        ).strip()
        or
        "unknown"
    )


def _candidate_from_bound(bound):

    for key in (
        "candidato",
        "candidate",
        "item",
        "asset",
        "midia",
        "media",
    ):

        if key in bound:

            value = bound.get(
                key
            )

            if value is not None:
                return value

    return None


def _scene_from_candidate(candidate):

    if not isinstance(
        candidate,
        dict,
    ):
        return None

    for key in (
        "numero",
        "scene",
        "scene_id",
        "scene_num",
        "cena",
        "cena_id",
        "cena_num",
        "index",
        "indice",
    ):

        value = candidate.get(
            key
        )

        if value is None:
            continue

        try:
            return int(value)
        except Exception:
            pass

    return None


def _scene_id(
    original,
    args,
    kwargs,
):

    bound = {}

    try:

        sig = inspect.signature(
            original
        )

        b = sig.bind_partial(
            *args,
            **kwargs,
        )

        bound = dict(
            b.arguments
        )

    except Exception:
        pass


    for key in (
        "numero",
        "scene",
        "scene_id",
        "scene_num",
        "cena",
        "cena_id",
        "cena_num",
        "indice",
        "index",
        "n",
    ):

        value = bound.get(
            key
        )

        if value is None:
            continue

        try:

            number = int(value)

            if 0 <= number <= 999:
                return number

        except Exception:
            pass


    candidate = _candidate_from_bound(
        bound
    )

    number = _scene_from_candidate(
        candidate
    )

    if number is not None:
        return number


    # Fallback cuidadoso: argumentos numéricos.
    for value in args[1:]:

        if isinstance(
            value,
            bool,
        ):
            continue

        try:

            number = int(value)

            if 0 <= number <= 999:
                return number

        except Exception:
            continue


    return None


def _result_ok(result):

    if isinstance(
        result,
        tuple,
    ):

        if not result:
            return False

        return bool(
            result[0]
        )

    if isinstance(
        result,
        dict,
    ):

        for key in (
            "ok",
            "success",
            "sucesso",
        ):

            if key in result:
                return bool(
                    result[key]
                )

    return bool(
        result
    )


def _result_dest(result):

    if (
        isinstance(
            result,
            tuple,
        )
        and
        len(result) >= 2
    ):

        value = result[1]

        if value:
            return str(value)


    if isinstance(
        result,
        dict,
    ):

        for key in (
            "destino",
            "destination",
            "path",
            "local_path",
            "arquivo",
        ):

            value = result.get(
                key
            )

            if value:
                return str(value)


    return None


def _blocked_result():

    global _return_shape

    if _return_shape == "bool":
        return False

    return (
        False,
        None,
    )


def _remember_shape(result):

    global _return_shape

    if isinstance(
        result,
        tuple,
    ):
        _return_shape = "tuple"

    elif isinstance(
        result,
        bool,
    ):
        _return_shape = "bool"


def _cleanup_sibling(destination):

    if not destination:
        return


    try:

        path = Path(
            destination
        )

        if not path.is_file():
            return


        match = re.match(
            r"^(scene_\d+)\.(jpg|jpeg|png|webp|mp4|mov|webm)$",
            path.name,
            flags=re.IGNORECASE,
        )

        if not match:
            return


        stem = match.group(1)

        media_suffixes = (
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".mp4",
            ".mov",
            ".webm",
        )


        for suffix in media_suffixes:

            sibling = (
                path.parent
                /
                f"{stem}{suffix}"
            )

            try:

                if (
                    sibling != path
                    and
                    sibling.is_file()
                ):

                    sibling.unlink()

                    print(
                        "SCENE_COMMIT_SIBLING_REMOVED="
                        f"{sibling.name}"
                    )

            except Exception:
                pass


    except Exception:
        pass


def _note_success(candidate):

    try:

        from media_diversity_guard_v1 import (
            note_success,
        )

        note_success(
            candidate
        )

    except Exception:
        pass


def install_runtime(namespace):

    if not _ENABLED:

        print(
            "SCENE_COMMIT_LOCK=DISABLED"
        )

        return False


    if not isinstance(
        namespace,
        dict,
    ):
        return False


    original = namespace.get(
        "baixar_candidato_5_2"
    )


    if not callable(
        original
    ):

        print(
            "SCENE_COMMIT_INSTALL=NO_DOWNLOADER"
        )

        return False


    # Já é nossa versão atual.
    if getattr(
        original,
        "_sap_scene_commit_v21",
        False,
    ):

        return True


    original_id = id(
        original
    )


    def wrapped(
        *args,
        **kwargs,
    ):

        scene = _scene_id(
            original,
            args,
            kwargs,
        )

        sid = _short_id(
            namespace
        )


        key = None

        if scene is not None:

            key = (
                sid,
                int(scene),
            )


        if (
            key is not None
            and
            key in _committed
        ):

            print(
                "SCENE_COMMIT_LOCK=BLOCKED "
                f"scene={scene:02d}"
            )

            return _blocked_result()


        result = original(
            *args,
            **kwargs,
        )


        _remember_shape(
            result
        )


        if not _result_ok(
            result
        ):

            return result


        destination = _result_dest(
            result
        )


        # Se não conhecíamos a cena antes,
        # tenta extrair do nome final.
        if (
            scene is None
            and
            destination
        ):

            match = re.search(
                r"scene_(\d+)",
                Path(
                    destination
                ).name,
                flags=re.IGNORECASE,
            )

            if match:

                scene = int(
                    match.group(1)
                )

                key = (
                    sid,
                    scene,
                )


        if key is not None:

            _committed.add(
                key
            )

            print(
                "SCENE_COMMIT_LOCK=COMMITTED "
                f"scene={scene:02d}"
            )


        _cleanup_sibling(
            destination
        )


        # Registra diversidade apenas após sucesso real.
        bound = {}

        try:

            sig = inspect.signature(
                original
            )

            bound = dict(
                sig.bind_partial(
                    *args,
                    **kwargs,
                ).arguments
            )

        except Exception:
            pass


        candidate = _candidate_from_bound(
            bound
        )

        if candidate is None and args:
            candidate = args[0]


        _note_success(
            candidate
        )


        return result


    wrapped._sap_scene_commit_v21 = True
    wrapped._sap_original_downloader = original


    namespace[
        "baixar_candidato_5_2"
    ] = wrapped


    _wrapped_ids.add(
        original_id
    )


    print(
        "SCENE_COMMIT_INSTALL=PASS"
    )

    return True


if __name__ == "__main__":

    print(
        "SCENE_COMMIT_LOCK_V21=READY"
    )
