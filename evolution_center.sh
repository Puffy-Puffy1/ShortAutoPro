#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"
CORE="$BASE/shortautopro_evolution.py"

if [ ! -f "$CORE" ]; then
    echo "ERRO: shortautopro_evolution.py não encontrado em $BASE"
    exit 1
fi

pause() {
    echo
    read -r -p "Pressione Enter para voltar..." _ || true
}

header() {
    clear 2>/dev/null || printf '\033c'
    echo "========================================"
    echo " SHORTAUTOPRO - EVOLUTION CENTER 1.2"
    echo "========================================"
    echo
}

latest_state_id() {
    local state
    state="$(find "$BASE/.sap_state" -maxdepth 1 -type f -name '*.json' -print0 2>/dev/null \
        | xargs -0 -r ls -1t 2>/dev/null | head -1)"
    if [ -n "$state" ]; then
        basename "$state" .json
    fi
}

latest_video_id() {
    local video
    video="$(find "$BASE/videos" -maxdepth 1 -type f -name 'short_v6_*.mp4' -print0 2>/dev/null \
        | xargs -0 -r ls -1t 2>/dev/null | head -1)"
    if [ -n "$video" ]; then
        basename "$video" .mp4 | sed 's/^short_v6_//'
    fi
}

run_core() {
    python "$CORE" "$@"
}

quality_latest() {
    local sid
    sid="$(latest_state_id)"
    if [ -z "$sid" ]; then sid="$(latest_video_id)"; fi
    if [ -z "$sid" ]; then
        echo "Nenhuma produção encontrada."
        return 0
    fi
    echo "Short ID: $sid"
    echo
    run_core quality-score --short-id "$sid"
}

resume_plan_latest() {
    if [ ! -f "$BASE/resume_short.sh" ]; then
        echo "ERRO: resume_short.sh não encontrado."
        return 1
    fi
    bash "$BASE/resume_short.sh" --status
}

resume_execute_latest() {
    if [ ! -f "$BASE/resume_short.sh" ]; then
        echo "ERRO: resume_short.sh não encontrado."
        return 1
    fi
    echo "Plano detectado:"
    bash "$BASE/resume_short.sh" --status || return 1
    echo
    local confirm
    read -r -p "Executar retomada segura agora? [s/N]: " confirm || return 0
    case "$confirm" in
        s|S|sim|SIM|Sim) bash "$BASE/resume_short.sh" ;;
        *) echo "Retomada cancelada." ;;
    esac
}

e2e_latest() {
    local sid
    sid="$(latest_video_id)"
    if [ -z "$sid" ]; then
        echo "Nenhum vídeo V6 encontrado."
        return 0
    fi
    echo "Short ID: $sid"
    echo
    run_core e2e --short-id "$sid"
}

longform_wizard() {
    local topic minutes chapters profile confirm
    if [ ! -f "$BASE/longform_runtime.py" ]; then
        echo "ERRO: longform_runtime.py não encontrado."
        return 1
    fi
    read -r -p "Assunto factual do vídeo longo: " topic || return 0
    [ -n "$topic" ] || { echo "Assunto vazio."; return 0; }
    read -r -p "Duração alvo em minutos [15]: " minutes || return 0
    minutes="${minutes:-15}"
    if ! [[ "$minutes" =~ ^[0-9]+$ ]] || [ "$minutes" -lt 5 ] || [ "$minutes" -gt 60 ]; then
        echo "Duração inválida (5-60 minutos)."
        return 0
    fi
    read -r -p "Capítulos [automático]: " chapters || return 0
    if [ -n "$chapters" ] && { ! [[ "$chapters" =~ ^[0-9]+$ ]] || [ "$chapters" -lt 3 ] || [ "$chapters" -gt 12 ]; }; then
        echo "Capítulos inválidos (3-12)."
        return 0
    fi
    echo "Perfis PT-BR disponíveis:"
    run_core profiles
    read -r -p "Perfil [true_crime]: " profile || return 0
    profile="${profile:-true_crime}"
    echo
    echo "Tema: $topic"
    echo "Duração: ${minutes} min"
    echo "Perfil: $profile"
    [ -n "$chapters" ] && echo "Capítulos: $chapters"
    read -r -p "Iniciar produção long-form? [s/N]: " confirm || return 0
    case "$confirm" in
        s|S|sim|SIM|Sim)
            if [ -n "$chapters" ]; then
                python "$BASE/longform_runtime.py" run --topic "$topic" --minutes "$minutes" --chapters "$chapters" --profile "$profile"
            else
                python "$BASE/longform_runtime.py" run --topic "$topic" --minutes "$minutes" --profile "$profile"
            fi
            ;;
        *) echo "Produção cancelada." ;;
    esac
}

