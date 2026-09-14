# ShortAutoPro Evolution 1.2

## Escopo certificado desta fase

Esta fase mantém a produção principal em português do Brasil. O perfil em inglês foi adiado deliberadamente e não aparece entre os perfis operacionais.

## Shorts com perfil

`profile_run.sh <perfil>` resolve um perfil allow-listed e aplica cenas, voz Piper, loudness, limite visual e políticas de runtime antes de chamar o pipeline oficial.

Perfis operacionais:
- `default`
- `true_crime`
- `cinepulsar`
- `psicotoon`

## Assunto exato

`topic_engine_runtime.py` preserva o Topic Engine automático quando não há assunto exato. Quando `SHORT_TOPIC_EXACT` está definido, o assunto solicitado precisa passar por Wikipedia + Source Identity antes de ser aceito. O modo exato não desliga o gate factual.

## Jobs de cliente

`client_job_create.py` cria jobs PT-BR locais e `client_job_runner.py` executa/retoma item por item. Um item com vídeo e Quality Gate aprovados é pulado numa retomada. Falhas preservam o estado do job.

## Retomada segura de Short

`resume_short.sh` + `resume_short_runtime.py` detectam limites conservadores:
- `post_media`
- `post_audio`
- `post_captions`
- `post_assembly`
- `post_render`
- `complete`

O runtime só pula trabalho quando o artefato correspondente existe e, para a fronteira de mídia, quando o Production Supervisor já foi aprovado. Se não houver prova suficiente, o pipeline completo é reexecutado.

## Long-form V1

`longform_runtime.py` é um motor separado do Shorts e produz vídeo 16:9 por capítulos retomáveis.

Fluxo:
1. verifica o assunto factual;
2. recupera a fonte pública;
3. cria outline e capítulos sem mudar de fonte;
4. gera narração PT-BR;
5. gera áudio com Piper;
6. pesquisa visuais no Wikimedia Commons;
7. salva autor, licença e fonte das mídias;
8. gera legendas ASS;
9. renderiza cada capítulo em H.264/AAC 1920x1080;
10. concatena os capítulos;
11. valida o contrato técnico;
12. salva estado e permite retomada.

Faixa operacional V1: 5 a 60 minutos e 3 a 12 capítulos. A duração real é validada contra uma tolerância em torno do alvo.

Comandos principais:

```bash
python longform_runtime.py run --topic "Assunto real" --minutes 15 --profile true_crime
python longform_runtime.py status
python longform_runtime.py resume
```

## Evolution Center

O menu `evolution_center.sh` reúne dashboard, métricas, inventário, qualidade, E2E, Short com perfil/assunto exato, jobs de cliente, retomada segura de Shorts e produção/retomada de long-form.

## Política de segurança

- sem credencial GitHub no runner de produção;
- sem `eval` de entrada do usuário fora do export allow-listed de perfil;
- nenhum assunto exato pula verificação factual;
- retomada não pula etapas narrativas precoces sem checkpoint seguro;
- artefatos long-form e estados locais ficam fora do Git;
- promoção ao `termux-stable` continua condicionada ao workflow de validação aprovado.
