#!/data/data/com.termux/files/usr/bin/bash

set -euo pipefail

PROJECT_DIR="${SAP_PROJECT_DIR:-$HOME/ShortAutoPro}"
BRANCH="${SAP_BRIDGE_BRANCH:-termux-stable}"
BRIDGE="$PROJECT_DIR/automation/termux_bridge.sh"
STATE_DIR="${SAP_BRIDGE_STATE_DIR:-$HOME/.shortautopro_bridge}"
CRON_TAG="# SHORTAUTOPRO_TERMUX_BRIDGE"
CRON_LINE="*/15 * * * * bash \"$BRIDGE\" $CRON_TAG"

say() {
    printf '%s\n' "$*"
}

fail() {
    printf 'ERRO: %s\n' "$*" >&2
    exit 1
}

command -v git >/dev/null 2>&1 || fail "git nao encontrado"
command -v bash >/dev/null 2>&1 || fail "bash nao encontrado"
command -v flock >/dev/null 2>&1 || fail "flock nao encontrado (instale util-linux no Termux)"
command -v crontab >/dev/null 2>&1 || fail "crontab nao encontrado (instale cronie no Termux)"

[ -d "$PROJECT_DIR/.git" ] || fail "repositorio nao encontrado em $PROJECT_DIR"

cd "$PROJECT_DIR"

if ! git diff --quiet -- || ! git diff --cached --quiet --; then
    git status --short
    fail "ha alteracoes locais rastreadas; salve/commit antes de instalar"
fi

say "[1/6] Buscando branch aprovada: $BRANCH"
git fetch origin "$BRANCH"

git rev-parse --verify "origin/$BRANCH" >/dev/null 2>&1 \
    || fail "origin/$BRANCH nao existe"

say "[2/6] Mudando o Termux para a branch aprovada"
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git switch "$BRANCH"
    git merge --ff-only "origin/$BRANCH"
else
    git switch --track -c "$BRANCH" "origin/$BRANCH"
fi

[ -f "$BRIDGE" ] || fail "bridge nao encontrado: $BRIDGE"

mkdir -p "$STATE_DIR"

say "[3/6] Preservando o crontab atual"
CURRENT_CRON="$(mktemp)"
NEW_CRON="$(mktemp)"
trap 'rm -f "$CURRENT_CRON" "$NEW_CRON"' EXIT
crontab -l >"$CURRENT_CRON" 2>/dev/null || true
cp "$CURRENT_CRON" "$STATE_DIR/crontab.before_bridge.txt"

# Remove somente uma configuracao antiga deste bridge; todas as outras tarefas permanecem intactas.
grep -vF "$CRON_TAG" "$CURRENT_CRON" >"$NEW_CRON" || true
printf '%s\n' "$CRON_LINE" >>"$NEW_CRON"
crontab "$NEW_CRON"

say "[4/6] Garantindo que o cron esteja ativo"
if ! pgrep -x crond >/dev/null 2>&1; then
    crond || fail "nao foi possivel iniciar crond"
fi

say "[5/6] Executando sincronizacao inicial"
bash "$BRIDGE" || {
    say "Falha no bridge. Ultimas linhas do log:"
    tail -n 30 "$STATE_DIR/bridge.log" 2>/dev/null || true
    exit 1
}

say "[6/6] Verificacao final"
say "BRANCH=$(git branch --show-current)"
say "COMMIT=$(git rev-parse --short HEAD)"
say "CRON_BRIDGE=$(crontab -l | grep -F "$CRON_TAG" || true)"
say "LOG=$STATE_DIR/bridge.log"
say "TERMUX_BRIDGE_INSTALL=PASS"
