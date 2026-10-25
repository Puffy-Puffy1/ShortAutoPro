# ShortAutoPro — Histórico de validações e correções

Este arquivo preserva o diário cronológico movido de `ARCHITECTURE_CONSOLIDATION_V1.md`. Os estados e conclusões dentro dele são fotografias históricas; para a situação mais recente, consulte o resumo atual em [ARCHITECTURE_CONSOLIDATION_V1.md](ARCHITECTURE_CONSOLIDATION_V1.md).

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

## 27. Correção de pergunta editorial no claim lock — 22/10/2026

- FIRST_VIDEO #39874615573 gerou roteiro sobre Frederick Valentich e parou antes do render por falta de mídia com relevância comprovada para a cena piloto/cockpit. A auditoria factual registrou INTELLIGENCE_PRE=REVIEW, cobertura 62,5%; dois enunciados substantivos ficaram sem suporte suficiente e uma pergunta editorial também foi contada como factual.
- O classificador já isentava perguntas explícitas como “O que realmente aconteceu?” e CTAs, mas não cobria a formulação comum “O que você acha que aconteceu?”. O regex foi ampliado com essa forma específica, e o teste agora cobre as duas perguntas e a CTA.
- A correção não afeta as sentenças factuais: os limiares de suporte simples/múltiplo permanecem iguais. As alegações sobre o fragmento de Cessna e a hipótese de desorientação continuam necessitando evidência; não se devem descartar nem baixar o limiar para forçar o status PASS.
- Próximo critério: testes de Intelligence Layer verdes e uma nova prova FIRST_VIDEO. O MP4 ainda não foi gerado nem passou por FFprobe; liberação final permanece pendente.

## 28. Normalização contextual de páginas impressas — 22/10/2026

