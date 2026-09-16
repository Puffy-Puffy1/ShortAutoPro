# ShortAutoPro Consolidation 3.0

## Objetivo

A Consolidation 3.0 estabelece um único pipeline oficial de Shorts. A entrada canônica é `main.py` e o fluxo de produção é:

`tema -> roteiro -> cenas -> mídia -> áudio -> legenda -> edição -> QA -> exportação`

Módulos especializados são estágios do mesmo pipeline; não existem pipelines Standard/Professional concorrentes.

## Entrada e recuperação

- `main.py run`: produção oficial.
- `main.py resume`: retomada segura por checkpoints validados.
- `main.py audit`: auditoria estrutural do repositório.
- `main.py storage`: preflight/status/limpeza de armazenamento.
- `profile_run.sh`: aplica o perfil e delega para `main.py`.
- `resume_short_runtime.py`: retoma somente o pipeline `PROFESSIONAL_CANONICAL`. Produções antigas sem os artefatos 3.0 voltam ao início com o mesmo `SHORT_ID` em vez de misturar arquiteturas.

## Estágios de qualidade

A produção integra sourcing factual, roteiro, Visual Director, continuidade visual, seleção de mídia, score visual multidimensional, motion/rhythm, edição Professional, múltiplos assets, Retention Engine, Sound Design, Speech Director, Piper, Whisper, captions Professional, safe-zone guard, assembler multi-beat, render Professional, masterização pós-AAC, Visual QA, gates técnicos/editoriais e Release Gate.

## Release Gate

O Release Gate consolida os scores de roteiro, mídia, visual, áudio, legenda, retenção e qualidade técnica. O pipeline permite um ciclo limitado de auto-reparo antes de bloquear uma produção que continue abaixo do nível exigido.

## Resiliência

- ID forte por geração.
- lock por `short_id`.
- retries limitados por estágio apropriado.
- checkpoints atômicos.
- resume fail-closed.
- fallback de providers/modelos onde suportado.
- storage preflight e cleanup pelo `storage_manager.py`.

## Código legado proibido

A auditoria 3.0 falha se os antigos entrypoints voltarem a ser rastreados, incluindo `gerar_short.sh`, `video.py`, `v6.py`, `v6_runtime.py`, `limpar_storage.sh` e wrappers Professional antigos.

## Validação e promoção

Toda alteração deve passar pela Portable Validation. A promoção para `termux-stable` ocorre somente para o SHA exato validado em `main` e por fast-forward.
