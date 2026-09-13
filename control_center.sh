#!/data/data/com.termux/files/usr/bin/bash

set -u

BASE="$HOME/ShortAutoPro"

# ======================================
# CORES SIMPLES
# ======================================

RESET="\033[0m"
BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
CYAN="\033[36m"


pausa() {
    echo
    read -r -p "Pressione Enter para voltar..."
}


cabecalho() {
    clear

    echo -e "${BOLD}${CYAN}"
    echo "======================================"
    echo "      SHORTAUTO PRO - CONTROL CENTER"
    echo "               STABLE 2.0"
    echo "======================================"
    echo -e "${RESET}"
}


ultimo_video() {

    local VIDEO

    VIDEO="$(
        ls -t "$BASE"/videos/short_v*.mp4 \
        2>/dev/null \
        | head -1
    )"

    if [ -z "$VIDEO" ]; then
        echo "Nenhum vídeo encontrado."
        return
    fi

    echo
    echo "Último vídeo:"
    echo "$VIDEO"
    echo

    ffprobe \
        -v error \
        -show_entries \
        format=duration,size \
        -show_entries \
        stream=codec_name,width,height,avg_frame_rate \
        -of default=noprint_wrappers=1 \
        "$VIDEO" \
        2>/dev/null || true
}


ver_historico() {

    if [ ! -f "$BASE/historico_assuntos.json" ]; then
        echo "Nenhum histórico ainda."
        return
    fi

    python - <<'PY'
import json
from pathlib import Path

p = Path.home() / "ShortAutoPro" / "historico_assuntos.json"

try:
    dados = json.loads(
        p.read_text(
            encoding="utf-8"
        )
    )
except Exception:
    print("Histórico inválido.")
    raise SystemExit

if not dados:
    print("Histórico vazio.")
    raise SystemExit

print()
print("ASSUNTOS PRODUZIDOS")
print("===================")
print()

for i, item in enumerate(
    reversed(dados),
    1
):

    print(
        f"{i:02d}. "
        f"{item.get('topic', '?')}"
    )

    print(
        f"    ID: "
        f"{item.get('short_id', '?')}"
    )

    print()
PY
}


