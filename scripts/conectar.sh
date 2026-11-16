#!/usr/bin/env bash
# Prepara este clon para trabajar: Obsidian con auto-pull sobre vault/. Idempotente.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
vault="$root/vault"
plugin="$vault/.obsidian/plugins/obsidian-git"
mkdir -p "$plugin"

if [ ! -f "$plugin/main.js" ]; then
  base="https://github.com/Vinzent03/obsidian-git/releases/latest/download"
  for f in main.js manifest.json styles.css; do curl -fsSL "$base/$f" -o "$plugin/$f"; done
fi
if [ ! -f "$plugin/data.json" ]; then
  # Solo pull: los cambios suben por PR, nunca push directo a main.
  echo '{"autoPullOnBoot":true,"autoPullInterval":10,"autoSaveInterval":0,"autoPushInterval":0,"disablePush":true}' > "$plugin/data.json"
fi

uri="obsidian://open?path=$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "$vault")"
if [ "$(uname)" = "Darwin" ]; then
  [ -d /Applications/Obsidian.app ] || { command -v brew >/dev/null && brew install --cask obsidian; } || true
  [ -d /Applications/Obsidian.app ] && open "$uri" && echo "OK: bóveda abierta en Obsidian. Acepta 'Confiar en el autor y activar plugins' la primera vez." \
    || echo "AVISO: instala Obsidian (https://obsidian.md) y abre $vault como bóveda."
elif command -v obsidian >/dev/null; then
  xdg-open "$uri" >/dev/null 2>&1 &
  echo "OK: bóveda abierta en Obsidian. Acepta 'Confiar en el autor y activar plugins' la primera vez."
else
  echo "AVISO: instala Obsidian (https://obsidian.md) y abre $vault como bóveda."
fi
echo "OK: plugin Git listo (pull al abrir y cada 10 min, sin push)."
