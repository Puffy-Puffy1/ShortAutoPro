# ShortAutoPro Consolidation 3.0

## Objetivo

A Consolidation 3.0 estabelece um único pipeline oficial de Shorts. A entrada canônica é `main.py` e o fluxo de produção é:

`tema -> roteiro -> cenas -> mídia -> áudio -> legenda -> edição -> QA -> exportação`

Módulos especializados são estágios do mesmo pipeline; não existem pipelines Standard/Professional concorrentes.

## Entrada e recuperação

- `main.py run`: produção oficial de Shorts (pipeline canônico).
- `main.py longform run --topic "assunto" --minutes 15`: produção de vídeo longo pelo runtime Long-form existente.
- `main.py longform resume --run-id ID`: retoma um vídeo longo salvo.
- `main.py longform status --run-id ID`: consulta o estado de um vídeo longo.
- O comando unificado carrega primeiro a configuração privada do Termux e só então inicia o runtime longo, garantindo que as variáveis de ambiente estejam disponíveis no processo.
- IDs de execução long-form são validados antes de qualquer acesso ao diretório de projetos.

- `main.py resume`: retomada segura por checkpoints validados.
- `main.py audit`: auditoria estrutural do repositório.
- `main.py storage`: preflight/status/limpeza de armazenamento.
- `profile_run.sh`: aplica o perfil e delega para `main.py`.
- `resume_short_runtime.py`: retoma somente o pipeline `PROFESSIONAL_CANONICAL`. Produções antigas sem os artefatos 3.0 voltam ao início com o mesmo `SHORT_ID` em vez de misturar arquiteturas.

## Limitações atuais do Long-form V1

O runtime Long-form gera roteiro factual com `GEMINI_API_KEY`, narração com Piper e finaliza MP4 H.264/AAC. A geração visual local por clipes é opcional e depende do worker/modelo realmente instalado no aparelho; isso não torna o roteiro/TTS totalmente offline. A validação de uma produção real no Termux continua obrigatória.

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


## Long-form com clipes locais gerados (integração em validação)

O Long-form pode consumir, opcionalmente, um manifesto `generated_manifest.json`
exportado pela fila local de geração de clipes. A integração valida a assinatura
SHA-256 do manifesto, o workspace, a sequência temporal, os checksums e os
metadados FFprobe antes de usar qualquer arquivo.

Exemplo pelo entrypoint oficial:

```bash
python main.py longform run --topic "Tema factual" --minutes 15 --chapters 6 \
  --generated-manifest "$HOME/.shortautopro/projects/PROJECT_ID/generated_manifest.json"
```

Para gerar automaticamente os clipes pela fila local compartilhada, use:

```bash
python main.py longform run --topic "Tema factual" --minutes 15 --chapters 6 \
  --local-ai-backend-config "$HOME/ShortAutoPro/config/local_video_backend.json"
```

O runtime cria um projeto idempotente, usa a fila/worker/exportador da PR #160,
gera prompts de vídeo por trecho de capítulo e retoma o mesmo projeto quando
a execução é interrompida. A configuração e seu SHA-256 ficam registrados no
estado; uma alteração do arquivo bloqueia a retomada. O manifesto continua
sendo validado antes de entrar na timeline.

`--generated-manifest` permanece disponível para quem já possui um manifesto.
As duas opções são mutuamente exclusivas. Sem nenhuma delas, o fluxo Wikimedia
Commons/Ken Burns continua como fallback. O renderizador final, áudio e legendas
continuam compartilhados.

A integração automática requer que o worker da PR #160 esteja presente no checkout
e um executável/modelo local real configurado. O runtime Long-form permanece
limitado a 5–60 minutos e usa Gemini para roteiro e Piper para narração. Os clipes
locais são gerados em 640x360 e normalizados pelo render existente para 1920x1080.
CI e clipes sintéticos não comprovam inferência real; uma produção MP4 no Termux
com FFprobe continua obrigatória antes de declarar o recurso concluído.
