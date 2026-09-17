#!/usr/bin/env python3

"""Bridge point used by midia.py before scene acquisition starts.

Consolidation 3.0 keeps this import path for compatibility, but the old VG4X
acquisition/commit stack is no longer an independent selection authority.
The bridge installs the canonical media runtime, targeted acquisition recovery,
and the narrow fail-closed explicit-MUST commit guard. Legacy VG4X remains
opt-in for diagnostics only.
"""

import os

from media_runtime_adapter_v2 import install as install_media_runtime
from media_acquisition_recovery import install as install_acquisition_recovery
from media_strict_must_guard import install as install_strict_must_guard


def install(namespace):
    media_runtime = install_media_runtime(namespace)
    acquisition_recovery = install_acquisition_recovery(namespace)
    strict_must = install_strict_must_guard(namespace)

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
        "acquisition_recovery": acquisition_recovery,
        "strict_must": strict_must,
        "legacy_vg4x": legacy_enabled,
        "acquisition": acquisition,
        "commit": commit,
    }

    print(
        "VG4X_BRIDGE=COMPAT "
        f"canonical_adapter={media_runtime.get('installed')} "
        f"acquisition_recovery={acquisition_recovery.get('installed')} "
        f"strict_must={strict_must.get('installed')} "
        f"legacy={legacy_enabled}"
    )

    return result
