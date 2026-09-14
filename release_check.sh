#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

BASE="$HOME/ShortAutoPro"
ERROS=0

ok() { echo "OK   $1"; }
erro() { echo "ERRO $1"; ERROS=$((ERROS + 1)); }

echo
echo "======================================"
echo " SHORTAUTO PRO - RELEASE CHECK 2.4"
echo "======================================"
echo

if [ ! -d "$BASE" ]; then
    echo "ERRO projeto não encontrado: $BASE"
    exit 1
fi

# O preflight é a fonte única de verdade para dependências do pipeline V6.
if [ -f "$BASE/preflight_check.sh" ] && bash "$BASE/preflight_check.sh"; then
    ok "Preflight V6"
else
    erro "Preflight V6"
fi

# Health inclui Piper, Whisper e componentes obrigatórios.
if [ -f "$BASE/health_check.sh" ] && bash "$BASE/health_check.sh"; then
    ok "Health Check"
else
    erro "Health Check"
fi

# Revalida toda a sintaxe shell de primeiro nível, inclusive utilitários que
# não fazem parte do caminho principal de produção.
while IFS= read -r -d '' arq; do
    if bash -n "$arq" >/dev/null 2>&1; then
        ok "Bash $(basename "$arq")"
    else
        erro "Sintaxe Bash $(basename "$arq")"
    fi
done < <(find "$BASE" -maxdepth 1 -type f -name '*.sh' -print0)

# Compila todos os módulos Python de primeiro nível para pegar dependências
# auxiliares e código de auditoria além do pipeline principal.
while IFS= read -r -d '' arq; do
    if python -m py_compile "$arq" >/dev/null 2>&1; then
        ok "Python $(basename "$arq")"
    else
        erro "Python $(basename "$arq")"
    fi
done < <(find "$BASE" -maxdepth 1 -type f -name '*.py' -print0)

cd "$BASE" || exit 1
if python - <<'PY' >/dev/null 2>&1
import subtitle_alignment
import topic_memory
import topic_reserve
import source_identity
import wiki_client
PY
then
    ok "Imports internos críticos"
else
    erro "Imports internos críticos"
fi

FFMPEG_FILTERS="$(ffmpeg -hide_banner -filters 2>/dev/null || true)"
for filtro in sidechaincompress loudnorm ass xfade zoompan; do
    if grep -F "$filtro" <<< "$FFMPEG_FILTERS" >/dev/null 2>&1; then
        ok "FFmpeg $filtro"
    else
        erro "FFmpeg $filtro ausente"
    fi
done

# Valida que a configuração foi realmente carregada e que a chave principal
# não desapareceu entre health/preflight e produção.
if [ -f "$BASE/config.sh" ]; then
    # shellcheck disable=SC1090
    source "$BASE/config.sh"
    ok "config.sh"
else
    erro "config.sh ausente"
fi

if [ -n "${GEMINI_API_KEY:-}" ]; then
    ok "Gemini key carregada"
else
    erro "Gemini key ausente"
fi

LIVRE_KB="$(df -Pk "$HOME" 2>/dev/null | awk 'NR==2 {print $4}')"
if [[ "${LIVRE_KB:-}" =~ ^[0-9]+$ ]]; then
    LIVRE_MB=$((LIVRE_KB / 1024))
    if [ "$LIVRE_MB" -ge 1500 ]; then
        ok "Storage ${LIVRE_MB} MB livres"
    else
        erro "Storage baixo: ${LIVRE_MB} MB"
    fi
else
    erro "Não consegui medir storage"
fi

# Opcional: no Termux o usuário pode pedir a mesma suíte simulada usada pelo
# runner do PC antes de um release local.
if [ "${SHORT_RELEASE_RUN_TESTS:-0}" = "1" ]; then
    if python -m unittest discover -s "$BASE/tests_sim" -p 'test_*.py' -v; then
        ok "Testes simulados"
    else
        erro "Testes simulados"
    fi
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
    echo "STATUS: RELEASE READY"
    exit 0
fi

echo "STATUS: BLOQUEADO"
exit 1
