#!/bin/sh
set -e
ITT="$(cd "$(dirname "$0")/.." && pwd)"
export KOZGAZ_FM_ADAT="${KOZGAZ_FM_ADAT:-$HOME/.local/share/kozgaz-fm-web}"
ADAT="$KOZGAZ_FM_ADAT"
if [ -z "${KOZGAZ_FM_ZENE:-}" ]; then
    KOZGAZ_FM_ZENE="$(xdg-user-dir MUSIC 2>/dev/null || true)"
    [ -n "$KOZGAZ_FM_ZENE" ] && [ "$KOZGAZ_FM_ZENE" != "$HOME" ] || KOZGAZ_FM_ZENE="$HOME/Zenék"
fi
export KOZGAZ_FM_ZENE
mkdir -p "$ADAT/munkamenetek"
BEALLITAS="-d expose_php=0 -d display_errors=0 -d log_errors=1 -d memory_limit=256M -d upload_max_filesize=32M -d post_max_size=34M -d date.timezone=Europe/Budapest -d session.save_path=$ADAT/munkamenetek -d session.cookie_httponly=1 -d session.cookie_samesite=Strict -d session.use_strict_mode=1"
php $BEALLITAS -S "127.0.0.1:8898" -t "$ITT/public" "$ITT/rendszer/router.php" &
SPOTIFY=$!
trap 'kill $SPOTIFY 2>/dev/null' EXIT INT TERM
php $BEALLITAS -S "${KFM_WEB_CIM:-0.0.0.0}:${KFM_WEB_PORT:-8080}" -t "$ITT/public" "$ITT/rendszer/router.php"
