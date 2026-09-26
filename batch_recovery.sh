#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"
case "${1:-}" in
  --resume) exec python "$BASE/batch_runtime.py" resume ;;
  --status) exec python "$BASE/batch_runtime.py" status ;;
  --report) exec python "$BASE/batch_runtime.py" report ;;
  --reset)
    rm -f "$BASE/queue/batch_state.json"
    echo "Estado do lote apagado."
    exit 0
    ;;
  "") exec python "$BASE/batch_runtime.py" run "${SHORT_LOTE:-3}" ;;
  *) exec python "$BASE/batch_runtime.py" run "$1" ;;
esac
