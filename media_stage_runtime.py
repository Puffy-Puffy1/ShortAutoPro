#!/usr/bin/env python3
"""Deprecated Stage-6 compatibility shim.

Stage 6 is retired from the production path. Media acquisition belongs to
Media Engine V2. This shim intentionally never imports or executes midia.py.
It exists only so old external callers fail over to the canonical V2 boundary.
"""
from __future__ import annotations
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SID = os.getenv("SHORT_ID", date.today().isoformat()).strip()


def round_env(round_index: int) -> dict[str, str]:
    """Compatibility-only provider budget contract; execution stays V2-only."""
    idx = max(0, min(int(round_index), 2))
    provider_timeout = (10, 12, 12)[idx]
    wiki_deadline = (8, 10, 12)[idx]
    env = os.environ.copy()
    env["SHORT_ID"] = SID
    env["SAP_MEDIA_PROVIDER_RESULT_TIMEOUT"] = str(provider_timeout)
    env["SAP_WIKIMEDIA_SEARCH_DEADLINE"] = str(wiki_deadline)
    env["SAP_MEDIA_SCENE_BUDGET_SECONDS"] = "18"
    env["SAP_VSE4_QUERY_EXPANSION"] = "1"
    env["SAP_VSE4_QUERY_ONLY_ON_EMPTY"] = "1"
    env["SAP_VSE4_QUERY_EXTRA"] = "1"
    return env


def main() -> int:
    if not SID:
        print("MEDIA_STAGE_RUNTIME=BLOCKED reason=SHORT_ID_EMPTY")
        return 1
    engine = BASE / "media_engine_v2.py"
    if not engine.is_file():
        print(f"MEDIA_STAGE_RUNTIME=BLOCKED reason=MEDIA_ENGINE_V2_MISSING path={engine}")
        return 1
    env = os.environ.copy()
    env["SHORTAUTOPRO_BASE"] = str(BASE)
    env["SHORT_ID"] = SID
    print(f"MEDIA_STAGE_RUNTIME=DEPRECATED_SHIM delegate=media_engine_v2.py short_id={SID}")
    proc = subprocess.run([sys.executable, str(engine), "--short-id", SID], cwd=str(BASE), env=env, check=False)
    print(f"MEDIA_STAGE_RUNTIME=V2_RESULT returncode={proc.returncode} short_id={SID}")
    return proc.returncode

if __name__ == "__main__":
    raise SystemExit(main())
