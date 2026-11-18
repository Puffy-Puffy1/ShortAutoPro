# ShortAutoPro Studio no Termux

Esta versão estende o **pipeline canônico** do ShortAutoPro. Não cria um segundo motor de vídeo e não publica em redes sociais: gera o MP4 e os arquivos de apoio para você revisar e publicar.

## O que pode gerar

| Perfil | Duração | Quadro | FPS | Cenas |
|---|---:|---:|---:|---:|
| Short | 30 s | 1080 × 1920 (vertical) | 30 | 8 |
| Short | 45 s | 1080 × 1920 (vertical) | 30 | 12 |
| Short | 60 s | 1080 × 1920 (vertical) | 30 | 16 |
| Longo | 10 min | 1280 × 720 (horizontal) | 24 | 30 |
| Longo | 15 min | 1280 × 720 (horizontal) | 24 | 45 |
| Longo | 20 min | 1280 × 720 (horizontal) | 24 | 60 |

Estilos aceitos: documentário, cinematográfico, storytelling, animação, anime, cartoon, minimalista, educativo, terror, mistério, histórico, natureza e tecnologia.

Os estilos orientam a direção visual, as buscas de mídia e a edição. O renderizador local faz movimento de câmera (pan/zoom), cortes, trilha/voz e legendas; **não é um modelo local de geração de vídeo/anime**. A qualidade e a variedade de imagens dependem das fontes gratuitas de mídia encontradas para o tema.

## Instalação no Termux

Use Termux atualizado em Android ARM64. Mantenha espaço livre: a pré-verificação exige 1,2 GB para Shorts e 2,5 GB para vídeos longos; compilação e modelos podem precisar de espaço adicional.

1. Instale Git e baixe o repositório:

```bash
pkg update -y
pkg install -y git
git clone https://github.com/Puffy-Puffy1/ShortAutoPro.git
cd ~/ShortAutoPro
git fetch origin feat/termux-longform-studio-20261118
git checkout feat/termux-longform-studio-20261118
```

2. Execute o instalador:

```bash
bash termux_setup.sh
```

O instalador instala Python/FFmpeg, compila Whisper.cpp e baixa o modelo Whisper base e a voz pt-BR Faber. A voz é verificada por SHA-256. O executável Piper para Termux é fornecido por um projeto comunitário separado; por segurança, o instalador **não instala automaticamente um pacote binário de terceiros**. Ele mostra a página de releases para você revisar e instalar a versão ARM64. Depois, execute novamente `bash termux_setup.sh`.

3. Abra o painel:

```bash
bash control_center.sh
```

Escolha a opção **35 — Studio - Criar Short ou vídeo longo** e informe formato, duração, tema e estilo.

## Comandos diretos

Short vertical de 45 segundos:

```bash
python main.py studio --format short --duration 45 --theme "história" --style cinematic
```

Vídeo horizontal de 10 minutos:

```bash
python main.py studio --format long --duration 10 --theme "ciência" --style documentary
```

Assunto exato (não use junto com `--theme`):

```bash
python main.py studio --format long --duration 10 --topic "Apollo 11" --style historical
```

## O que significa “gratuito”

O modo gratuito é o padrão e desativa a chave Gemini. Voz, transcrição e montagem são executadas localmente com Piper, Whisper.cpp e FFmpeg. Pesquisa e obtenção de mídia ainda precisam de internet e dependem de serviços/fontes gratuitos disponíveis. Algumas fontes opcionais podem exigir chave; nenhuma chave paga é obrigatória para o modo gratuito. Dados móveis e armazenamento do aparelho continuam sendo custos do usuário.

Em vídeos longos, a geração é bloqueada quando a fonte pública não contém texto factual suficiente para a duração escolhida. O fallback local reutiliza frases documentadas, preserva a ordem e não repete afirmações para preencher tempo.

## Saída e validação

O pipeline guarda o MP4 em `~/ShortAutoPro/videos/short_v6_<ID>.mp4` e tenta copiá-lo para a pasta Downloads compartilhada do Android. Também cria relatório de produção, fontes e pacote com título/descrição/hashtags.

Antes de tratar a versão como pronta para uso diário, é necessário validar o pipeline completo em um aparelho Termux real e assistir a um MP4 de ponta a ponta. O CI do GitHub valida compilação, shell, configuração, legenda, roteiro, Piper e um smoke test de renderização FFmpeg; isso não substitui um teste real de 10–20 minutos no celular.
