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
    secao "SHORTAUTO PRO - DIAGNÓSTICO 2.3"

    echo "Data: $(date)"
    echo "Base: $BASE"

    echo
    echo "Versão/config detectada:"

    grep -E \
        'SHORTAUTO PRO - STABLE|SHORT_BATCH_COOLDOWN|SHORT_VIDEO_META|SHORT_RETENTION_ENGINE' \
        "$BASE/gerar_short.sh" \
        "$BASE/config.sh" \
        2>/dev/null || true


    # ==================================
    # HEALTH
    # ==================================

    secao "HEALTH CHECK"

    if [ -x "$BASE/health_check.sh" ]; then

        "$BASE/health_check.sh" \
            2>&1 || true

    else

        echo "health_check.sh ausente"

    fi


    # ==================================
    # PREFLIGHT
    # ==================================

    secao "PREFLIGHT"

    if [ -x "$BASE/preflight_check.sh" ]; then

        "$BASE/preflight_check.sh" \
            2>&1 || true

    else

        echo "preflight_check.sh ausente"

    fi


    # ==================================
    # ARMAZENAMENTO
    # ==================================

    secao "ARMAZENAMENTO"

    df -h "$HOME" \
        2>&1 || true

    echo

    du -h -d 1 "$BASE" \
        2>/dev/null \
        | sort -h \
        || true


    # ==================================
    # ESTADO DO LOTE
    # ==================================

    secao "ESTADO DO LOTE"

    STATE="$BASE/queue/batch_state.json"

    if [ -f "$STATE" ]; then
        cat "$STATE"
    else
        echo "Nenhum estado de lote."
    fi


    # ==================================
    # ÚLTIMO LOG DE LOTE
    # ==================================

    secao "ÚLTIMO LOG DE LOTE"

    ULTIMO_LOTE="$(
        ls -t \
        "$BASE"/logs/lotes/lote_*.log \
        2>/dev/null \
        | head -1
    )"

    if [ -n "$ULTIMO_LOTE" ]; then

        echo "Arquivo:"
        echo "$ULTIMO_LOTE"
        echo

        tail -220 \
            "$ULTIMO_LOTE"

    else

        echo "Nenhum log de lote encontrado."

    fi


    # ==================================
    # ÚLTIMO LOG DE PRODUÇÃO
    # ==================================

    secao "ÚLTIMO LOG DE PRODUÇÃO"

    ULTIMO_PROD="$(
        ls -t \
        "$BASE"/logs/producao/short_*.log \
        2>/dev/null \
        | head -1
    )"

    if [ -n "$ULTIMO_PROD" ]; then

        echo "Arquivo:"
        echo "$ULTIMO_PROD"
        echo

        tail -220 \
            "$ULTIMO_PROD"

    else

        echo "Nenhum log de produção encontrado."

    fi


    # ==================================
    # ERROS RECENTES
    # ==================================

    secao "ERROS RECENTES"

    if [ -n "$ULTIMO_LOTE" ]; then

        grep -inE \
            'erro|fail|falhou|429|too many|exception|traceback|command not found|rejeitado|warning|aviso' \
            "$ULTIMO_LOTE" \
            | tail -100 \
            || true

    elif [ -n "$ULTIMO_PROD" ]; then

        grep -inE \
            'erro|fail|falhou|429|too many|exception|traceback|command not found|rejeitado|warning|aviso' \
            "$ULTIMO_PROD" \
            | tail -100 \
            || true

    else

        echo "Nenhum log para analisar."

    fi


    # ==================================
    # HISTÓRICO
    # ==================================

    secao "ÚLTIMOS ASSUNTOS"

    python - <<'PY'
import json
from pathlib import Path

p = Path.home() / "ShortAutoPro" / "historico_assuntos.json"

if not p.exists():
    print("Sem histórico.")
    raise SystemExit

try:
    dados = json.loads(
        p.read_text(
            encoding="utf-8"
        )
    )
except Exception as e:
    print(
        f"Histórico inválido: {e}"
    )
    raise SystemExit

for item in dados[-10:]:
    print(
        f"{item.get('short_id', '?')} | "
        f"{item.get('topic', '?')}"
    )
PY


    # ==================================
    # MANIFESTS
    # ==================================

    secao "ÚLTIMOS MANIFESTS"

    python - <<'PY'
import json
from pathlib import Path

base = (
    Path.home()
    / "ShortAutoPro"
    / "manifests"
)

arquivos = sorted(
    base.glob("*.json"),
    key=lambda p: p.stat().st_mtime,
    reverse=True
)[:5]

if not arquivos:
    print("Nenhum manifest.")
    raise SystemExit

for p in arquivos:

    try:

        d = json.loads(
            p.read_text(
                encoding="utf-8"
            )
        )

        print(
            f"{d.get('short_id', '?')} | "
            f"{d.get('status', '?')} | "
            f"{d.get('topic', '?')}"
        )

    except Exception as e:

        print(
            f"{p.name} | ERRO: {e}"
        )
PY


    # ==================================
    # CACHE WIKIPEDIA
    # ==================================

    secao "CACHE WIKIPEDIA"

    CACHE="$BASE/cache/wikipedia"

    if [ -d "$CACHE" ]; then

        QTD="$(
            find "$CACHE" \
                -type f \
                -name '*.json' \
                2>/dev/null \
                | wc -l
        )"

        TAM="$(
            du -sh "$CACHE" \
                2>/dev/null \
                | awk '{print $1}'
        )"

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
