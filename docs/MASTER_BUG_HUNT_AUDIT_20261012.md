# ShortAutoPro — Master Bug Hunt
## Baseline da auditoria (2026-10-12)

Status: **auditoria em andamento; não certificada como concluída**.

## 1. Preservação e estado inicial

- Repositório: `Puffy-Puffy1/ShortAutoPro`
- Branch padrão observada: `main`
- Branch de auditoria criada a partir de `main`: `audit/master-bug-hunt-20261012`
- Pull request de arquitetura já existente: [PR #148](https://github.com/Puffy-Puffy1/ShortAutoPro/pull/148)
- Branch de arquitetura: `refactor/canonical-pipeline-first-video-20261006`
- HEAD informado pelo GitHub para PR #148 durante esta inspeção: `45971d3ed577fd5b572dbd25fe235cac48f04e9b`
- Não foi feita alteração em `main` nesta auditoria.
- A branch de auditoria é separada; o PR #148 permanece aberto e não foi mesclado.

## 2. Evidências observadas

### AUD-CI-001 — Validação canônica anterior passou

O workflow run `38098258113`, associado ao commit `c96e4859be7f79eca1f859aff3fbf1b1d8b0c17a`, terminou com sucesso. O job `canonical-contract` executou e passou, incluindo:
- testes de contrato/arquitetura;
- renderização real FFmpeg/FFprobe de integração;
- teste de isolamento de renderização consecutiva 1-2-5-10.

**Limite:** esse resultado não prova que os checks passaram no HEAD atual do PR #148 nem que o pipeline live produziu um vídeo real.

### AUD-LIVE-001 — FIRST_VIDEO não foi comprovado

O workflow run `38086768267` falhou na etapa `Verify required live credentials`, antes de executar `first_video.py`. O job não comprovou a produção de um MP4. Portanto, nenhum sucesso E2E live pode ser declarado com base nessa execução.

### AUD-WF-001 — Preflight de credenciais tardio e excessivamente restritivo no workflow de main

O arquivo `.github/workflows/first-video-live.yml` em `main` verifica `PEXELS_API_KEY`, `PIXABAY_API_KEY` e `GEMINI_API_KEY` somente depois de instalar dependências, baixar o modelo de voz e compilar/baixar Whisper.cpp. Isso desperdiça tempo de runner quando secrets estão ausentes e trata Pexels/Pixabay como obrigatórios, apesar de o desenho documentado do PR #148 permitir provedores alternativos.

No branch do PR #148, a versão inspecionada já move o preflight para o início e exige somente `GEMINI_API_KEY`, deixando Pexels/Pixabay como opcionais. Essa diferença precisa ser resolvida de forma coordenada com o PR canônico, sem criar um segundo pipeline concorrente.

### AUD-STATUS-001 — A validação precisa corresponder ao HEAD atual

O status consultado para o HEAD `45971d3ed577fd5b572dbd25fe235cac48f04e9b` não retornou status checks, e a consulta de runs associados a esse SHA não retornou execuções. Os resultados verdes observados pertencem a outro SHA. A revisão atual ainda precisa de evidência de CI correspondente ao HEAD atual.

## 3. Próximas etapas

1. Confirmar a execução de CI no HEAD atual do PR #148; corrigir falhas reproduzíveis sem desativar testes.
2. Completar o inventário estático de imports, dependências, contratos, subprocessos, caminhos, manifests, gates e recovery.
3. Auditar os adapters/provedores individualmente e os contratos de áudio, legendas, RenderPlan, FFmpeg/FFprobe e exportação.
4. Revisar segurança, concorrência, isolamento de execução e compatibilidade Termux.
5. Executar FIRST_VIDEO live quando `GEMINI_API_KEY` estiver configurada em GitHub Actions e registrar o artefato MP4 e o resultado FFprobe.
6. Abrir/atualizar PRs pequenos e reversíveis; não mesclar automaticamente.

## 4. Critério de honestidade

Este documento registra somente a linha de base e os achados com evidência disponíveis em 2026-10-12. Não representa auditoria completa, não certifica o HEAD atual como verde e não afirma que um vídeo live foi gerado.
