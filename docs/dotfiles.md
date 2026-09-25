# Personal dotfile sources and adaptations

Updated 2026-09-25 from
[jamesbowman/mysettings at 8154b54](https://github.com/jamesbowman/mysettings/tree/8154b54eedb059babe91853c1af3a3c88e397a0f)
and the local Mac's `.zshrc`, `.zsh_aliases`, `.zprofile`, `.tmux.conf`, and
`.vimrc`. The local `.vimrc` points into the local mysettings checkout, which
has uncommitted changes beyond that revision. Those newer Vim preferences took
precedence. No local i3 config was present, so i3 comes from the GitHub version.
The source checkout and live home dotfiles were not modified.

## Included preferences

- **i3:** Terminus 16px, xfce4-terminal, j/k/l/semicolon and arrow navigation,
  ten workspaces, resize mode, launch keys, and the scrot-to-xclip screenshot
  shortcut. The bar stays disabled as in mysettings. The workstation's explicit
  lock shortcut, sleep-lock integration, network applet, policy agent, and exit
  confirmation remain. No power transition bindings were added.
- **tmux:** Ctrl-A prefix, Ctrl-A Ctrl-A for the previous window, Ctrl-A a to
  send a literal Ctrl-A, and the blue bottom status bar with hostname on the
  right. The duplicate original Ctrl-A binding was reduced to its effective
  last-window behavior. Window numbering uses tmux's default zero-based index.
- **zsh:** `$ ` prompt, Emacs editing keys, F5 to run `bash go`, `~/bin` on PATH,
  and separate history when inside Screen. Aliases load from `~/.zsh_aliases`
  regardless of the working directory. The effective vi editor preference is
  represented by Debian's explicitly installed `vim`.
- **Vim:** two-space default indentation, Python/Forth/assembly overrides,
  syntax disabled, industry colors, tags searched upward, cursor restoration,
  MRU, paging keys, `bash go` build shortcuts, and the debug/clipboard mappings.
  Local F5 and upward tag-search changes were retained; Tab remains unbound.
  Literal control bytes were replaced by readable Vim key notation.

The MRU plugin, its documentation, and the Python compiler file are vendored
unchanged from mysettings under `dotfiles/vim/runtime/`. Local plugin/compiler
copies matched GitHub. MRU copyright/license notices remain in the source and
documentation. The help tags are generated from the included documentation.
User setup installs these individual files into `~/.vim/`, preserving unrelated
files and refusing to replace differing existing files or symlinks.

## Debian adaptations

- Homebrew/MacTeX PATH entries and `.zprofile` initialization are omitted.
- Vim F8 uses the X11 clipboard via `xclip`, replacing `pbpaste`; F9 uses that
  same clipboard. The superseded Taglist and timestamp mappings were omitted.
- The optional `~/.vim/forth.vim` hook is guarded because that file was absent.
- F3 retains the project-specific system-test shortcut, uses `python3`, and
  restores the search register it actually saved. It requires that project's
  `src/tests/systemtests.py`; it is not run during setup or Vim startup.
- `ac` activates the current project's `.venv`, replacing a fixed Mac pyenv path.
  `p` invokes `python3`, which also respects an activated Python venv.
- `lh DIRECTORY` uses zsh's history stack and `.zsh_history`; `fc -P` returns to
  the previous history. `ii` forwards arguments to `gh issue view --web` correctly.
- `gp` pushes only after a successful pull. `proj` retains the explicit GitHub
  clone/project-bootstrap workflow with argument and failure checks. These
  commands run only when invoked, never while loading shell configuration.
- The optional `rs` alias is defined only when `~/bin/rs` exists. The legacy
  transfer.sh uploader and unrelated bootstrap/disk scripts are not included.
- `.xbindkeysrc` is not installed: it depends on an unavailable `macwave` helper
  and remaps Delete globally; relevant i3 shortcuts are already covered above.

The manifests add tig/gh and xfce4-terminal/Terminus/xclip/scrot for these
preferences. GitHub CLI authentication is separate and interactive. No credentials,
history databases, cache files, or repository-local environment files were copied.

Vim retains the original explicit `.local.vim` workflow; opening Vim in a project
sources that file if present. Use this only with trusted projects. Personal
machine overrides can use `~/.vimrc.local` and `~/.zshrc.local`.

## Validation

The configs loaded in isolated temporary-home Vim and zsh processes and a tmux
server with a private socket on macOS. Vim checks covered MRU loading, key maps,
Python/Forth indentation and the compiler file; tmux confirmed the Ctrl-A prefix.
The repository fixture suite covers installation/preservation of the added
assets. No Linux installation commands or live home configuration changes ran.
On Debian, run `i3 -C -c dotfiles/i3/config`, then check the terminal/font,
screenshot/clipboard, resize keys, and screen-lock behavior in an X11 session.
