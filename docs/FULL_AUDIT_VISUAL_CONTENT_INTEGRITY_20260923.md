# ShortAutoPro — Auditoria Completa de Integridade Visual

**Data:** 2026-09-23  
**Escopo:** produção canônica 3.0.3, Stage 6, recuperação, render, QA e release  
**Base auditada:** `bfa217d65e4f2d9c18df1c6014e06e89f305771e`  
**Branch de correção:** `fix/visual-content-integrity-20260923`

## 1. Sintoma real observado

O Short finaliza e possui áudio/legendas, porém o início do vídeo aparece sem conteúdo visual útil. Imagens reais começam a aparecer apenas do meio para o final.

A investigação mostra que o renderer não é a causa primária. Ele recebe 12 arquivos e os monta corretamente na ordem. O erro nasce antes: arquivos gerados como placeholders editoriais neutros eram tratados como mídia válida, persistidos em cache, aprovados por gates técnicos e renderizados normalmente.

## 2. Inventário estrutural do repositório

No snapshot desta auditoria existem:

- 413 arquivos rastreados;
- 311 arquivos Python;
- 141 testes em `tests_sim/`;
- 67 arquivos JSON;
- 15 scripts shell;
- 9 arquivos Markdown;
- aproximadamente 3.09 MB de conteúdo rastreado;
- 181 arquivos na raiz;
- 46 arquivos sob `manifests/`;
- 17 sob `config/`;
- 120 caminhos cujo nome indica versão, bridge, adapter, VI, shadow, legacy ou geração histórica.

A auditoria estrutural cobre toda a árvore rastreada. A revisão linha-a-linha aprofundada foi concentrada no grafo canônico executado por `main.py` e nos módulos compartilhados que podem alterar seus artefatos.

## 3. Grafo canônico relevante

Fluxo visual ativo:

`main.py`
→ planejamento de cena  
→ `visual_query_guard.py`  
→ `visual_shot_bridge.py`  
→ guards de risco/continuidade  
→ `media_stage_runtime.py`  
→ `midia.py`  
→ `media_master_gate.py`  
→ `visual_score_engine.py`  
→ `motion_director.py`  
→ `rhythm_director.py`  
→ `professional_edit_director.py`  
→ `professional_edit_repair.py`  
→ `multi_asset_director.py`  
→ `retention_engine.py`  
→ `production_supervisor.py`  
→ áudio/legendas  
→ `production_recovery.py`  
→ `render_preflight.py`  
→ `video_professional.py`  
→ `v6_professional.py`  
→ `audio_finalizer.py`  
→ `visual_qa.py`  
→ `quality_check.py`  
→ `production_manifest.py`  
→ `final_quality.py`  
→ `professional_quality_gate.py`  
→ `release_gate.py`.

## 4. Causa raiz

### F-001 — CRITICAL — Neutral slate era aceito como mídia de produção

`media_emergency_fallback.py` possui um fallback que, sem fonte real disponível, cria um quadro procedural neutro. Esse quadro é deliberadamente não factual e recebe `truth_claim=NONE`.

Antes desta correção, `midia.py` chamava esse fallback dentro de cada cena ainda durante a primeira passagem. Como as cenas são processadas sequencialmente:

1. cena 1 falha nos providers;
2. não existe ainda nenhuma mídia real aceita;
3. é criado neutral slate para cena 1;
4. cena 2 também não pode usar cena 1 como fonte real porque editorial é excluído;
5. outro neutral slate é criado;
6. o processo pode continuar assim até algum provider finalmente fornecer mídia real;
7. por isso imagens reais aparecem apenas no meio/final do Short.

**Correção:** neutral slate deixa de ser válido para produção. `create_editorial_reuse(..., allow_neutral=False)` retorna ausência em vez de inventar pixels de preenchimento.

### F-002 — CRITICAL — Placeholders voltavam pelo cache incremental

`midia.py` restaurava por hash qualquer asset aprovado pelo relatório antigo `media_quality`, incluindo neutral slates.

**Correção:** cenas marcadas como `neutral_slate` são excluídas do cache. Cenas reais válidas continuam reutilizadas; somente placeholders/faltantes são readquiridos.

### F-003 — HIGH — Cache parcial válido era descartado inteiro

Quando o relatório anterior não restaurava 100% das cenas, `midia.py` limpava `resume_cached_media` completamente.

**Impacto:** aumento de rede, mais rate limit, mais tempo e maior chance de nova falha.

**Correção:** cache parcial real agora é preservado e somente as cenas faltantes/placeholder voltam à aquisição.

### F-004 — HIGH — Estado/commit local podia vazar entre cenas

No bloco `FALLBACK LOCAL FINAL`, chamadas de cleanup/commit ficavam fora de `if origem:`, e havia double commit. Em execução sem origem local, `escolhido` poderia continuar referenciando um candidato anterior da mesma cena que falhou no download.

