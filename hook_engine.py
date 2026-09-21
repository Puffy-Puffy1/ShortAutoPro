#!/usr/bin/env python3

import os
import sys
import re
import json
import time
import shutil
from datetime import date

from gemini_runtime import generate_text


BASE = os.path.abspath(os.path.expanduser(os.getenv("SHORTAUTOPRO_BASE", "~/ShortAutoPro")))

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

ROTEIRO = os.path.join(
    BASE,
    "roteiros",
    f"short_{SHORT_ID}.txt"
)

FONTE = os.path.join(
    BASE,
    "roteiros",
    f"fonte_{SHORT_ID}.txt"
)

HOOK_JSON = os.path.join(
    BASE,
    "roteiros",
    f"hook_{SHORT_ID}.json"
)

HOOK_TXT = os.path.join(
    BASE,
    "roteiros",
    f"hook_{SHORT_ID}.txt"
)

BACKUP = os.path.join(
    BASE,
    "roteiros",
    f"short_{SHORT_ID}_pre_hook.txt"
)

API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite"
)

try:
    HOOK_MIN_SCORE = float(
        os.getenv(
            "SHORT_HOOK_MIN_SCORE",
            "72"
        )
    )
except ValueError:
    HOOK_MIN_SCORE = 72.0

HOOK_MIN_SCORE = max(
    50.0,
    min(HOOK_MIN_SCORE, 95.0)
)


if not os.path.exists(ROTEIRO):
    sys.exit(
        f"ERRO: roteiro não encontrado:\n{ROTEIRO}"
    )

if not os.path.exists(FONTE):
    sys.exit(
        f"ERRO: fonte factual não encontrada:\n{FONTE}"
    )


with open(
    ROTEIRO,
    "r",
    encoding="utf-8"
) as f:
    roteiro_original = f.read().strip()


with open(
    FONTE,
    "r",
    encoding="utf-8"
) as f:
    fonte = f.read().strip()


if not roteiro_original:
    sys.exit(
        "ERRO: roteiro vazio."
    )

if not fonte:
    sys.exit(
        "ERRO: fonte factual vazia."
    )


def contar_palavras(texto):

    return len(
        re.findall(
            r"\b[\wÀ-ÿ'-]+\b",
            texto,
            flags=re.UNICODE
        )
    )


def limpar(texto):

    return (
        texto
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )



def atomic_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(str(text))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def atomic_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


# =========================================
# BACKUP
# =========================================

shutil.copy2(
    ROTEIRO,
    BACKUP
)


# =========================================
# GEMINI
# =========================================

def chamar_gemini(prompt):
    return generate_text(
        prompt,
        temperature=0.55,
        max_output_tokens=1800,
        component="Hook Engine",
        api_key=API_KEY,
    )


# =========================================
# PROMPT
# =========================================

prompt = f"""
Você é especialista em retenção de YouTube Shorts
e também um revisor factual rigoroso.

Existe um roteiro factual já aprovado.

ROTEIRO ORIGINAL:

========================
{roteiro_original}
========================

FONTE FACTUAL:

========================
{fonte[:16000]}
========================

Sua tarefa é melhorar SOMENTE o gancho inicial
sem inventar nenhuma informação.

Crie 3 opções de gancho.

Cada gancho:

- precisa ser factual;
- precisa ser sustentado pela fonte;
- deve ter aproximadamente 8 a 18 palavras;
- precisa gerar curiosidade imediatamente;
- não deve usar clickbait falso;
- não pode revelar tudo;
- não pode inventar número, data, pessoa ou fato;
- deve soar natural em português do Brasil;
- deve funcionar nos primeiros 2 a 3 segundos
  de um YouTube Short.

Depois escolha o melhor dos três.

Em seguida produza uma versão FINAL do roteiro:

- use o gancho escolhido na abertura;
- preserve os fatos do roteiro original;
- preserve o sentido geral;
- não acrescente fatos novos;
- mantenha entre 105 e 125 palavras REAIS;
- mantenha CTA curto;
- mantenha ritmo rápido;
- não use títulos;
- não use markdown.

Avalie os 3 ganchos com notas de 0 a 10 para:

- curiosity
- clarity
- factuality
- retention

RESPONDA SOMENTE EM JSON VÁLIDO:

{{
  "hooks": [
    {{
      "text": "gancho",
      "curiosity": 0,
      "clarity": 0,
      "factuality": 0,
      "retention": 0
    }},
    {{
      "text": "gancho",
      "curiosity": 0,
      "clarity": 0,
      "factuality": 0,
      "retention": 0
    }},
    {{
      "text": "gancho",
      "curiosity": 0,
      "clarity": 0,
      "factuality": 0,
      "retention": 0
    }}
  ],
  "chosen": 1,
  "final_script": "roteiro final completo"
}}

chosen precisa ser 1, 2 ou 3.

Não escreva absolutamente nada fora do JSON.
"""


