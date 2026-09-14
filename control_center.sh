#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

BASE="$HOME/ShortAutoPro"

RESET="\033[0m"
BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
CYAN="\033[36m"

pausa() {
    echo
    read -r -p "Pressione Enter para voltar..." _ || true
}

cabecalho() {
    clear 2>/dev/null || printf '\033c'
    echo -e "${BOLD}${CYAN}"
    echo "======================================"
    echo "      SHORTAUTO PRO - CONTROL CENTER"
    echo "               STABLE 2.2"
    echo "======================================"
    echo -e "${RESET}"
}

rodar_shell() {
    local arquivo="$1"
    shift
    if [ ! -f "$BASE/$arquivo" ]; then
        echo "ERRO: $arquivo não encontrado."
        return 1
    fi
    bash "$BASE/$arquivo" "$@"
}

ultimo_video() {
    local video
    video="$(find "$BASE/videos" -maxdepth 1 -type f -name 'short_v6_*.mp4' -print0 2>/dev/null \
        | xargs -0 -r ls -1t 2>/dev/null | head -1)"

    if [ -z "$video" ]; then
        echo "Nenhum vídeo V6 encontrado."
        return 0
    fi

    echo
    echo "Último vídeo:"
    echo "$video"
    echo
    ffprobe -v error \
        -show_entries format=duration,size \
        -show_entries stream=codec_type,codec_name,width,height,avg_frame_rate \
        -of default=noprint_wrappers=1 "$video" 2>/dev/null \
        || echo "AVISO: não foi possível ler metadados do vídeo."
}

ver_historico() {
    if [ ! -f "$BASE/historico_assuntos.json" ]; then
        echo "Nenhum histórico ainda."
        return 0
    fi

    BASE_CC="$BASE" python - <<'PY'
import json
import os
from pathlib import Path

p = Path(os.environ["BASE_CC"]) / "historico_assuntos.json"
try:
    dados = json.loads(p.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"ERRO: histórico inválido: {exc}")
    raise SystemExit(1)

if not isinstance(dados, list) or not all(isinstance(x, dict) for x in dados):
    print("ERRO: histórico precisa ser uma lista de objetos.")
    raise SystemExit(1)

if not dados:
    print("Histórico vazio.")
    raise SystemExit(0)

print("\nASSUNTOS PRODUZIDOS\n===================\n")
for i, item in enumerate(reversed(dados), 1):
    print(f"{i:02d}. {item.get('topic', '?')}")
    print(f"    ID: {item.get('short_id', '?')}\n")
PY
}

ver_manifests() {
    mkdir -p "$BASE/manifests"
    mapfile -t arquivos < <(
        find "$BASE/manifests" -maxdepth 1 -type f -name '*.json' ! -name '*_quality.json' ! -name '*_evolution.json' -print0 2>/dev/null \
            | xargs -0 -r ls -1t 2>/dev/null | head -10
    )

    if [ "${#arquivos[@]}" -eq 0 ]; then
        echo "Nenhum manifest de produção encontrado."
        return 0
    fi

    echo
    echo "ÚLTIMAS PRODUÇÕES"
    echo "================="
    echo

    for arq in "${arquivos[@]}"; do
        python - "$arq" <<'PY'
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
try:
    d = json.loads(p.read_text(encoding="utf-8"))
except Exception:
    print(f"{p.name} | JSON INVÁLIDO")
    raise SystemExit(0)

if not isinstance(d, dict) or not d.get("short_id"):
    print(f"{p.name} | NÃO É MANIFEST DE PRODUÇÃO")
else:
    print(f"{d.get('short_id', '?')} | {d.get('status', '?')} | {d.get('topic', '?')}")
PY
    done
}

gerar_um() {
    echo
    echo "Iniciando 1 Short..."
    echo
    unset SHORT_ID
    rodar_shell "gerar_short.sh"
}

gerar_lote() {
    local qtd
    echo
    read -r -p "Quantos Shorts? [1-10]: " qtd || return 1
    if ! [[ "$qtd" =~ ^[0-9]+$ ]] || [ "$qtd" -lt 1 ] || [ "$qtd" -gt 10 ]; then
        echo "Use um número entre 1 e 10."
        return 1
    fi
    echo
    echo "Iniciando lote de $qtd Shorts..."
    echo
    rodar_shell "batch_recovery.sh" "$qtd"
}