**Correção:** commit/cleanup local só ocorre depois de cópia real bem-sucedida; removido commit incondicional e duplicado.

### F-005 — HIGH — Ledger canônico era atualizado apenas no primeiro caminho de sucesso

`visual_engine_unified.note_commit_runtime()` era chamado no download primário, mas não de forma consistente em retry simplificado, late recovery, degrade, local ou editorial.

**Impacto:** `selected_media_<SID>.json` podia ter cobertura inferior a 75%. `visual_score_engine.py` então baixava a confiança para OBSERVE e removia `weak_scenes`, impedindo recuperação automática de cenas ruins.

**Correção:** todo caminho de sucesso passa pelo mesmo commit canônico no bloco final da cena.

### F-006 — CRITICAL — Media Master Gate aprovava neutral slate

`media_master_gate.py` conhecia o índice editorial, mas qualquer editorial reuse era apenas warning.

**Correção:** neutral placeholder é erro crítico. Reuso editorial baseado em mídia real permanece permitido, porém limitado por `SAP_MEDIA_EDITORIAL_REUSE_MAX_SCENES` (default 3).

### F-007 — CRITICAL — Pre-render confundia “arquivo decodificável” com “conteúdo visual”

`render_preflight.py` aceitava qualquer arquivo acima de 1000 bytes com stream visual.

**Correção:** preflight lê o índice editorial, bloqueia neutral slates e bloqueia reuso editorial acima do limite. Isso impede render caro com entradas vazias.

### F-008 — HIGH — Refresh não selecionava placeholders editoriais

`visual_media_refresh.py` procurava números de cena principalmente em strings `scene_XX`. O warning antigo `editorial_reuse_scenes=1,2` não entrava como target.

**Correção:** refresh lê diretamente o índice editorial, prioriza todos os neutral slates e reusos editoriais excedentes, move os assets para backup e remove metadado editorial obsoleto.

### F-009 — HIGH — Blackdetect final não prova conteúdo visual

`visual_qa.py` usava `blackdetect` no frame inteiro. Legendas brancas/amarelas já burnadas podem impedir detecção de uma base preta. Além disso, neutral slate não é preto puro: contém ruído, caixas e vignette.

**Correção:** nova auditoria de pixels amostra a região superior sem legenda em 0.15s e no ponto médio de cada cena. Calcula média, desvio, proporção escura e faixa dinâmica com thresholds conservadores. Abertura realmente vazia gera `blank_opening_frame`; cena vazia gera `render_blank_scene_XX`, ambos BLOCK.

### F-010 — CRITICAL — Release Gate usava PASS como default se Visual QA não existisse

Antes:
`vqa.get("status", "PASS")`.

Isso permitia ausência do próprio QA ser interpretada como aprovação.

**Correção:** release agora é fail-closed para:
- relatório de mídia ausente;
- mídia não PASS;
- neutral editorial presente;
- Visual QA ausente;
- Visual QA BLOCK;
- rendered-content measurement ausente;
- abertura vazia;
- qualquer cena renderizada vazia.

### F-011 — HIGH — Production Manifest não carregava integridade visual renderizada

Manifest validava codecs, resolução, áudio, numeração e artefatos, mas não exigia conteúdo visual.

**Correção:** novos flags:
- `media_gate_pass`;
- `neutral_editorial_absent`;
- `visual_qa_present`;
- `visual_qa_not_blocked`;
- `rendered_content_verified`.

### F-012 — HIGH — Final Quality pontuava visual principalmente por técnica/contagem

Um vídeo com 12 arquivos, 1080x1920 e áudio podia obter alta pontuação mesmo com conteúdo visual ruim.

**Correção:** os novos flags de integridade visual do manifest passam a ser obrigatórios em `final_quality.py`.

### F-013 — HIGH — Production Supervisor só validava presença física

Supervisor aceitava `physical_media_12` sem saber se eram placeholders.

**Correção:** supervisor agora exige `media_quality` PASS e bloqueia neutral editorial.

### F-014 — MEDIUM — Renderer era tecnicamente correto, porém content-unaware

`video_professional.py` ordena cenas corretamente e `v6_professional.py` valida codec/duração/decode. Não foi encontrada evidência de offset que “coma” a cena inicial.

O problema é que ambos renderizavam corretamente o asset errado fornecido pelo Stage 6.

**Correção:** conteúdo é certificado antes do renderer e novamente no MP4 final.

### F-015 — MEDIUM — Grande superfície histórica/VI/bridge

Existem muitas gerações de VI, bridges, adapters e policies. Algumas ainda são importadas por `midia.py`, outras são testes/shadow/históricas.

**Risco:** autoridade visual distribuída, fail-open em múltiplas camadas e maior dificuldade de provar qual módulo decidiu a cena.

