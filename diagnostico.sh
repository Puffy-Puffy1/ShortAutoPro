#!/data/data/com.termux/files/usr/bin/bash

set -u

BASE="$HOME/ShortAutoPro"
OUT_DIR="$BASE/diagnosticos"
mkdir -p "$OUT_DIR"

ID="$(date +%F_%H%M%S)"
OUT="$OUT_DIR/diagnostico_${ID}.txt"

secao() {
    echo
    echo "======================================"
    echo " $1"
    echo "======================================"
    echo
}

{
    secao "SHORTAUTO PRO - DIAGNÓSTICO 3.0"
    echo "Data: $(date)"
    echo "Base: $BASE"
    echo
    echo "Versão/config detectada:"
    grep -E \
        'CONSOLIDATION_3_0|PROFESSIONAL_CANONICAL|SAP_RELEASE_ENFORCE|SAP_RETENTION_MIN_SCORE|SHORT_BATCH_COOLDOWN' \
        "$BASE/main.py" \
        "$BASE/config.sh" \
        2>/dev/null || true

    secao "HEALTH CHECK"
    if [ -x "$BASE/health_check.sh" ]; then "$BASE/health_check.sh" 2>&1 || true; else echo "health_check.sh ausente"; fi

    secao "PREFLIGHT"
    if [ -x "$BASE/preflight_check.sh" ]; then "$BASE/preflight_check.sh" 2>&1 || true; else echo "preflight_check.sh ausente"; fi

    secao "REPOSITORY AUDIT"
    if [ -f "$BASE/tools/repo_audit.py" ]; then python "$BASE/tools/repo_audit.py" 2>&1 || true; else echo "tools/repo_audit.py ausente"; fi

    secao "PRODUCTION DOCTOR"
    if [ -f "$BASE/production_doctor.py" ]; then python "$BASE/production_doctor.py" 2>&1 || true; else echo "production_doctor.py ausente"; fi

    secao "ARMAZENAMENTO"
    if [ -f "$BASE/storage_manager.py" ]; then python "$BASE/storage_manager.py" status 2>&1 || true; fi
    df -h "$HOME" 2>&1 || true
    echo
    du -h -d 1 "$BASE" 2>/dev/null | sort -h || true

    secao "ESTADO DO LOTE"
    STATE="$BASE/queue/batch_state.json"
    if [ -f "$STATE" ]; then cat "$STATE"; else echo "Nenhum estado de lote."; fi

    secao "ÚLTIMO LOG DE LOTE"
    ULTIMO_LOTE="$(ls -t "$BASE"/logs/lotes/lote_*.log 2>/dev/null | head -1)"
    if [ -n "$ULTIMO_LOTE" ]; then echo "Arquivo:"; echo "$ULTIMO_LOTE"; echo; tail -220 "$ULTIMO_LOTE"; else echo "Nenhum log de lote encontrado."; fi

    secao "ÚLTIMO LOG DE PRODUÇÃO"
    ULTIMO_PROD="$(ls -t "$BASE"/logs/producao/short_*.log "$BASE"/logs/real_runs/consolidation3_*.log 2>/dev/null | head -1)"
    if [ -n "$ULTIMO_PROD" ]; then echo "Arquivo:"; echo "$ULTIMO_PROD"; echo; tail -220 "$ULTIMO_PROD"; else echo "Nenhum log de produção encontrado."; fi

    secao "ERROS RECENTES"
    LOG_ALVO="${ULTIMO_LOTE:-${ULTIMO_PROD:-}}"
    if [ -n "$LOG_ALVO" ]; then
        grep -inE 'erro|fail|falhou|429|too many|exception|traceback|command not found|rejeitado|warning|aviso|blocked' "$LOG_ALVO" | tail -100 || true
    else
        echo "Nenhum log para analisar."
    fi

    secao "ÚLTIMOS ASSUNTOS"
    python - <<'PY'
import json
from pathlib import Path
p = Path.home() / "ShortAutoPro" / "historico_assuntos.json"
if not p.exists():
    print("Sem histórico.")
    raise SystemExit
try:
    dados = json.loads(p.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"Histórico inválido: {exc}")
    raise SystemExit
for item in dados[-10:]:
    print(f"{item.get('short_id', '?')} | {item.get('topic', '?')}")
PY

    secao "ÚLTIMOS RELEASE GATES"
    python - <<'PY'
import json
from pathlib import Path
base = Path.home() / "ShortAutoPro" / "manifests"
files = sorted(base.glob("*_release.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
if not files:
    print("Nenhum release gate encontrado.")
    raise SystemExit
for p in files:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        print(f"{d.get('short_id', '?')} | {d.get('decision', '?')} | score={d.get('shortautopro_score', '?')}")
    except Exception as exc:
        print(f"{p.name} | ERRO: {exc}")
PY

    secao "ÚLTIMOS MANIFESTS"
    python - <<'PY'
import json
from pathlib import Path
base = Path.home() / "ShortAutoPro" / "manifests"
files = sorted((p for p in base.glob("*.json") if not p.name.endswith("_release.json")), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
if not files:
    print("Nenhum manifest.")
    raise SystemExit
for p in files:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        print(f"{d.get('short_id', '?')} | {d.get('status', '?')} | {d.get('topic', '?')}")
    except Exception as exc:
        print(f"{p.name} | ERRO: {exc}")
PY

    secao "CACHE WIKIPEDIA"
    CACHE="$BASE/cache/wikipedia"
    if [ -d "$CACHE" ]; then
        QTD="$(find "$CACHE" -type f -name '*.json' 2>/dev/null | wc -l)"
        TAM="$(du -sh "$CACHE" 2>/dev/null | awk '{print $1}')"
        echo "Arquivos: $QTD"
        echo "Tamanho: ${TAM:-0}"
    else
        echo "Cache ainda não existe."
    fi

    secao "FIM DO DIAGNÓSTICO"
} | tee "$OUT"

echo
echo "Diagnóstico salvo em:"
echo "$OUT"
echo