print()
print("================================")
print("HOOK ENGINE - STABLE 1.2")
print("================================")
print()

print(
    f"ID: {SHORT_ID}"
)

print(
    f"Roteiro original: "
    f"{contar_palavras(roteiro_original)} palavras"
)

print()


# =========================================
# GERAR
# =========================================

try:

    bruto = chamar_gemini(
        prompt
    )

except Exception as e:

    print(
        f"AVISO: Hook Engine falhou: {e}"
    )

    print(
        "Mantendo roteiro original."
    )

    sys.exit(0)


bruto = limpar(
    bruto
)


try:

    dados = json.loads(
        bruto
    )

except Exception:

    print(
        "AVISO: JSON do Hook Engine inválido."
    )

    print(
        "Mantendo roteiro original."
    )

    sys.exit(0)


hooks = dados.get(
    "hooks",
    []
)

chosen = dados.get(
    "chosen"
)

roteiro_final = str(
    dados.get(
        "final_script",
        ""
    )
).strip()



# =========================================
# RETENTION SCORE 2.3.3
# =========================================

def retention_score_hook(texto):

    texto = str(texto).strip()

    palavras = texto.split()
    qtd = len(palavras)

    score = 50.0

    lower = texto.lower()


    # -----------------------------
    # TAMANHO
    # -----------------------------

    if 7 <= qtd <= 14:
        score += 18

    elif 15 <= qtd <= 18:
        score += 10

    elif qtd > 22:
        score -= 15

    elif qtd < 5:
        score -= 10


    # -----------------------------
    # GATILHOS DE CURIOSIDADE
    # -----------------------------

    fortes = [
        "mas",
        "ninguém",
        "ninguem",
        "nunca",
        "desapareceu",
        "sumiu",
        "encontraram",
        "encontrado",
        "mistério",
        "misterio",
        "segredo",
        "último",
        "ultimo",
        "corpo",
        "prova",
        "verdade",
        "como",
        "por que",
        "o que aconteceu"
    ]

    for termo in fortes:

        if termo in lower:
            score += 4


    # -----------------------------
    # ABERTURAS FRACAS
    # -----------------------------

    fracas = [
        "hoje vamos",
        "neste vídeo",
        "nesse vídeo",
        "você sabia que",
        "voce sabia que",
        "vamos falar",
        "essa é a história",
        "essa e a historia"
    ]

    for termo in fracas:

        if lower.startswith(
            termo
        ):
            score -= 25


    # -----------------------------
    # PONTUAÇÃO
    # -----------------------------

    if "?" in texto:
        score += 6

    if "!" in texto:
        score += 2


    return max(
        0.0,
        min(
            score,
            100.0
        )
    )

# =========================================
# VALIDAR
# =========================================

if len(hooks) != 3:

    print(
        "AVISO: não foram gerados 3 hooks."
    )

    print(
        "Mantendo roteiro original."
    )

    sys.exit(0)


try:
    chosen = int(
        chosen
    )
except Exception:
    chosen = 0


if chosen not in [
    1,
    2,
    3
]:

    print(
        "AVISO: hook escolhido inválido."
    )

    print(
        "Mantendo roteiro original."
    )

    sys.exit(0)


