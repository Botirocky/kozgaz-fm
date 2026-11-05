#!/bin/sh
set -e
ITT="$(cd "$(dirname "$0")/.." && pwd)"
export KOZGAZ_FM_ADAT="${KOZGAZ_FM_ADAT:-$HOME/.local/share/kozgaz-fm-web}"
if [ -z "${KOZGAZ_FM_ZENE:-}" ]; then
    KOZGAZ_FM_ZENE="$(xdg-user-dir MUSIC 2>/dev/null || true)"
    [ -n "$KOZGAZ_FM_ZENE" ] && [ "$KOZGAZ_FM_ZENE" != "$HOME" ] || KOZGAZ_FM_ZENE="$HOME/Zenék"
fi
export KOZGAZ_FM_ZENE
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
if [ -z "${PULSE_SERVER:-}" ]; then
    for _ in $(seq 1 60); do
        [ -S "$XDG_RUNTIME_DIR/pulse/native" ] && break
        sleep 1
    done
    [ -S "$XDG_RUNTIME_DIR/pulse/native" ] && export PULSE_SERVER="unix:$XDG_RUNTIME_DIR/pulse/native" \
        || echo "Nincs PipeWire/PulseAudio-hangrendszer ($XDG_RUNTIME_DIR/pulse/native). Futtasd: sudo kozgaz-fm-szerver fm-be $(id -un)" >&2
fi
mkdir -p "$KOZGAZ_FM_ADAT" "$KOZGAZ_FM_ZENE"
exec php -d memory_limit=512M -d date.timezone=Europe/Budapest "$ITT/bin/demon.php"
