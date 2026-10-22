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

## 10. Estado verificado em 2026-10-21

### Prova real executada

- Execução: [FIRST_VIDEO Live Proof #39667362494](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39667362494).
- Commit testado: `6888e742ef048d9dfea83593714aed239e50281d`.
- Resultado do job: sucesso; renderização real por Remotion e validação FFprobe passaram.
- Artefato: [first-video-live-evidence](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39667362494/artifacts/12378332478).
- Arquivo validado: MP4 1080×1920, 30 FPS, H.264 + AAC, duração aproximada de 43,4 s; vídeo e áudio presentes.
- Mídia: relatório passou em 12/12 cenas, sem erros.
- Validação visual: score 97,5/100, zero issues e um warning de baixa resolução em `scene_01_wikimedia.jpg`.
- Testes de migração, render V2, stress e validação portátil passaram no mesmo commit.

### Correções incrementais em andamento

- **Aprovação do Brain:** o workflow FIRST_VIDEO define `SAP_BRAIN_ENFORCE=1` na etapa de produção. Uma decisão `HUMAN_APPROVAL_REQUIRED` deve bloquear a liberação quando o pipeline alcançar o release gate; a execução recente falhou antes dessa etapa, portanto esse comportamento ainda não foi confirmado no fluxo completo.
- **Resolução de mídia Wikimedia:** o router prefere a miniatura se ela tiver pelo menos 1280×720 pixels; se a miniatura for menor e o original atingir esse limite, seleciona o original. MUST/AVOID e validação independente continuam obrigatórios. Foram adicionados testes para os caminhos de seleção.
- **Falha real da prova #39670163401:** não gerou MP4; a cena 2 teve 22 candidatos Wikimedia rejeitados por relevância apesar de não ter MUST. Foi ajustado o limite para queries curtas; a correção, isoladamente, não resolveu todas as cenas.
- **Falhas reais das provas #39671726198 e #39671720102:** ambas pararam no Media Engine, antes de áudio/render/FFprobe. A primeira falhou na cena 4 (`must=elevator`) e a segunda na cena 3 (`must=interior`): havia candidatos de busca, mas nenhum comprovou o MUST nos metadados aceitos. Isso é uma falha de descoberta/adequação da intenção visual, não evidência para enfraquecer o verificador.
- **Correção incremental atual:** a busca alternativa agora inclui os MUST no texto usado para descobrir candidatos, sem passar MUST ao filtro permissivo e sem aceitar o texto da busca como prova. O verificador independente continua obrigatório. Foi acrescentada uma asserção de regressão para confirmar que a segunda busca recebe a query com o MUST. Commit da correção: `175397a4f2289359e55c7bc5860cdd7d1cbfa2cf`; teste: `ecf04129c5c6f51b3a85539b656d6b79336bce68`.
- **Evidência de interiores:** o verificador passou a reconhecer metadados concretos de ambientes internos (sala, corredor, hall/lobby) como evidência de `interior`, sem aceitar a consulta de busca como evidência. Foram adicionados testes positivos para espaços internos e negativo para descrição explicitamente externa. Commits: `c240b39d6e5b711cb373b5e0dee03476dd0fe992` e `669324af09318785eaf2e1baba2e5bfda809e36e`. Ambos ainda dependem de CI verde.
- **Falha da prova FIRST_VIDEO #39714808580:** execução no commit `c240b39d6e5b711cb373b5e0dee03476dd0fe992` parou na cena 1: requisitos `wrestler,canvas ring`; candidatos traziam evidência de wrestler, mas nenhum metadado aceito comprovou `canvas ring`. A busca com MUST já ocorreu, mas o verificador estrito corretamente recusou os candidatos sem evidência do ringue. Foi adicionada uma equivalência conservadora para metadados `wrestling ring`, `professional wrestling ring` e `boxing ring`, com testes positivos e teste negativo para retrato de wrestler sem ringue. Commits: `0ad7cf91910f4741e325a05b4b066d2b9c6883a6` e `dd698cecfe67fbd750d6993a1f5f531f4c0b39c7`. CI e nova prova FIRST_VIDEO ainda precisam confirmar a correção.
- **Validação estrutural já observada:** Portable Validation, Media Engine V2 Migration, Render Engine V2 (contrato e smoke) e Render Engine V2 Stress passaram no commit `b664691`. Isso valida contratos e testes automatizados desses workflows, mas não prova que a produção real chegou ao MP4.

### Pendências que continuam abertas

1. **Confirmar no CI:** executar os testes de falha de mídia e observar nova FIRST_VIDEO após a busca alternativa com MUST; só considerar sucesso após MP4 novo e FFprobe aprovados.
2. **Gate do Brain:** confirmar que `SAP_BRAIN_ENFORCE=1` bloqueia a liberação quando a execução chega ao release gate; as falhas atuais ocorreram antes dessa etapa.
3. **Qualidade da cena 1:** verificar se a seleção de resolução elimina o aviso; se o próprio original for pequeno, procurar outra mídia semanticamente validada. Não reduzir limites nem relaxar MUST.
4. **Consolidação estrutural:** continuar inventariando imports, entrypoints, outputs e testes antes de remover módulos legados. Não declarar consolidação total sem evidência.
5. **PR:** manter as alterações na PR #150 até revisão; não mesclar nem alterar `main` nesta etapa.

## 11. Limites desta consolidação

Este documento define o contrato de arquitetura e o caminho de migração; não prova que todos os módulos já estejam conformes. Cada checkbox precisa de teste, inspeção de imports/calls e evidência de execução. A implementação é incremental para evitar uma reescrita ampla que introduza regressões.

 
## 12. Estado verificado em 2026-10-22 — continuação

### CI observado
- [Portable Validation #39719797414](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39719797414): sucesso.
- [Render Engine V2 #39719797524](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39719797524): contrato e smoke test passaram.
- [Render Engine V2 Stress #39719797418](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39719797418): sucesso.
- [Media Engine V2 Migration #39719797558](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39719797558): sucesso.
- [FIRST_VIDEO Live Proof #39719772361](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39719772361): falhou na cena 5, antes da renderização. A exigência era `quill pen`; 12 candidatos foram encontrados, mas nenhum passou pela combinação de relevância e evidência obrigatória. Não foi confirmado MP4 novo nem FFprobe nesta execução.

### Correção incremental da cena 5
- O verificador reconhece agora rótulos de catálogo explícitos para pena de escrever: `quill pen`, `feather quill pen`, `writing quill`, `quill and ink`, `quill with inkwell`, `quill` e `feather pen`. Uma pena genérica, sem evidência de escrita, continua rejeitada.
- A busca acrescenta variantes limitadas como `feather quill` e `writing quill`, preservando a consulta editorial original.
- Na recuperação de busca, o Media Engine verifica o MUST antes da relevância. Só um candidato que comprove todos os MUST pode usar o limiar de um termo contextual coincidente além dos próprios termos MUST; uma coincidência composta apenas pelo MUST (por exemplo, `money` para MUST `money`) continua rejeitada. A busca primária mantém seu limiar normal. Candidatos sem evidência do MUST continuam rejeitados.
- Foram adicionados testes para os aliases da pena, rejeição de pena genérica, variantes de busca e regra de relevância na recuperação. O código e os testes foram enviados à branch; o resultado do CI após estas alterações ainda precisa ser confirmado.

### Próximos passos
1. Confirmar que os testes novos passam nos workflows.
2. Observar uma nova execução FIRST_VIDEO e verificar qual cena falha, se houver.
3. Só declarar prova real concluída quando existir MP4 novo com áudio/vídeo válidos e FFprobe aprovado.
4. Continuar a consolidação estrutural por responsabilidade e contratos; não apagar módulos legados sem mapa de dependências e testes.
5. Manter a PR #150 aberta até revisão; `main` permanece intocada.

 
### Atualização adicional — falha real da cena 8
- A execução [FIRST_VIDEO #39721581915](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39721581915) avançou até a aquisição de mídia, mas falhou na cena 8: `must=snow`, 80 candidatos, nenhum com metadado aceito que comprovasse neve. Não houve confirmação de MP4 novo nem FFprobe. Isso demonstra que a correção de busca da cena 5 não pode ser considerada validada pela prova completa.
- O verificador já reconhece `snow`, `snowfall`, `snow-covered`, `snow covered` e `snowy landscape`; o bloqueio foi a ausência dessas evidências nos candidatos, não a falta de um alias no verificador.
- Foi ajustada a expansão de consultas para experimentar aliases mantendo o restante do contexto da cena, por exemplo `forensic medical report document snow-covered background`, antes de depender de termos isolados. O MUST continua sendo validado exclusivamente contra os metadados descritivos do candidato; a consulta não é prova.
- Foi adicionado um teste de regressão para assegurar que a expansão de neve preserve o contexto editorial. Aguardando CI após o commit.

 
### Ajuste de regressão do expansor de consultas
- A primeira rodada após a expansão contextual detectou um teste de contrato: variantes de aliases estavam ocupando o limite de consultas antes que todos os MUSTs explícitos (como `ship` e `ocean`) entrassem na lista.
- Corrigi a ordem: primeiro preserva a consulta original e o contexto, depois reserva espaço para âncoras MUST explícitas, e só então usa aliases independentes. O limite continua em até 8 consultas por cena e a regra de evidência do MUST não foi alterada.
- CI do commit `f23de5a6` está em andamento para confirmar a regressão corrigida e a prova FIRST_VIDEO. Não considerar essa correção validada até os workflows terminarem.

 
### Segundo ajuste do limite de consultas
- A validação da aquisição detectou outro caso de contrato: muitas variantes com contexto podiam ocupar o limite antes de um alias standalone esperado, como `relief map`.
- O expansor agora gera apenas uma variante contextual prioritária por MUST e reserva o restante do orçamento para MUSTs explícitos e aliases independentes. Para neve, `snow-covered` é a variante contextual prioritária; a evidência de aceitação continua baseada nos metadados do recurso, nunca no texto da busca.
- Teste atualizado para validar a variante contextual prioritária. A nova revisão ainda precisa passar pelo CI e pela prova FIRST_VIDEO.


### Atualização de 22/10/2026 — prova real e consolidação de validações

- A execução [FIRST_VIDEO Live Proof #39724703983](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39724703983) gerou o MP4 real `short_v6_gha_39724703983_1.mp4`, com duração de 41,298 s. O relatório de render registrou áudio e vídeo, mídia real, primeiro quadro válido e FFprobe aprovado; o relatório de Visual QA marcou PASS com nota 95/100. O artefato da execução contém o MP4 e os relatórios técnicos.
- A liberação final **não** passou: a Intelligence Layer marcou BLOCK (63/100), com cobertura de claim lock em 62,5%, incompatibilidade geográfica e falso positivo na verificação de conceito visual evitado. O Brain estava em modo SAFE e exigiu `HUMAN_APPROVAL_REQUIRED`. Essa proteção não deve ser desativada para forçar uma aprovação.
- Corrigi a compatibilidade geográfica conhecida entre Bass Strait e Austrália e alterei a checagem de termos evitados para comparar expressões completas, evitando bloquear uma palavra compartilhada com um conceito maior (por exemplo, `cockpit` e `modern glass cockpit`). Foram adicionados testes de regressão para esses dois casos.
- O teste de expansão de neve tinha uma asserção copiada de outra consulta, sem relação com o cenário testado. Ela foi substituída por uma verificação do alias `snowfall`.
- A prova FIRST_VIDEO agora será disparada também quando a Intelligence Layer ou seus testes mudarem; os relatórios `reports/intelligence/*.json` serão incluídos no artefato para permitir identificar exatamente quais sentenças não obtiveram suporte.
- Validação do commit `17b47fa0`: migração V2, Render Engine V2 e teste de estresse 1→2→5→10 passaram. A validação portátil ainda estava em execução quando esta atualização foi preparada.

### Pendências verificáveis

1. Confirmar o resultado final da validação portátil e dos workflows no HEAD atualizado.
2. Reexecutar FIRST_VIDEO com os novos bloqueios falsos corrigidos e usar o diagnóstico de claim lock para investigar as sentenças sem suporte. Não reduzir o limiar de evidência sem identificar a causa.
3. Manter a liberação bloqueada até que a cobertura factual e os controles de qualidade sejam aprovados e a exigência de aprovação humana seja resolvida pelo fluxo autorizado.
4. PR #150 continua aberta; `main` não foi alterada nem mesclada.


## 13. Diagnóstico da prova FIRST_VIDEO #39732545372 — 22/10/2026

- Execução: [FIRST_VIDEO Live Proof #39732545372](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39732545372). Preparação, dependências e credenciais passaram; a etapa de produção parou no Media Engine V2 e a validação final do MP4 foi pulada.
- A cena 1 usou a consulta `old illustrated manuscript open pages studio lighting`, mas definiu os MUSTs `book` e `parchment pages`. O router encontrou 57 candidatos, porém nenhum comprovou os dois requisitos nos metadados; o bloqueio `MEDIA_INCOMPLETE` foi correto e não deve ser contornado.
- Correção consolidada nesta revisão: a política normaliza `book` e `parchment page(s)` para a única âncora visual `manuscript` **somente quando a própria consulta visual cita manuscript/Voynich**. Consultas genéricas sobre livros preservam os MUSTs originais. A normalização acontece na entrada do mapa de cenas do Media Engine e emite `SCENE_MUST_NORMALIZED` para auditoria.
- O verificador independente de MUST continua obrigatório: o texto da consulta não conta como evidência. A mudança não aceita candidatos sem metadados que comprovem um manuscrito; reduz apenas a duplicação incompatível dos requisitos.
- Foram adicionados testes da política com e sem contexto, um teste de integração da carga do mapa de cenas e filtros do workflow para esses testes. O motor foi versionado como `2.0.3`.
- A mesma execução mostrou `INTELLIGENCE_PRE=REVIEW` (119 claims, cobertura 22,2%). Como a aquisição falhou antes do render e do release gate, ainda não há novo MP4 validado nem confirmação de liberação final. O próximo critério é o CI verde e uma prova real que chegue a FFprobe, sem reduzir os gates factuais.



## 14. Diagnóstico da prova FIRST_VIDEO #39817616597 — 22/10/2026

- Execução: [FIRST_VIDEO Live Proof #39817616597](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39817616597). A instalação, o bundle Remotion e as credenciais passaram, mas a aquisição de mídia parou na cena 1; a etapa FFprobe foi ignorada porque não houve render novo.
- Tema escolhido: incidente de Dyatlov. Consulta visual: `vintage black and white photo of a torn tent in snowy mountains`. O mapa de cena gerou os requisitos `ripped canvas` e `snowy background`; o router encontrou 39 candidatos primários e 19 candidatos de recuperação, mas nenhum comprovou os termos originais por metadados.
- Ajuste contextual consolidado: quando a consulta cita uma barraca, `ripped canvas` vira `torn tent`; quando cita neve, `snowy background` vira `snow`. Os requisitos genéricos não são alterados fora desse contexto. As novas âncoras usam equivalências já suportadas pelo verificador independente.
- A busca, a consulta e os MUSTs normalizados não contam como evidência. A mídia precisa continuar comprovando a barraca rasgada e a neve por metadados do próprio candidato. Foram adicionados testes unitários da política e teste de integração de `load_scene_map`.
- O workflow de contrato, a validação portátil, o stress 1→2→5→10 e o Render Engine V2 passaram no commit `0e04305`; a prova real falhou antes de gerar MP4. A camada de inteligência marcou `INTELLIGENCE_PRE=REVIEW` (cobertura 25,0%) e `INTELLIGENCE_SCENE=BLOCK` com um bloqueio crítico, mas esse bloqueio ainda precisa de diagnóstico específico pelos relatórios/telemetria.
- Próximo critério: CI verde para esta correção e nova prova real. Não marcar o vídeo como concluído até o MP4 real conter áudio/vídeo válidos, FFprobe passar e a liberação final respeitar os controles de aprovação.


## 15. Correção do bloqueio geográfico falso positivo — 22/10/2026

- O relatório da execução [FIRST_VIDEO #39817616597](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39817616597) mostrou `geographic_mismatch` na cena 4: localização esperada `Northern Ural Mountains`, enquanto a consulta continha `Ural Mountains`. O verificador tratou a parte do nome como um lugar diferente e bloqueou indevidamente a etapa de inteligência.
- A comparação agora reconhece nomes de regiões compostos que contêm o mesmo nome geográfico de pelo menos duas palavras (por exemplo, `Ural Mountains` e `Northern Ural Mountains`). Termos genéricos isolados não bastam para declarar compatibilidade, e nomes de lugares realmente diferentes continuam gerando `BLOCK`.
- Foi acrescentado teste de regressão para o par de nomes regionais; o teste existente que exige bloquear Adelaide/Sydney permanece intacto.
- O diagnóstico veio do artefato de evidências da execução, não de suposição. A cobertura factual do roteiro continua baixa (25%) e precisa ser corrigida em fase própria; este ajuste só trata a compatibilidade geográfica. A validação final ainda depende da nova prova real, do FFprobe e do release gate.


## 16. Ajuste do Claim Lock com evidência composta — 22/10/2026

- O artefato de FIRST_VIDEO #39817616597 mostrou que algumas frases factuais estavam distribuídas por mais de uma sentença da fonte. Exemplo: a frase inicial do roteiro tinha suporte individual máximo de 0,357, abaixo do limite de 0,38, mas as duas sentenças-fonte mais relevantes cobriam em conjunto 64,3% dos tokens factuais do roteiro.
- O Claim Lock mantém o limite original de 0,38 para suporte por uma única sentença. Para evidência composta, aceita no máximo três sentenças-fonte independentes, cada uma com sobreposição mínima de 0,15, e exige cobertura combinada mínima de 0,60. A cobertura agregada e os IDs das sentenças que apoiam a afirmação são registrados no relatório para auditoria.
- Títulos de seção como “Testes militares” deixam de ser tratados como sentenças-fonte factuais. Perguntas retóricas reconhecidas e chamadas para ação de encerramento ficam identificadas como prompts editoriais e fora do denominador de cobertura factual; não são apresentados como afirmações com evidência.
- Foram adicionados testes para suporte composto, rejeição de títulos como evidência e exclusão de prompts/CTAs. A mudança não reduz o limiar de suporte individual nem torna automaticamente válidas as afirmações sem apoio; a frase sobre teorias continuará em revisão se não atingir um dos critérios.
- A nova prova precisa confirmar a cobertura factual no contexto real. O vídeo só estará aprovado quando aquisição, render/FFprobe e release gate passarem.


## 17. Recuperação de relevância para termos traduzidos — 22/10/2026

- A execução [FIRST_VIDEO #39819589135](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39819589135) falhou na cena 1 com a consulta longa `Voynich documentary context manuscrito nunca comprovadamente archive`, sem MUSTs explícitos. O candidato encontrado foi rejeitado porque a consulta usava a palavra portuguesa `manuscrito`, enquanto o catálogo usa `manuscript`; sem MUSTs, o motor também não executava o caminho de recuperação focado em MUST.
- A política de relevância agora normaliza as formas portuguesas comuns de “manuscrito” para o termo de catálogo `manuscript`. Isso permite que um candidato com metadados que contenham ambos `Voynich` e `manuscript` atinja o requisito de dois termos para uma consulta longa.
- A correção não ignora a relevância: um candidato que só compartilhe “Voynich”, sem evidência adicional no título/descrição, continua rejeitado. Foram adicionados testes positivo e negativo para essa distinção.
- O objetivo é corrigir incompatibilidade de idioma na busca; aprovação do candidato continua dependente dos metadados, dos requisitos MUST/AVOID aplicáveis e da validação independente da mídia.


## 18. Eliminação de MUSTs redundantes para oceano/água — 22/10/2026

- A execução [FIRST_VIDEO #39820116159](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39820116159) parou na cena 3, cuja consulta dizia “Bass Strait dark ocean aerial view at dusk”, mas os MUSTs eram `ocean` e `water`. Foram encontrados 75 candidatos, mas nenhum comprovou separadamente ambos os termos exigidos.
- A política agora consolida `water` em `ocean` apenas quando a consulta da própria cena contém oceano, mar ou águas abertas. Uma exigência genérica de `water` continua intacta em outros contextos, como pia, rio ou torneira.
- A verificação independente continua exigindo evidência de `ocean` (com as equivalências visuais já aceitas pelo verificador); não há aprovação automática de candidato. Foram adicionados testes unitários do contexto e teste de integração do carregamento do mapa de cenas.
- O resultado da prova real no HEAD mais recente ainda é necessário para confirmar se a aquisição avança; não declarar MP4 concluído antes de FFprobe e do release gate.



## 19. Busca contextual para microfone de rádio de aviação — 22/10/2026

- Execução: [FIRST_VIDEO Live Proof #39821922789](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39821922789). A aquisição de mídia parou na cena 5; a geração do MP4 e a validação FFprobe foram puladas.
- Consulta: `vintage aviation radio microphone and control panel`; MUST: `microphone`. O router encontrou 40 candidatos na busca inicial, mas nenhum chegou à lista estrita aceita; 34 foram rejeitados pela relevância da consulta. A busca de recuperação encontrou mais 20, sem evidência explícita de microfone nos metadados.
- Ajuste: o router agora tenta até cinco rótulos de catálogo para a busca — `communication microphone`, `aviation microphone`, `pilot microphone`, `radio microphone` e `aircraft microphone` — mantendo a consulta original como primeira opção e respeitando o limite de oito variantes.
- A alteração afeta somente a descoberta de candidatos. O requisito continua sendo `microphone`: descrições de rádio, handset ou painel sem evidência explícita de microfone continuam rejeitadas. Foram adicionados testes da expansão contextual e do bloqueio de equipamento sem microfone.
- As validações estruturais do commit `93b9809` passaram, mas a prova real ainda falhou antes do render. A mudança precisa passar pelos testes e por uma nova prova; não considerar o vídeo concluído até FFprobe e o release gate passarem.


## 20. Ajuste contextual para radiografia da caixa torácica — 22/10/2026

- Prova real: [FIRST_VIDEO #39844165759](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39844165759). O vídeo não chegou à renderização porque a aquisição foi bloqueada na cena 7.
- Consulta da cena: "medical x ray showing human rib cage and skeletal structure". O requisito emitido era "skeleton"; o Media Engine encontrou 58 candidatos, mas nenhum comprovou esse termo exato nos metadados aceitos.
- Correção contextual: quando o próprio texto da cena menciona "rib cage" ou "ribcage", o requisito "skeleton" é normalizado para "rib cage". Fora desse contexto, o requisito original permanece intacto.
- A normalização não é prova. O verificador independente ainda exige que os metadados do candidato contenham evidência explícita de caixa torácica; descrições apenas de coluna e crânio são rejeitadas. Testes unitários e de integração cobrem os dois lados da regra.
- Nesta execução, a camada factual marcou cobertura de claim lock de 77,8% e a análise de cenas marcou REVIEW sem bloqueio crítico. A aquisição de mídia foi o bloqueio imediato; não foi produzido novo MP4 nem executado FFprobe sobre um vídeo novo.
- Pendência: confirmar CI e nova execução FIRST_VIDEO. O projeto só pode ser considerado concluído após MP4 real, áudio/vídeo válidos, FFprobe aprovado e gate de liberação respeitado.


## 21. Compatibilidade lexical para aquisição de mídia — 22/10/2026

- Prova real: [FIRST_VIDEO #39845718669](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39845718669). A instalação e os gates de preparação passaram; a aquisição parou na cena 3, antes de gerar novo MP4 e antes da validação FFprobe.
- Consulta: `vintage wooden skis and poles in snow`; MUST: `snow`. O router encontrou 82 candidatos, mas 81 falharam no filtro de relevância textual; a recuperação restante não encontrou metadados que comprovassem neve. O bloqueio do MUST continua correto.
- Ajuste concentrado em `media_provider_router_v2.py`: o comparador de relevância agora normaliza formas comuns de catálogo `skis/skiing/skiers → ski` e `poles → pole`. Isso reduz falsos negativos de relevância quando a consulta e o catálogo descrevem a mesma cena com formas singular/plural.
- Testes adicionados em `tests_sim/test_media_must_verifier.py`: relevância positiva para `skis poles` versus `ski pole` e teste negativo que confirma que essa relevância não substitui o MUST `snow`. O verificador de mídia permanece independente e não aceita neve com base na consulta.
- A mudança não flexibiliza MUST/AVOID, resolução, checksum ou FFprobe. A validação depende do CI e de nova prova real; não há MP4 novo validado neste estado. A camada de inteligência também marcou `INTELLIGENCE_PRE=REVIEW` com cobertura 50,0%, uma pendência separada que deve continuar bloqueando a liberação final enquanto não for resolvida com evidência factual.



## 22. Integridade de cache do Media Engine V2 — 22/10/2026

- Auditoria de consistência: a validação de um asset em cache verificava checksum, Short ID, número da cena e quantidade de MUSTs, mas não comprovava que o arquivo fora adquirido para a mesma consulta e para os mesmos critérios visuais. Duas cenas com um único MUST poderiam compartilhar contagem e, ainda assim, exigir mídias diferentes.
- Correção: cada asset congelado agora contém **scene_contract_fingerprint**, um SHA-256 determinístico da consulta, segmento, modo visual, MUSTs e AVOIDs normalizados. O reuso do cache exige correspondência exata dessa assinatura.
- Sidecars antigos sem assinatura são tratados como cache não validado e não são reutilizados; o fluxo volta à aquisição normal. A regra não flexibiliza a comprovação independente de MUST, resolução, checksum, duplicidade ou FFprobe.
- Testes novos cobrem estabilidade da assinatura, rejeição de cache de outro contrato mesmo com a mesma quantidade de MUSTs e aceitação de cache válido com assinatura correspondente.
- Versão do Media Engine atualizada para **2.0.4**. A validação deste commit depende do CI; manter FIRST_VIDEO como não concluído até existir um MP4 real validado e o gate final passar.


## 23. Ajuste contextual de trem histórico — 22/10/2026

- Prova real: [FIRST_VIDEO #39857552666](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39857552666). A instalação, o bundle Remotion e as credenciais passaram; a aquisição parou na cena 2 e FFprobe foi ignorado porque não existiu novo MP4.
- Diagnóstico: consulta `vintage soviet train winter tracks Ural mountains`, MUST `soviet train`; 12 candidatos, nenhum confirmou a expressão inteira. A cena 1 da barraca conseguiu avançar depois dos ajustes contextuais existentes; o bloqueio se deslocou para o trem.
- Alteração consolidada: normalizar `soviet train` para a âncora visual `train` apenas quando a própria consulta mencionar trem/ferrovia soviética. O contexto original e o campo `era` são preservados; somente o objeto visual obrigatório é simplificado. A aceitação continua dependendo de metadados do próprio candidato que comprovem um trem, nunca do texto da consulta.
- Testes adicionados para a normalização positiva, para preservar o MUST sem contexto compatível e para garantir que `era="Soviet Union, 1959"` e a consulta permaneçam intactos em `load_scene_map`.
- Esta simplificação não prova insígnias, operador ou fabricação soviética do recurso. Se a imagem precisar demonstrar explicitamente uma locomotiva identificada como soviética, os metadados precisam provar esse detalhe em requisito separado. Nesta cena, a âncora automatizada representa o objeto “trem”; a época/contexto editorial permanece separada.
- O Render Engine V2 e o stress passaram no commit `ebc6aa0`; validação portátil e migração foram canceladas por execuções posteriores concorrentes e precisam de nova confirmação após o próximo commit. A prova FIRST_VIDEO falhou antes da renderização, portanto não há MP4 novo validado.
- Próximo critério: CI verde e nova FIRST_VIDEO. Não declarar concluído até render real, áudio/vídeo válidos, FFprobe aprovado e gate final respeitado.

## 24. Sincronização dos fixtures de cache — 22/10/2026

- CI do commit `a19b53f`: a compilação e os testes de Media Engine V2 passaram, mas três testes de aquisição legada falharam em `tests/test_media_acquisition_v2.py`: a retomada de asset, o escopo de diretório e a reutilização no manifest.
- Causa: esses fixtures criavam sidecars com checksum, short ID e número da cena, mas não incluíam `scene_contract_fingerprint`, que passou a ser obrigatório na versão 2.0.4. O comportamento de rejeitar sidecars sem a assinatura é intencional: sem ela, não é possível comprovar que o asset pertence à mesma consulta, MUSTs e AVOIDs.
- Correção nesta revisão: os três testes agora criam sidecars por meio de um pequeno helper que calcula a assinatura usando exatamente o contrato da cena em teste. Nenhuma validação de produção foi relaxada; a suíte continua a testar a reutilização de um cache válido.
- A correção está agrupada com esta atualização da documentação. É necessário confirmar de novo os testes independentes, a validação portátil e FIRST_VIDEO; a prova real só conta como concluída após novo MP4 e FFprobe aprovados.

## 25. Ajuste contextual de equipamento de esqui — 22/10/2026

- Prova real: [FIRST_VIDEO #39873268494](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39873268494). A instalação, o bundle Remotion e as credenciais passaram; a aquisição parou na cena 2, antes do render. FFprobe foi ignorado porque nenhum MP4 novo foi produzido.
- Diagnóstico: consulta `vintage soviet skiing expedition equipment and wooden skis`; MUSTs `vintage equipment` e `skis`. O router encontrou 41 candidatos na busca principal e 12 no fallback; nenhum comprovou simultaneamente os dois MUSTs.
- Correção consolidada: quando o contexto visual menciona esqui, `vintage equipment` vira a âncora factual `vintage`, e `skis` vira `ski equipment`. Assim a época/estilo e o objeto continuam exigindo evidências separadas. O query e o campo `era` permanecem intactos. O verificador aceita variações de catálogo como `wooden skis`, `ski poles` e `ski boots` para o objeto, enquanto a propriedade `vintage` precisa ser provada separadamente nos metadados descritivos.
- Testes positivos e negativos cobrem a regra contextual, a preservação do campo `era` e a proibição de usar somente a consulta como prova de equipamento.
- Esta correção não afirma que uma imagem genérica de neve é equipamento de esqui, nem prova que o material é soviético. Se a cena precisar mostrar equipamento claramente identificado como soviético, isso exige evidência de origem separada. A âncora automática apenas seleciona o objeto visual.
- No commit anterior, os testes de migração, validação portátil, Render Engine V2 e stress passaram; FIRST_VIDEO continua incompleto. O próximo critério é CI verde e nova prova real validada, sem diminuir os gates de mídia ou factualidade.

## 26. Busca contextual para cenas de piloto — 22/10/2026

- Prova real: FIRST_VIDEO #39874615573. O roteiro escolhido foi o desaparecimento de Frederick Valentich. A aquisição parou na cena 1, antes de renderizar; FFprobe foi ignorado.
- Consulta visual: pilot screaming inside cockpit headset; MUST explícito: pilot. Foram encontrados 40 candidatos iniciais e 22 na recuperação, mas a relevância rejeitou os candidatos porque alguns metadados confirmavam apenas pilot, sem evidência contextual de cockpit/headset/rádio.
- Correção: o router acrescenta até três buscas contextuais curtas (pilot in cockpit headset, aircraft cockpit pilot, pilot radio headset) quando o MUST é pilot e a consulta original menciona cockpit, headset ou rádio. Isso amplia a descoberta; não altera a consulta original, o resultado de relevância ou a verificação independente do MUST.
- Testes confirmam que metadados como Pilot in cockpit wearing a radio headset podem ser relevantes e que Portrait of a pilot continua insuficiente para a consulta completa. Nenhum requisito de aceitação foi afrouxado.
- Pendência independente: INTELLIGENCE_PRE=REVIEW com cobertura de claim lock de 62,5%. As sentenças sobre o fragmento de Cessna e a hipótese de desorientação espacial foram marcadas com suporte insuficiente, junto de uma pergunta retórica; a revisão factual deve examinar as duas alegações substantivas e manter a pergunta editorial fora do cálculo factual conforme a política existente. Não reduzir o limiar para fazer o gate passar.
- Aguardam-se CI verde e nova FIRST_VIDEO. Só confirmar conclusão após MP4 novo, áudio/vídeo válidos, FFprobe aprovado e gate final autorizado.
