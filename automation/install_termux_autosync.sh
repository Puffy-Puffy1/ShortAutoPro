#!/data/data/com.termux/files/usr/bin/bash

# ShortAutoPro Termux AutoSync installer
# Installs a safe 10-minute cron job that runs automation/termux_bridge.sh.
# Existing project: ~/ShortAutoPro
# Sync branch: termux-stable

set -euo pipefail

PROJECT_DIR="${SAP_PROJECT_DIR:-$HOME/ShortAutoPro}"
BRIDGE="$PROJECT_DIR/automation/termux_bridge.sh"
STATE_DIR="${SAP_BRIDGE_STATE_DIR:-$HOME/.shortautopro_bridge}"
CRON_TAG="# ShortAutoPro AutoSync"
CRON_LINE="*/10 * * * * SAP_PROJECT_DIR=\"$PROJECT_DIR\" SAP_BRIDGE_BRANCH=termux-stable bash \"$BRIDGE\""

echo "[ShortAutoPro] Configurando sincronizacao automatica..."

if [ ! -d "$PROJECT_DIR/.git" ]; then
  echo "ERRO: repositorio nao encontrado em $PROJECT_DIR"
  exit 10
fi

if [ ! -f "$BRIDGE" ]; then
  echo "ERRO: bridge nao encontrado em $BRIDGE"
  exit 11
fi

if ! command -v git >/dev/null 2>&1; then
  echo "ERRO: git nao encontrado. Rode: pkg install git"
  exit 12
fi

if ! command -v crond >/dev/null 2>&1 || ! command -v crontab >/dev/null 2>&1; then
  echo "[ShortAutoPro] Instalando cronie..."
  pkg install -y cronie
fi

mkdir -p "$STATE_DIR"
chmod +x "$BRIDGE"

TMP_CRON="$(mktemp)"
trap 'rm -f "$TMP_CRON"' EXIT

crontab -l 2>/dev/null | grep -vF "$CRON_TAG" | grep -vF "$BRIDGE" > "$TMP_CRON" || true
{
  cat "$TMP_CRON"
  echo "$CRON_TAG"
  echo "$CRON_LINE"
} | crontab -

if ! pgrep -x crond >/dev/null 2>&1; then
  crond
fi

BOOT_DIR="$HOME/.termux/boot"
BOOT_SCRIPT="$BOOT_DIR/shortautopro-autosync.sh"
mkdir -p "$BOOT_DIR"
cat > "$BOOT_SCRIPT" <<'BOOT'
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock >/dev/null 2>&1 || true
pgrep -x crond >/dev/null 2>&1 || crond
BOOT
chmod +x "$BOOT_SCRIPT"

echo "[ShortAutoPro] Executando primeira sincronizacao segura..."
SAP_PROJECT_DIR="$PROJECT_DIR" SAP_BRIDGE_BRANCH=termux-stable bash "$BRIDGE" || {
  code=$?
  echo "[ShortAutoPro] Bridge retornou codigo $code. Veja: $STATE_DIR/bridge.log"
  exit "$code"
}

echo
echo "OK: AutoSync configurado."
echo "Projeto: $PROJECT_DIR"
echo "Branch: termux-stable"
echo "Intervalo: 10 minutos"
echo "Log: $STATE_DIR/bridge.log"
echo
echo "Status rapido:"
echo "  tail -n 50 $STATE_DIR/bridge.log"
echo
echo "Cron ativo:"
crontab -l | grep -F "$BRIDGE" || true
