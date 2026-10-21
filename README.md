# ClipDev

Gerenciador de área de transferência (**clipboard**) para GNOME/Ubuntu, com
ícone na barra superior (perto do Wi‑Fi) e abertura por atalho global **Super+V**.

O repositório também inclui o setup do **Flameshot** (captura de tela) na tecla
**Print** — usando a interface própria do Flameshot, sem o seletor nativo do
GNOME.

![tema](docs/preview.png)

- **Versão:** 1.1.0
- **App ID:** `io.github.clipdev.ClipDev`
- **Ambiente alvo:** Ubuntu 22.04 / GNOME 42, sessão **X11**
- **Stack:** Python 3.10 (sistema) + PyGObject + GTK3 + SQLite + DBus + GSettings

## Índice

- [Visão geral](#visão-geral)
- [Recursos](#recursos)
- [Flameshot (captura de tela)](#flameshot-captura-de-tela)
- [Requisitos](#requisitos)
- [Instalação (passo a passo)](#instalação-passo-a-passo)
- [Primeiros passos](#primeiros-passos)
- [Comandos da CLI](#comandos-da-cli)
- [Usando o popup](#usando-o-popup)
- [Ícone na barra](#ícone-na-barra)
- [Preferências](#preferências)
- [API DBus](#api-dbus)
- [Onde os dados ficam](#onde-os-dados-ficam)
- [Configuração (constantes)](#configuração-constantes)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Desenvolvimento e testes](#desenvolvimento-e-testes)
- [Solução de problemas](#solução-de-problemas)
- [Desinstalação](#desinstalação)

---

## Visão geral

O ClipDev roda como um **processo único** (`Gtk.Application`) em Python 3.10 +
GTK3. Ele observa a área de transferência, persiste tudo em **SQLite**, mostra um
**popup** de histórico com busca e itens fixáveis, desenha um **ícone** no painel
superior e responde ao atalho global **Super+V** (via GSettings → DBus).

```
ClipboardMonitor ──► Store (SQLite) ──► images/ (originais + thumbnails)
      │                    │
      ▼                    ▼
Popup (Gtk.Window) ◄── DBus toggle ◄── Super+V (GSettings keybinding)
Indicator (AyatanaAppIndicator3) ──► Menu (abrir / limpar / preferências / sair)
```

## Recursos

- Ícone no painel superior direito (**AyatanaAppIndicator3**).
- Atalho global **Super+V** para abrir/fechar o histórico.
- Histórico persistente de **até 50 itens não-fixados** (`MAX_UNPINNED = 50`),
  configurável. Os mais antigos saem primeiro; itens **fixados nunca são
  apagados**.
- Suporta **texto e imagens**. Imagens são salvas em disco (original + thumbnail)
  e podem ser copiadas de volta.
- Na lista, a imagem aparece como **prévia quadrada de 30×30px** (nunca a imagem
  inteira).
- **Dedup automático**: copiar algo que já existe promove o item ao topo, sem
  duplicar.
- **Seções** “Fixados” e “Não fixados”.
- Cada item tem **estrela para fixar** (cinza → amarela) e **barra vertical
  colorida** à esquerda (amarela nos fixados).
- **Busca/filtro** no popup; **15 linhas visíveis** de **40px** (rolagem para as
  demais).
- **Tamanho da fonte ajustável** (padrão **14px**; de **8** a **20px**) pelos
  botões `−`/`+` no rodapé e na janela de Preferências — a altura da linha
  acompanha.
- Botão **Limpar não fixados** no rodapé.
- Tema escuro: fundo `#1D212A`, azul `#0086FF`, fixados em amarelo `#FFC700`.
- **Autostart** no login e controle por **DBus**.
- Integração com o **Flameshot** na tecla **Print** (setup opcional): o
  `scripts/flameshot-setup.sh` instala o Flameshot nativo em `~/.local` e aponta
  o Print para ele — usando a interface própria do Flameshot, sem o seletor
  "Captura de tela" do GNOME.

## Requisitos

- **Ubuntu 22.04 / GNOME 42** (testado), sessão **X11**.
- `/usr/bin/python3.10` com **PyGObject** e **GTK3** (`python3-gi`,
  `gir1.2-gtk-3.0`) — já vêm no Ubuntu.
- **`gir1.2-ayatanaappindicator3-0.1`** — necessário para o **ícone na barra**.
- Extensão **`ubuntu-appindicators@ubuntu.com`** ativa no GNOME (para desenhar o
  ícone).
- `sqlite3`, `Gio.DBus` e `Gdk` (todos disponíveis por padrão).

> **Importante:** o projeto usa o `python3.10` do **sistema** porque é ele que
> tem o PyGObject. Se o seu `python3` do PATH for outro (ex.: 3.11 via pyenv),
> não afeta — o launcher fixa `/usr/bin/python3.10`.

## Instalação (passo a passo)

### 1. Pré-requisitos do sistema

```bash
sudo apt update
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1
```

Confirme que a extensão de ícones do GNOME está ativa:

```bash
gnome-extensions list --enabled | grep appindicators
```

### 2. Obtenha o código

```bash
git clone <url-do-repositório> ClipDev
cd ClipDev
```

### 3. Rode o instalador

```bash
./scripts/install.sh
```

O `install.sh` faz, em ordem:

1. Verifica se o typelib do **AyatanaAppIndicator3** está presente (avisa se
   faltar).
2. Valida a sanidade do **PyGObject/GTK3** em `/usr/bin/python3.10` (aborta se
   faltar).
3. Cria o comando **`~/.local/bin/clipdev`** (symlink para `scripts/clipdev`) e
   o marca como executável.
4. Registra o atalho **Super+V** (`clipdev install-shortcut`).
5. Habilita o **autostart** no login (`clipdev autostart-install`).
6. Recarrega o serviço de atalhos do GNOME (`gsd-media-keys`) para o Super+V
   valer imediatamente.

### 4. Garanta que `~/.local/bin` está no PATH

Se o comando `clipdev` não for encontrado, adicione ao `~/.bashrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### 5. Inicie o ClipDev

```bash
clipdev run &     # inicia agora (ou simplesmente aperte Super+V)
```

### 6. Verifique a instalação

```bash
clipdev status
```

Saída esperada:

```
Daemon rodando: sim
Atalho instalado: sim
Autostart: sim
Ícone (AppIndicator): disponível
```

### 7. (Opcional) Instale o Flameshot na tecla Print

```bash
./scripts/flameshot-setup.sh
```

Baixa o Flameshot **nativo** (v11) para `~/.local` e aponta a tecla **Print**
para ele. **Requer sessão X11 (Xorg)** — no Wayland o Flameshot nativo não
captura e cai no portal do GNOME.

## Primeiros passos

1. Copie qualquer coisa (Ctrl+C) — o ClipDev captura automaticamente.
2. Aperte **Super+V** para abrir o histórico no canto superior direito.
3. Navegue e pressione **Enter** para copiar de volta (ou clique no item).
4. Cole com **Ctrl+V** no app de destino.

## Comandos da CLI

| Comando                       | O que faz                                        |
|-------------------------------|--------------------------------------------------|
| `clipdev run`                 | Inicia o daemon (ícone na barra).                |
| `clipdev toggle`              | Abre/fecha o popup (alvo do Super+V).            |
| `clipdev open`                | Abre o popup.                                    |
| `clipdev quit`                | Encerra o daemon.                                |
| `clipdev status`              | Mostra daemon/atalho/autostart/ícone.            |
| `clipdev clear`               | Apaga os itens **não-fixados**.                  |
| `clipdev install-shortcut`    | Registra o atalho Super+V.                       |
| `clipdev uninstall-shortcut`  | Remove o atalho Super+V.                         |
| `clipdev autostart-install`   | Inicia no login.                                 |
| `clipdev autostart-remove`    | Não inicia no login.                             |

Sem argumentos, `clipdev` imprime a ajuda.

## Usando o popup

**Teclado**

| Tecla            | Ação                     |
|------------------|--------------------------|
| Digitar          | Filtra/busca no histórico |
| **↑ / ↓**        | Navega na lista          |
| **Enter**        | Copia o item selecionado |
| **Delete**       | Exclui o item selecionado |
| **Esc**          | Fecha o popup            |

**Mouse**

- **Clique** no item → copia (depois use Ctrl+V).
- No **hover** aparecem os botões: **estrela** (fixar/desafixar), **copiar** e
  **excluir**.
- **Rodapé:** `−`/`+` ajustam a fonte, **⚙** abre Preferências e **Limpar não
  fixados** apaga o histórico não fixado.
- O popup fecha automaticamente ao perder o foco.

## Ícone na barra

O ícone fica no painel superior direito. O **clique esquerdo simples sempre abre
o menu** — é uma limitação da extensão `ubuntu-appindicators` no GNOME 42, não do
ClipDev.

- **Menu:** Abrir histórico, Preferências, Limpar não fixados, Sair.
- Para abrir o histórico **diretamente**, use o **Super+V** ou o **duplo-clique**
  (ou clique do meio) no ícone.

## Preferências

Ajuste o **tamanho da fonte** da lista (`FONT_MIN` 8px até `FONT_MAX` 20px,
padrão 14px). Acessível pelo botão **⚙** no rodapé do popup, pelo menu do ícone
ou pelos botões `−`/`+` do rodapé. A preferência é salva em `settings.json` e a
altura das linhas se ajusta automaticamente.

## API DBus

O daemon assume o nome `io.github.clipdev.ClipDev.Control` no barramento de
sessão, no caminho `/io/github/clipdev/ClipDev`, com a interface
`io.github.clipdev.ClipDev`:

| Método   | Ação                    |
|----------|-------------------------|
| `Toggle` | Abre/fecha o popup      |
| `Open`   | Abre o popup            |
| `Clear`  | Limpa itens não-fixados |
| `Quit`   | Encerra o daemon        |

Exemplo com `gdbus`:

```bash
gdbus call --session \
  --dest io.github.clipdev.ClipDev.Control \
  --object-path /io/github/clipdev/ClipDev \
  --method io.github.clipdev.ClipDev.Toggle
```

## Onde os dados ficam

Tudo em `~/.local/share/clipdev/` (ou `$XDG_DATA_HOME/clipdev`):

```
~/.local/share/clipdev/
├── clipdev.db          # banco SQLite (histórico)
├── settings.json       # preferências (ex.: font_size)
└── images/
    ├── <hash>.<ext>    # imagem original
    └── <hash>_thumb.png # thumbnail
```

O autostart fica em `~/.config/autostart/clipdev.desktop`.

### Modelo de dados (tabela `items`)

| Campo        | Tipo    | Descrição                                |
|--------------|---------|------------------------------------------|
| `id`         | INTEGER | PK autoincrement                         |
| `kind`       | TEXT    | `text` ou `image`                        |
| `content`    | TEXT    | texto **ou** caminho do arquivo de imagem |
| `preview`    | TEXT    | texto curto **ou** caminho da thumbnail  |
| `hash`       | TEXT    | sha256 (dedup), `UNIQUE`                 |
| `pinned`     | INTEGER | 0/1                                      |
| `created_at` | INTEGER | epoch (ms)                               |
| `updated_at` | INTEGER | epoch (ms)                               |

## Configuração (constantes)

Definidas em `clipdev/config.py`:

| Constante          | Valor      | Descrição                              |
|--------------------|------------|----------------------------------------|
| `APP_VERSION`      | `1.1.0`    | Versão                                 |
| `MAX_UNPINNED`     | `50`       | Máx. de itens não-fixados              |
| `VISIBLE_ROWS`     | `15`       | Linhas visíveis sem rolar              |
| `ROW_HEIGHT`       | `40`       | Altura da linha (px)                   |
| `POPUP_WIDTH`      | `440`      | Largura do popup (px)                  |
| `FONT_MIN`/`MAX`   | `8` / `20` | Faixa do tamanho de fonte              |
| `FONT_DEFAULT`     | `14`       | Fonte padrão (px)                      |
| `THUMB_SIZE`       | `128`      | Thumbnail armazenada (px)              |
| `ROW_ICON_SIZE`    | `30`       | Ícone de texto na linha (px)           |
| `ROW_THUMB_SIZE`   | `30`       | Prévia quadrada da imagem (px)         |
| `MAX_IMAGE_BYTES`  | `10485760` | Limite de 10 MB por imagem             |
| `COLOR_BLUE`       | `#0086FF`  | Acento/seleção                         |
| `COLOR_YELLOW`     | `#FFC700`  | Itens fixados                          |
| `COLOR_RED`        | `#FF3B30`  | Ação destrutiva                        |
| `COLOR_BLACK`      | `#1D212A`  | Fundo                                  |

## Flameshot (captura de tela)

O projeto inclui o setup do **Flameshot** para a tecla **Print**, gerenciado
pelo script `scripts/flameshot-setup.sh`:

```bash
./scripts/flameshot-setup.sh
```

O que ele faz:

1. Baixa o pacote `flameshot` do apt **sem instalar no sistema**.
2. Extrai o binário para `~/.local/opt/flameshot/` e cria o launcher
   `~/.local/bin/flameshot` (já no PATH do usuário).
3. Aponta a tecla **Print** para `flameshot gui` (reaproveitando o binding
   existente, se houver).
4. Garante a precedência do Flameshot nativo (desktop file + serviço D-Bus do
   usuário) sobre outras instalações (ex.: flatpak).
5. Recarrega o serviço de atalhos do GNOME (`gsd-media-keys`).

> **Requer sessão X11 (Xorg).** No Wayland o Flameshot nativo não captura e o
> seletor de área fica por conta do portal do GNOME ("Captura de tela"). O
> Flameshot **flatpak** (v14) também delega ao portal mesmo no X11 — por isso o
> setup usa o **nativo**.

Para desfazer:

```bash
rm -f ~/.local/bin/flameshot ~/.local/opt/flameshot/flameshot
rm -f ~/.local/share/applications/org.flameshot.Flameshot.desktop
rm -f ~/.local/share/dbus-1/services/org.flameshot.Flameshot.service
```

## Estrutura do repositório

```
ClipDev/
├── README.md
├── .gitignore
├── clipdev/                      # pacote principal
│   ├── __init__.py               # expõe APP_ID/APP_NAME/APP_VERSION
│   ├── __main__.py               # CLI (argparse) + comandos
│   ├── app.py                    # Gtk.Application: junta tudo
│   ├── clipboard.py              # monitor do clipboard (texto e imagem)
│   ├── store.py                  # persistência SQLite (dedup, pin, retenção)
│   ├── images.py                 # salva imagem + thumbnail, prévia quadrada
│   ├── popup.py                  # janela do histórico (seções, estrela, fonte)
│   ├── prefs.py                  # janela de preferências (tamanho da fonte)
│   ├── indicator.py              # ícone na barra (AyatanaAppIndicator3)
│   ├── shortcut.py               # atalho global Super+V (GSettings)
│   ├── dbus_service.py           # controle por DBus (toggle/open/clear/quit)
│   ├── autostart.py              # inicialização no login (.desktop)
│   ├── config.py                 # caminhos, constantes e paleta
│   ├── style.css                 # tema escuro
│   └── icons/
│       └── clipdev.svg           # ícone da barra
├── scripts/
│   ├── clipdev                   # launcher (fixa /usr/bin/python3.10)
│   ├── install.sh                # instalador
│   ├── uninstall.sh              # desinstalador
│   ├── test.sh                   # roda a suíte de testes
│   ├── flameshot-setup.sh        # instala o Flameshot nativo na tecla Print
│   └── preview_popup.py          # gera PNG de preview do popup
├── tests/                        # testes unitários (pytest, headless)
│   ├── test_store.py             # Store: add/dedup/limpar/busca/delete
│   ├── test_retention.py         # retenção + limpeza de arquivos de imagem
│   ├── test_images.py            # salvar/thumbnail/prévia quadrada
│   └── test_config.py            # preferências (load/save/clamp)
└── docs/
    ├── preview.png               # captura do popup
    └── superpowers/specs/
        └── 2026-10-16-clipdev-design.md   # spec de design
```

## Desenvolvimento e testes

```bash
./scripts/test.sh                     # roda os testes (pytest -v)
python3.10 scripts/preview_popup.py   # gera um PNG de preview do popup
```

- Os testes rodam **headless** (sem display), usando `CLIPDEV_DATA_DIR` para
  isolar os dados em diretório temporário.
- Para apontar os dados para outro diretório:
  `export CLIPDEV_DATA_DIR=/tmp/algum`.

## Solução de problemas

### O Super+V não funciona de imediato

O GNOME (`gsd-media-keys`) às vezes não recarrega atalhos recém-criados, e um
clipboard manager antigo (ex.: **Diodon**) pode estar segurando `<Super>v`.

```bash
# ver se outro app ocupa o Super+V
gsettings list-recursively | grep "'<Super>v'"

# recarregar o serviço de atalhos (ou simplesmente faça logout/login)
killall gsd-media-keys    # o GNOME sobe de novo automaticamente
```

### O ícone não aparece na barra

Confirme que o pacote e a extensão estão presentes:

```bash
sudo apt install gir1.2-ayatanaappindicator3-0.1
clipdev status   # deve mostrar "Ícone (AppIndicator): disponível"
```

Sem o typelib GIR o ícone não sobe, mas o resto do app (popup, atalho, DBus)
continua funcionando.

### `clipdev: command not found`

Adicione `~/.local/bin` ao PATH (veja o passo 4 da instalação) ou chame o
launcher diretamente: `./scripts/clipdev status`.

### O `python3` do PATH quebra o `gi`

Não use o `python3` do PATH — o launcher e os scripts fixam o interpretador em
`/usr/bin/python3.10`, que é onde o PyGObject vive.

### O Print abre o "Captura de tela" do GNOME em vez do Flameshot

Causas prováveis:

- Sessão **Wayland**: o Flameshot nativo não captura e o GNOME assume o Print.
  Troque para "Ubuntu on Xorg" na tela de login.
- Comando do Print apontando para o **flatpak** do Flameshot (v14), que delega a
  captura ao portal do GNOME mesmo no X11.

Solução: rode `./scripts/flameshot-setup.sh` na sessão X11 e confira o comando:

```bash
gsettings get org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ command
# esperado: 'flameshot gui'
```

## Desinstalação

```bash
./scripts/uninstall.sh
```

Isso encerra o daemon, remove o atalho, o autostart e o comando
`~/.local/bin/clipdev`. **Os seus dados são mantidos.** Para apagar também o
histórico e as imagens:

```bash
rm -rf ~/.local/share/clipdev
```