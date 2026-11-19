# Sourced by every tool: what differs between Linux, macOS and Windows (Git Bash), so the scripts need not know.
# Each tool runs under bash 3.2 (macOS's own) with the BSD or GNU userland, or Git Bash's MSYS one:
# no GNU-only flags (sed -i, ls --time-style), no bash 4 (wait -n, mapfile, declare -A), no python3 or bc.
case "$(uname -s)" in
  Darwin) OS=mac ;;
  MINGW*|MSYS*|CYGWIN*) OS=windows ;;
  *) OS=linux; grep -qi microsoft /proc/version 2>/dev/null && OS_WSL=1 ;;
esac
export OS
export PYTHONUTF8=1   # Windows' Python otherwise reads and writes cp1252, and every script, plan and narration is UTF-8
# Where the renders live: each video is copied here and rendered (tools/sync.sh); caches stay between runs
export RENDER_ROOT="${RENDER_ROOT:-$HOME/slab_render}"
# TinyTeX (manim's LaTeX) installs into a per-OS folder with its own per-OS bin
case "$OS" in
  mac) TEX_BIN="$HOME/Library/TinyTeX/bin/universal-darwin" ;;
  windows) TEX_BIN="$(cygpath -u "${APPDATA:-$HOME/AppData/Roaming}")/TinyTeX/bin/windows" ;;
  *) TEX_BIN="$HOME/.TinyTeX/bin/x86_64-linux" ;;
esac
# (last on Windows: TinyTeX's bin holds DLLs, which a Python extension would otherwise load in place of its own)
if [ "$OS" = windows ]; then export PATH="$HOME/.pixi/bin:$PATH:$TEX_BIN"
else export PATH="$HOME/.pixi/bin:$TEX_BIN:$HOME/.local/bin:$PATH"; fi

ncpu() { nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4; }
# memory free for renders, in GB (macOS reports no "available": take 60% of the total)
mem_gb() {
  if [ -r /proc/meminfo ]; then awk '/MemAvailable/ {print int($2 / 1048576)}' /proc/meminfo
  else echo $(( $(sysctl -n hw.memsize 2>/dev/null || echo 8589934592) * 6 / 10 / 1073741824 )); fi
}
# a path as a native program takes it: C:/... for a Windows program, from Git Bash or from WSL; itself elsewhere.
# ffmpeg reads list.txt itself, so a path written into a file needs this even where the shell would convert it.
natpath() {
  case "$OS" in windows) cygpath -m "$1" ;; *) if [ -n "${OS_WSL:-}" ] && [ "${2:-}" = exe ]; then wslpath -m "$1"; else echo "$1"; fi ;; esac
}
# strip Windows line endings from files in place (a checkout with autocrlf breaks bash on every \r)
strip_cr() { for f in "$@"; do tr -d '\r' < "$f" > "$f.lf" && mv "$f.lf" "$f"; done; }
# a stdlib-only Python for the small helpers (timelog, review times): the system's, else pixi's own
pyhost() {
  for p in python3 python; do "$p" -c "import sys; sys.exit(sys.version_info < (3, 9))" >/dev/null 2>&1 && { "$p" "$@"; return; }; done
  pixi exec python "$@"
}
# a program from the current folder's pixi env, as a path the shell can run (each `pixi run` costs ~0.4 s)
envbin() {
  local p; p="$(pixi run python -c "import shutil, sys; print(shutil.which(sys.argv[1]) or '')" "$1" | tr -d '\r')"
  [ "$OS" = windows ] && [ -n "$p" ] && p="$(cygpath -u "$p")"
  echo "$p"
}
# the Kokoro voice's own env (voices.py runs it with pixi, which installs it on first use), set up once
ensure_kokoro() {
  local d="${KOKORO_ENV:-$HOME/kokoro_env}"
  local src; src="$(dirname "${BASH_SOURCE[0]}")/kokoro_env/pixi.toml"
  cmp -s "$src" "$d/pixi.toml" || { mkdir -p "$d" && cp "$src" "$d/"; }   # kept current: pixi re-solves on change
  # installed here, once, not by the first narration: two voice workers each starting `pixi run` on a missing env
  # race to install it, and the loser's error went nowhere (Windows CI)
  case "${TTS:-kokoro}" in kokoro) pixi install -q --manifest-path "$d/pixi.toml" || echo "kokoro env did not install ($d)" >&2 ;; esac
}
# TinyTeX with the packages manim's MathTex needs, installed once (no admin rights needed)
ensure_tex() {
  command -v dvisvgm >/dev/null && command -v latex >/dev/null && return
  echo "== installing TinyTeX (once)"
  case "$OS" in
    windows) local t; t="$(mktemp -d)"; curl -fsSL -o "$t/tt.ps1" "https://tinytex.yihui.org/install-bin-windows.ps1"
             powershell -ExecutionPolicy Bypass -File "$(cygpath -w "$t/tt.ps1")" ;;
    *) curl -fsSL "https://yihui.org/tinytex/install-bin-unix.sh" | sh ;;
  esac
  local pk="standalone preview dvisvgm doublestroke babel-english cm-super lm amsfonts"
  if [ "$OS" = windows ]; then cmd //c "$(cygpath -w "$TEX_BIN/tlmgr.bat")" install $pk; else tlmgr install $pk; fi
  command -v latex >/dev/null || { echo "TinyTeX did not install: no latex in $TEX_BIN" >&2; return 1; }
}
