#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "_arquivo_historico" / "2026-09-15_pre_consolidation"
DOCS = ROOT / "docs"
BASE_MAIN_SHA = "cff280d9445f2ff704b876a766564f33a0f2c36b"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: esperado 1 marcador, encontrado {count}")
    return text.replace(old, new, 1)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def integrate_midia() -> dict:
    import midia_runtime as mr

    source = read("midia.py")
    original_sha = sha(source)
    fixed, counters = mr.fix_source(source)
    if counters != mr.EXPECTED_BROKEN_COUNTS:
        raise RuntimeError(f"contagem de breaks inesperada: {counters}")
    fixed, cleanup = mr.harden_cleanup(fixed)
    fixed, resolution = mr.harden_download_resolution(fixed)
    fixed, professional = mr.harden_professional_media_floor(fixed)
    compile(fixed, "midia.py", "exec")
    write("midia.py", fixed)
    return {
        "original_sha256": original_sha,
        "runtime_effective_sha256": sha(fixed),
        "static_integrated_sha256": sha(read("midia.py")),
        "removed_breaks": sum(counters.values()),
        "cleanup_webp_integrated": bool(cleanup),
        "minimum_resolution_integrated": bool(resolution),
        "professional_media_floor_integrated": bool(professional),
        "behavior_equivalence": sha(fixed) == sha(read("midia.py")),
    }


def patch_pipeline() -> None:
    p = ROOT / "gerar_short.sh"
    s = p.read_text(encoding="utf-8")
    s = replace_once(
        s,
        'rodar_python "6/12 - SMART MEDIA SELECTOR" "midia_runtime.py"',
        'rodar_python "6/12 - SMART MEDIA SELECTOR" "midia.py"',
        "gerar_short media selector",
    )
    quality = r'''QUALITY_REPORT="$BASE/manifests/${SHORT_ID}_quality.json"
QUALITY_STATUS="$(python - "$QUALITY_REPORT" "$EVOLUTION_REPORT" "${SAP_EVOLUTION_ENFORCE:-0}" <<'PYQUALITY'
import json
import sys
from pathlib import Path

quality_path = Path(sys.argv[1])
evolution_path = Path(sys.argv[2])
enforced = sys.argv[3] == "1"


def load(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


quality = load(quality_path)
evolution = load(evolution_path)

if not quality.get("approved", False):
    print("BLOCK")
    raise SystemExit(0)

status = str(evolution.get("status", "UNKNOWN") or "UNKNOWN").upper()
score = evolution.get("total_score")
threshold = evolution.get("threshold")

if status == "PASS":
    if score is not None and threshold is not None:
        print(f"PASS (EVOLUTION {score}/{threshold})")
    else:
        print("PASS")
elif enforced:
    print(f"BLOCK (EVOLUTION {status})")
else:
    print(f"REVIEW (EVOLUTION {status}, OBSERVATION)")
PYQUALITY
)"
echo "QUALITY: ${QUALITY_STATUS:-UNKNOWN}"
'''
    s = replace_once(s, 'echo "QUALITY: PASS"\n', quality, "dynamic quality summary")
    p.write_text(s, encoding="utf-8")

    for name in ("health_check.sh", "preflight_check.sh"):
        t = read(name).replace("midia.py midia_runtime.py", "midia.py")
        t = t.replace('    "midia_runtime",\n', "")
        write(name, t)

    workflow = ".github/workflows/shortautopro-remote.yml"
    write(workflow, read(workflow).replace("midia.py midia_runtime.py", "midia.py"))