ver_manifests() {

    mkdir -p "$BASE/manifests"

    mapfile -t ARQUIVOS < <(
        ls -t "$BASE"/manifests/*.json \
        2>/dev/null \
        | head -10
    )

    if [ "${#ARQUIVOS[@]}" -eq 0 ]; then
        echo "Nenhum manifest encontrado."
        return
    fi

    echo
    echo "ÚLTIMAS PRODUÇÕES"
    echo "================="
    echo

    for ARQ in "${ARQUIVOS[@]}"; do

        python - "$ARQ" <<'PY'
import json
import sys

arquivo = sys.argv[1]

try:
    with open(
        arquivo,
        encoding="utf-8"
    ) as f:
        d = json.load(f)
except Exception:
    raise SystemExit

print(
    f"{d.get('short_id', '?')} | "
    f"{d.get('status', '?')} | "
    f"{d.get('topic', '?')}"
)
PY

    done
}


gerar_um() {

    echo
    echo "Iniciando 1 Short..."
    echo

    unset SHORT_ID

    source "$BASE/config.sh"

    "$BASE/gerar_short.sh"
}


gerar_lote() {

    echo
    read -r -p "Quantos Shorts? [1-10]: " QTD

    if ! [[ "$QTD" =~ ^[0-9]+$ ]]; then
        echo "Quantidade inválida."
        return
    fi

    if [ "$QTD" -lt 1 ] || [ "$QTD" -gt 10 ]; then
        echo "Use um número entre 1 e 10."
        return
    fi

    echo
    echo "Iniciando lote de $QTD Shorts..."
    echo

    "$BASE/batch_recovery.sh" "$QTD"
}


retomar_lote() {

    "$BASE/batch_recovery.sh" --status

    echo

    read -r -p "Retomar esse lote? [s/N]: " RESPOSTA

    case "$RESPOSTA" in
        s|S|sim|SIM|Sim)
            "$BASE/batch_recovery.sh" --resume
            ;;
        *)
            echo "Cancelado."
            ;;
    esac
}


storage_guard() {

    echo
    echo "Primeiro será executada uma simulação."
    echo

    "$BASE/limpar_storage.sh"

    echo

    read -r -p "Executar limpeza real? [s/N]: " RESPOSTA

    case "$RESPOSTA" in
        s|S|sim|SIM|Sim)

            "$BASE/limpar_storage.sh" --execute

            ;;

        *)

            echo "Limpeza cancelada."

            ;;

    esac
}


mostrar_publish() {

    local PACK

    PACK="$(
        ls -t "$BASE"/roteiros/publish_*.txt \
        2>/dev/null \
        | head -1
    )"

    if [ -z "$PACK" ]; then
        echo "Nenhum Publish Pack encontrado."
        return
    fi

    echo
    echo "ÚLTIMO PUBLISH PACK"
    echo "==================="
    echo

    cat "$PACK"
}


status_sistema() {

    echo
    echo "ARMAZENAMENTO:"
    echo

    df -h "$HOME" | tail -1

    echo
    echo "SHORTAUTO PRO:"
    echo

    du -sh "$BASE" 2>/dev/null

    echo
    echo "VÍDEOS:"
    echo

    find "$BASE/videos" \
        -maxdepth 1 \
        -type f \
        -name '*.mp4' \
        2>/dev/null \
        | wc -l

    echo
    echo "ASSUNTOS NO HISTÓRICO:"
    echo

    python - <<'PY'
import json
from pathlib import Path

p = Path.home() / "ShortAutoPro" / "historico_assuntos.json"

try:
    d = json.loads(
        p.read_text(
            encoding="utf-8"
        )
    )
    print(len(d))
except Exception:
    print(0)
PY
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
    echo "0) Sair"
    echo

    read -r -p "Escolha: " OPCAO

    case "$OPCAO" in

        1)
            cabecalho
            gerar_um
            pausa
            ;;

        2)
            cabecalho
            gerar_lote
            pausa
            ;;

        3)
            cabecalho
            retomar_lote
            pausa
            ;;

        4)
            cabecalho
            "$BASE/batch_recovery.sh" --status
            pausa
            ;;

        5)
            cabecalho
            ver_historico
            pausa
            ;;

        6)
            cabecalho
            ver_manifests
            pausa
            ;;

        7)
            cabecalho
            mostrar_publish
            pausa
            ;;

        8)
            cabecalho
            ultimo_video
            pausa
            ;;

        9)
            cabecalho
            "$BASE/health_check.sh"
            pausa
            ;;

        10)
            cabecalho
            storage_guard
            pausa
            ;;

        11)
            cabecalho
            status_sistema
            pausa
            ;;

        12)
            cabecalho

            read -r -p \
            "Apagar estado do lote salvo? [s/N]: " \
            RESPOSTA

            case "$RESPOSTA" in
                s|S|sim|SIM|Sim)
                    "$BASE/batch_recovery.sh" --reset
                    ;;
                *)
                    echo "Cancelado."
                    ;;
            esac

            pausa
            ;;

        13)
            cabecalho
            "$BASE/preflight_check.sh"
            pausa
            ;;

        14)
            cabecalho

            read -r -p             "Quantas últimas produções analisar? [1-10]: "             QTD_REPORT

            if [[ "$QTD_REPORT" =~ ^[0-9]+$ ]]; then
                python "$BASE/batch_report.py" "$QTD_REPORT"
            else
                echo "Quantidade inválida."
            fi

            pausa
            ;;

        15)
            cabecalho
            "$BASE/diagnostico.sh"
            pausa
            ;;

        16)
            cabecalho
            echo "Sincronizando ShortAutoPro com GitHub..."
            echo
            sap-iniciar
            pausa
            ;;

        17)
            cabecalho
            echo "Salvando alterações do ShortAutoPro..."
            echo
            sap-salvar
            pausa
            ;;

        18)
            cabecalho
            echo "========================================"
            echo " STATUS DO GIT"
            echo "========================================"
            echo
            git -C "$BASE" status
            echo
            pausa
            ;;

        19)
            cabecalho
            echo "========================================"
            echo " ÚLTIMOS COMMITS"
            echo "========================================"
            echo
            git -C "$BASE" --no-pager log                 --oneline                 --decorate                 -10
            echo
            pausa
            ;;

        20)
            cabecalho
            echo "========================================"
            echo " STATUS DA SINCRONIZAÇÃO"
            echo "========================================"
            echo

            cd "$BASE" || {
                echo "ERRO: projeto não encontrado."
                pausa
                continue
            }

            echo "Branch:"
            git branch --show-current
            echo

            echo "Commit local:"
            git --no-pager log -1 --oneline
            echo

            echo "Consultando GitHub..."
            if git fetch origin; then
                echo

                ATRAS_LOCAL="$(git rev-list --count HEAD..origin/main 2>/dev/null || echo 0)"
                ATRAS_REMOTO="$(git rev-list --count origin/main..HEAD 2>/dev/null || echo 0)"

                echo "Commits existentes no GitHub e ausentes no celular: $ATRAS_LOCAL"
                echo "Commits existentes no celular e ausentes no GitHub: $ATRAS_REMOTO"
                echo

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
                echo
                echo "Não foi possível consultar o GitHub."
            fi

            echo
            echo "Arquivos locais:"
            git status --short
            echo
            pausa
            ;;

        0)
            clear
            echo "ShortAutoPro encerrado."
            exit 0
            ;;

        *)
            echo
            echo "Opção inválida."
            sleep 1
            ;;

    esac

done
