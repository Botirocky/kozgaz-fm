#!/usr/bin/env bash
set -euo pipefail

GYOKER="$(cd "$(dirname "$0")/../.." && pwd)"
DIST="${1:-$GYOKER/dist/KozgazFM}"
KIMENET="${2:-$GYOKER/dist}"
VERZIO="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$GYOKER/src/kozgaz_fm/__init__.py")"
ARCH="$(dpkg --print-architecture)"
NEV="kozgaz-fm_${VERZIO}_${ARCH}"

[ -x "$DIST/KozgazFM" ] || { echo "Nincs PyInstaller-build: $DIST" >&2; exit 1; }

MUNKA="$(mktemp -d)"
trap 'rm -rf "$MUNKA"' EXIT
R="$MUNKA/$NEV"

install -d "$R/DEBIAN" "$R/opt/kozgaz-fm" "$R/usr/bin" "$R/usr/lib/kozgaz-fm" \
    "$R/usr/share/applications" "$R/usr/share/doc/kozgaz-fm" "$R/usr/share/polkit-1/actions"
cp -a "$DIST/." "$R/opt/kozgaz-fm/"
ln -s /opt/kozgaz-fm/KozgazFM "$R/usr/bin/kozgaz-fm"
install -m755 "$GYOKER/packaging/debian/frissites-telepito" "$R/usr/lib/kozgaz-fm/frissites-telepito"
install -m644 "$GYOKER/packaging/debian/hu.kozgazfm.frissites.policy" "$R/usr/share/polkit-1/actions/"
install -m644 "$GYOKER/packaging/linux/kozgaz-fm.desktop" "$R/usr/share/applications/kozgaz-fm.desktop"
for meret in 16 24 32 48 64 128 256 512; do
    install -Dm644 "$GYOKER/assets/ikon-$meret.png" "$R/usr/share/icons/hicolor/${meret}x${meret}/apps/kozgaz-fm.png"
done
install -m644 "$GYOKER/src/kozgaz_fm/sugo.md" "$R/usr/share/doc/kozgaz-fm/HASZNALATI-UTMUTATO.md"
{
    echo "Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/"
    echo "Upstream-Name: kozgaz-fm"
    echo "Source: https://github.com/Botirocky/kozgaz-fm"
    echo
    echo "Files: *"
    echo "Copyright: Botirocky és a Közgáz FM csapata"
    echo "License: GPL-3.0-or-later"
    echo " /usr/share/common-licenses/GPL-3"
} > "$R/usr/share/doc/kozgaz-fm/copyright"

MERET="$(du -sk --exclude=DEBIAN "$R" | cut -f1)"
cat > "$R/DEBIAN/control" <<CONTROL
Package: kozgaz-fm
Version: $VERZIO
Architecture: $ARCH
Maintainer: Botirocky <noreply@github.com>
Installed-Size: $MERET
Section: sound
Priority: optional
Homepage: https://github.com/Botirocky/kozgaz-fm
Depends: libc6 (>= 2.35), libegl1, libgl1, libxkbcommon0, libxkbcommon-x11-0, libfontconfig1, libfreetype6, libdbus-1-3, libxcb-cursor0, libxcb-icccm4, libxcb-keysyms1, libxcb-shape0, libxcb-xinerama0, libxcb-randr0, libxcb-render-util0, libxcb-image0, libpulse0, python3, ca-certificates
Recommends: pkexec | policykit-1, espeak-ng, ffmpeg
Description: Iskolai csengetőrendszer és szünetzene-lejátszó
 A csengetési rend szerint magától csenget, a szünetekben zenét játszik
 helyi MP3-ból, YouTube-ról vagy Spotifyról, és hangosbemondásra is képes.
 Webes vezérlés telefonról, zenekérés QR-kóddal, tartalékgép, hangzónák.
CONTROL

cat > "$R/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    command -v update-desktop-database >/dev/null && update-desktop-database -q /usr/share/applications || true
    command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -f /usr/share/icons/hicolor || true
fi
exit 0
POSTINST
cp "$R/DEBIAN/postinst" "$R/DEBIAN/postrm"
sed -i 's/if \[ "\$1" = "configure" \]; then/if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then/' "$R/DEBIAN/postrm"
chmod 755 "$R/DEBIAN/postinst" "$R/DEBIAN/postrm"

mkdir -p "$KIMENET"
dpkg-deb --root-owner-group -Zxz --build "$R" "$KIMENET/$NEV.deb"
echo "$KIMENET/$NEV.deb"
