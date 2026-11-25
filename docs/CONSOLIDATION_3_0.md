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


## Shorts com clipes locais gerados (integração em validação)

O pipeline canônico de Shorts aceita opcionalmente um manifesto da fila local:
um clipe vertical 9:16 para cada cena do mapa de cenas. A aquisição continua
sob responsabilidade do Media Engine V2; os clipes são copiados para o workspace
normal, revalidados pelo Media Validator e passam pela verificação visual de
quadros (MUST/AVOID/intenção da cena). Se a verificação visual bloquear um clipe,
a produção falha de forma explícita e não o substitui silenciosamente.

Uso pelo entrypoint oficial:

```bash
python main.py run --generated-clips-manifest "$HOME/.shortautopro/projects/PROJECT_ID/generated_manifest.json"
```

A retomada pelo comando oficial recupera o manifesto salvo no estado da produção.
O projeto local precisa ter exatamente um clipe por cena e um prompt específico
por clipe; o manifesto deve ser do tipo `shorts`, proporção 9:16 e conter uma
timeline completa. Sem o argumento, o fluxo de aquisição convencional permanece
inalterado.

Os clipes gerados continuam passando pelo Render Engine V2, timeline, áudio,
legendas, QA e Release Gate existentes. Esta integração não cria renderer novo.
A validação visual de quadros é independente do prompt registrado; prompt sozinho
não é aceito como prova de que o clipe atende à cena.


### Geração automática local (sem manifesto prévio)

Se o backend/modelo de vídeo já estiver instalado no Termux e existir um arquivo
de configuração compatível com o worker local, o próprio pipeline pode montar
um prompt por cena, criar/retomar a fila, gerar os clipes, exportar o manifesto
e continuar pelo Media Engine V2:

```bash
python main.py run --local-ai-backend-config "$HOME/ShortAutoPro/config/local_video_backend.json"
```

O arquivo de configuração deve apontar para um executável e modelo realmente
instalados no aparelho, com um `command_template` de argumentos sem shell.
A integração limita Shorts a até 20 cenas e até 180 segundos de clipes agendados.
O worker é retomável e a configuração fica registrada no estado da produção.
Se a fila falhar ou algum clipe não passar pelo FFprobe/verificação visual,
o pipeline interrompe a etapa de mídia; não troca silenciosamente para imagens
de terceiros. A aquisição convencional continua disponível quando nenhuma
das duas opções de mídia gerada é informada.


Exemplo estrutural de configuração (substitua executável e argumentos pelos
aceitos pelo gerador que realmente estiver instalado):

```json
{
  "executable": "/caminho/absoluto/do/gerador-local",
  "command_template": [
    "--prompt", "{prompt}",
    "--output", "{output}",
    "--width", "{width}",
    "--height", "{height}",
    "--frames", "{frames}",
    "--seed", "{seed}",
    "--model", "{model}"
  ],
  "timeout_seconds": 1800,
  "fps": 12,
  "seed": 1,
  "model": "modelo-local",
  "ffprobe": "ffprobe"
}
```

O worker passa cada item como argumento separado a `subprocess`, sem shell.
O exemplo é apenas um contrato de configuração: não instala nem representa
um gerador embutido no ShortAutoPro.
