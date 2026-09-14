# ShortAutoPro Evolution System 1.0

Esta camada evolui o ShortAutoPro sem substituir os motores que já funcionam.
Ela é **stdlib-only**, gratuita, compatível com Termux/Windows e foi desenhada
para trabalhar ao lado do pipeline V6.

## Objetivos

1. Mapear o repositório antes de remover legado.
2. Registrar checkpoint e duração de cada etapa.
3. Medir qualidade visual, legendas, áudio, render e editorial.
4. Gerar um score central de 0–100 com recomendações de correção.
5. Dar visibilidade de métricas e falhas no celular.
6. Criar fundações para perfis de canal, vídeo longo e serviço para clientes.

## Fluxo integrado

`gerar_short.sh` agora registra cada estágio no diretório local `.sap_state/`.
Após o Production Supervisor roda o Visual Audit. Depois do Whisper roda o
Caption Audit. Depois do render V6 roda o E2E. Após os gates existentes roda o
Evolution Quality Score.

O score central usa os seguintes pesos:

- Visual: 35%
- Legendas: 15%
- Áudio: 15%
- Técnico: 20%
- Editorial: 15%

O limite padrão é 80/100. Nesta primeira implantação o score trabalha em
**observação**. Os gates atuais continuam bloqueantes. Para tornar o novo score
bloqueante depois de calibrar com vídeos reais:

```bash
export SAP_EVOLUTION_ENFORCE=1
export SAP_EVOLUTION_MIN_SCORE=80
```

Isso evita rejeitar produções boas por um limite ainda não calibrado.

## Evolution Center

No `control_center.sh`, escolha **21) Abrir Evolution Center**.

O submenu oferece:

- dashboard geral;
- métricas acumuladas;
- mapa de consolidação do projeto;
- estado de recuperação da última produção;
- score da última produção;
- perfis de canal;
- validação E2E do último vídeo;
- planejamento de vídeo longo;
- criação de job para cliente.

Também pode ser aberto diretamente:

```bash
cd ~/ShortAutoPro
bash evolution_center.sh
```

## Inventário e consolidação

```bash
python shortautopro_evolution.py inventory
```

O relatório classifica arquivos como `PRODUCAO`, `DEPENDENCIA`, `TESTE`,
`INFRAESTRUTURA`, `LEGADO_PROVAVEL`, `CONFIG_OU_DOC` ou `NAO_IDENTIFICADO`.
Ele é deliberadamente somente leitura: **não apaga nenhum arquivo**.

O relatório fica em `reports/evolution/inventory.json` e é ignorado pelo Git.

## Checkpoint e recuperação

Cada etapa chamada por `gerar_short.sh` registra `RUNNING`, `PASS` ou `FAIL`,
além do tempo gasto. O estado fica em `.sap_state/<SHORT_ID>.json`.

```bash
python shortautopro_evolution.py resume-plan --short-id <SHORT_ID>
```

A versão 1.0 identifica com precisão o estágio candidato à retomada. Ela **não
pula automaticamente etapas ainda não certificadas como idempotentes**. Essa é
uma trava de segurança: retomar exatamente no meio será ativado por estágio
somente depois dos testes de reexecução, para evitar histórico duplicado,
artefatos inconsistentes ou publicação parcial.

## Visual Audit

```bash
python shortautopro_evolution.py visual-audit --short-id <SHORT_ID>
```

Mede estrutura das 12 cenas, presença de query/must-have, repetição entre cenas,
diversidade visual, cobertura física e status do Production Supervisor.
Quando disponível, incorpora também o `media_quality` existente.

O seletor de mídia atual continua sendo a autoridade de busca. Ele já possui
Semantic Guard, cobertura de MUST, penalidade por repetição, prioridade
Wikimedia/documental e retries relaxados; o Evolution adiciona uma visão
agregada e comparável entre produções.

## Caption Audit

A legenda dinâmica mantém o renderer existente, mas cria um espelho em
`temp/<SHORT_ID>/short_<SHORT_ID>.ass` para auditoria. O auditor mede eventos
longos e excesso de linhas conforme o perfil do canal.

## Áudio

`audio.py` passou a aplicar mastering `loudnorm` na voz Piper antes do mix final.
Valores padrão:

- voz: -14 LUFS;
- true peak: -1.5 dB;
- LRA: 7;
- MP3: 160 kbps / 44.1 kHz mono.

Podem ser ajustados sem editar código:

```bash
export SAP_AUDIO_TARGET_LUFS=-14
export SAP_AUDIO_TRUE_PEAK_DB=-1.5
export SAP_AUDIO_LRA=7
```

O renderer V6 mantém o Broadcast Audio Director já existente, incluindo ducking
automático da música, SFX, compressor, limiter e loudness final.

## E2E

```bash
python shortautopro_evolution.py e2e --short-id <SHORT_ID>
```

Valida vídeo, áudio, resolução vertical e duração via ffprobe. Uma inspeção mais
pesada de black frames pode ser solicitada manualmente:

```bash
python shortautopro_evolution.py e2e --short-id <SHORT_ID> --black-frames
```

## Perfis

`config/channel_profiles.json` contém presets gratuitos para:

- `default`
- `true_crime`
- `cinepulsar`
- `psicotoon`
- `english`

Selecione um perfil com:

```bash
export SAP_CHANNEL_PROFILE=true_crime
```

Os perfis centralizam política de cenas, legenda, áudio, visual e narrativa. A
migração dos motores antigos para consumir todas as chaves será gradual para
não alterar produção silenciosamente.

## Métricas

No fim de cada produção é gravado um evento local em
`metrics/production.jsonl` com status, tempo, quantidade de estágios e score.

```bash
python shortautopro_evolution.py metrics
python shortautopro_evolution.py dashboard
```

Os arquivos de runtime são ignorados pelo Git.

## Long-form

A fundação de long-form cria capítulos com continuidade global e checkpoint por
capítulo:

```bash
python shortautopro_evolution.py longform-plan \
  --topic "Tema" --minutes 15
```

Ela ainda não transforma automaticamente o pipeline de Shorts em um render de
15 minutos. O planejamento existe para que o futuro motor longo use capítulos,
memória de entidades, continuidade e retomada, em vez de simplesmente esticar
um Short.

## Serviço para clientes

```bash
python shortautopro_evolution.py client-job \
  --client "Cliente" \
  --topic "Tema" \
  --quantity 3 \
  --language pt-BR \
  --profile default
```

O job prevê entrega de vídeo, título, descrição, hashtags, créditos e relatório
de qualidade. Jobs ficam em `reports/evolution/client_jobs/`.

## Princípio de segurança

A camada Evolution não ganha permissão de escrita no runner Windows. O modelo
continua sendo: código entra pelo GitHub, o PC valida com permissões de leitura,
e somente commits aprovados pelo fluxo existente podem chegar à branch estável
do Termux.
