#!/usr/bin/env python3

"""Bridge point used by midia.py before scene acquisition starts.

Consolidation 3.0 keeps this import path for compatibility, but the old VG4X
acquisition/commit stack is no longer an independent selection authority.
The bridge now installs the canonical media runtime adapter and only enables
legacy VG4X when explicitly requested for diagnostics.
"""

import os

from media_runtime_adapter_v2 import install as install_media_runtime


def install(namespace):
    media_runtime = install_media_runtime(namespace)

    # Legacy VG4X is diagnostic/rollback-only.  It must never silently compete
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
