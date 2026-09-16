#!/usr/bin/env python3

"""Compatibility bridge that installs the canonical media runtime.

The old VG4X acquisition/commit stack is diagnostic-only. The canonical media
adapter is mandatory: if it cannot be imported/installed, media acquisition
must stop instead of silently falling back to a retired selection authority.
"""

import os


def _install_canonical(namespace):
    try:
        from media_runtime_adapter_v2 import install as install_media_runtime
        result = install_media_runtime(namespace)
    except Exception as exc:
        print(
            "MEDIA_RUNTIME_CANONICAL=FAIL_CLOSED "
            + type(exc).__name__
            + ":"
            + str(exc)
        )
        raise SystemExit(70) from exc

    if not isinstance(result, dict) or result.get("installed") is not True:
        print("MEDIA_RUNTIME_CANONICAL=FAIL_CLOSED invalid_install_result")
        raise SystemExit(70)
    if result.get("authority") != "VISUAL_UNIFIED":
        print("MEDIA_RUNTIME_CANONICAL=FAIL_CLOSED invalid_authority")
        raise SystemExit(70)
    return result


def install(namespace):
    media_runtime = _install_canonical(namespace)

    # Legacy VG4X is diagnostic/rollback-only. It must never silently compete
    # with the canonical Visual Unified selector in production.
    legacy_enabled = os.getenv("SAP_VG4X_LEGACY", "0") == "1"
    acquisition = {"installed": False}
    commit = {"installed": False}

    if legacy_enabled:
        try:
            from vg4x_acquisition import install as install_acquisition
            from vg4x_commit import install as install_commit
            os.environ["SAP_VG4X"] = "1"
            acquisition = install_acquisition(namespace)
            commit = install_commit(namespace)
        except Exception as exc:
            print(
                "VG4X_LEGACY=FAIL_OPEN "
                + type(exc).__name__
                + ":"
                + str(exc)
            )
    else:
        os.environ["SAP_VG4X"] = "0"

    result = {
        "enabled": True,
        "media_runtime": media_runtime,
        "legacy_vg4x": legacy_enabled,
        "acquisition": acquisition,
        "commit": commit,
    }

    print(
        "VG4X_BRIDGE=COMPAT "
        f"canonical_adapter={media_runtime.get('installed')} "
        f"legacy={legacy_enabled}"
    )

    return result
