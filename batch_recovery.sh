#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

BASE="$HOME/ShortAutoPro"
COOLDOWN="${SHORT_BATCH_COOLDOWN:-20}"

if ! [[ "$COOLDOWN" =~ ^[0-9]+$ ]]; then COOLDOWN=20; fi
COOLDOWN=$((COOLDOWN))
if [ "$COOLDOWN" -lt 10 ]; then COOLDOWN=10; fi
if [ "$COOLDOWN" -gt 120 ]; then COOLDOWN=120; fi

STATE_DIR="$BASE/queue"
mkdir -p "$STATE_DIR"
STATE_FILE="$STATE_DIR/batch_state.json"

salvar_estado() {
    local batch_id="$1"
    local total="$2"
    local atual="$3"
    local sucessos="$4"
    local falhas="$5"
    local status="$6"

    BATCH_ID_PY="$batch_id" TOTAL_PY="$total" ATUAL_PY="$atual" \
    SUCESSOS_PY="$sucessos" FALHAS_PY="$falhas" STATUS_PY="$status" \
    STATE_FILE_PY="$STATE_FILE" python - <<'PY'
import json
import os
from datetime import datetime
from pathlib import Path

path = Path(os.environ["STATE_FILE_PY"])
data = {
    "batch_id": os.environ["BATCH_ID_PY"],
    "total": int(os.environ["TOTAL_PY"]),
    "current": int(os.environ["ATUAL_PY"]),
    "successes": int(os.environ["SUCESSOS_PY"]),
    "failures": int(os.environ["FALHAS_PY"]),
    "status": os.environ["STATUS_PY"],
    "updated_at": datetime.now().isoformat(),
}

tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
try:
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
finally:
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass
PY
}

ler_campo() {
    local campo="$1"
    CAMPO_PY="$campo" STATE_FILE_PY="$STATE_FILE" python - <<'PY'
import json
import os
from pathlib import Path

p = Path(os.environ["STATE_FILE_PY"])
if not p.exists():
    print("")
else:
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("estado não é objeto")
        print(data.get(os.environ["CAMPO_PY"], ""))
    except Exception:
        print("")
PY
}

MODO="${1:-}"

if [ "$MODO" = "--status" ]; then
    if [ ! -f "$STATE_FILE" ]; then
        echo "Nenhum lote salvo."
        exit 0
    fi
    echo
echo "======================================"
    echo " BATCH RECOVERY - STATUS"
    echo "======================================"
    echo
    cat "$STATE_FILE"
    echo
    exit 0
fi

if [ "$MODO" = "--reset" ]; then
    rm -f "$STATE_FILE"
    echo "Estado do lote apagado."
    exit 0
fi

if [ "$MODO" = "--resume" ]; then
    if [ ! -f "$STATE_FILE" ]; then
        echo "ERRO: nenhum lote salvo."
        exit 1
    fi

    BATCH_ID="$(ler_campo batch_id)"
    TOTAL="$(ler_campo total)"
    ATUAL="$(ler_campo current)"
    SUCESSOS="$(ler_campo successes)"
    FALHAS="$(ler_campo failures)"
    STATUS="$(ler_campo status)"

    for valor in "$TOTAL" "$ATUAL" "$SUCESSOS" "$FALHAS"; do
        if ! [[ "$valor" =~ ^[0-9]+$ ]]; then
            echo "ERRO: estado inválido."
            exit 1
        fi
    done

    if [ -z "$BATCH_ID" ]; then
        echo "ERRO: batch_id ausente no estado."
        exit 1
    fi

    if [ "$STATUS" = "completed" ]; then
        echo "Este lote já foi concluído com sucesso."
        exit 0
    fi

    if [ "$STATUS" = "completed_with_errors" ]; then
        echo "Este lote foi concluído, mas possui falhas registradas."
        exit 1
    fi

    if [ "$ATUAL" -gt "$TOTAL" ]; then
        echo "ERRO: estado inconsistente (current > total)."
        exit 1
    fi

    INICIO=$((ATUAL + 1))
    if [ "$INICIO" -gt "$TOTAL" ]; then
        echo "ERRO: lote sem item pendente, mas status não está concluído."
        exit 1
    fi

    echo
