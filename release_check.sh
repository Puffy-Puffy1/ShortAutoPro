#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"
ERROS=0

ok() { echo "OK   $1"; }
erro() { echo "ERRO $1"; ERROS=$((ERROS + 1)); }

echo
echo "======================================"
echo " SHORTAUTO PRO - RELEASE CHECK 3.0"
echo "======================================"
echo

if [ ! -d "$BASE" ]; then
    echo "ERRO projeto não encontrado: $BASE"
    exit 1
fi

# Preflight e health validam exatamente o pipeline Professional canônico 3.0.
if [ -f "$BASE/preflight_check.sh" ] && bash "$BASE/preflight_check.sh"; then ok "Preflight 3.0"; else erro "Preflight 3.0"; fi
if [ -f "$BASE/health_check.sh" ] && bash "$BASE/health_check.sh"; then ok "Health Check 3.0"; else erro "Health Check 3.0"; fi

# Auditoria estrutural é obrigatória para impedir retorno de entrypoints legados.
if [ -f "$BASE/tools/repo_audit.py" ] && python "$BASE/tools/repo_audit.py" >/dev/null; then
    ok "Repository Audit 3.0"
else
    erro "Repository Audit 3.0"
fi

while IFS= read -r -d '' arq; do
    if bash -n "$arq" >/dev/null 2>&1; then ok "Bash $(basename "$arq")"; else erro "Sintaxe Bash $(basename "$arq")"; fi
done < <(find "$BASE" -maxdepth 1 -type f -name '*.sh' -print0)

while IFS= read -r -d '' arq; do
    if python -m py_compile "$arq" >/dev/null 2>&1; then ok "Python $(basename "$arq")"; else erro "Python $(basename "$arq")"; fi
done < <(find "$BASE" -maxdepth 1 -type f -name '*.py' -print0)

cd "$BASE" || exit 1
if python - <<'PY' >/dev/null 2>&1
import subtitle_alignment
import topic_memory
import topic_reserve
import source_identity
import wiki_client
import visual_continuity_engine
import visual_score_engine
import retention_engine
import sound_design_engine
PY
then
    ok "Imports internos críticos 3.0"
else
    erro "Imports internos críticos 3.0"
fi

FFMPEG_FILTERS="$(ffmpeg -hide_banner -filters 2>/dev/null || true)"
for filtro in sidechaincompress loudnorm ass xfade zoompan blackdetect cropdetect; do
    if grep -F "$filtro" <<< "$FFMPEG_FILTERS" >/dev/null 2>&1; then ok "FFmpeg $filtro"; else erro "FFmpeg $filtro ausente"; fi
done

if [ -f "$BASE/config.sh" ]; then
    # shellcheck disable=SC1090
    source "$BASE/config.sh"
    ok "config.sh"
else
    erro "config.sh ausente"
fi

if [ -n "${GEMINI_API_KEY:-}" ]; then ok "Gemini key carregada"; else erro "Gemini key ausente"; fi

LIVRE_KB="$(df -Pk "$BASE" 2>/dev/null | awk 'NR==2 {print $4}')"
if [[ "${LIVRE_KB:-}" =~ ^[0-9]+$ ]]; then
    LIVRE_MB=$((LIVRE_KB / 1024))
    if [ "$LIVRE_MB" -ge 1500 ]; then ok "Storage ${LIVRE_MB} MB livres"; else erro "Storage baixo: ${LIVRE_MB} MB"; fi
else
    erro "Não consegui medir storage"
fi

if [ "${SHORT_RELEASE_RUN_TESTS:-0}" = "1" ]; then
    if python -m unittest discover -s "$BASE/tests_sim" -p 'test_*.py' -v; then ok "Testes simulados"; else erro "Testes simulados"; fi
else
    echo "INFO Testes simulados locais não solicitados (SHORT_RELEASE_RUN_TESTS=1 para ativar)."
fi

echo
echo "======================================"
echo " RELEASE RESULT"
echo "======================================"
echo "Erros: $ERROS"
echo

if [ "$ERROS" -eq 0 ]; then
    echo "STATUS: RELEASE READY 3.0"
    exit 0
fi

echo "STATUS: BLOQUEADO"
exit 1