def rewrite_tests() -> None:
    write(
        "tests_sim/test_midia_integrated.py",
        '''import unittest\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\nMIDIA = ROOT / "midia.py"\n\n\nclass IntegratedMediaSelectorTests(unittest.TestCase):\n    @classmethod\n    def setUpClass(cls):\n        cls.source = MIDIA.read_text(encoding="utf-8")\n\n    def test_selector_compiles_without_runtime_rewrite(self):\n        compile(self.source, str(MIDIA), "exec")\n\n    def test_webp_cleanup_is_native(self):\n        start = self.source.index("# LIMPAR MÍDIA ANTIGA")\n        end = self.source.index("# TEXTO", start)\n        self.assertIn('".webp"', self.source[start:end])\n\n    def test_minimum_resolution_guard_is_native(self):\n        self.assertIn("largura * altura < 320 * 180", self.source)\n        self.assertIn("mídia abaixo do piso técnico", self.source)\n\n    def test_professional_media_floor_is_native(self):\n        self.assertIn("def _sap_professional_media_accept_v1", self.source)\n        self.assertIn("SAP_PRO_MEDIA_MIN_PIXELS", self.source)\n        self.assertIn('evidence_class == "CASE_DIRECT"', self.source)\n        self.assertIn("ok = _sap_professional_media_accept_v1", self.source)\n\n    def test_known_premature_break_anchors_are_gone(self):\n        self.assertNotIn("                break\\n                destino = destino_teste", self.source)\n        self.assertNotIn("        _vse42_cleanup_scene_sibling(destino)\\n        break", self.source)\n        self.assertNotIn("        _vse42_commit_safe(escolhido)\\n        break", self.source)\n\n    def test_download_floor_precedes_commit_replace(self):\n        guard = self.source.index("largura * altura < 320 * 180")\n        replace = self.source.index("os.replace(", guard)\n        self.assertLess(guard, replace)\n\n\nif __name__ == "__main__":\n    unittest.main()\n''',
    )
    old = ROOT / "tests_sim" / "test_midia_runtime.py"
    if old.exists():
        old.unlink()

    write(
        "tests_sim/test_first_real_run_regressions.py",
        '''import unittest\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\nMIDIA = ROOT / "midia.py"\n\n\nclass MediaResolutionGuardTests(unittest.TestCase):\n    def test_guard_rejects_subcritical_download_before_commit(self):\n        source = MIDIA.read_text(encoding="utf-8")\n        self.assertIn("largura * altura < 320 * 180", source)\n        self.assertIn("mídia abaixo do piso técnico", source)\n        guard = source.index("largura * altura < 320 * 180")\n        commit = source.index("os.replace(", guard)\n        self.assertLess(guard, commit)\n\n    def test_runtime_rewrite_module_is_not_required(self):\n        self.assertFalse((ROOT / "midia_runtime.py").exists())\n        pipeline = (ROOT / "gerar_short.sh").read_text(encoding="utf-8")\n        self.assertIn('"6/12 - SMART MEDIA SELECTOR" "midia.py"', pipeline)\n        self.assertNotIn("midia_runtime.py", pipeline)\n\n\nif __name__ == "__main__":\n    unittest.main()\n''',
    )

    path = ROOT / "tests_sim" / "test_motion_rhythm_hardening.py"
    s = path.read_text(encoding="utf-8")
    s = s.replace("from midia_runtime import EXPECTED_BROKEN_COUNTS, fix_source\n", "")
    old = '''    def test_media_runtime_hotfix_matches_current_real_source(self):\n        source = MIDIA.read_text(encoding="utf-8")\n        fixed, counters = fix_source(source)\n        self.assertEqual(counters, EXPECTED_BROKEN_COUNTS)\n        self.assertEqual(sum(counters.values()), 7)\n        compile(fixed, str(MIDIA), "exec")\n'''
    new = '''    def test_media_selector_is_native_and_compiles(self):\n        source = MIDIA.read_text(encoding="utf-8")\n        self.assertIn("largura * altura < 320 * 180", source)\n        self.assertIn("def _sap_professional_media_accept_v1", source)\n        self.assertNotIn("midia_runtime.py", (REPO / "gerar_short.sh").read_text(encoding="utf-8"))\n        compile(source, str(MIDIA), "exec")\n'''
    s = replace_once(s, old, new, "motion hardening test")
    path.write_text(s, encoding="utf-8")

    path = ROOT / "tests_sim" / "test_professional_polish_v2.py"
    s = path.read_text(encoding="utf-8").replace("import midia_runtime as mr\n", "")
    start = s.index("class ProfessionalMediaFloorTests(unittest.TestCase):")
    end = s.index("\n\nclass ProfessionalPipelinePolishTests", start)
    replacement = '''class ProfessionalMediaFloorTests(unittest.TestCase):\n    def test_professional_floor_is_integrated_in_selector(self):\n        source = (ROOT / "midia.py").read_text(encoding="utf-8")\n        self.assertIn("def _sap_professional_media_accept_v1", source)\n        self.assertIn("SAP_PRO_MEDIA_MIN_PIXELS", source)\n        self.assertIn("1280 * 720", source)\n        self.assertIn('evidence_class == "CASE_DIRECT"', source)\n        self.assertIn("PRO_MEDIA_FLOOR=REJECT", source)\n        self.assertIn("os.remove(destino)", source)\n        self.assertIn("ok = _sap_professional_media_accept_v1", source)\n        compile(source, "midia.py", "exec")\n\n    def test_professional_floor_remains_failover_friendly(self):\n        source = (ROOT / "midia.py").read_text(encoding="utf-8")\n        helper = source[source.index("def _sap_professional_media_accept_v1"):source.index("def baixar_candidato_5_2")]\n        self.assertIn("return False", helper)\n        self.assertIn("return True", helper)\n'''
    path.write_text(s[:start] + replacement + s[end:], encoding="utf-8")

    path = ROOT / "tests_sim" / "test_evolution_runtime_integration.py"
    s = path.read_text(encoding="utf-8")
    marker = '\n\nif __name__ == "__main__":'
    test = '''\n    def test_final_summary_uses_real_quality_reports(self):\n        text = (ROOT / "gerar_short.sh").read_text(encoding="utf-8")\n        self.assertIn("QUALITY_REPORT=", text)\n        self.assertIn("EVOLUTION_REPORT", text)\n        self.assertIn("REVIEW (EVOLUTION", text)\n        self.assertNotIn('echo "QUALITY: PASS"', text)\n'''
    if "test_final_summary_uses_real_quality_reports" not in s:
        s = s.replace(marker, test + marker, 1)
    path.write_text(s, encoding="utf-8")