longform_resume() {
    if [ ! -f "$BASE/longform_runtime.py" ]; then
        echo "ERRO: longform_runtime.py não encontrado."
        return 1
    fi
    python "$BASE/longform_runtime.py" status || true
    echo
    local confirm
    read -r -p "Retomar o long-form mais recente? [s/N]: " confirm || return 0
    case "$confirm" in
        s|S|sim|SIM|Sim) python "$BASE/longform_runtime.py" resume ;;
        *) echo "Retomada cancelada." ;;
    esac
}

profiled_short_wizard() {
    local profile mode value
    echo "Perfis disponíveis:"
    python "$BASE/profile_runtime.py" --profile default --json >/dev/null 2>&1 || {
        echo "ERRO: profile_runtime.py indisponível."
        return 1
    }
    run_core profiles
    echo
    read -r -p "Perfil [default]: " profile || return 0
    profile="${profile:-default}"
    echo "1) Tema amplo (sistema escolhe o caso)"
    echo "2) Assunto exato verificado"
    read -r -p "Modo [1]: " mode || return 0
    mode="${mode:-1}"
    if [ "$mode" = "2" ]; then
        read -r -p "Assunto exato: " value || return 0
        [ -n "$value" ] || { echo "Assunto vazio."; return 0; }
        SHORT_TOPIC_EXACT="$value" SAP_CHANNEL_PROFILE="$profile" bash "$BASE/profile_run.sh" "$profile"
    else
        read -r -p "Tema amplo [manter perfil/config atual]: " value || return 0
        if [ -n "$value" ]; then
            SHORT_TEMA="$value" SAP_CHANNEL_PROFILE="$profile" bash "$BASE/profile_run.sh" "$profile"
        else
            SAP_CHANNEL_PROFILE="$profile" bash "$BASE/profile_run.sh" "$profile"
        fi
    fi
}

client_wizard() {
    local client topic qty profile mode
    read -r -p "Nome/identificador do cliente: " client || return 0
    read -r -p "Tema ou assunto: " topic || return 0
    read -r -p "Quantidade [1]: " qty || return 0
    qty="${qty:-1}"
    read -r -p "Perfil [default]: " profile || return 0
    profile="${profile:-default}"
    echo "1) Tema amplo"
    echo "2) Assunto exato verificado"
    read -r -p "Modo [1]: " mode || return 0
    mode="${mode:-1}"
    if ! [[ "$qty" =~ ^[0-9]+$ ]] || [ "$qty" -lt 1 ] || [ "$qty" -gt 100 ]; then
        echo "Quantidade inválida (1-100)."
        return 0
    fi
    local topic_mode="theme"
    [ "$mode" = "2" ] && topic_mode="exact"
    python "$BASE/client_job_create.py" \
        --client "$client" \
        --topic "$topic" \
        --quantity "$qty" \
        --language "pt-BR" \
        --profile "$profile" \
        --topic-mode "$topic_mode"
}

run_latest_client_job() {
    if [ ! -f "$BASE/client_job_runner.py" ]; then
        echo "ERRO: client_job_runner.py não encontrado."
        return 1
    fi
    echo "Simulação do job mais recente:"
    echo
    python "$BASE/client_job_runner.py" || return 1
    echo
    local confirm
    read -r -p "Executar produção real desse job? [s/N]: " confirm || return 0
    case "$confirm" in
        s|S|sim|SIM|Sim) python "$BASE/client_job_runner.py" --execute ;;
        *) echo "Execução real cancelada." ;;
    esac
}

while true; do
    header
    echo "1) Dashboard geral"
    echo "2) Métricas de produção"
    echo "3) Mapa de consolidação do projeto"
    echo "4) Plano de recuperação da última produção"
    echo "5) Score de qualidade da última produção"
    echo "6) Perfis de canal PT-BR"
    echo "7) E2E do último vídeo"
    echo "8) Gerar vídeo longo"
    echo "9) Criar job para cliente"
    echo "10) Gerar Short com perfil / assunto exato"
    echo "11) Executar ou retomar último job de cliente"
    echo "12) Retomar Short interrompido com checkpoint seguro"
    echo "13) Retomar último vídeo longo"
    echo "0) Voltar"
    echo
    read -r -p "Escolha: " option || exit 0

    case "$option" in
        1) header; run_core dashboard || true; pause ;;
        2) header; run_core metrics || true; pause ;;
        3) header; run_core inventory || true; pause ;;
        4) header; resume_plan_latest || true; pause ;;
        5) header; quality_latest || true; pause ;;
        6) header; run_core profiles || true; pause ;;
        7) header; e2e_latest || true; pause ;;
        8) header; longform_wizard || true; pause ;;
        9) header; client_wizard || true; pause ;;
        10) header; profiled_short_wizard || true; pause ;;
        11) header; run_latest_client_job || true; pause ;;
        12) header; resume_execute_latest || true; pause ;;
        13) header; longform_resume || true; pause ;;
        0) exit 0 ;;
        *) echo "Opção inválida."; sleep 1 ;;
    esac
done
