#!/data/data/com.termux/files/usr/bin/bash
set -u
set -o pipefail
BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"
MAIN="$BASE/main.py"
RESET="\033[0m";BOLD="\033[1m";GREEN="\033[32m";YELLOW="\033[33m";RED="\033[31m";CYAN="\033[36m"
pausa(){ echo; read -r -p "Pressione Enter para voltar..." _ || true; }
cabecalho(){ clear 2>/dev/null || printf '\033c'; echo -e "${BOLD}${CYAN}"; echo "======================================"; echo " SHORTAUTO PRO - CONTROL CENTER 3.0"; echo "       CANONICAL MAIN.PY"; echo "======================================"; echo -e "${RESET}"; }
rodar_shell(){ local arquivo="$1";shift;[ -f "$BASE/$arquivo" ]||{ echo "ERRO: $arquivo não encontrado.";return 1;};bash "$BASE/$arquivo" "$@"; }
rodar_main(){ [ -f "$MAIN" ]||{ echo "ERRO: main.py não encontrado.";return 1;};python "$MAIN" "$@"; }
ultimo_video(){ local video;video="$(find "$BASE/videos" -maxdepth 1 -type f -name 'short_v6_*.mp4' -print0 2>/dev/null|xargs -0 -r ls -1t 2>/dev/null|head -1)";[ -n "$video" ]||{ echo "Nenhum vídeo V6 encontrado.";return;};echo "Último vídeo: $video";ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_type,codec_name,width,height,avg_frame_rate -of default=noprint_wrappers=1 "$video" 2>/dev/null||true; }
mostrar_publish(){ local pack;pack="$(find "$BASE/roteiros" -maxdepth 1 -type f -name 'publish_*.txt' -print0 2>/dev/null|xargs -0 -r ls -1t 2>/dev/null|head -1)";[ -n "$pack" ]&&cat "$pack"||echo "Nenhum Publish Pack."; }
ver_manifests(){ find "$BASE/manifests" -maxdepth 1 -type f -name '*_release.json' -print0 2>/dev/null|xargs -0 -r ls -1t 2>/dev/null|head -10|while read -r arq;do python - "$arq" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
try:d=json.loads(p.read_text(encoding="utf-8"));print(f"{d.get('short_id','?')} | {d.get('decision','?')} | Score={d.get('shortautopro_score','?')}")
except Exception:print(f"{p.name} | JSON INVÁLIDO")
PY
done; }
storage_guard(){ echo "Simulação/status:";rodar_main storage status||return 1;echo;local r;read -r -p "Executar limpeza segura? [s/N]: " r||return 0;case "$r" in s|S|sim|SIM|Sim) rodar_main storage cleanup --execute;;*)echo "Cancelado.";;esac; }
status_sistema(){ echo "ARMAZENAMENTO:";df -h "$HOME"|tail -1||true;echo;du -sh "$BASE" 2>/dev/null||true;echo;echo "VÍDEOS:";find "$BASE/videos" -maxdepth 1 -type f -name 'short_v6_*.mp4' 2>/dev/null|wc -l;echo;echo "GIT:";git -C "$BASE" status --short||true; }
while true;do
 cabecalho
 echo "1) Gerar 1 Short (main.py)";echo "2) Gerar lote";echo "3) Retomar lote";echo "4) Status do lote";echo "5) Retomar Short";echo "6) Status da retomada";echo "7) Últimas releases";echo "8) Último Publish Pack";echo "9) Último vídeo";echo "10) Auditoria do repositório";echo "11) Storage Manager";echo "12) Status do sistema";echo "13) Preflight";echo "14) Health Check";echo "15) Diagnóstico";echo "16) Evolution Center";echo "17) Git status";echo "18) Últimos commits";echo "0) Sair";echo
 read -r -p "Escolha: " OP||exit 0
 case "$OP" in
  1)cabecalho;unset SHORT_ID;rodar_main run||true;pausa;;
  2)cabecalho;read -r -p "Quantos Shorts? [1-10]: " q;if [[ "$q" =~ ^[0-9]+$ ]]&&[ "$q" -ge 1 ]&&[ "$q" -le 10 ];then rodar_shell batch_recovery.sh "$q"||true;else echo "Quantidade inválida.";fi;pausa;;
  3)cabecalho;rodar_shell batch_recovery.sh --resume||true;pausa;;
  4)cabecalho;rodar_shell batch_recovery.sh --status||true;pausa;;
  5)cabecalho;rodar_main resume||true;pausa;;
  6)cabecalho;rodar_main resume --status||true;pausa;;
  7)cabecalho;ver_manifests;pausa;;
  8)cabecalho;mostrar_publish;pausa;;
  9)cabecalho;ultimo_video;pausa;;
  10)cabecalho;rodar_main audit||true;pausa;;
  11)cabecalho;storage_guard||true;pausa;;
  12)cabecalho;status_sistema;pausa;;
  13)cabecalho;rodar_shell preflight_check.sh||true;pausa;;
  14)cabecalho;rodar_shell health_check.sh||true;pausa;;
  15)cabecalho;rodar_shell diagnostico.sh||true;pausa;;
  16)cabecalho;rodar_shell evolution_center.sh||true;;
  17)cabecalho;git -C "$BASE" status;pausa;;
  18)cabecalho;git -C "$BASE" --no-pager log --oneline --decorate -10||true;pausa;;
  0)clear 2>/dev/null||true;exit 0;;
  *)echo "Opção inválida.";sleep 1;;
 esac
done