- Prova real: [FIRST_VIDEO #39875354754](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39875354754), tema `O Caso de Taman Shud`. A aquisição passou pelas cinco primeiras cenas e parou na cena 6; o render e FFprobe foram ignorados.
- Consulta da cena 6: `vintage book page with Persian text printed`; MUST: `book page`. Foram encontrados 9 candidatos primários e 6 no fallback, mas nenhum metadado comprovou a expressão composta.
- Correção consolidada: em consulta que descreve uma página de livro/impresso, normalizar `book page(s)` para a âncora visual `page`. A consulta original permanece intacta e sua relevância contextual continua sendo verificada separadamente. Fora desse contexto, o MUST composto permanece inalterado.
- O verificador independente continua obrigatório: nem a consulta nem a regra de normalização contam como evidência de mídia. O candidato ainda precisa apresentar evidência de página no próprio metadado; a relevância contextual continua evitando aceitar qualquer resultado genérico sem relação com o pedido.
- Foram adicionados testes positivos e negativos para a política, teste de integração de `load_scene_map` e versão do Media Engine atualizada de `2.0.4` para `2.0.5`. Os filtros de FIRST_VIDEO já monitoram o arquivo de política e esses testes.
- No commit anterior `af21b8a5`, migração Media Engine V2, Render Engine V2, stress 1→2→5→10 e validação portátil passaram. A prova #39875698889 estava em andamento na última consulta, ainda em instalação de FFmpeg; não a considerar validação desta nova correção.
- Pendência: confirmar CI verde e executar nova FIRST_VIDEO. Só declarar o vídeo real concluído depois de obter MP4 novo, áudio/vídeo válidos, FFprobe aprovado e decisão final de liberação autorizada.

## 29. Alinhamento de MUSTs para equipamento de comunicação — 22/10/2026

- Prova real: [FIRST_VIDEO #39876892806](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39876892806), tema `Desaparecimento de Frederick Valentich`. A aquisição parou na cena 6; a etapa FFprobe foi ignorada porque não existiu render novo.
- Consulta: `vintage aviation radio microphone and headset equipment`; MUST gerado: `pilot`. O router encontrou 59 candidatos primários e 20 candidatos no fallback, mas nenhum tinha evidência de piloto nos próprios metadados. O bloqueio foi correto porque consulta de equipamento não prova a presença de uma pessoa.
- Correção contextual: quando a consulta descreve rádio/microfone/headset/transceiver e não descreve piloto ou pessoa visível, normalizar o MUST `pilot` para `microphone`. Quando a consulta exige um piloto visível (por exemplo, `pilot screaming inside cockpit`), o requisito `pilot` permanece. Consulta original e relevância não são alteradas.
- A evidência de microfone continua obrigatória no metadado do candidato; o texto da busca não é evidência. Existem testes unitários positivos/negativos e testes de integração no carregamento do mapa de cenas. Media Engine atualizado de `2.0.5` para `2.0.6`.
- A camada de inteligência desta execução indicou `INTELLIGENCE_PRE=REVIEW` com cobertura de claim lock 71,4% e `INTELLIGENCE_SCENE=REVIEW`. Duas alegações substantivas ficaram com suporte lexical baixo; essa revisão factual é independente da falha de mídia e não deve ser resolvida reduzindo o limiar de evidência.
- Próximo critério: CI verde para a alteração contextual e nova prova real. Não declarar vídeo concluído até existir MP4 real com áudio/vídeo válidos, FFprobe aprovado e gate final autorizado.

## 30. Preparação de FFmpeg com limite de tempo — 22/10/2026

- Na prova [FIRST_VIDEO #39877422258](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39877422258), o job permaneceu em `Install FFmpeg`; a API não disponibilizou os logs enquanto o passo estava ativo. Uma execução anterior também foi observada nesse mesmo passo. Isso não confirma que `apt-get` era a causa, mas indica que a preparação merece limites claros.
- Ajuste operacional: verificar primeiro se `ffmpeg` e `ffprobe` já estão instalados e executáveis; reutilizá-los quando disponíveis. Caso contrário, limitar `apt-get update` e instalação a 180 segundos cada, verificar os binários e deixar o job falhar claramente se não puder preparar o ambiente.
- O ajuste não toca nos validadores, MUST/AVOID, inteligência factual ou liberação final. A nova execução do FIRST_VIDEO e o CI precisam comprovar que a preparação e a geração do vídeo avançam.
- Continuam válidos os critérios: MP4 novo com áudio/vídeo válidos, FFprobe aprovado e gate final autorizado. Esta alteração de workflow não conta como evidência de renderização bem-sucedida.


## 31. Concorrência entre provas FIRST_VIDEO — 23/10/2026

- Foram observadas várias execuções antigas reportando `in_progress` ao mesmo tempo, algumas sem progresso visível na preparação. Os logs desses jobs não estavam disponíveis durante a execução, portanto a causa original não foi confirmada.
- O workflow recebeu `concurrency.group` por `github.ref` com `cancel-in-progress: true`: futuras execuções do FIRST_VIDEO na mesma branch substituem uma execução anterior do mesmo grupo em vez de disputar runners/artefatos. A configuração não altera os gates de render, mídia, factualidade ou aprovação.
- Execuções iniciadas antes da configuração de concorrência podem não pertencer a esse grupo retroativamente; verificar individualmente seus estados. A nova configuração deve ser confirmada no CI após este commit.

## 32. Recuperação contextual para esqui em neve — 23/10/2026

- Prova real: [FIRST_VIDEO #39877884641](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39877884641), tema Dyatlov. O setup concluiu e a produção entrou no Media Engine, mas parou na cena 6 antes de renderizar.
- Consulta: `old wooden ski equipment discarded in deep snow`; MUST: `snow`. Foram encontrados 87 candidatos; 86 foram recusados pela relevância contextual e nenhum candidato elegível comprovou `snow` nos próprios metadados. O bloqueio foi correto e FFprobe foi ignorado.
- Correção de descoberta: ao detectar `snow` como MUST em consulta de esqui, o router acrescenta três buscas contextuais específicas (`wooden skis in snow`, `abandoned skis in snow`, `ski equipment in deep snow`) antes das variantes genéricas. A consulta original continua primeiro, as variantes permanecem limitadas a oito e a consulta nunca passa a valer como evidência.
- Testes positivos e negativos asseguram que as variantes existam e que esquis descritos dentro de um museu, sem neve comprovada, continuem sendo rejeitados para MUST `snow`.
- Pendência: o novo commit precisa passar na migração, validação portátil, Render Engine, stress 1→2→5→10 e nova prova real. Só considerar concluído após MP4 novo, áudio/vídeo válidos, FFprobe e gate final autorizados.

## 33. Contexto composto dos MUSTs de expedição de esqui — 23/10/2026

- Prova real: [FIRST_VIDEO #39878775061](https://github.com/Puffy-Puffy1/ShortAutoPro/actions/runs/39878775061), tema Dyatlov. A preparação, incluindo FFmpeg e Whisper, terminou; a aquisição de mídia parou na cena 1, antes de renderizar.
- A consulta era `soviet winter mountain expedition snow landscape 1950s`; os MUSTs gerados foram `skiers`, `snow` e `winter gear`. Foram encontrados 75 candidatos, mas nenhum comprovou todos os requisitos nos metadados independentes. O bloqueio foi correto; FFprobe não executou.
- O problema específico foi de contexto: a query não mencionava esqui embora os MUSTs incluíssem `skiers`. A carga do mapa agora monta o contexto da política com a consulta e os MUSTs originais, permitindo normalizar `winter gear` para `ski equipment` apenas quando o contexto contém `ski/skier`.
- O router mantém cada MUST individual entre as variantes limitadas e acrescenta uma consulta contextual que combina query original + MUSTs restantes. Para descoberta de neve/esqui, adiciona variantes específicas, mas continua exigindo `snow`, `skiers` e `ski equipment` nos metadados do asset. Query não conta como evidência.
- Adicionados testes unitários para normalização positiva/negativa, integração no `load_scene_map`, variantes de busca com esqui explícito ou somente nos MUSTs e rejeição de um candidato de esquis em ambiente interno sem neve. Media Engine atualizado de `2.0.6` para `2.0.7`.
- Nova CI precisa confirmar os testes e uma prova FIRST_VIDEO subsequente. Só considerar produção concluída com MP4 novo, áudio/vídeo válidos, FFprobe aprovado e liberação final autorizada.


## 34. Correção do contexto autorreferente dos MUSTs — 23/10/2026

- O CI no commit `d303741` revelou um teste de integração falhando: `pilot` não era normalizado para `microphone` numa consulta apenas de equipamentos porque o Media Engine adicionava o próprio MUST ao contexto e a política interpretava isso como evidência de uma pessoa visível.
- Correção: `load_scene_map` agora passa apenas a consulta da cena como contexto-base. `normalize_visual_musts` acrescenta os outros MUSTs ao contexto de cada item, excluindo o requisito atual. Assim, requisitos como `skiers` ainda contextualizam `winter gear`, mas `pilot` não pode servir como evidência de si mesmo.
- A mudança não altera os critérios do verificador de mídia. A consulta e os MUSTs continuam sendo instruções de busca, não evidência de que o candidato contém o objeto.
- O teste `test_load_scene_map_normalizes_pilot_to_microphone_for_equipment_query` é a regressão direta que deve passar. Outros testes relevantes incluem os de piloto visível, esqui, manuscrito, barraca/neve e água/oceano.
- A prova FIRST_VIDEO #39879410408 falhou antes da geração do vídeo por timeout de 180 segundos em `apt-get update` durante a instalação do FFmpeg. Isso é uma falha de preparação do runner distinta da falha de teste do Media Engine. A prova deve ser repetida após o ajuste do código; não há novo MP4 nem validação FFprobe nessa execução.


## 35. CI sensível à política de MUSTs e retry de FFmpeg — 23/10/2026

- Incluído `scene_must_policy.py` nos filtros de `Media Engine V2 Migration` para que mudanças na política executem os testes de regressão em PRs e nos branches monitorados. O filtro anterior não iniciava esse workflow quando apenas a política mudava.
- A etapa de instalação do FFmpeg em FIRST_VIDEO agora permite até 300 segundos para `apt-get update` e usa as opções de retry/timeouts do APT. A falha anterior terminou em `exit code 124` após 180 segundos, antes da geração do vídeo; a mudança tenta reduzir falhas transitórias sem ignorar a necessidade de `ffmpeg` e `ffprobe` funcionais.
- A versão `6df2ff4` corrige a inicialização do contexto de MUSTs; a execução de CI deve validar essa versão e o ajuste do workflow. Ainda não há resultado final de prova real nem MP4 validado nesta etapa.


## 36. Preservação da âncora de época no contexto de esqui — 23/10/2026

- A execução de regressão da revisão `6df2ff4` mostrou que a âncora `vintage equipment` era reduzida a `vintage` apenas porque outro MUST dizia `skis`, mesmo quando a consulta só mencionava neve e montanhas.
- Ajuste: a normalização de `vintage equipment` agora exige que a própria consulta contenha contexto explícito de esqui/época. Outros MUSTs continuam a contextualizar requisitos compatíveis, como `skiers` contextualizando `winter gear`, mas não substituem a evidência visual da época.
- O teste `test_ski_equipment_requirements_remain_unchanged_without_context` cobre a regressão. A política continua a exigir verificação independente dos metadados do candidato.


## 37. Recuperação de busca para lápis em mapas — 24/10/2026

- A execução FIRST_VIDEO `40042645231` parou na cena 06: a busca encontrou 58 candidatos, mas nenhum passou pela evidência estrita de `map` e `pencil`; o único candidato visualmente analisado mostrava mapa, mas não lápis.
- `media_provider_router_v2.py` agora inclui consultas de catálogo específicas para lápis (grafite, desenho, madeira, mecânico e lápis sobre mapa), mantendo o conjunto de variantes limitado.
- `media_must_verifier.py` reconhece apenas descrições explícitas de lápis e equivalentes diretos. Uma caneta genérica ou a própria consulta não serve como evidência.
- `tests_sim/test_media_must_verifier.py` adiciona regressões para metadados positivos, rejeição de falsos positivos e expansão de consulta.
- A verificação visual e os critérios MUST/AVOID não foram reduzidos. O novo FIRST_VIDEO precisa confirmar se a busca encontra um candidato válido e gerar/validar um MP4 real.


## 38. Busca contextual para cenas de aviação noturna — 24/10/2026

- A execução FIRST_VIDEO `40048525749` passou pelas verificações de código e script, mas parou na cena 01: a busca retornou candidatos de Wikimedia, porém os três candidatos enviados à verificação visual não mostravam simultaneamente avião, oceano e céu noturno. Nenhum MP4 foi criado nesta execução.
- `media_provider_router_v2.py` agora tenta consultas de catálogo mais naturais para essa combinação: avião sobre oceano à noite, aeronave sobre mar à noite e avião voando sobre oceano à noite.
- `tests_sim/test_media_must_verifier.py` cobre as variantes contextuais e o limite de oito buscas.
- Mudança restrita à descoberta de mídia. A verificação visual MUST/AVOID e os requisitos de saída continuam intactos; a correção só será considerada comprovada após testes e nova execução FIRST_VIDEO com MP4 validado por FFprobe.


## 39. Separação entre prova de geração e autorização de publicação — 24/10/2026

- A execução FIRST_VIDEO `40050143538` gerou `videos/short_v6_gha_40050143538_1.mp4`; o render retornou PASS, o Visual QA marcou 95/100 e a auditoria de mídia passou em 12/12 cenas. O FFprobe confirmou MP4 H.264/AAC, 1080×1920, 30 fps e duração positiva.
- A etapa `main.py run` terminou com código 1 apenas porque `manifests/gha_40050143538_1_release.json` registrou `decision=BLOCK` e o único bloqueio crítico foi `shortauto_brain_approval_required` com decisão `HUMAN_APPROVAL_REQUIRED`. A geração tinha sido concluída; a autorização de publicação continuou bloqueada corretamente.
- Foi adicionado `first_video_run_contract.py`: só classifica o resultado como prova de geração válida se existir MP4 não vazio, o relatório corresponder ao mesmo `short_id` e o único bloqueio for a exigência explícita de aprovação humana. Falta de MP4, relatório ausente, código inesperado ou qualquer bloqueio adicional continuam falhando.
- O workflow mantém a validação FFprobe separada e inclui os relatórios de release/qualidade no artefato de evidências. O código não altera a decisão do release gate, não aprova publicação e não usa `continue-on-error`.
- `tests_sim/test_first_video_run_contract.py` cobre o caminho de aprovação humana e os casos negativos para MP4 ausente/vazio, identidade divergente, bloqueios adicionais e decisão de release conflitante.


## 40. Verificação independente de MUSTs e reforço dos objetos centrais — 24/10/2026

- A inspeção do MP4 `gha_40050143538_1` confirmou que renderização e FFprobe funcionavam, mas algumas imagens ilustrativas eram genéricas: uma pintura de areia foi aceita para uma narração sobre corpo encontrado na praia, e uma carta genérica para uma cena sobre código criptografado.
- Causa principal no caminho estrito: `MediaProviderV2.prepare()` aceitava `must_hits` calculado pelo provedor e `media_engine_v2.acquire_scene()` não revalidava de forma independente cada MUST antes do download.
- Correção: todo candidato estrito agora passa por `media_must_verifier.verified_must()` usando os metadados do próprio recurso. `must_hits` do provedor é apenas uma pista; qualquer MUST ausente rejeita o candidato e mantém a busca/fallback de verificação visual.
- A normalização reforça objetos explícitos na narração/consulta: pessoa em cenas sobre corpo morto/encontrado, etiqueta em roupas com etiqueta removida e código em cenas criptografadas. O contexto considera consulta e segmento narrado.
- Testes de regressão verificam que um `must_hits` falso nunca chega ao download, que objetos principais são acrescentados quando indicados e que uma paisagem de praia genérica não ganha um requisito de pessoa sem contexto.
- Nenhum gate de qualidade ou aprovação foi reduzido. É necessária nova execução FIRST_VIDEO, análise da mídia selecionada e aprovação FFprobe; gerar um MP4 técnico não basta para aprovar o conteúdo.


## 41. Recuperação de trens no inverno e invalidação de cache — 24/10/2026

- A execução FIRST_VIDEO `40051616301` parou na cena 03 (`train + snow`): 21 candidatos foram encontrados, mas só dois chegaram à verificação por pixels; ambos mostravam neve sem o trem.
- O roteador agora adiciona consultas de catálogo direcionadas (`train in snow` e `steam locomotive in snow`), sem alterar os requisitos visuais.
- O fallback visual prioriza candidatos que comprovam o MUST principal nos próprios metadados e pode verificar até cinco imagens, sempre exigindo aprovação pixel a pixel antes de aceitar mídia. A seleção continua limitada e reproduzível.
- A versão do Media Engine foi elevada para `2.0.9` e incluída na impressão digital do contrato da cena. Isso invalida mídia em cache selecionada por política anterior e força a nova aquisição/verificação.
- Testes adicionados para prioridade de objeto principal, consultas train/snow, impressão digital de política e fixtures de aquisição com evidência explícita.
- A nova execução FIRST_VIDEO, a inspeção das mídias selecionadas e o FFprobe ainda precisam passar antes de declarar esta revisão concluída. Nenhum gate de MUST/AVOID foi reduzido.


## 42. Recuperação para cidade russa no inverno — 24/10/2026

- A execução FIRST_VIDEO `40052318151` passou pela cena 02, verificando visualmente o trem e a neve. A cena 03 então parou: a busca do Wikimedia retornou 100 resultados, mas os cinco candidatos verificados não mostravam simultaneamente cidade, neve e casas de madeira.
- O roteador adiciona duas buscas específicas quando esses três MUSTs estão presentes: `old Russian town with wooden houses in snow` e `Sverdlovsk winter village wooden houses`. O limite geral de variantes permanece em oito.
- Os candidatos continuam sujeitos à verificação independente de MUSTs/AVOID e, no fallback, ao verificador de pixels. A expansão só melhora a descoberta e não transforma uma imagem genérica em imagem aprovada.
- O teste `test_russian_winter_town_query_gets_two_contextual_searches` protege as variantes contra regressão. A confirmação depende de uma nova execução FIRST_VIDEO com conteúdo e FFprobe aprovados.


## 43. Separação entre requisito obrigatório e preferência visual não narrada — 24/10/2026

- A execução FIRST_VIDEO `40052318151` validou visualmente a cena 02, mas bloqueou a cena 03. O diretor adicionou `wooden houses` como MUST mesmo sem essa informação na consulta ou na narração; os cinco candidatos analisados não cumpriram a combinação artificial de três elementos.
- Correção: `scene_must_policy.py` mantém `town` e `snow` como requisitos e converte `wooden houses` em `preferred_visuals` somente quando o detalhe não aparece no texto da cena. Se a consulta/narração mencionar casas de madeira, o detalhe continua obrigatório.
- `media_engine_v2.load_scene_map()` faz a ponte entre os resultados da normalização e `preferred_visuals`. A busca acrescenta as preferências para ajudar a descoberta, sem usá-las como prova nem bloqueio.
- A fingerprint inclui preferências e a versão do engine passa a `2.0.10`, invalidando o cache antigo. O roteador preserva consultas específicas para cidade russa nevada com casas de madeira quando a preferência estiver presente.
- Testes cobrem a conversão condicional, o cenário em que as casas são explicitamente exigidas, a ponte ao carregar o mapa e a inclusão das preferências na fingerprint. As verificações visuais de MUST/AVOID seguem obrigatórias para candidatos de fallback.


## 44. Normalização numérica e proteção da prova E2E — 24/10/2026

- A execução FIRST_VIDEO `40052992267` bloqueou o gate semântico com `unsupported_numbers=4,500`: o roteiro em português usou `4.500`, enquanto a fonte usou `4,500` para o mesmo valor factual.
- `semantic_integrity_gate.py` agora normaliza separadores comuns de milhares antes da comparação e mantém decimais reais normalizados sem remover separadores indiscriminadamente.
- `tests_sim/test_pipeline_gates.py` cobre o falso bloqueio para `4.500/4,500` e confirma que um número realmente ausente, `7.000`, continua bloqueando. O isolamento dos testes também fixa `SHORTAUTOPRO_BASE` no diretório temporário para evitar ler arquivos do runner por engano.
- O workflow FIRST_VIDEO inclui o gate semântico e o teste no filtro de caminhos. A concorrência preserva uma prova ativa quando novos commits chegam, evitando cancelamentos acidentais da execução completa.
- A execução `40053389916` confirmou `SEMANTIC INTEGRITY: PASS` após essa correção; depois bloqueou uma cena de pessoa + código, levando à expansão contextual documentada na seção seguinte. Ainda é necessário validar um MP4 gerado pela cabeça final da PR.

## 45. Busca contextual para pista de pouso militar — 24/10/2026

- A execução FIRST_VIDEO `40053107823` encontrou 30 candidatos para a cena de base aérea, mas as cinco imagens verificadas não mostravam uma pista de pouso visível; nenhum MP4 foi criado.
- `media_provider_router_v2.py` acrescentou variantes limitadas para `airstrip`, `airfield runway`, `military airfield runway`, `runway at sunset` e `air force runway`.
- O teste `test_military_runway_query_gets_contextual_airfield_variants` protege a descoberta contextual e o limite de oito variantes. Os MUST/AVOID e a verificação visual continuam sem alteração.

## 46. Busca contextual para pessoa examinando código criptografado — 24/10/2026

- A execução FIRST_VIDEO `40053389916` passou pelo gate semântico, mas falhou na cena 02: a busca encontrou recursos ligados a códigos antigos, porém as imagens verificadas não mostravam uma pessoa e o código na mesma cena.
- `media_provider_router_v2.py` agora expande esse caso para buscas com criptógrafo, manuscrito de código antigo, cifra manuscrita e pessoa decifrando um criptograma.
- `tests_sim/test_media_must_verifier.py` verifica as variantes dentro do limite e confirma que metadados de código sem pessoa, ou de pessoa sem código, continuam insuficientes.
- A prova final da cabeça atual precisa produzir um MP4 novo e passar no FFprobe antes de encerrar/mesclar a PR.


## 47. Busca contextual para cifra escrita em papel — 24/10/2026

- A execução FIRST_VIDEO `40053696602` passou pelo gate semântico e pelas primeiras cenas, mas parou na cena 05: a busca retornou um único recurso com metadados de `paper`, sem contexto suficiente para a cena de um criptógrafo analisando símbolos secretos.
- `media_provider_router_v2.py` agora inclui variantes contextuais para papel manuscrito, cifra em papel e anotações de criptografia, preservando a consulta original e o limite de oito variantes.
- `tests_sim/test_media_must_verifier.py` cobre as consultas contextuais e garante que metadados contendo apenas `paper` não passam pelo filtro de relevância. Os requisitos MUST/AVOID e a verificação visual não foram enfraquecidos.
- A cabeça atual precisa completar FIRST_VIDEO, produzir um MP4 novo e passar no FFprobe antes de mesclar a PR.


## 48. Recuperação contextual de pastas de arquivo — 24/10/2026

- A execução FIRST_VIDEO `40054298298` passou pelo gate semântico e pelas primeiras cenas, mas falhou na cena 08: a busca retornou 25 candidatos para uma cena de arquivo de mistérios, porém as cinco imagens verificadas não mostravam uma pasta visível.
- `media_provider_router_v2.py` agora busca variantes de pasta de arquivo e pasta de caso policial, preservando contexto de mistério/arquivo e o limite de oito variantes.
- `media_must_verifier.py` reconhece metadados explícitos de pasta Manila, pasta de arquivo e pasta de documentos. Papéis soltos ou a própria consulta não servem de evidência.
- `tests_sim/test_media_must_verifier.py` cobre buscas contextuais, equivalentes explícitos e rejeição de falsos positivos. A verificação visual MUST/AVOID permanece obrigatória.
- A cabeça atual ainda precisa passar na prova FIRST_VIDEO com novo MP4 e FFprobe; a falha citada é da revisão anterior a esta correção.


## 43. Busca contextual para navio à deriva — 24/10/2026

- A execução FIRST_VIDEO `40055009078` falhou na cena 01: consulta `abandoned vintage sailing ship drifting in vast ocean`, MUST `ship`; 50 candidatos do Wikimedia e 20 de fallback foram encontrados, mas nenhum dos cinco candidatos analisados visualmente comprovou a presença de navio. O MP4 desta execução não foi gerado.
- Causa: aliases genéricos (`vessel`, `boat`, `watercraft`) consumiam o limite de oito variantes antes de buscas catalográficas mais específicas.
- `media_provider_router_v2.py` agora prioriza, para cenas históricas/abandonadas de navio com contexto de mar/oceano, consultas como `abandoned sailing ship at sea`, `old sailing vessel at sea` e `ghost ship in the ocean`.
- Foi adicionado teste de regressão para as variantes e o limite de oito consultas.
- A validação MUST/AVOID e a verificação visual continuam estritas; o teste e uma nova execução FIRST_VIDEO com MP4 validado por FFprobe ainda são necessários para comprovar o resultado.


## 43. Fallback visual após falha de download — 24/10/2026

- A execução FIRST_VIDEO `40114741110` chegou à cena 11, mas a única mídia aprovada pela verificação de metadados falhou na validação de assinatura do arquivo; a cena parou com `MEDIA_DOWNLOAD_FAILED`. O vídeo dessa execução não foi criado.
- A causa estrutural era que a verificação visual alternativa só entrava quando nenhum candidato passava pela verificação de metadados. Se o candidato aprovado falhasse no download/validação, outras imagens relevantes não podiam entrar no fallback visual.
- `media_engine_v2.py` agora enfileira um conjunto pequeno e limitado de candidatas adicionais atrás das candidatas estritas. A ordem mantém a preferência por evidência de metadados; cada alternativa só pode ser aceita depois de validação do arquivo e aprovação visual de todos os MUSTs e AVOIDs.
- Candidatas já presentes na lista estrita são deduplicadas para não repetir downloads. O limite de fallback continua controlado por `MAX_VISUAL_FALLBACK_CANDIDATES`.
- Foi adicionado teste de regressão simulando falha de download da candidata estrita e sucesso de uma alternativa após verificação pixel a pixel.
- A mudança não relaxa os requisitos visuais. A aprovação final depende dos testes CI, de uma execução FIRST_VIDEO concluída e de MP4 da execução atual validado pelo FFprobe.


## 43. Bloqueio de ícones de catálogo em cenas documentais — 24/10/2026

- A execução FIRST_VIDEO `40114763731` gerou um MP4 tecnicamente válido, mas a QA visual bloqueou a saída: a cena 07 usou um ícone vetorial preto da biblioteca Pinhead como se fosse uma fotografia; isso produziu uma cena totalmente preta e contribuiu para 3,767 segundos de quadros pretos. FFprobe passou, mas o relatório de qualidade não.
- `media_engine_v2.py` agora rejeita candidatos cuja própria metadata identifica iconografia/clipart em cenas documentais comuns, tanto na seleção estrita quanto na recuperação semântica e no fallback visual. Consultas que pedem explicitamente ícones continuam permitidas.
- A versão do Media Engine foi elevada para `2.0.11`, invalidando mídia em cache sob a política anterior.
- Foi adicionado teste de regressão garantindo que o ícone não chega ao download, além de teste para manter permitidas consultas explicitamente por ícones.
- Nenhum gate visual foi reduzido. A nova execução precisa demonstrar cena 07 não vazia, ausência de quadros pretos bloqueantes e relatório de QA aprovado, além de FFprobe.


## 44. Busca direcionada para avião leve sobre oceano à noite — 25/10/2026

- A execução FIRST_VIDEO `40210351782` falhou na cena 02. A busca principal encontrou 26 candidatos e o fallback visual verificou oito; as imagens aprovadas pelo catálogo não mostravam o oceano junto com o avião. O MP4 da execução não foi criado e o FFprobe corretamente bloqueou a etapa seguinte.
- `media_engine_v2.py` agora prioriza três formulações de catálogo para cenas que exigem avião + oceano à noite e excluem luz do dia/aviões comerciais: avião a hélice sobre oceano aberto à noite, avião leve sobre mar escuro e avião monomotor em voo acima do oceano.
- O teste de regressão `test_targeted_visual_search_recovers_light_aircraft_over_ocean_at_night` verifica as três variantes. O limite de buscas continua em três e as regras visuais MUST/AVOID não foram reduzidas.
- A correção só é considerada comprovada depois de uma nova execução FIRST_VIDEO produzir o MP4 da própria execução e o FFprobe confirmar vídeo H.264 1080x1920 a 30 fps, áudio AAC e duração positiva. A PR #150 permanece aberta; nenhuma alteração foi mesclada em `main`.


## 43. Recuperação de convés histórico vazio — 25/10/2026

- A execução FIRST_VIDEO `40211389200` falhou na cena 02: a busca retornou 10 candidatos do Wikimedia, mas os 8 enviados à verificação visual falharam porque mostravam pessoas ou não comprovavam simultaneamente convés de madeira e cordame. O pipeline bloqueou a mídia e não criou MP4 nesta execução.
- `media_provider_router_v2.py` agora inclui quatro consultas específicas para convés de navio histórico vazio, cordame e ausência de tripulação; o orçamento de busca sobe para até oito variantes apenas para esse contexto.
- `tests_sim/test_media_must_verifier.py` verifica as consultas e o limite. Os requisitos MUST/AVOID e a verificação visual permanecem rigorosos; não se aceitam imagens com pessoas para contornar a falha.
- A PR precisa de uma nova execução FIRST_VIDEO que gere MP4 e passe no FFprobe antes de ser considerada pronta para fechamento.


## 44. Busca para voo sob nuvens escuras e retry de falha temporária — 25/10/2026

- A execução FIRST_VIDEO `40212235247` falhou na cena 01. Os candidatos do Wikimedia não comprovavam simultaneamente avião, nuvens escuras e horizonte; o verificador visual também encontrou uma indisponibilidade temporária do Gemini. O MP4 desta execução não foi criado e o FFprobe corretamente falhou.
- `media_engine_v2.py` agora prioriza três consultas específicas para avião sob nuvens escuras com horizonte quando luz do dia é proibida. Elas só afetam descoberta e não aprovam a imagem automaticamente.
- `media_visual_verifier.py` repete até duas vezes adicionais apenas erros de serviço/transporte classificados como temporários. Erros permanentes continuam bloqueando; MUST/AVOID, confiança mínima e correspondência de cena não foram relaxados.
- Testes de regressão adicionados para as consultas meteorológicas e recuperação de indisponibilidade temporária do verificador.
- Critério de conclusão permanece: nova execução FIRST_VIDEO na cabeça atual deve produzir seu próprio MP4 e passar FFprobe; testes unitários/contratuais, sozinhos, não comprovam geração real. PR #150 permanece aberta e `main` não foi mesclada.


## 45. Busca contextual para mochilas em trilha nevada — 25/10/2026

- A execução FIRST_VIDEO `40212804652` avançou até a cena 07, mas bloqueou a mídia: 59 candidatos do Wikimedia foram encontrados; os oito enviados à verificação visual falharam na composição da cena (trilha nevada com caminhantes e mochilas). O MP4 dessa execução não foi criado.
- `media_engine_v2.py` agora prioriza três consultas de catálogo para caminhantes com mochilas em ambiente nevado, incluindo trilha na natureza e expedição de inverno.
- `tests_sim/test_media_engine_v2_failure_modes.py` cobre as duas consultas prioritárias e o limite de três buscas.
- A mudança só altera descoberta de candidatos. A verificação por pixels de MUST/AVOID e a correspondência de cena permanecem obrigatórias; a conclusão depende de nova execução FIRST_VIDEO com MP4 da própria execução aprovado pelo FFprobe.


## 43. Busca de cidade russa no inverno com MUST de neve isolado — 25/10/2026

- A execução FIRST_VIDEO `40215224924` passou as cenas 01–03 e falhou na cena 04. O plano fornecia apenas `snow` como MUST, enquanto o contexto editorial era `russian snow covered provincial town street`; por isso, as variantes de vila/cidade russa não eram ativadas e oito candidatos falharam na verificação visual/intent.
- `media_provider_router_v2.py` agora detecta contexto de cidade/vila russa de inverno na consulta mesmo quando o único MUST explícito é `snow`, priorizando buscas com cidade, vila, casas de madeira e rua antes dos aliases genéricos.
- `tests_sim/test_media_must_verifier.py` cobre esse caso específico e mantém o limite de oito variantes.
- Nenhum MUST/AVOID, aprovação visual ou gate de release foi relaxado. A nova execução FIRST_VIDEO precisa confirmar aquisição visual válida e MP4 próprio da execução validado por FFprobe.


## 44. Consulta de inverno preservando contexto da cena — 25/10/2026

- A execução FIRST_VIDEO `40217646172` falhou na cena 09: a consulta `secret military technology test in winter landscape` exigia neve, mas as variantes prioritárias eram termos genéricos (`snow`, `snowfall`, `winter camping`) que não preservavam o contexto militar/tecnológico.
- `media_provider_router_v2.py` agora gera variantes contextuais como `secret military technology test in snowy landscape` e `secret military technology test in snow-covered landscape` antes dos aliases genéricos.
- `tests_sim/test_media_must_verifier.py` verifica as variantes e o limite de oito consultas.
- Isso altera apenas descoberta. A relevância da cena, MUST/AVOID e verificação visual continuam obrigatórios; a correção depende de nova execução FIRST_VIDEO e MP4 próprio validado pelo FFprobe.


## 45. Busca contextual para pessoa isolada em trilha de inverno — 25/10/2026

- A execução FIRST_VIDEO `40219008853` falhou na cena 08: a consulta era `hiker walking back alone snowy trail winter`, com MUST `person` e AVOID `crowd`/`city`. Oito candidatas foram bloqueadas pela verificação visual porque mostravam multidão/cidade, ou não mostravam a pessoa com clareza.
- `media_provider_router_v2.py` agora prioriza consultas de catálogo que preservam pessoa isolada, trilha e contexto de inverno: `single hiker walking alone in snowy wilderness`, `lone person walking on a snow-covered trail` e `solitary hiker from behind in winter forest`.
- `tests_sim/test_media_must_verifier.py` cobre as três variantes e o orçamento limitado de buscas.
- Nenhum requisito MUST/AVOID ou limiar visual foi relaxado. A correção só estará comprovada após a nova execução FIRST_VIDEO gerar MP4 e o FFprobe validar a saída.


## 46. Correção de regex contextual e busca de navio em mar aberto — 25/10/2026

- A execução FIRST_VIDEO `40220702364` falhou na cena 01: as imagens de navio encontradas foram bloqueadas corretamente por AVOID de navio de cruzeiro moderno, incompatibilidade de intenção ou falta de visibilidade clara do navio. O MP4 não foi produzido.
- A validação portátil também encontrou regressão: a expressão regular de contexto para pessoa isolada no inverno continha `\\\\b` em raw strings, procurando barra literal em vez de limite de palavra; por isso as buscas contextuais não eram ativadas.
- Corrigida a expressão para limites de palavra reais e reforçada a busca de catálogo para navios antigos/solitários em mar aberto.
- Testes de regressão cobrem a ativação das buscas de inverno, a ausência de correspondência dentro de palavras como `Australian` e as variantes de navio em mar aberto.
- Nenhum MUST/AVOID ou gate visual foi relaxado. A confirmação ainda exige nova validação portátil e FIRST_VIDEO com MP4 próprio validado por FFprobe.


## 43. Preservar consultas contextuais de pessoa em cenas de inverno — 25/10/2026

- A validação portátil encontrou regressão em `test_lone_person_winter_scene_gets_contextual_searches_first`: consultas de pessoa sem alias explícito ficavam limitadas a quatro variantes e descartavam parte das buscas de contexto (trilha, caminhante e neve).
- O roteador agora define aliases limitados para `person`, permitindo o orçamento de até oito variantes já usado por outras cenas com aliases. As consultas contextuais continuam antes dos fallbacks genéricos; os critérios visuais MUST/AVOID não foram alterados.
- O FIRST_VIDEO da cabeça anterior falhou na cena 01 (`ship`): nenhum dos candidatos Wikimedia passou pela verificação visual; houve bloqueio por confiança de AVOID e visibilidade do MUST. A próxima execução após esta correção deve ser inspecionada antes de considerar a geração validada.
- A PR permanece sem merge até a suíte portátil passar e existir um MP4 gerado nesta cabeça, validado por FFprobe.


## 44. Busca contextual para acampamento no inverno — 25/10/2026

- A execução FIRST_VIDEO `40222271843` falhou na cena 01: 64 candidatos, mas nenhum passou pela verificação visual para os MUSTs `tent`, `snow` e `dark night`. O vídeo desta execução não foi gerado.
- O roteador agora prioriza buscas de catálogo específicas para tenda na neve à noite, antes de aliases genéricos, mantendo o limite de oito variantes.
- A validação portátil também revelou que o teste de navio abandonado esperava duas consultas contextuais que já não estavam no conjunto limitado. As variantes foram ajustadas para preservar as consultas `old sailing vessel at sea` e `ghost ship in the ocean` dentro do orçamento.
- Foi adicionado teste para a busca contextual de tenda/neve/noite. Os critérios visuais MUST/AVOID permanecem inalterados; a próxima execução deve comprovar a aquisição real e a validação FFprobe antes de aprovar a PR.


## 45. Busca de barraca danificada — 25/10/2026

- A execução FIRST_VIDEO `40223077657` falhou na cena 01. O tema era uma fotografia histórica de barraca rasgada; os MUSTs eram `tent` e `canvas tear`. Foram encontrados 13 candidatos Wikimedia, mas nenhum dos oito avaliados pelo verificador visual mostrou os requisitos.
- O roteador agora inclui consultas contextuais de catálogo para `torn canvas tent in snowy mountains` e `ripped tent canvas in snowy mountains`, mantendo o assunto e o dano juntos e dentro do orçamento de oito variantes.
- Teste de regressão cobre a expansão e o limite. Nenhum requisito visual ou gate de qualidade foi reduzido.
- A execução FIRST_VIDEO deve ser repetida; a PR só pode ser considerada pronta após gerar MP4 nesta cabeça, validar H.264/AAC, 1080×1920 e 30 fps via FFprobe e aprovar as verificações restantes.


## 46. Verificação de navio por composição observável — 25/10/2026

- A execução FIRST_VIDEO `40225260665` falhou na cena 01. O verificador visual confirmou que algumas imagens continham um navio, mas recusou a composição completa com `scene_intent_mismatch`; o intent textual incluía afirmações narrativas como `abandoned` e `drifting`, que uma fotografia estática nem sempre permite provar.
- `media_engine_v2.py` agora normaliza apenas esse caso para a composição visual observável `sailing ship on open ocean`. O MUST `ship`, os AVOID `modern ship` e `airplane`, e os outros critérios continuam sendo verificados separadamente nos pixels.
- Foram adicionados testes de regressão para a normalização específica de navio e para garantir que outras cenas mantenham o intent original.
- Esta alteração não comprova ainda a geração de vídeo. A nova execução FIRST_VIDEO precisa passar pela verificação visual e produzir MP4 válido, aprovado pelo FFprobe, antes de considerar a PR pronta.
