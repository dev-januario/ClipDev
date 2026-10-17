# ClipDev — Clipboard Manager para GNOME (Ubuntu 22.04)

Data: 2026-10-16

## Objetivo

Gerenciador de área de transferência (clipboard) que vive como ícone na barra
superior direita do GNOME (perto do ícone de Wi-Fi) e é aberto por um atalho
global **Super+V**. Tema escuro preto com detalhes azuis; itens fixados em
amarelo.

Paleta:

| Cor       | Hex       | Uso                          |
|-----------|-----------|------------------------------|
| Azul      | `#0086FF` | Acentos, bordas, seleção     |
| Amarelo   | `#FFC700` | Itens fixados (pino/borda)   |
| Preto     | `#1D212A` | Fundo                        |

## Ambiente alvo (verificado)

- Ubuntu 22.04.5 LTS, GNOME Shell 42.9, sessão X11.
- Extensão `ubuntu-appindicators@ubuntu.com` ativa (ícones de app na barra).
- `/usr/bin/python3.10` com PyGObject 3.42.1 + GTK3 OK.
- `sqlite3`, `Gio.DBus`, `Gdk` OK.
- **Requer:** `gir1.2-ayatanaappindicator3-0.1` (typelib GIR) via apt.
- **Nota:** o `python3` do PATH é 3.11 e quebra o `gi`; o projeto fixa o
  interpretador em `/usr/bin/python3.10`.

## Arquitetura

Processo único (`Gtk.Application`) em Python 3.10 + GTK3:

```
ClipboardMonitor ──► Store (SQLite) ──► images/ (thumb + originais)
      │                    │
      ▼                    ▼
Popup (Gtk.Window) ◄── DBus toggle ◄── Super+V (GSettings keybinding)
Indicator (AyatanaAppIndicator3) ──► Menu (abrir/limpar/sair)
```

## Modelo de dados

SQLite em `~/.local/share/clipdev/clipdev.db`.

Tabela `items`:

| campo        | tipo    | descrição                              |
|--------------|---------|----------------------------------------|
| `id`         | INTEGER | PK autoincrement                       |
| `kind`       | TEXT    | `text` ou `image`                      |
| `content`    | TEXT    | texto OU caminho do arquivo de imagem  |
| `preview`    | TEXT    | texto curto OU caminho da thumbnail    |
| `hash`       | TEXT    | sha256 (dedup), UNIQUE                 |
| `pinned`     | INTEGER | 0/1                                    |
| `created_at` | INTEGER | epoch                                  |
| `updated_at` | INTEGER | epoch                                  |

## Retenção e dedup

- Máximo **50 itens não-fixados** (`MAX_UNPINNED = 50`, configurável).
- Ao estourar, apaga os mais antigos não-fixados, um a um.
- **Fixados nunca são apagados.**
- Dedup: conteúdo existente sobe pro topo (atualiza `updated_at`), sem duplicar.
- Imagens: arquivo original em `images/<hash>.<ext>` + thumbnail 64px;
  limite ~10MB por imagem.

## Captura do clipboard

`Gdk.SELECTION_CLIPBOARD` + sinal `owner-change`, leitura assíncrona
(`request_targets` → `request_text` / `request_image`). Flag anti-loop para
ignorar cópias feitas pelo próprio ClipDev. Sem filtro de senhas (decisão do
usuário: "salvar tudo").

## Popup

- `Gtk.Toplevel` sem decoração, `skip_taskbar`, `keep_above`, ancorada no
  canto superior direito.
- Topo: `Gtk.SearchEntry` com foco automático (busca/filtro).
- Lista: `ScrolledWindow` + `ListBox`, **15 linhas visíveis**, altura de
  **15px por linha**, com barra de rolagem para os demais.
- Texto → preview 1 linha elipsado + ícone de tipo. Imagem → thumbnail.
- Hover → copiar, fixar/desfixar, excluir.
- Teclado: ↑/↓ navega, Enter copia, Delete exclui, Esc fecha.
- Clique → só copia (Ctrl+V manual pelo usuário).
- CSS: fundo `#1D212A`, acentos/seleção `#0086FF`, fixados `#FFC700`.

## Indicador e atalho

- Ícone SVG próprio no painel.
- Menu: "Abrir histórico", "Limpar não-fixados", "Sair".
- **Super+V**: keybinding custom via GSettings
  (`org.gnome.settings-daemon.plugins.media-keys`) → `clipdev toggle` → DBus.
- Autostart: `.desktop` em `~/.config/autostart/`.

## Estrutura de arquivos

```
ClipDev/
  clipdev/            __init__.py, __main__.py, app.py, indicator.py, popup.py,
                      clipboard.py, store.py, images.py, shortcut.py,
                      dbus_service.py, config.py, style.css, icons/clipdev.svg
  scripts/            clipdev, install.sh, uninstall.sh
  tests/              test_store.py, test_images.py, test_retention.py
  docs/superpowers/specs/2026-10-16-clipdev-design.md
  README.md
```

## Testes

- Unitários (pytest) headless para Store/retenção/dedup/images — TDD na
  camada de dados.
- GUI validada por smoke test manual.

## Fora de escopo (YAGNI)

- Sincronização em nuvem, múltiplos dispositivos.
- Detecção de conteúdo sensível.
- Busca fuzzy / regex.
- Colar automaticamente no app em foco.