**Ação nesta correção:** não apagar em massa. A remoção sem análise de import graph pode introduzir regressão. O pipeline canônico é reforçado para que bridges auxiliares não possam transformar placeholder em aprovação final.

## 5. Política nova de mídia

Uma cena de produção somente é considerada concluída quando:

1. existe exatamente um asset primário válido;
2. o arquivo é decodificável;
3. não está marcado como neutral slate;
4. Media Master Gate está PASS;
5. reuso editorial total está dentro do limite;
6. Render Preflight está READY;
7. o MP4 final possui pixels visuais verificáveis na abertura e em cada cena;
8. Visual QA não está BLOCK;
9. Production Manifest registra rendered content como verificado;
10. Release Gate confirma toda a cadeia.

## 6. Fallback editorial após correção

Existem dois conceitos distintos:

**Neutral slate:** quadro gerado sem fonte real. Não pode mais concluir cena de produção.

**Editorial derivative:** composição derivada de uma mídia real já aceita, marcada `truth_claim=NONE`. Pode ser utilizada apenas como último recurso limitado e continua sujeita a duplicate/QA/gates.

O controller final de Stage 6 passa `allow_neutral=False`.

## 7. Recuperação de Shorts antigos

Shorts já produzidos com neutral slates não devem ser considerados saudáveis só porque possuem MP4 final.

Na próxima revalidação:
- Pre-Render identifica o índice;
- Visual Media Refresh remove os placeholders para backup;
- Stage 6 preserva cenas reais;
- reacquire somente cenas ruins;
- neutral não volta pelo cache;
- caso reste um pequeno tail, só source-based editorial pode completar;
- novo Visual QA verifica o MP4 resultante por pixels.

## 8. Matriz de defesa

| Camada | Antes | Depois |
|---|---|---|
| Aquisição in-round | neutral podia concluir | neutral deferred/proibido |
| Cache | neutral reaproveitado | neutral rejeitado |
| Stage 6 final | neutral podia completar | source-based somente |
| Media Master Gate | warning | BLOCK |
| Refresh | não identificava neutral | target prioritário |
| Pre-Render | probe técnico | probe + integridade editorial |
| Visual Score | fallbacks podiam faltar no ledger | commit canônico unificado |
| Supervisor | contagem física | exige media gate sem neutral |
| Final MP4 QA | blackdetect global | opening + cena por pixels |
| Manifest | técnico | inclui visual integrity |
| Final Quality | técnico/editorial | exige visual integrity |
| Release Gate | QA ausente podia virar PASS | fail-closed |

## 9. Riscos residuais

- Providers externos podem sofrer rate limit/offline; não existe garantia de zero falha externa.
- Uma cena pode ser visualmente válida mas semanticamente apenas razoável; isso continua coberto por visual score/MUST/evidence, não pelo blank detector.
- O detector de pixels é propositalmente conservador para não bloquear cenas legitimamente escuras.
- Reuso editorial baseado em fonte real pode reduzir variedade; por isso existe limite e diversidade QA.
- A superfície histórica de VI/bridges ainda merece uma fase futura de consolidação, mas somente após confirmação em Termux de que o pipeline corrigido produz Shorts reais sem regressão.

## 10. Critério de aceite desta correção

A correção só pode ser promovida quando:

- compileall PASS;
- deploy smoke PASS;
- todos os testes simulados PASS;
- regressões críticas Stage 6 PASS;
- testes específicos de visual-content integrity PASS;
- FFmpeg synthetic E2E PASS;
- Bash audit PASS;
- repository audit PASS;
- PR exact-head verde;
- pós-merge em `main` verde;
- promoção para `termux-stable` verde;
- `main` e `termux-stable` idênticos.

## 11. Arquivos diretamente corrigidos

- `media_emergency_fallback.py`
- `midia.py`
- `media_stage_runtime.py`
- `media_master_gate.py`
- `visual_media_refresh.py`
- `render_preflight.py`
- `visual_qa.py`
- `production_supervisor.py`
- `production_manifest.py`
- `final_quality.py`
- `release_gate.py`
- `tools/deploy_smoke.py`
- `.github/workflows/shortautopro-portable.yml`
- testes de regressão associados.

## 12. Conclusão técnica

O defeito “primeiro trecho sem imagens” não era um único bug de FFmpeg. Era uma falha de contrato distribuída: placeholder neutro era criado cedo, contado como sucesso, cacheado, aceito por gates de presença, renderizado corretamente e aprovado por uma cadeia que media estrutura técnica mais do que conteúdo visual.

A correção muda o contrato de ponta a ponta: **placeholder não é mídia**, **arquivo não é evidência de conteúdo**, e **MP4 tecnicamente válido não é publicável sem cobertura visual renderizada comprovada**.
