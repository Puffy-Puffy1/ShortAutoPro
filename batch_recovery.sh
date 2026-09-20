#!/data/data/com.termux/files/usr/bin/bash
set -u
set -o pipefail
BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"; COOLDOWN="${SHORT_BATCH_COOLDOWN:-20}"
if ! [[ "$COOLDOWN" =~ ^[0-9]+$ ]]; then COOLDOWN=20; fi
COOLDOWN=$((COOLDOWN)); [ "$COOLDOWN" -lt 10 ] && COOLDOWN=10; [ "$COOLDOWN" -gt 120 ] && COOLDOWN=120
STATE_DIR="$BASE/queue"; mkdir -p "$STATE_DIR"; STATE_FILE="$STATE_DIR/batch_state.json"; LOCK_FILE="$STATE_DIR/.batch_recovery.lock"; LOCK_DIR="$STATE_DIR/.batch_recovery.lockdir"; LOCK_FALLBACK=0
liberar_lock_fallback(){ if [ "$LOCK_FALLBACK" -eq 1 ]; then rm -f "$LOCK_DIR/pid" 2>/dev/null || true; rmdir "$LOCK_DIR" 2>/dev/null || true; fi; }
adquirir_lock(){
 if command -v flock >/dev/null 2>&1; then exec 8>"$LOCK_FILE"; flock -n 8 || { echo "ERRO: já existe um Batch Recovery em andamento."; exit 75; }; return; fi
 if ! mkdir "$LOCK_DIR" 2>/dev/null; then local antigo=""; [ -f "$LOCK_DIR/pid" ] && antigo="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"; if [ -n "$antigo" ] && kill -0 "$antigo" 2>/dev/null; then echo "ERRO: já existe um Batch Recovery em andamento."; exit 75; fi; rm -rf "$LOCK_DIR" 2>/dev/null || true; mkdir "$LOCK_DIR" 2>/dev/null || { echo "ERRO: lock indisponível."; exit 75; }; fi
 printf '%s\n' "$$" > "$LOCK_DIR/pid"; LOCK_FALLBACK=1; trap liberar_lock_fallback EXIT INT TERM
}
salvar_estado(){
 BATCH_ID_PY="$1" TOTAL_PY="$2" ATUAL_PY="$3" SUCESSOS_PY="$4" FALHAS_PY="$5" STATUS_PY="$6" STATE_FILE_PY="$STATE_FILE" python - <<'PY'
import json,os,tempfile
from datetime import datetime
from pathlib import Path
p=Path(os.environ["STATE_FILE_PY"]);data={"batch_id":os.environ["BATCH_ID_PY"],"total":int(os.environ["TOTAL_PY"]),"current":int(os.environ["ATUAL_PY"]),"successes":int(os.environ["SUCESSOS_PY"]),"failures":int(os.environ["FALHAS_PY"]),"status":os.environ["STATUS_PY"],"updated_at":datetime.now().isoformat()};p.parent.mkdir(parents=True,exist_ok=True);fd,t=tempfile.mkstemp(prefix=f".{p.name}.",suffix=".tmp",dir=str(p.parent))
try:
 with os.fdopen(fd,"w",encoding="utf-8") as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
 os.replace(t,p)
finally:
 try:os.unlink(t)
 except OSError:pass
PY
}
ler_campo(){ CAMPO_PY="$1" STATE_FILE_PY="$STATE_FILE" python - <<'PY'
import json,os
from pathlib import Path
p=Path(os.environ["STATE_FILE_PY"])
try:d=json.loads(p.read_text(encoding="utf-8"));print(d.get(os.environ["CAMPO_PY"],"") if isinstance(d,dict) else "")
except Exception:print("")
PY
}
resultado_final_ok(){ python "$BASE/release_artifact_guard.py" --short-id "$1" >/dev/null 2>&1; }
MODO="${1:-}"
if [ "$MODO" = "--status" ]; then [ -f "$STATE_FILE" ] || { echo "Nenhum lote salvo."; exit 0; }; echo; echo "======================================"; echo " BATCH RECOVERY - STATUS"; echo "======================================"; cat "$STATE_FILE"; echo; exit 0; fi
adquirir_lock
if [ "$MODO" = "--reset" ]; then rm -f "$STATE_FILE"; echo "Estado do lote apagado."; exit 0; fi
if [ "$MODO" = "--resume" ]; then
 [ -f "$STATE_FILE" ] || { echo "ERRO: nenhum lote salvo."; exit 1; }; BATCH_ID="$(ler_campo batch_id)"; TOTAL="$(ler_campo total)"; ATUAL="$(ler_campo current)"; SUCESSOS="$(ler_campo successes)"; FALHAS="$(ler_campo failures)"; STATUS="$(ler_campo status)"
 for valor in "$TOTAL" "$ATUAL" "$SUCESSOS" "$FALHAS"; do [[ "$valor" =~ ^[0-9]+$ ]] || { echo "ERRO: estado inválido."; exit 1; }; done
 [[ "$BATCH_ID" =~ ^[A-Za-z0-9_.-]+$ ]] || { echo "ERRO: batch_id inválido."; exit 1; }
 [ "$STATUS" = "completed" ] && { echo "Este lote já foi concluído com sucesso."; exit 0; }; [ "$STATUS" = "completed_with_errors" ] && { echo "Lote concluído com falhas registradas."; exit 1; }; [ "$STATUS" = "running" ] || { echo "ERRO: status inválido: $STATUS"; exit 1; }
 [ "$ATUAL" -le "$TOTAL" ] || { echo "ERRO: current > total."; exit 1; }; INICIO=$((ATUAL+1)); [ "$INICIO" -le "$TOTAL" ] || { echo "ERRO: lote sem item pendente."; exit 1; }; echo "Retomando lote: $BATCH_ID | Próximo: $INICIO/$TOTAL"
