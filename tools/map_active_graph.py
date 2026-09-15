#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_PREFIX = "_arquivo_historico/"
CODE_EXTS = {".py", ".sh"}

# Operational entrypoints only. Tests and workflows are added separately below.
# Documentation is intentionally NOT a seed: mentioning obsolete code in a doc
# must never keep that code alive in the production graph.
DEFAULT_SEEDS = {
    "control_center.sh",
    "gerar_short.sh",
    "profile_run.sh",
    "evolution_center.sh",
    "resume_short.sh",
    "finalize_short.sh",
    "batch_queue.sh",
    "batch_recovery.sh",
    "health_check.sh",
    "preflight_check.sh",
    "diagnostico.sh",
    "release_check.sh",
    "production_ready.sh",
    "client_job_create.py",
    "client_job_runner.py",
    "longform_runtime.py",
    "tools/map_active_graph.py",
    "tools/repo_audit.py",
}

FILE_REF_RE = re.compile(r"(?<![A-Za-z0-9_./-])([A-Za-z0-9_.-]+\.(?:py|sh))(?![A-Za-z0-9_.-])")
MODULE_LITERAL_RE = re.compile(r"[\"']([A-Za-z_][A-Za-z0-9_.]*)[\"']")


def repo_files():
    out = {}
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith(ARCHIVE_PREFIX) or rel.startswith(".git/"):
            continue
        out[rel] = p
    return out


def module_map(files):
    mapping = {}
    for rel in files:
        if not rel.endswith(".py"):
            continue
        mod = rel[:-3].replace("/", ".")
        if mod.endswith(".__init__"):
            mod = mod[:-9]
        mapping.setdefault(mod, rel)
        if "/" not in rel:
            mapping.setdefault(Path(rel).stem, rel)
    return mapping


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
                for alias in node.names:
                    name = alias.name
                    while name:
                        if name in modules:
                            refs.add(modules[name])
                            break
                        name = name.rpartition(".")[0]
            elif isinstance(node, ast.ImportFrom):
                name = node.module or ""
                while name:
                    if name in modules:
                        refs.add(modules[name])
                        break
                    name = name.rpartition(".")[0]
    refs |= refs_from_text(text, files, modules)
    return refs


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
        mod = match.group(1)
        if mod in modules:
            refs.add(modules[mod])
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
    seeds |= {rel for rel in files if rel.startswith("tests_sim/") and rel.endswith(".py")}
    seeds |= {rel for rel in files if rel.startswith(".github/workflows/") and rel.endswith((".yml", ".yaml"))}
    seeds = {s for s in seeds if s in files}

    q = deque(sorted(seeds))
    reachable = set(seeds)
    while q:
        cur = q.popleft()
        for nxt in graph.get(cur, ()):
            if nxt not in reachable:
                reachable.add(nxt)
                q.append(nxt)

    code_files = sorted(rel for rel in files if Path(rel).suffix in CODE_EXTS)
    active_code = sorted(set(code_files) & reachable)
    inactive_code = sorted(set(code_files) - reachable)
    return files, graph, seeds, active_code, inactive_code


def main():
    _, graph, seeds, active, inactive = build()
    payload = {
        "seeds": sorted(seeds),
        "active_code": active,
        "inactive_code": inactive,
        "counts": {
            "seed_count": len(seeds),
            "active_code": len(active),
            "inactive_code": len(inactive),
        },
        "edges": {k: sorted(v) for k, v in graph.items() if v},
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
