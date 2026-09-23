#!/data/data/com.termux/files/usr/bin/bash

# ShortAutoPro Termux Bridge
# Pull-based bridge: GitHub termux-stable -> Termux automatically.
# Safety rules:
#   - never overwrites tracked local changes
#   - only accepts fast-forward updates from origin/termux-stable
#   - validates tracked Python and shell files after update
#   - rolls back automatically if syntax validation fails

set -uo pipefail

PROJECT_DIR="${SAP_PROJECT_DIR:-$HOME/ShortAutoPro}"
STATE_DIR="${SAP_BRIDGE_STATE_DIR:-$HOME/.shortautopro_bridge}"
LOG_FILE="$STATE_DIR/bridge.log"
LOCK_FILE="$STATE_DIR/bridge.lock"
LAST_OK_FILE="$STATE_DIR/last_ok_commit"
BRANCH="${SAP_BRIDGE_BRANCH:-termux-stable}"

mkdir -p "$STATE_DIR"
touch "$LOG_FILE"

exec >>"$LOG_FILE" 2>&1

stamp() {
    date '+%Y-%m-%d %H:%M:%S %z'
}

log() {
    printf '[%s] %s\n' "$(stamp)" "$*"
}

log "BRIDGE_RUN=START"

if ! command -v git >/dev/null 2>&1; then
    log "BRIDGE_ERROR=git_not_found"
    exit 10
fi

if ! command -v flock >/dev/null 2>&1; then
    log "BRIDGE_ERROR=flock_not_found"
    exit 11
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    log "BRIDGE_SKIP=already_running"
    exit 0
fi

if [ ! -d "$PROJECT_DIR/.git" ]; then
    log "BRIDGE_ERROR=repo_not_found PROJECT_DIR=$PROJECT_DIR"
    exit 12
fi

cd "$PROJECT_DIR" || {
    log "BRIDGE_ERROR=cannot_cd PROJECT_DIR=$PROJECT_DIR"
    exit 13
}

CURRENT_BRANCH="$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
    log "BRIDGE_BLOCKED=wrong_branch CURRENT=$CURRENT_BRANCH EXPECTED=$BRANCH"
    exit 20
fi

# Never destroy tracked work done locally in Termux.
if ! git diff --quiet -- || ! git diff --cached --quiet --; then
    log "BRIDGE_BLOCKED=tracked_local_changes"
    git status --short
    exit 21
fi

OLD_COMMIT="$(git rev-parse HEAD 2>/dev/null)" || {
    log "BRIDGE_ERROR=cannot_read_local_commit"
    exit 22
}

log "FETCH=START BRANCH=$BRANCH LOCAL=$OLD_COMMIT"
if ! git fetch --quiet origin "$BRANCH"; then
    log "BRIDGE_ERROR=git_fetch_failed"
    exit 23
fi

REMOTE_COMMIT="$(git rev-parse "origin/$BRANCH" 2>/dev/null)" || {
    log "BRIDGE_ERROR=cannot_read_remote_commit"
    exit 24
}

if [ "$OLD_COMMIT" = "$REMOTE_COMMIT" ]; then
    log "BRIDGE_STATUS=up_to_date COMMIT=$OLD_COMMIT"
    printf '%s\n' "$OLD_COMMIT" > "$LAST_OK_FILE"
    exit 0
fi

# Refuse divergence; automation may only fast-forward.
if ! git merge-base --is-ancestor "$OLD_COMMIT" "$REMOTE_COMMIT"; then
    log "BRIDGE_BLOCKED=history_diverged LOCAL=$OLD_COMMIT REMOTE=$REMOTE_COMMIT"
    exit 25
fi

log "UPDATE=START FROM=$OLD_COMMIT TO=$REMOTE_COMMIT"
if ! git merge --ff-only "origin/$BRANCH"; then
    log "BRIDGE_ERROR=fast_forward_failed"
    exit 26
fi

rollback() {
    local reason="$1"
    log "VALIDATION=FAIL REASON=$reason"
    log "ROLLBACK=START TARGET=$OLD_COMMIT"
    if git reset --hard "$OLD_COMMIT"; then
        log "ROLLBACK=PASS TARGET=$OLD_COMMIT"
    else
        log "ROLLBACK=FAIL TARGET=$OLD_COMMIT"
    fi
    exit 30
}

# Validate only files tracked by Git so generated media/cache does not interfere.
if command -v python >/dev/null 2>&1; then
    while IFS= read -r -d '' file; do
        if ! python -m py_compile "$file"; then
            rollback "python_syntax:$file"
        fi
    done < <(git ls-files -z '*.py')
else
    rollback "python_not_found"
fi

while IFS= read -r -d '' file; do
    if ! bash -n "$file"; then
        rollback "bash_syntax:$file"
    fi
done < <(git ls-files -z '*.sh')

if [ ! -f "tools/deploy_smoke.py" ]; then
    rollback "deploy_smoke_missing"
fi
if ! python tools/deploy_smoke.py; then
    rollback "deploy_smoke_failed"
fi
log "DEPLOY_SMOKE=PASS"

NEW_COMMIT="$(git rev-parse HEAD)"
printf '%s\n' "$NEW_COMMIT" > "$LAST_OK_FILE"

log "VALIDATION=PASS"
log "BRIDGE_STATUS=UPDATED FROM=$OLD_COMMIT TO=$NEW_COMMIT"
log "BRIDGE_RUN=PASS"
exit 0
