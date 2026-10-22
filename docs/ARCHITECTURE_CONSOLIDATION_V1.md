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