qtd_final = contar_palavras(
    roteiro_final
)


if not (
    105 <= qtd_final <= 125
):

    print(
        f"AVISO: roteiro final ficou "
        f"com {qtd_final} palavras."
    )

    print(
        "Mantendo roteiro original."
    )

    sys.exit(0)


# Recalcula o melhor hook com score local.

melhor_indice = None
melhor_score = -1.0

for indice, hook in enumerate(
    hooks
):

    texto_hook = str(
        hook.get(
            "text",
            ""
        )
    ).strip()

    local_score = retention_score_hook(
        texto_hook
    )

    hook[
        "local_retention_score"
    ] = round(
        local_score,
        1
    )

    # combina score local com as notas Gemini

    try:

        gemini_retention = float(
            hook.get(
                "retention",
                0
            )
        )

        gemini_curiosity = float(
            hook.get(
                "curiosity",
                0
            )
        )

        gemini_clarity = float(
            hook.get(
                "clarity",
                0
            )
        )

    except Exception:

        gemini_retention = 0
        gemini_curiosity = 0
        gemini_clarity = 0


    combinado = (
        local_score * 0.60
        + gemini_retention * 2.0
        + gemini_curiosity * 1.5
        + gemini_clarity * 0.5
    )


    hook[
        "combined_score"
    ] = round(
        combinado,
        1
    )


    if combinado > melhor_score:

        melhor_score = combinado
        melhor_indice = indice


if melhor_indice is not None:

    chosen = melhor_indice + 1


# =========================================
# HOOK QUALITY GATE 2.3.4
# =========================================

if melhor_score < HOOK_MIN_SCORE:

    print()
    print("================================")
    print("HOOK QUALITY GATE")
    print("================================")
    print()

    print(
        f"Melhor score: {melhor_score:.1f}"
    )

    print(
        f"Mínimo exigido: {HOOK_MIN_SCORE:.1f}"
    )

    print(
        "Hooks abaixo do padrão."
    )

    print(
        "Mantendo roteiro original "
        "em vez de forçar hook fraco."
    )

    sys.exit(0)


print()
print(
    f"HOOK QUALITY: PASS "
    f"({melhor_score:.1f}/"
    f"{HOOK_MIN_SCORE:.1f})"
)


hook_escolhido = str(
    hooks[
        chosen - 1
    ].get(
        "text",
        ""
    )
).strip()


if not hook_escolhido:

    print(
        "AVISO: hook escolhido vazio."
    )

    print(
        "Mantendo roteiro original."
    )

    sys.exit(0)


# =========================================
# SALVAR
# =========================================

atomic_text(ROTEIRO, roteiro_final)
atomic_text(HOOK_TXT, hook_escolhido)
atomic_json(HOOK_JSON, dados)


# =========================================
# RESULTADO
# =========================================

print()
print("3 HOOKS GERADOS:")
print()


for numero, hook in enumerate(
    hooks,
    1
):

    texto = str(
        hook.get(
            "text",
            ""
        )
    )

    curiosity = hook.get(
        "curiosity",
        "?"
    )

    clarity = hook.get(
        "clarity",
        "?"
    )

    factuality = hook.get(
        "factuality",
        "?"
    )

    retention = hook.get(
        "retention",
        "?"
    )

    marcador = (
        " <-- ESCOLHIDO"
        if numero == chosen
        else ""
    )

    print(
        f"{numero}. {texto}{marcador}"
    )

    local_score = hook.get(
        "local_retention_score",
        "?"
    )

    combined_score = hook.get(
        "combined_score",
        "?"
    )

    print(
        f"   curiosity={curiosity} "
        f"clarity={clarity} "
        f"factuality={factuality} "
        f"retention={retention} "
        f"local={local_score} "
        f"combined={combined_score}"
    )


print()
print(
    f"Hook escolhido:\n"
    f"{hook_escolhido}"
)

print()

print(
    f"Roteiro final: "
    f"{qtd_final} palavras"
)

print()

print(
    "HOOK ENGINE: OK"
)

print()