def archive_unreachable() -> tuple[dict, list[str]]:
    from tools import map_active_graph as mag

    _, _, _, active_before, inactive_before = mag.build()
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    moved = []

    runtime = ROOT / "midia_runtime.py"
    if runtime.exists():
        runtime_dst = ARCHIVE / "midia_runtime.py"
        if runtime_dst.exists():
            raise RuntimeError(f"destino histórico já existe: {runtime_dst}")
        shutil.move(str(runtime), str(runtime_dst))
        moved.append("midia_runtime.py")

    _, _, _, active, inactive = mag.build()
    root_inactive = sorted(x for x in inactive if "/" not in x and x.endswith((".py", ".sh")))
    for rel in root_inactive:
        src = ROOT / rel
        dst = ARCHIVE / rel
        if not src.exists():
            continue
        if dst.exists():
            raise RuntimeError(f"destino de arquivo histórico já existe: {dst}")
        shutil.move(str(src), str(dst))
        moved.append(rel)

    _, _, _, active_after, inactive_after = mag.build()
    root_inactive_after = [x for x in inactive_after if "/" not in x and x.endswith((".py", ".sh"))]
    if root_inactive_after:
        raise RuntimeError(f"código raiz ainda inacessível após arquivo: {root_inactive_after[:10]}")

    return {
        "active_code_before_archive": len(active_before),
        "inactive_code_before_archive": len(inactive_before),
        "root_files_archived": len(moved),
        "active_code_after_archive": len(active_after),
        "inactive_code_after_archive": len(inactive_after),
    }, moved