else
 TOTAL="${1:-${SHORT_LOTE:-3}}"; [[ "$TOTAL" =~ ^[0-9]+$ ]] || { echo "ERRO: quantidade inválida."; exit 1; }; TOTAL=$((TOTAL)); [ "$TOTAL" -lt 1 ] && TOTAL=1; [ "$TOTAL" -gt 10 ] && TOTAL=10; BATCH_ID="$(date +%F_%H%M%S)_$$"; INICIO=1; SUCESSOS=0; FALHAS=0; salvar_estado "$BATCH_ID" "$TOTAL" 0 "$SUCESSOS" "$FALHAS" "running"
fi
[ -f "$BASE/config.sh" ] || { echo "ERRO: config.sh não encontrado."; exit 1; }; [ -f "$BASE/main.py" ] || { echo "ERRO: main.py não encontrado."; exit 1; }; [ -f "$BASE/release_artifact_guard.py" ] || { echo "ERRO: release_artifact_guard.py não encontrado."; exit 1; }
# shellcheck disable=SC1091
source "$BASE/config.sh"
LOG_DIR="$BASE/logs/lotes"; mkdir -p "$LOG_DIR"; LOG="$LOG_DIR/lote_${BATCH_ID}.log"; exec > >(tee -a "$LOG") 2>&1
printf '\n======================================\n SHORTAUTO PRO - BATCH RECOVERY 3.0\n======================================\nLote: %s\nTotal: %s\nInício: %s\n\n' "$BATCH_ID" "$TOTAL" "$INICIO"
for ((i=INICIO;i<=TOTAL;i++)); do
 echo; echo "######################################"; echo " SHORT $i/$TOTAL"; echo "######################################"; SHORT_ID="${BATCH_ID}_$(printf '%02d' "$i")"; export SHORT_ID
 if resultado_final_ok "$SHORT_ID"; then
  echo "RECOVERY: Release Gate já aprovado para $SHORT_ID."; if python "$BASE/register_topic.py"; then SUCESSOS=$((SUCESSOS+1)); salvar_estado "$BATCH_ID" "$TOTAL" "$i" "$SUCESSOS" "$FALHAS" "running"; else FALHAS=$((FALHAS+1)); salvar_estado "$BATCH_ID" "$TOTAL" "$i" "$SUCESSOS" "$FALHAS" "running"; fi
 else
  salvar_estado "$BATCH_ID" "$TOTAL" "$((i-1))" "$SUCESSOS" "$FALHAS" "running"; INICIO_SHORT="$(date +%s)"
  if python "$BASE/main.py" run; then SUCESSOS=$((SUCESSOS+1)); STATUS_SHORT="OK"; else CODIGO=$?; FALHAS=$((FALHAS+1)); STATUS_SHORT="ERRO $CODIGO"; fi
  TEMPO="$(( $(date +%s)-INICIO_SHORT ))"; salvar_estado "$BATCH_ID" "$TOTAL" "$i" "$SUCESSOS" "$FALHAS" "running"; echo "SHORT $i: $STATUS_SHORT | ID=$SHORT_ID | ${TEMPO}s"
 fi
 unset SHORT_ID; if [ "$i" -lt "$TOTAL" ]; then echo "Cooldown: ${COOLDOWN}s..."; sleep "$COOLDOWN"; fi
done
if [ "$FALHAS" -eq 0 ] && [ "$SUCESSOS" -eq "$TOTAL" ]; then STATUS_FINAL="completed"; else STATUS_FINAL="completed_with_errors"; fi
salvar_estado "$BATCH_ID" "$TOTAL" "$TOTAL" "$SUCESSOS" "$FALHAS" "$STATUS_FINAL"; printf '\n======================================\n LOTE FINALIZADO\n======================================\nTotal: %s\nSucessos: %s\nFalhas: %s\nStatus: %s\nEstado: %s\nLog: %s\n' "$TOTAL" "$SUCESSOS" "$FALHAS" "$STATUS_FINAL" "$STATE_FILE" "$LOG"
[ "$STATUS_FINAL" = "completed" ] && exit 0
exit 1
