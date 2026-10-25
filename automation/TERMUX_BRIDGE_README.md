# ShortAutoPro Termux Stable Bridge

Este bridge mantém o Termux sincronizado apenas com commits aprovados pelo workflow `ShortAutoPro Remote Control`.

## Fluxo

1. Alterações entram em `main`.
2. O runner Windows self-hosted executa os testes.
3. Somente quando o workflow termina com `success`, o workflow `Promote Termux Stable` move `termux-stable` para o SHA testado.
4. O Termux consulta `termux-stable` a cada 15 minutos.
5. O instalador configura `cronie`/`util-linux` quando faltam, preserva o crontab existente e prepara o arranque do cron via Termux:Boot.
6. O bridge aceita apenas fast-forward, preserva alterações locais rastreadas e faz rollback automático se a validação de sintaxe falhar.

## Instalação única no Termux

Dentro de `~/ShortAutoPro`, atualize o repositório e execute:

```bash
git fetch origin main
git switch main
git pull --ff-only origin main
bash automation/install_termux_bridge.sh
```

Esse é o instalador canônico. O antigo `install_termux_autosync.sh` permanece como atalho compatível e delega para ele, sem manter uma segunda agenda. O agendamento único é de 15 minutos.

O instalador preserva o crontab existente e salva uma cópia em:

```text
~/.shortautopro_bridge/crontab.before_bridge.txt
```

## Status

```bash
git -C ~/ShortAutoPro branch --show-current
git -C ~/ShortAutoPro rev-parse --short HEAD
tail -n 50 ~/.shortautopro_bridge/bridge.log
crontab -l
```

A branch esperada no Termux é `termux-stable`. Para iniciar o cron após reiniciar o Android, instale também o aplicativo Termux:Boot pela mesma fonte do Termux e abra-o uma vez. Sem o Termux:Boot, o sincronismo funciona enquanto o processo `crond` permanecer ativo.

## Execução manual

```bash
~/ShortAutoPro/automation/termux_bridge.sh
```

## Remover somente o auto-sync

```bash
crontab -l | grep -v '# SHORTAUTOPRO_TERMUX_BRIDGE' | crontab -
```

Isso não apaga o ShortAutoPro nem altera as outras tarefas do cron.