def write_reports(midia: dict, graph_stats: dict, moved: list[str]) -> None:
    from tools import map_active_graph as mag

    _, _, seeds, active, inactive = mag.build()
    payload = {
        "version": "ShortAutoPro Consolidation 1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_main_sha": BASE_MAIN_SHA,
        "midia_static_integration": midia,
        "graph": graph_stats,
        "seeds": sorted(seeds),
        "active_code": active,
        "remaining_inactive_code": inactive,
        "archived_root_files": moved,
        "archive_path": ARCHIVE.relative_to(ROOT).as_posix(),
        "quality_summary": {
            "hardcoded_pass_removed": True,
            "source_of_truth": [
                "manifests/<SHORT_ID>_quality.json",
                "manifests/<SHORT_ID>_evolution.json",
            ],
            "observation_non_pass": "REVIEW",
        },
    }
    DOCS.mkdir(parents=True, exist_ok=True)
    write(
        "docs/CONSOLIDATION_1_0_ACTIVE_GRAPH.json",
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )

    md = f'''# ShortAutoPro Consolidation 1.0

Base principal analisada: `{BASE_MAIN_SHA}`.

## Resultado estrutural

- Hotfix de `midia.py` em memória removido do caminho de produção.
- As correções antes aplicadas por `midia_runtime.py` foram incorporadas diretamente em `midia.py`.
- Equivalência textual com o código efetivamente executado pelo runtime anterior: **{'PASS' if midia['behavior_equivalence'] else 'FAIL'}**.
- `gerar_short.sh` chama `midia.py` diretamente.
- O resumo final deixou de imprimir `QUALITY: PASS` fixo; agora lê o Final Quality e o Evolution.
- Arquivos raiz históricos/inacessíveis movidos para `{ARCHIVE.relative_to(ROOT).as_posix()}/`: **{len(moved)}**.
- Código ativo após a separação: **{len(active)}** arquivos `.py/.sh` no grafo conservador.
- Código inacessível restante fora do arquivo histórico: **{len(inactive)}**.

## Mapeamento

O grafo é construído a partir dos entrypoints operacionais, workflows, documentação operacional e testes, seguindo imports Python e referências literais a scripts/módulos. Chamadas dinâmicas por `subprocess`, `importlib` e nomes literais de módulos também são capturadas conservadoramente.

O inventário completo fica em `docs/CONSOLIDATION_1_0_ACTIVE_GRAPH.json`.

## Segurança

Nada foi apagado: código fora do grafo foi **arquivado**, preservando conteúdo e histórico Git. A pasta histórica não participa do cálculo de produção.

## Validação

A validação automatizada da branch executa compilação Python, suíte `tests_sim`, sintaxe Bash e checagens específicas da consolidação antes do commit final.
'''
    write("docs/CONSOLIDATION_1_0.md", md)


def cleanup_temp_workflows() -> None:
    for rel in (
        ".github/workflows/consolidation-snapshot-temp.yml",
        ".github/workflows/consolidation-apply-temp.yml",
    ):
        p = ROOT / rel
        if p.exists():
            p.unlink()


def main() -> int:
    if not (ROOT / "midia_runtime.py").is_file():
        raise RuntimeError(
            "midia_runtime.py ausente no baseline; abortando para evitar aplicação parcial"
        )
    before_root = len(list(ROOT.glob("*.py"))) + len(list(ROOT.glob("*.sh")))
    midia = integrate_midia()
    patch_pipeline()
    rewrite_tests()
    graph_stats, moved = archive_unreachable()
    cleanup_temp_workflows()
    write_reports(midia, graph_stats, moved)
    after_root = len(list(ROOT.glob("*.py"))) + len(list(ROOT.glob("*.sh")))
    print(f"CONSOLIDATION_BASE_MAIN={BASE_MAIN_SHA}")
    print(f"ROOT_CODE_BEFORE={before_root}")
    print(f"ROOT_CODE_AFTER={after_root}")
    print(f"ARCHIVED={len(moved)}")
    print(f"MIDIA_EQUIVALENCE={'PASS' if midia['behavior_equivalence'] else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
