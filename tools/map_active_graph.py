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

# These are analysis/test entrypoints, not production roots. Keeping them as
# roots in the global graph preserves the existing repository safety audit,
# while the split report below can distinguish their dependencies.
NON_PRODUCTION_SEEDS = {
    "tools/map_active_graph.py",
    "tools/repo_audit.py",
    "tools/deploy_smoke.py",
    "tests/test_media_acquisition_v2.py",
}

SUPPORT_SEEDS = {
    "automation/install_termux_bridge.sh",
}

PRODUCTION_SEEDS = DEFAULT_SEEDS - NON_PRODUCTION_SEEDS - SUPPORT_SEEDS

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


def add_import_reference(module: str, modules, refs: set[str]) -> None:
    """Add an imported module and all tracked parent package initializers."""
    candidate = module
    while candidate:
        if candidate in modules:
            refs.add(modules[candidate])
            parent = candidate.rpartition(".")[0]
            while parent:
                package_file = modules.get(parent)
                if package_file and Path(package_file).name == "__init__.py":
                    refs.add(package_file)
                parent = parent.rpartition(".")[0]
            return
        candidate = candidate.rpartition(".")[0]


def is_execution_call(node: ast.Call) -> bool:
    """Only inspect string arguments of calls that can execute a script/stage."""
    function = node.func
    if isinstance(function, ast.Name):
        return function.id in {"run_stage", "run_script", "run_python", "execute_script"}
    if not isinstance(function, ast.Attribute):
        return False
    receiver = function.value
    receiver_name = receiver.id if isinstance(receiver, ast.Name) else ""
    if function.attr == "run":
        # p.run is the canonical Pipeline stage runner; subprocess.run executes
        # a concrete command. Other .run methods are not file dependencies.
        return receiver_name in {"p", "subprocess"}
    if function.attr == "Popen":
        return receiver_name == "subprocess"
    return False


def refs_from_python(path: Path, files, modules):
    """Resolve imports and script paths passed to actual execution calls.

    Arbitrary strings used by Path checks, logs, diagnostics or forbidden-file
    guards are not execution dependencies. Only known process/stage execution
    APIs contribute path literals to the dependency graph.
    """
    refs = set()
    text = path.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return refs

    called_literals = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            names = []
        for name in names:
            add_import_reference(name, modules, refs)

        if isinstance(node, ast.Call) and is_execution_call(node):
            call_values = list(node.args) + [
                keyword.value for keyword in node.keywords
            ]
            for value in call_values:
                for literal in ast.walk(value):
                    if isinstance(literal, ast.Constant) and isinstance(literal.value, str):
                        if literal.value in files:
                            refs.add(literal.value)
                        called_literals.append(literal.value)

    # Build the filename/module lookup once per source file, not once per literal.
    if called_literals:
        refs |= refs_from_text("\n".join(called_literals), files, modules)
    return refs


def build_analysis():
    """Build the dependency graph once and return all reachability categories."""
    files = repo_files()
    modules = module_map(files)
    graph = {rel: set() for rel in files}
    for rel, path in files.items():
        if path.suffix == ".py":
            graph[rel] = refs_from_python(path, files, modules)
        elif path.suffix in {".sh", ".yml", ".yaml"}:
            graph[rel] = refs_from_text(path.read_text(encoding="utf-8", errors="ignore"), files, modules)

    seeds = set(DEFAULT_SEEDS)
    seeds |= SUPPORT_SEEDS & set(files)
    seeds |= {rel for rel in files if rel.startswith("tests_sim/") and rel.endswith(".py")}
    seeds |= {rel for rel in files if rel.startswith(".github/workflows/") and rel.endswith((".yml", ".yaml"))}
    seeds = {seed for seed in seeds if seed in files}

    reachable = reachable_from(graph, seeds)
    code_paths = sorted(rel for rel in files if Path(rel).suffix in CODE_EXTS)
    active_code = sorted(set(code_paths) & reachable)
    inactive_code = sorted(set(code_paths) - reachable)

    production_seeds = {seed for seed in PRODUCTION_SEEDS if seed in files}
    test_seeds = {
        rel for rel in files
        if (
            (rel.startswith("tests/") or rel.startswith("tests_sim/"))
            and rel.endswith(".py")
        ) or (
            rel.startswith(".github/workflows/")
            and rel.endswith((".yml", ".yaml"))
        )
    }
    test_seeds |= NON_PRODUCTION_SEEDS & set(files)
    support_seeds = SUPPORT_SEEDS & set(files)
    classification = classify_reachability(
        graph, code_paths, production_seeds, test_seeds, support_seeds
    )
    return files, graph, seeds, active_code, inactive_code, classification


def build():
    """Backward-compatible five-value view of the dependency graph."""
    files, graph, seeds, active, inactive, _ = build_analysis()
    return files, graph, seeds, active, inactive


def reachable_from(graph: dict[str, set[str]], seeds: set[str]) -> set[str]:
    """Return files reachable from an explicit set of graph roots."""
    reachable = set(seeds)
    queue = deque(sorted(seeds))
    while queue:
        current = queue.popleft()
        for target in graph.get(current, ()):
            if target not in reachable:
                reachable.add(target)
                queue.append(target)
    return reachable


def classify_reachability(
    graph: dict[str, set[str]],
    code_paths: list[str],
    production_seeds: set[str],
    test_seeds: set[str],
    support_seeds: set[str] | None = None,
) -> dict[str, list[str]]:
    """Separate production, compatibility tests, support tools and orphans.

    This static report is non-destructive. Test-only files are compatibility
    code, support files are manual tools, and neither is automatically safe to
    delete.
    """
    production = reachable_from(graph, production_seeds)
    tests = reachable_from(graph, test_seeds)
    support = reachable_from(graph, support_seeds or set())
    code = set(code_paths)
    production_code = sorted(code & production)
    support_code = sorted((code & support) - production)
    test_only_code = sorted((code & tests) - production - support)
    inactive_code = sorted(code - production - tests - support)
    return {
        "production_code": production_code,
        "test_only_code": test_only_code,
        "support_code": support_code,
        "inactive_code": inactive_code,
    }


def main():
    _, graph, seeds, active, inactive, classification = build_analysis()
    payload = {
        "scope": "tracked_git_files",
        "seeds": sorted(seeds),
        "active_code": active,
        "production_code": classification["production_code"],
        "test_only_code": classification["test_only_code"],
        "support_code": classification["support_code"],
        "inactive_code": inactive,
        "counts": {
            "seed_count": len(seeds),
            "active_code": len(active),
            "production_code": len(classification["production_code"]),
            "test_only_code": len(classification["test_only_code"]),
            "support_code": len(classification["support_code"]),
            "inactive_code": len(inactive),
        },
        "edges": {key: sorted(value) for key, value in graph.items() if value},
    }
    if "--json" in sys.argv:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            f"SEEDS={len(seeds)} ACTIVE_CODE={len(active)} "
            f"PRODUCTION={len(classification['production_code'])} "
            f"TEST_ONLY={len(classification['test_only_code'])} "
            f"SUPPORT={len(classification['support_code'])} "
            f"INACTIVE={len(inactive)}"
        )
        for item in active:
            print("ACTIVE", item)
        for item in inactive:
            print("INACTIVE", item)


if __name__ == "__main__":
    main()
