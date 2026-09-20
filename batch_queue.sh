#!/data/data/com.termux/files/usr/bin/bash
set -u
set -o pipefail
BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"
COOLDOWN="${SHORT_BATCH_COOLDOWN:-20}"
if ! [[ "$COOLDOWN" =~ ^[0-9]+$ ]]; then COOLDOWN=20; fi
COOLDOWN=$((COOLDOWN)); [ "$COOLDOWN" -lt 10 ] && COOLDOWN=10; [ "$COOLDOWN" -gt 120 ] && COOLDOWN=120
QTD="${1:-${SHORT_LOTE:-3}}"
if ! [[ "$QTD" =~ ^[0-9]+$ ]]; then echo "ERRO: quantidade inválida."; exit 1; fi
QTD=$((QTD)); [ "$QTD" -lt 1 ] && QTD=1; [ "$QTD" -gt 10 ] && QTD=10
[ -f "$BASE/config.sh" ] || { echo "ERRO: config.sh não encontrado."; exit 1; }
# shellcheck disable=SC1091
source "$BASE/config.sh"
[ -f "$BASE/main.py" ] || { echo "ERRO: main.py não encontrado."; exit 1; }
[ -f "$BASE/release_artifact_guard.py" ] || { echo "ERRO: release_artifact_guard.py não encontrado."; exit 1; }
BATCH_ID="$(date +%F_%H%M%S)_$$"; LOG_DIR="$BASE/logs/lotes"; mkdir -p "$LOG_DIR"; LOG="$LOG_DIR/lote_${BATCH_ID}.log"; exec > >(tee -a "$LOG") 2>&1
printf '\n======================================\n SHORTAUTO PRO - BATCH QUEUE 3.0\n======================================\nLote: %s\nQuantidade: %s\nInício: %s\nLog: %s\n\n' "$BATCH_ID" "$QTD" "$(date)" "$LOG"
SUCESSOS=0; FALHAS=0; declare -a IDS_OK=(); declare -a IDS_ERRO=()
release_valido() {
 local run_id="$1"
 python "$BASE/release_artifact_guard.py" --short-id "$run_id" >/dev/null 2>&1 && printf '%s\n' "$run_id"
}
for ((i=1; i<=QTD; i++)); do
 printf '\n######################################\n SHORT %s/%s\n######################################\n\n' "$i" "$QTD"
 SHORT_ID="${BATCH_ID}_$(printf '%02d' "$i")"; export SHORT_ID; INICIO="$(date +%s)"
 if python "$BASE/main.py" run; then
  FIM="$(date +%s)"; TEMPO="$((FIM-INICIO))"; ID_OK="$(release_valido "$SHORT_ID" 2>/dev/null || true)"
  if [ -n "$ID_OK" ]; then SUCESSOS=$((SUCESSOS+1)); IDS_OK+=("$ID_OK"); echo "SHORT $i: OK | ID=$ID_OK | ${TEMPO}s"
  else FALHAS=$((FALHAS+1)); IDS_ERRO+=("$SHORT_ID:release_invalido"); echo "SHORT $i: FALHOU | Release Gate ausente/não aprovado | ${TEMPO}s"; fi
 else
  CODIGO=$?; FIM="$(date +%s)"; TEMPO="$((FIM-INICIO))"; FALHAS=$((FALHAS+1)); IDS_ERRO+=("$SHORT_ID:exit_$CODIGO"); echo "SHORT $i: FALHOU | ID=$SHORT_ID | código=$CODIGO | ${TEMPO}s"
 fi
 unset SHORT_ID
 if [ "$i" -lt "$QTD" ]; then echo "Cooldown das APIs: ${COOLDOWN}s..."; sleep "$COOLDOWN"; fi
done
printf '\n======================================\n BATCH QUEUE FINALIZADA\n======================================\nQuantidade: %s\nSucessos: %s\nFalhas: %s\n' "$QTD" "$SUCESSOS" "$FALHAS"
if [ "${#IDS_OK[@]}" -gt 0 ]; then echo "SHORTS CRIADOS:"; for ID in "${IDS_OK[@]}"; do echo "  OK $ID"; done; fi
if [ "${#IDS_ERRO[@]}" -gt 0 ]; then echo "FALHAS:"; for ID in "${IDS_ERRO[@]}"; do echo "  ERRO $ID"; done; fi
echo "Log: $LOG"; echo "Fim: $(date)"; echo "======================================"
[ "$FALHAS" -eq 0 ] && [ "$SUCESSOS" -eq "$QTD" ] && exit 0
exit 1
