# ShortAutoPro Consolidation 3.0

Objetivo: consolidar o ShortAutoPro em uma entrada oficial `main.py` e um pipeline único, preservando sourcing factual, perfis e rollback seguro, enquanto integra visual semântico multidimensional, continuidade, retenção, sound design, QA e release gate.

Fluxo oficial:

`tema -> roteiro -> cenas -> midia -> audio -> legenda -> edicao -> QA -> exportacao`

Princípios:
- uma única entrada operacional para Shorts;
- reutilizar módulos especializados comprovados, sem wrappers duplicados;
- cada estágio publica artefato/checkpoint auditável;
- fail-closed para factualidade e integridade técnica;
- auto-reparo limitado e determinístico antes de bloquear;
- runtime local e cache não fazem parte da arquitetura rastreada;
- soluções gratuitas/local-first continuam prioritárias.

## Escopo

1. `main.py` como entrada oficial e orquestrador canônico.
2. Diretor visual estruturado por cena e scoring multidimensional.
3. `visual_continuity_score` e plano de continuidade.
4. Ritmo variável, microcortes/múltiplos assets quando disponíveis, motion e transições por função narrativa.
5. Legendas com auditoria de densidade, safe-area e colisão visual por zona protegida.
6. TTS por perfil, pausas e master final verificado.
7. Sound design/music plan com ducking e limites de mix.
8. `retention_score` antes do render.
9. QA técnico/visual e score de confiança por módulo.
10. Release gate com auto-reparo limitado.
11. Auto-recovery/checkpoints/lock/storage integrados no orquestrador.
12. Auditoria final de código morto/duplicado e promoção somente após CI verde.
