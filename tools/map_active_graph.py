#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_PREFIX = "_arquivo_historico/"
CODE_EXTS = {".py", ".sh"}

# Consolidation 3.0 operational entrypoints. main.py is the only Short
# production root; profile/batch/control entrypoints delegate to it. Recovery
# helpers that are intentionally invoked directly are seeds too, otherwise the
# fail-closed repository audit incorrectly classifies a valid manual recovery
# entrypoint as orphaned code.
DEFAULT_SEEDS = {
    "main.py",
    "control_center.sh",
    "profile_run.sh",
    "evolution_center.sh",
    "resume_short.sh",
    "resume_after_semantic_fix.py",
    "batch_queue.sh",
    "batch_recovery.sh",
    "batch_runtime.py",
    "health_check.sh",
    "preflight_check.sh",
    "automation/install_termux_autosync.sh",
    "automation/termux_bridge.sh",
    "diagnostico.sh",
    "release_check.sh",
    "production_ready.sh",
    "client_job_create.py",
    "client_job_runner.py",
    "longform_runtime.py",
    "tools/map_active_graph.py",
    "tools/repo_audit.py",
    "tools/deploy_smoke.py",
    "tests/test_media_acquisition_v2.py",
}

FILE_REF_RE = re.compile(r"(?<![A-Za-z0-9_./-])([A-Za-z0-9_.-]+\.(?:py|sh))(?![A-Za-z0-9_.-])")
MODULE_LITERAL_RE = re.compile(r"[\"']([A-Za-z_][A-Za-z0-9_.]*)[\"']")


def tracked_rel_paths() -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git ls-files failed: {detail or proc.returncode}")
    return sorted(
        path
        for path in proc.stdout.decode("utf-8", errors="surrogateescape").split("\0")
        if path
    )


def repo_files():
    out = {}
    for rel in tracked_rel_paths():
        if rel.startswith(ARCHIVE_PREFIX) or rel.startswith(".git/"):
            continue
        path = ROOT / rel
        if path.is_file():
            out[rel] = path
    return out


def module_map(files):
    mapping = {}
    for rel in files:
        if not rel.endswith(".py"):
            continue
        module = rel[:-3].replace("/", ".")
        if module.endswith(".__init__"):
            module = module[:-9]
        mapping.setdefault(module, rel)
        if "/" not in rel:
            mapping.setdefault(Path(rel).stem, rel)
    return mapping


def refs_from_text(text: str, files, modules):
    refs = set()
    by_base = {}
    for rel in files:
        by_base.setdefault(Path(rel).name, []).append(rel)
    for match in FILE_REF_RE.finditer(text):
        base = match.group(1)
        options = by_base.get(base, [])
        if len(options) == 1:
            refs.add(options[0])
        elif base in files:
            refs.add(base)
    for match in MODULE_LITERAL_RE.finditer(text):
        module = match.group(1)
        if module in modules:
            refs.add(modules[module])
    return refs


def refs_from_python(path: Path, files, modules):
    refs = set()
    text = path.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        tree = None
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
                # Resolve relative imports such as from .diagnostics against the
                # importing package so V3 submodules remain in the active graph.
                if node.level and node.module:
                    package = path.parent.relative_to(ROOT).as_posix().replace("/", ".")
                    base = package
                    for _ in range(max(0, node.level - 1)):
                        base = base.rpartition(".")[0]
                    names = [f"{base}.{node.module}".strip(".")]
            else:
                continue
            for name in names:
                while name:
                    if name in modules:
                        refs.add(modules[name])
                        break
                    name = name.rpartition(".")[0]
    refs |= refs_from_text(text, files, modules)
    return refs


def build():
    files = repo_files()
    modules = module_map(files)
    graph = {rel: set() for rel in files}
    for rel, path in files.items():
        if path.suffix == ".py":
            graph[rel] = refs_from_python(path, files, modules)
        elif path.suffix in {".sh", ".yml", ".yaml"}:
            graph[rel] = refs_from_text(path.read_text(encoding="utf-8", errors="ignore"), files, modules)

    seeds = set(DEFAULT_SEEDS)
    # Unit/integration tests are executable graph roots as well.
    seeds |= {rel for rel in files if rel.startswith("tests/") and rel.endswith(".py")}
    seeds |= {rel for rel in files if rel.startswith("tests_sim/") and rel.endswith(".py")}
    seeds |= {rel for rel in files if rel.startswith(".github/workflows/") and rel.endswith((".yml", ".yaml"))}
    seeds = {seed for seed in seeds if seed in files}

    queue = deque(sorted(seeds))
    reachable = set(seeds)
    while queue:
        current = queue.popleft()
        for nxt in graph.get(current, ()):
            if nxt not in reachable:
                reachable.add(nxt)
                queue.append(nxt)

    code_files = sorted(rel for rel in files if Path(rel).suffix in CODE_EXTS)
    active_code = sorted(set(code_files) & reachable)
    inactive_code = sorted(set(code_files) - reachable)
    return files, graph, seeds, active_code, inactive_code


def main():
    _, graph, seeds, active, inactive = build()
    payload = {
        "scope": "tracked_git_files",
        "seeds": sorted(seeds),
        "active_code": active,
        "inactive_code": inactive,
        "counts": {
            "seed_count": len(seeds),
            "active_code": len(active),
            "inactive_code": len(inactive),
        },
        "edges": {key: sorted(value) for key, value in graph.items() if value},
    }
    if "--json" in sys.argv:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"SEEDS={len(seeds)} ACTIVE_CODE={len(active)} INACTIVE_CODE={len(inactive)}")
        for item in active:
            print("ACTIVE", item)
        for item in inactive:
            print("INACTIVE", item)


if __name__ == "__main__":
    main()
