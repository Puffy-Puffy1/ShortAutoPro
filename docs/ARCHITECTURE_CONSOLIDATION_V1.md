# ShortAutoPro — Contrato de Arquitetura e Consolidação

**Status:** contrato de integração incremental para a branch de correção; não é autorização para apagar módulos legados ou reescrever o produto inteiro.  
**Objetivo operacional:** um único caminho de produção, com módulos de responsabilidade única, interfaces explícitas, estado isolado por Short e falhas observáveis.  
**Regra de segurança:** preservar os gates de evidência, a validação de mídia, os checkpoints e a qualidade visual. Não transformar uma falha em sucesso artificial.

## 1. Caminho canônico único

`CLI / usuário` → `main.py` → `Pipeline` → etapas de roteiro e direção → `media_engine_v2.py` → manifesto de mídia validado e congelado → etapas de áudio/legenda/edição → QA → exportação → validação final com FFprobe.

- `main.py` é o orquestrador e o único entrypoint de produção suportado.
- `profile_runtime.py` resolve o perfil em variáveis allow-listed; não executa etapas nem modifica arquivos de produção.
- Cada etapa executa por subprocesso com timeout, checkpoint e código de saída explícito.
- Nenhuma etapa deve chamar `main.py` de volta, iniciar um pipeline alternativo ou executar etapas posteriores por conta própria.
- Recovery deve retomar/reparar checkpoints desse mesmo pipeline; não pode trocar silenciosamente para um renderer/assembler legado.
- A prova de sucesso é um MP4 novo do Short ID atual, com áudio e vídeo válidos, aprovado por FFprobe. Log “ETAPA OK” isolado não prova produção concluída.

## 2. Limites de responsabilidade

| Módulo | Responsabilidade única | Não deve fazer |
|---|---|---|
| `main.py` | Ordem das etapas, timeouts, lock por Short ID, checkpoints e estado global | Baixar mídia diretamente, validar semanticamente imagens ou renderizar dentro do orquestrador |
| `profile_runtime.py` | Validar perfil e produzir configuração de runtime allow-listed | Ler segredos, iniciar produção ou sobrescrever configuração persistente |
| `scene_director.py` e diretores | Criar intenção visual por cena: query, MUST/AVOID e contexto | Fazer download, alterar o gate de evidência ou marcar asset como validado |
| `media_engine_v2.py` | Coordenar aquisição por cena, validar requisitos, gerar manifesto imutável e sidecars | Renderizar, codificar vídeo final, inventar placeholders ou relaxar MUST automaticamente |
| `media_provider_v2.py` | Fachada estável entre engine e router | Implementar cliente de cada fornecedor ou importar controlador legado |
| `media_provider_router_v2.py` | Adaptadores dos fornecedores, busca, download e proveniência | Decidir se uma cena é semanticamente correta ou ignorar validação |
| `media_validator_v2.py` | Validar bytes, assinatura, streams, dimensões, duração e checksum | Buscar assets, pontuar cenas ou criar fallback |
| `media_must_verifier.py` | Verificar MUST contra evidência descritiva real do asset | Contar a query de busca como evidência do asset |
| `media_external_resilience.py` | Circuit breaker por fornecedor e quarentena de asset | Decidir relevância semântica ou fazer o pipeline inteiro falhar por uma única consulta vazia |
| etapas de áudio/legendas/render | Consumir artefatos validados e produzir seus próprios outputs | Rebaixar a validação de mídia ou editar o manifesto congelado |
| QA/exportação | Verificar o artefato final e publicar o resultado | Declarar sucesso sem arquivo novo, áudio/vídeo e probe aprovados |

## 3. Contratos de dados entre etapas

### Entrada visual por cena
Cada cena deve ter um registro explícito com `short_id`, `scene_id`, `query`, `must_have[]`, `avoid[]` e contexto editorial. IDs devem ser únicos e validados antes da aquisição.