retomar_lote() {
    rodar_shell "batch_recovery.sh" --status || return 1
    echo
    local resposta
    read -r -p "Retomar esse lote? [s/N]: " resposta || return 0
    case "$resposta" in
        s|S|sim|SIM|Sim) rodar_shell "batch_recovery.sh" --resume ;;
        *) echo "Cancelado." ;;
    esac
}

storage_guard() {
    echo
    echo "Primeiro será executada uma simulação."
    echo
    rodar_shell "limpar_storage.sh" || return 1
    echo
    local resposta
    read -r -p "Executar limpeza real? [s/N]: " resposta || return 0
    case "$resposta" in
        s|S|sim|SIM|Sim) rodar_shell "limpar_storage.sh" --execute ;;
        *) echo "Limpeza cancelada." ;;
    esac
}

mostrar_publish() {
    local pack
    pack="$(find "$BASE/roteiros" -maxdepth 1 -type f -name 'publish_*.txt' -print0 2>/dev/null \
        | xargs -0 -r ls -1t 2>/dev/null | head -1)"
    if [ -z "$pack" ]; then
        echo "Nenhum Publish Pack encontrado."
        return 0
    fi
    echo
    echo "ÚLTIMO PUBLISH PACK"
    echo "==================="
    echo
    cat "$pack"
}

status_sistema() {
    echo
    echo "ARMAZENAMENTO:"
    df -h "$HOME" | tail -1 || true
    echo
    echo "SHORTAUTO PRO:"
    du -sh "$BASE" 2>/dev/null || true
    echo
    echo "VÍDEOS V6:"
    find "$BASE/videos" -maxdepth 1 -type f -name 'short_v6_*.mp4' 2>/dev/null | wc -l
    echo
    echo "ASSUNTOS NO HISTÓRICO:"
    BASE_CC="$BASE" python - <<'PY'
import json
import os
from pathlib import Path
p = Path(os.environ["BASE_CC"]) / "historico_assuntos.json"
if not p.exists():
    print(0)
else:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(d, list):
            raise ValueError("não é lista")
        print(len(d))
    except Exception:
        print("INVÁLIDO")
PY
}

executar_helper_git() {
    local comando="$1"
    if command -v "$comando" >/dev/null 2>&1; then
        "$comando"
    else
        echo "ERRO: comando '$comando' não está disponível neste Termux."
        echo "Use a configuração Git já instalada ou sincronize manualmente antes de continuar."
        return 127
    fi
}