echo "Retomando lote: $BATCH_ID"
    echo "Próximo Short: $INICIO/$TOTAL"
    echo
else
    TOTAL="${1:-${SHORT_LOTE:-3}}"
    if ! [[ "$TOTAL" =~ ^[0-9]+$ ]]; then
        echo "ERRO: quantidade inválida."
        exit 1
    fi
    TOTAL=$((TOTAL))
    if [ "$TOTAL" -lt 1 ]; then TOTAL=1; fi
    if [ "$TOTAL" -gt 10 ]; then TOTAL=10; fi

    BATCH_ID="$(date +%F_%H%M%S)_$$"
    INICIO=1
    SUCESSOS=0
    FALHAS=0
    salvar_estado "$BATCH_ID" "$TOTAL" 0 "$SUCESSOS" "$FALHAS" "running"
fi

if [ -f "$BASE/config.sh" ]; then
    # shellcheck disable=SC1091
    source "$BASE/config.sh"
else
    echo "ERRO: config.sh não encontrado."
    exit 1
fi

LOG_DIR="$BASE/logs/lotes"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/lote_${BATCH_ID}.log"
exec > >(tee -a "$LOG") 2>&1

echo
echo "======================================"
echo " SHORTAUTO PRO - BATCH RECOVERY 2.1"
echo "======================================"
echo "Lote: $BATCH_ID"
echo "Total: $TOTAL"
echo "Início em: $INICIO"
echo "Sucessos anteriores: $SUCESSOS"
echo "Falhas anteriores: $FALHAS"
echo

for ((i=INICIO; i<=TOTAL; i++)); do
    echo
echo "######################################"
    echo " SHORT $i/$TOTAL"
    echo "######################################"
    echo

    SHORT_ID="${BATCH_ID}_$(printf '%02d' "$i")"
    export SHORT_ID

    # current só avança depois que a tentativa termina. Se o processo for
    # interrompido durante gerar_short.sh, o mesmo item será refeito no resume.
    salvar_estado "$BATCH_ID" "$TOTAL" "$((i - 1))" "$SUCESSOS" "$FALHAS" "running"
    INICIO_SHORT="$(date +%s)"

    if "$BASE/gerar_short.sh"; then
        SUCESSOS=$((SUCESSOS + 1))
        STATUS_SHORT="OK"
    else
        CODIGO=$?
        FALHAS=$((FALHAS + 1))
        STATUS_SHORT="ERRO $CODIGO"
    fi

    FIM_SHORT="$(date +%s)"
    TEMPO="$((FIM_SHORT - INICIO_SHORT))"
    salvar_estado "$BATCH_ID" "$TOTAL" "$i" "$SUCESSOS" "$FALHAS" "running"

    echo
echo "SHORT $i: $STATUS_SHORT"
    echo "ID: $SHORT_ID"
    echo "Tempo: ${TEMPO}s"
    echo "Sucessos: $SUCESSOS"
    echo "Falhas: $FALHAS"

    unset SHORT_ID

    if [ "$i" -lt "$TOTAL" ]; then
        echo
echo "Cooldown das APIs: ${COOLDOWN}s..."
        sleep "$COOLDOWN"
    fi
done

if [ "$FALHAS" -eq 0 ] && [ "$SUCESSOS" -eq "$TOTAL" ]; then
    STATUS_FINAL="completed"
else
    STATUS_FINAL="completed_with_errors"
fi

salvar_estado "$BATCH_ID" "$TOTAL" "$TOTAL" "$SUCESSOS" "$FALHAS" "$STATUS_FINAL"

echo
echo "======================================"
echo " LOTE FINALIZADO"
echo "======================================"
echo "Total: $TOTAL"
echo "Sucessos: $SUCESSOS"
echo "Falhas: $FALHAS"
echo "Status: $STATUS_FINAL"
echo "Estado: $STATE_FILE"
echo "Log: $LOG"
echo

if [ "$STATUS_FINAL" = "completed" ]; then
    exit 0
fi
exit 1