### Candidato de fornecedor
Um candidato deve manter proveniência (`provider`, `asset_id`, `url`), descrição real do asset, tipo de mídia, score, contagem de MUST/AVOID e classe da evidência. Metadados ausentes significam “não comprovado”, não “comprovado”.

### Asset validado
Um asset só pode ser consumido por etapas posteriores depois de:
1. download concluído;
2. extensão/assinatura compatíveis;
3. validação de imagem ou FFprobe bem-sucedida;
4. checksum calculado;
5. MUST/AVOID aprovados;
6. sidecar escrito atomicamente com `short_id`, número de cena, checksum, proveniência e resultado da validação.

### Manifesto congelado
O manifesto é a fonte de verdade para as etapas posteriores. Depois de congelado, etapas downstream não devem alterá-lo em lugar; uma correção cria uma nova revisão explícita e revalida integridade/checksum.

## 4. Regras de isolamento e concorrência

- Todo arquivo temporário, manifesto, sidecar, log e saída pertence a um `SHORT_ID` explícito.
- Locks são por produção; uma segunda execução com o mesmo ID deve falhar claramente. IDs diferentes não devem compartilhar arquivos intermediários.
- Escritas de JSON devem usar arquivo temporário no mesmo diretório + flush/fsync + replace atômico.
- Não compartilhar caches mutáveis entre processos sem TTL/limite e chaves completas. Cache de busca é otimização, nunca prova de validade.
- Um módulo não deve alterar variáveis de ambiente globais depois que uma etapa consumidora já começou.
- Configuração de usuário e segredos não devem ser gravados em logs, manifests, artefatos ou commits.

## 5. Política uniforme de falhas

1. **Erro transitório de rede / HTTP 429 / 5xx:** retry limitado, respeitando `Retry-After` e deadline total.
2. **Erro permanente do asset (404, assinatura inválida, mídia corrompida):** rejeitar/quarentenar só aquele asset; tentar outro candidato elegível.
3. **Fornecedor indisponível:** abrir circuito com motivo e tempo restantes; continuar para os outros fornecedores independentes.
4. **Busca sem resultados:** resultado vazio daquela consulta, não prova de que o fornecedor está indisponível.
5. **MUST/AVOID não comprovados:** rejeitar candidato e continuar buscando; nunca converter query, nome do arquivo ou tema da cena em evidência.
6. **Nenhum asset válido depois das tentativas limitadas:** falhar com código de erro específico, cena, etapa e resumo seguro; não produzir placeholder e não fingir que a etapa passou.
7. **Erro inesperado:** preservar traceback nos logs de CI protegidos e emitir identificador/código seguro no resumo; nunca capturar tudo e retornar sucesso.

Retries e fallbacks devem ter limites claros de tentativas, tempo e custo. Não deve existir loop infinito nem “recovery” que repita toda a produção sem limite.

## 6. Logs de integração mínimos

Usar eventos estruturados e estáveis, incluindo:
- `SAP_PIPELINE_STAGE`: short_id, etapa, início/fim, status, duração, código de saída;
- `SAP_MEDIA_SEARCH`: fornecedor(es), número de variantes, candidatos, máximo de MUST hits (sem tokens ou URLs);
- `SAP_MEDIA_DOWNLOAD_RETRY`: fornecedor, classe/status, tentativa e atraso;
- `SAP_MEDIA_DOWNLOAD_FAILURE`: fornecedor, classe e código seguro da validação;
- `SAP_MEDIA_PROVIDER_GATE`: fornecedor, motivo e tempo restante;
- `SAP_MEDIA_MANIFEST`: short_id, quantidade de cenas, quantidade validada e checksum;
- `FIRST_VIDEO_FFPROBE`: só PASS após validação real do MP4 novo.

Logs não devem incluir API keys, cabeçalhos de autorização, URLs assinadas, payloads completos de fornecedor ou dados pessoais.

## 7. Regras de dependência

Dependências permitidas são direcionadas para baixo:
- orquestrador → etapas;
- Media Engine → fachada de provider + verificador + validador;
- fachada → router;
- router → adaptadores + resiliência + validador;
- etapas downstream → manifesto congelado e artefatos de áudio/legenda.

