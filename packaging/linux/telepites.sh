#!/usr/bin/env bash
set -euo pipefail

APP_ID="kozgaz-fm"
APP_NAME="Közgáz FM"
FORRAS="$(cd "$(dirname "$0")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CEL="$DATA_HOME/$APP_ID"
BIN="$HOME/.local/bin"
DESKTOP="$DATA_HOME/applications/$APP_ID.desktop"
IKONOK="$DATA_HOME/icons/hicolor"

sugo() {
    cat <<SUGO
$APP_NAME – Linux-telepítő

Használat:
  ./telepites.sh                telepítés vagy frissítés
  ./telepites.sh --eltavolitas  eltávolítás (a beállítások megmaradnak)
  ./telepites.sh --help         ez a súgó

Telepítés helye: $CEL
Indítás:         a menüből („$APP_NAME”) vagy terminálból: $APP_ID
SUGO
}

eltavolit() {
    rm -rf "$CEL"
    rm -f "$BIN/$APP_ID" "$DESKTOP"
    find "$IKONOK" -name "$APP_ID.*" -delete 2>/dev/null || true
    command -v update-desktop-database >/dev/null && update-desktop-database "$DATA_HOME/applications" || true
    echo "$APP_NAME eltávolítva."
}

ikonok() {
    local mappa="$1"
    for meret in 16 24 32 48 64 128 256 512; do
        if [ -f "$mappa/ikon-$meret.png" ]; then
            install -Dm644 "$mappa/ikon-$meret.png" "$IKONOK/${meret}x${meret}/apps/$APP_ID.png"
        fi
    done
    [ -f "$mappa/ikon.svg" ] && install -Dm644 "$mappa/ikon.svg" "$IKONOK/scalable/apps/$APP_ID.svg"
    true
}

telepit_csomagbol() {
    rm -rf "$CEL"
    mkdir -p "$CEL"
    cp -a "$FORRAS/KozgazFM/." "$CEL/"
    mkdir -p "$BIN"
    ln -sf "$CEL/KozgazFM" "$BIN/$APP_ID"
    ikonok "$FORRAS/ikonok"
}

telepit_forrasbol() {
    local gyoker
    gyoker="$(cd "$FORRAS/../.." && pwd)"
    if ! command -v uv >/dev/null; then
        echo "A forrásból telepítéshez az uv kell: https://docs.astral.sh/uv/" >&2
        exit 1
    fi
    rm -rf "$CEL"
    uv venv -q -p 3.14 "$CEL/venv"
    uv pip install -q -p "$CEL/venv" "$gyoker"
    mkdir -p "$BIN"
    ln -sf "$CEL/venv/bin/kozgaz-fm" "$BIN/$APP_ID"
    ikonok "$gyoker/assets"
}

case "${1:-}" in
    -h|--help) sugo; exit 0 ;;
    --eltavolitas) eltavolit; exit 0 ;;
    "") ;;
    *) sugo; exit 1 ;;
esac

if [ -x "$FORRAS/KozgazFM/KozgazFM" ]; then
    telepit_csomagbol
else
    telepit_forrasbol
fi
mkdir -p "$(dirname "$DESKTOP")"
sed "s|^Exec=.*|Exec=$BIN/$APP_ID|" "$FORRAS/kozgaz-fm.desktop" > "$DESKTOP"
command -v update-desktop-database >/dev/null && update-desktop-database "$DATA_HOME/applications" || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q "$IKONOK" 2>/dev/null || true
echo "$APP_NAME telepítve: $CEL"
case ":$PATH:" in
    *":$BIN:"*) ;;
    *) echo "Figyelem: a $BIN nincs a PATH-ban, a menüből indítsd, vagy add hozzá." ;;
esac