while true; do
    cabecalho
    echo "1) Gerar 1 Short"
    echo "2) Gerar lote de Shorts"
    echo "3) Retomar lote interrompido"
    echo "4) Ver status do lote"
    echo "5) Ver histórico de assuntos"
    echo "6) Ver últimas produções"
    echo "7) Ver último Publish Pack"
    echo "8) Ver último vídeo"
    echo "9) Health Check"
    echo "10) Storage Guard"
    echo "11) Status do sistema"
    echo "12) Resetar lote salvo"
    echo "13) Preflight Check"
    echo "14) Gerar Batch Report"
    echo "15) Diagnóstico completo"
    echo
    echo "──────── Git / GitHub ────────"
    echo "16) Sincronizar / iniciar trabalho"
    echo "17) Salvar alterações no GitHub"
    echo "18) Ver status do Git"
    echo "19) Ver últimos commits"
    echo "20) Status da sincronização"
    echo
    echo "──────── Evolution ───────────"
    echo "21) Abrir Evolution Center"
    echo "0) Sair"
    echo

    read -r -p "Escolha: " OPCAO || exit 0

    case "$OPCAO" in
        1) cabecalho; gerar_um || true; pausa ;;
        2) cabecalho; gerar_lote || true; pausa ;;
        3) cabecalho; retomar_lote || true; pausa ;;
        4) cabecalho; rodar_shell "batch_recovery.sh" --status || true; pausa ;;
        5) cabecalho; ver_historico || true; pausa ;;
        6) cabecalho; ver_manifests || true; pausa ;;
        7) cabecalho; mostrar_publish || true; pausa ;;
        8) cabecalho; ultimo_video || true; pausa ;;
        9) cabecalho; rodar_shell "health_check.sh" || true; pausa ;;
        10) cabecalho; storage_guard || true; pausa ;;
        11) cabecalho; status_sistema; pausa ;;
        12)
            cabecalho
            read -r -p "Apagar estado do lote salvo? [s/N]: " RESPOSTA || RESPOSTA=""
            case "$RESPOSTA" in
                s|S|sim|SIM|Sim) rodar_shell "batch_recovery.sh" --reset || true ;;
                *) echo "Cancelado." ;;
            esac
            pausa
            ;;
        13) cabecalho; rodar_shell "preflight_check.sh" || true; pausa ;;
        14)
            cabecalho
            read -r -p "Quantas últimas produções analisar? [1-10]: " QTD_REPORT || QTD_REPORT=""
            if [[ "$QTD_REPORT" =~ ^[0-9]+$ ]] && [ "$QTD_REPORT" -ge 1 ] && [ "$QTD_REPORT" -le 10 ]; then
                python "$BASE/batch_report.py" "$QTD_REPORT" || true
            else
                echo "Use um número entre 1 e 10."
            fi
            pausa
            ;;
        15) cabecalho; rodar_shell "diagnostico.sh" || true; pausa ;;
        16)
            cabecalho
            echo "Sincronizando ShortAutoPro com GitHub..."
            echo
            executar_helper_git sap-iniciar || true
            pausa
            ;;
        17)
            cabecalho
            echo "Salvando alterações do ShortAutoPro..."
            echo
            executar_helper_git sap-salvar || true
            pausa
            ;;
        18)
            cabecalho
            echo "========================================"
            echo " STATUS DO GIT"
            echo "========================================"
            echo
            git -C "$BASE" status || true
            pausa
            ;;
        19)
            cabecalho
            echo "========================================"
            echo " ÚLTIMOS COMMITS"
            echo "========================================"
            echo
            git -C "$BASE" --no-pager log --oneline --decorate -10 || true
            pausa
            ;;
        20)
            cabecalho
            echo "========================================"
            echo " STATUS DA SINCRONIZAÇÃO"
            echo "========================================"
            echo
            if ! cd "$BASE"; then
                echo "ERRO: projeto não encontrado."
                pausa
                continue
            fi
            BRANCH="$(git branch --show-current 2>/dev/null || true)"
            echo "Branch: ${BRANCH:-desconhecida}"
            echo
            echo "Commit local:"
            git --no-pager log -1 --oneline 2>/dev/null || true
            echo
            echo "Consultando GitHub..."
            if git fetch origin; then
                REMOTE_REF="origin/${BRANCH:-main}"
                if git rev-parse --verify "$REMOTE_REF" >/dev/null 2>&1; then
                    ATRAS_LOCAL="$(git rev-list --count HEAD.."$REMOTE_REF" 2>/dev/null || echo 0)"
                    ATRAS_REMOTO="$(git rev-list --count "$REMOTE_REF"..HEAD 2>/dev/null || echo 0)"
                    echo "Commits no GitHub ausentes no celular: $ATRAS_LOCAL"
                    echo "Commits no celular ausentes no GitHub: $ATRAS_REMOTO"
                    if [ "$ATRAS_LOCAL" -eq 0 ] && [ "$ATRAS_REMOTO" -eq 0 ]; then
                        echo "STATUS: SINCRONIZADO"
                    elif [ "$ATRAS_LOCAL" -gt 0 ] && [ "$ATRAS_REMOTO" -eq 0 ]; then
                        echo "STATUS: GITHUB TEM ATUALIZAÇÕES"
                    elif [ "$ATRAS_LOCAL" -eq 0 ] && [ "$ATRAS_REMOTO" -gt 0 ]; then
                        echo "STATUS: CELULAR TEM COMMITS PARA ENVIAR"
                    else
                        echo "STATUS: HISTÓRICOS DIVERGIRAM"
                        echo "Não faça merge automático."
                    fi
                else
                    echo "ERRO: branch remota $REMOTE_REF não encontrada."
                fi
            else
                echo "Não foi possível consultar o GitHub."
            fi
            echo
            echo "Arquivos locais:"
            git status --short 2>/dev/null || true
            pausa
            ;;
        21) cabecalho; rodar_shell "evolution_center.sh" || true ;;
        0) clear 2>/dev/null || true; echo "ShortAutoPro encerrado."; exit 0 ;;
        *) echo; echo "Opção inválida."; sleep 1 ;;
    esac
done