Proibido:
- router → `main.py`;
- validator → router/engine;
- diretores → download/estado de fornecedor;
- etapa downstream → mutação retroativa de intenção visual;
- módulos novos e legados disputando o mesmo output sem um contrato explícito;
- “selector V2/V3/V4/V42” experimental ativado em paralelo ao seletor canônico sem teste de compatibilidade.

Módulos legados não devem ser removidos apenas por parecerem duplicados. Primeiro mapear importações, entrypoints, outputs e testes; depois migrar consumidores, executar testes e remover somente em uma alteração isolada com evidência.

## 8. Plano incremental de consolidação

### Fase A — inventário e contratos
- Mapear entrypoints, chamadas subprocess, imports, caminhos de saída, env vars, flags de feature e arquivos compartilhados.
- Registrar cada sistema como ativo, compatibilidade, shadow ou legado.
- Definir owner único por arquivo de saída e por decisão de validação.

### Fase B — prova de contratos
- Testar parsing/validação de input, IDs duplicados, paths traversal, atomic writes, checksum e manifesto congelado.
- Testar circuit breaker, quarentena, retry 429/5xx/timeouts, falha de JSON e fornecedor vazio.
- Testar que query e filename nunca contam como evidência MUST.

### Fase C — integração de mídia
- Rodar busca, download e validação por cena com mocks determinísticos.
- Logar o código exato da validação; rejeitar somente o asset inválido e continuar para o próximo candidato.
- Não enfraquecer MUST/AVOID para fazer a execução “passar”.

### Fase D — pipeline completo
- Rodar o entrypoint canônico do começo ao fim.
- Verificar isolamento de Short ID, checkpoints, falha de etapa, timeout e recuperação limitada.
- Confirmar que áudio/legendas/render usam somente os artefatos da execução atual.

### Fase E — prova real
- Gerar um MP4 novo, confirmar 1080×1920, H.264, AAC, FPS esperado e duração > 0 com FFprobe.
- Guardar manifesto, sidecars, relatório de QA e probe como evidência.
- Só então declarar FIRST_VIDEO concluído.

## 9. Definition of Done

- [ ] Existe um único entrypoint de produção documentado e exercitado.
- [ ] Cada etapa tem input/output, owner, timeout, retry e código de falha explícitos.
- [ ] Não há escrita concorrente entre Shorts distintos ou duplicidade de produção para o mesmo ID.
- [ ] Fornecedor vazio/indisponível não desliga os demais fornecedores.
- [ ] O verificador semântico só usa evidência real do asset.
- [ ] Nenhum fallback inventa mídia nem ignora o validador.
- [ ] Testes unitários e portáteis passam sem desativar verificações.
- [ ] A prova real produz um MP4 novo validado por FFprobe.
- [ ] A branch fica em PR até revisão; não alterar `main` diretamente.

## 10. Estado atual — 23/10/2026

### Branch e validação
- Branch: `fix/first-video-canonical-entrypoint-20261014`.
- Último ajuste operacional de runtime observado: commit `d9ff6c1f499ac7301ab38cb5eb7f2bb9ca3f0e0f`; a cronologia detalhada foi separada para `ARCHITECTURE_CONSOLIDATION_HISTORY.md`.
- PR #150 continua aberta; `main` não foi alterada nem mesclada.
- Última prova real concluída: [FIRST_VIDEO #39878775061](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39878775061). Falhou na cena 1: os MUSTs `skiers`, `snow` e `winter gear` não foram comprovados juntos nos metadados; FFprobe foi ignorado e não há MP4 novo confirmado.
- No commit anterior `ce63f53`, os quatro workflows estruturais (migração Media Engine, validação portátil, Render Engine e stress 1→2→5→10) passaram. No commit atual, a migração Media Engine já passou; os demais workflows estão sendo revalidados após a mudança do setup FFmpeg.

### Correções atuais agrupadas
- **MUST visual contextual:** requisitos compostos são normalizados apenas quando a consulta visual fornece o contexto correspondente (manuscrito, barraca/neve, oceano/água, caixa torácica, equipamento de esqui, trem histórico, página impressa e equipamento de comunicação).
- **Integridade de mídia:** o verificador continua exigindo evidência nos metadados do próprio asset. Consulta de busca, nome de arquivo ou normalização não contam como prova.
- **Cache do Media Engine:** ativos em cache devem corresponder à assinatura do contrato da cena, incluindo consulta, MUST/AVOID e contexto visual.
- **Busca contextual de neve + esqui:** o router usa tanto a consulta quanto MUSTs de esqui para criar variantes dentro do limite de oito; em cenas com vários MUSTs, preserva o contexto e cada âncora independente. `winter gear` vira `ski equipment` apenas se os MUSTs/contexto indicarem esqui. Neve, esquiadores e equipamento continuam exigindo prova independente nos metadados.
- **Setup do FFmpeg:** o workflow reutiliza FFmpeg/FFprobe se ambos estiverem funcionais; caso precise instalar, as chamadas a `apt-get` têm limite de 180 segundos. Essa melhoria operacional ainda depende da conclusão da nova prova.
- **Concorrência da prova real:** o workflow usa um grupo por branch e cancela a execução anterior do mesmo grupo ao iniciar outra, para evitar duas gerações novas disputando recursos. A regra vale para execuções iniciadas com essa configuração.
- **Inteligência factual:** em provas anteriores, algumas sentenças substantivas ficaram com suporte abaixo do limiar; isso é uma pendência independente da aquisição de mídia. Não baixar o limiar nem classificar o roteiro como aprovado para forçar a liberação.

### Critérios de conclusão
1. CI verde para o commit atual.
2. FIRST_VIDEO completa a aquisição das 12 cenas e produz MP4 novo.
3. Vídeo e áudio presentes, metadados/duração válidos e FFprobe aprovado.
4. Visual QA e Intelligence Layer aprovados; qualquer aprovação humana exigida deve ocorrer pelo fluxo autorizado.
5. Manter a PR aberta para revisão. Não declarar conclusão com base apenas nos testes E2E sintéticos.

O histórico detalhado de execuções, falhas e correções anteriores foi preservado em [ARCHITECTURE_CONSOLIDATION_HISTORY.md](ARCHITECTURE_CONSOLIDATION_HISTORY.md).


## Estado consolidado — 23/10/2026

- Último commit analisado: `d303741fa41a1962986594df5a6b2466db63b459`.
- Correção em andamento: remover contexto autorreferente na normalização de MUSTs; o CI anterior encontrou 1 falha de teste de integração.
- Bloqueio separado da prova real: timeout do `apt-get update` durante instalação do FFmpeg, antes de executar FIRST_VIDEO.
- Critérios de conclusão permanecem: testes relevantes verdes, nova prova real, MP4 com áudio/vídeo válidos, FFprobe aprovado e gate final autorizado. PR #150 continua aberta; não fazer merge automaticamente.


## Atualização de CI — 23/10/2026

- A política `scene_must_policy.py` agora aciona explicitamente o workflow de migração/testes do Media Engine.
- FIRST_VIDEO usa retries e timeout ampliado para instalação do FFmpeg; a etapa continua exigindo os binários reais.
- A confirmação depende dos workflows do commit mais recente e da prova FIRST_VIDEO completar render, FFprobe e gate final.


## Ajuste de precisão dos MUSTs — 23/10/2026

- A âncora `vintage equipment` só é normalizada quando a consulta visual, e não apenas outro MUST, traz contexto explícito de esqui/época.
- A validação da política será repetida pelo workflow de migração, agora acionado também quando `scene_must_policy.py` muda.


## Correção da prova FIRST_VIDEO #39911433843 — 23/10/2026

- A execução [FIRST_VIDEO Live Proof #39911433843](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39911433843) passou por setup, Remotion bundle e credenciais, mas falhou na aquisição da cena 6; FFprobe foi ignorado porque o pipeline não chegou à renderização.
- A consulta era `old soviet investigation report paper document with russian text`, com MUSTs `document,text`. Foram encontrados 24 candidatos; nenhum comprovou ambos como etiquetas separadas, embora um candidato tenha comprovado `document`. A regra continua a exigir evidência real do objeto; não é correto simplesmente desativar o MUST.
- Correção agrupada nesta revisão: `text` é consolidado em `document` somente quando a própria consulta está em contexto de documento/relatório/arquivo e outro MUST já exige explicitamente `document`. A exigência de documento continua passando pelo verificador independente; consultas fora desse contexto mantêm `document` e `text` separados.
- Foram adicionados testes unitários positivos/negativos e um teste da integração no carregamento do mapa de cenas. A mudança se limita à política de requisitos da mídia; não altera critérios de áudio, renderização, FFprobe ou liberação final.
- A camada de inteligência da mesma execução registrou `INTELLIGENCE_PRE=REVIEW` com cobertura de claim lock em 50,0%. Esse problema factual é separado da aquisição de mídia e permanece pendente; não reduzir o limiar nem declarar aprovação automática.
- Critério de conclusão inalterado: CI verde, MP4 real novo, áudio/vídeo presentes, FFprobe aprovado, Visual QA/Intelligence Layer aprovados e qualquer aprovação humana processada pelo fluxo autorizado. PR #150 continua aberta; `main` não foi alterada.



## 15. Diagnóstico operacional do FIRST_VIDEO #39990137441 — 23/10/2026

- Execução: [FIRST_VIDEO Live Proof #39990137441](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39990137441). Falhou na etapa `Install FFmpeg`, com código de saída `124`; `Run FIRST_VIDEO` e FFprobe foram ignorados. Portanto, esta tentativa não dá evidência sobre a correção de mídia nem produziu um MP4 novo confirmado.
- A etapa foi interrompida durante `apt-get update`, antes da instalação e antes de executar código do ShortAutoPro. Trata-se de bloqueio de preparação do runner, separado das falhas semânticas de mídia observadas em tentativas anteriores.
- Consolidação nesta revisão: o workflow passa a usar explicitamente `ubuntu-24.04`, evitando depender da imagem `ubuntu-latest` observada como Ubuntu 26.04 no log. A instalação conserva a verificação dos binários reais e agora faz até três tentativas limitadas para atualizar os índices e instalar FFmpeg/FFprobe; depois falha claramente se não conseguir.
- A imagem fixada não elimina a validação do binário: cada execução verifica `ffmpeg -version` e `ffprobe -version`. Nenhum caminho de renderização, gate de qualidade, MUST factual ou aprovação foi afrouxado.
- No commit `828dde32`, Render Engine V2, Portable Validation e Render Engine V2 Stress passaram; Media Engine V2 Migration ainda estava em execução no momento da verificação. FIRST_VIDEO continua pendente de prova real completa.
- Próximo critério: validar este ajuste operacional no CI e confirmar uma nova execução FIRST_VIDEO que entre no pipeline de produção, adquira as 12 cenas, gere MP4 novo e passe por FFprobe e gates finais. Não declarar concluído até isso acontecer.


## 16. Consolidação do setup FFmpeg/FFprobe — 23/10/2026

- As execuções no commit `5a344a0` mostraram que o setup de FFmpeg/FFprobe estava duplicado em cinco workflows. Em várias execuções, a etapa APT ficou em andamento por tempo excessivo; no FIRST_VIDEO anterior, `apt-get update` terminou com código `124` antes do início da produção.
- Consolidação aplicada: criado `.github/actions/setup-ffmpeg/action.yml`, um componente reutilizável pelos workflows FIRST_VIDEO, Media Engine V2 Migration, Render Engine V2, Render Engine V2 Stress e Portable Validation. Os blocos de instalação repetidos foram substituídos por chamadas ao componente.
- O componente reaproveita binários de sistema válidos; tenta instalar via APT com limites de tempo/retries e, se a fonte APT falhar, usa versões fixadas `ffmpeg-static@5.3.0` e `@derhuerst/ffprobe-static@5.3.0`. O fallback também é verificado executando ambos os binários; nenhum teste aceita a mera presença de um arquivo.
- As workflows relevantes estão fixadas em `ubuntu-24.04` para reduzir variação da imagem entre execuções. Os testes de render e a prova real continuam obrigados a usar FFmpeg/FFprobe funcionais.
- Esta consolidação trata somente da preparação do ambiente. Não muda o gate de MUST/evidência, não libera candidatos sem metadados, não relaxa a Intelligence Layer e não representa prova de vídeo concluída.
- Critério da etapa: os cinco workflows devem passar pelo componente compartilhado. Depois, FIRST_VIDEO ainda precisa adquirir 12 cenas, renderizar MP4 novo, confirmar áudio/vídeo e FFprobe e passar pelos gates finais.



## 17. Prova FIRST_VIDEO #39991872760 e verificação visual por pixels — 23/10/2026

- Execução: [FIRST_VIDEO Live Proof #39991872760](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39991872760). Preparação e credenciais Gemini passaram; o Media Engine bloqueou a cena 1 antes da renderização. FFprobe foi ignorado; esta execução não produziu um MP4 novo confirmado.
- A cena pediu uma barraca rasgada em uma paisagem nevada. A normalização de contexto já funcionou ("ripped canvas" → "torn tent"), mas 64 candidatos primários e 20 candidatos de recuperação do Wikimedia não comprovaram simultaneamente "torn tent" e "snow" nos metadados.
- A execução reportou Pexels, Pixabay e Coverr sem suas respectivas chaves. O workflow permite continuar sem essas fontes; não é correto tratá-las como disponíveis. A causa imediata foi falta de evidência de mídia nos candidatos disponíveis, não um erro de renderização.
- Consolidação nesta revisão: a aquisição mantém primeiro o caminho estrito por metadados. Somente quando ele não encontra candidato aprovado, poderá baixar até duas imagens relevantes, validar integridade/resolução e usar o cliente gemini_runtime.py já existente para avaliar os pixels. Cada MUST precisa estar claramente visível e cada AVOID precisa estar ausente, com confiança mínima de 0,90 e evidência visual explícita.
- Essa recuperação é fail-closed: indisponibilidade do Gemini, arquivo inválido, resposta malformada, item ausente ou confiança insuficiente mantêm o bloqueio. A consulta de busca, a descrição do provedor e o nome do arquivo não são enviados como prova visual. O relatório separa visual_verification de metadata_must_hits, preservando a proveniência.
- Foram adicionados testes para o payload multimodal, limite de bytes/MIME, decisões positivas/negativas, fallback no Media Engine e exclusão dos arquivos cuja verificação visual falhar. A implementação precisa ainda passar pelos workflows e por uma nova prova real; não afirmar que a lacuna está resolvida antes dessas validações.
- Pendência independente: a mesma execução registrou INTELLIGENCE_PRE=REVIEW com cobertura de claim lock em 66,7%. Essa cobertura factual não pode ser corrigida relaxando o gate de mídia; precisa de uma revisão separada e verificável do roteiro/fonte.


## 18. Ajuste da asserção do runner portátil — 23/10/2026

- A execução [Portable Validation #39996149523](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39996149523) executou 948 testes e falhou somente em `test_portable_validator_is_github_hosted_and_read_only`: o teste esperava `ubuntu-latest`, mas o workflow foi intencionalmente fixado em `ubuntu-24.04`.
- Os testes recém-adicionados da integração multimodal do Gemini, do verificador de pixels e do fallback fail-closed passaram nessa execução. O erro foi uma expectativa de teste desatualizada, não uma falha da lógica de aquisição/renderização.
- Correção restrita: a asserção agora espera `ubuntu-24.04`, mantendo a verificação de runner hospedado e permissões somente de leitura. Nenhum gate de mídia ou produção foi relaxado.
- A suíte portátil e o workflow de migração precisam ser executados novamente antes de marcar esta etapa como validada.
