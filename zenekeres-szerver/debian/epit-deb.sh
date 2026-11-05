#!/usr/bin/env bash
set -euo pipefail

ITT="$(cd "$(dirname "$0")" && pwd)"
SZERVER="$(dirname "$ITT")"
GYOKER="$(dirname "$SZERVER")"
KIMENET="${1:-$GYOKER/dist}"
VERZIO="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$GYOKER/src/kozgaz_fm/__init__.py")"
NEV="kozgaz-fm-szerver"
CSOMAG="${NEV}_${VERZIO}_all"

MUNKA="$(mktemp -d)"
trap 'rm -rf "$MUNKA"' EXIT
R="$MUNKA/$CSOMAG"
OSZT="$R/usr/share/$NEV"

install -d "$R/DEBIAN" "$OSZT" "$R/usr/bin" "$R/usr/lib/systemd/system" "$R/usr/share/doc/$NEV"
cp -r "$SZERVER/public" "$SZERVER/src" "$OSZT/"
install -m644 "$ITT/router.php" "$OSZT/router.php"
install -m644 "$ITT/szerver.env.minta" "$OSZT/szerver.env.minta"
install -m755 "$ITT/kozgaz-fm-szerver" "$R/usr/bin/$NEV"
install -m644 "$ITT/$NEV.service" "$R/usr/lib/systemd/system/$NEV.service"
install -m644 "$SZERVER/README.md" "$R/usr/share/doc/$NEV/README.md"
find "$OSZT" -type d -exec chmod 755 {} + && find "$OSZT" -type f -exec chmod 644 {} +
{
    echo "Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/"
    echo "Upstream-Name: kozgaz-fm"
    echo "Source: https://github.com/Botirocky/kozgaz-fm"
    echo
    echo "Files: *"
    echo "Copyright: Botirocky és a Közgáz FM csapata"
    echo "License: GPL-3.0-or-later"
    echo " /usr/share/common-licenses/GPL-3"
} > "$R/usr/share/doc/$NEV/copyright"

MERET="$(du -sk --exclude=DEBIAN "$R" | cut -f1)"
cat > "$R/DEBIAN/control" <<CONTROL
Package: $NEV
Version: $VERZIO
Architecture: all
Maintainer: Botirocky <noreply@github.com>
Installed-Size: $MERET
Section: web
Priority: optional
Homepage: https://github.com/Botirocky/kozgaz-fm
Depends: php-cli (>= 2:8.1~) | php8.1-cli | php8.2-cli | php8.3-cli | php8.4-cli, php-sqlite3 | php8.1-sqlite3 | php8.2-sqlite3 | php8.3-sqlite3 | php8.4-sqlite3, php-mbstring | php8.1-mbstring | php8.2-mbstring | php8.3-mbstring | php8.4-mbstring, adduser, systemd
Suggests: tailscale
Description: Közgáz FM zenekérő szerver
 A diákok ezen a webszerveren kérnek zenét QR-kóddal, az iskolai Közgáz FM
 program innen kéri le és ellenőrzi a kéréseket, és innen tölti le a
 szünetzenéket. PHP beépített szerverrel, systemd-szolgáltatásként fut,
 Docker nélkül.
CONTROL


cat > "$R/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
set -e
NEV=kozgaz-fm-szerver
if [ "$1" = "configure" ]; then
    if ! getent passwd $NEV >/dev/null; then
        adduser --system --group --home /var/lib/$NEV --no-create-home --gecos "Közgáz FM zenekérő szerver" $NEV >/dev/null
    fi
    install -d -m 0750 -o root -g $NEV /etc/$NEV
    if [ ! -e /etc/$NEV/szerver.env ]; then
        KULCS=$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')
        sed "s/^KFM_GEP_KULCS=.*/KFM_GEP_KULCS=$KULCS/" /usr/share/$NEV/szerver.env.minta > /etc/$NEV/szerver.env
        UJ=1
    fi
    chown root:$NEV /etc/$NEV/szerver.env
    chmod 0640 /etc/$NEV/szerver.env
    [ -d /var/lib/$NEV ] || install -d -m 0750 -o $NEV -g $NEV /var/lib/$NEV
    [ -d /var/lib/$NEV/zene ] || install -d -m 0755 -o $NEV -g $NEV /var/lib/$NEV/zene
    if [ -d /run/systemd/system ]; then
        systemctl daemon-reload
        systemctl enable $NEV.service >/dev/null 2>&1
        systemctl restart $NEV.service || echo "A szolgáltatás nem indult el: journalctl -u $NEV" >&2
    fi
    if [ -n "${UJ:-}" ]; then
        echo "Közgáz FM zenekérő szerver: http://127.0.0.1:8100"
        echo "A program kulcsa: sudo $NEV kulcs"
    fi
fi
exit 0
POSTINST

cat > "$R/DEBIAN/prerm" <<'PRERM'
#!/bin/sh
set -e
NEV=kozgaz-fm-szerver
if [ "$1" = "remove" ] && [ -d /run/systemd/system ]; then
    systemctl disable --now $NEV.service >/dev/null 2>&1 || true
fi
exit 0
PRERM

cat > "$R/DEBIAN/postrm" <<'POSTRM'
#!/bin/sh
set -e
NEV=kozgaz-fm-szerver
[ -d /run/systemd/system ] && systemctl daemon-reload || true
if [ "$1" = "purge" ]; then
    rm -rf /etc/$NEV /var/lib/$NEV
    getent passwd $NEV >/dev/null && deluser --system $NEV >/dev/null 2>&1 || true
    getent group $NEV >/dev/null && delgroup --system $NEV >/dev/null 2>&1 || true
fi
exit 0
POSTRM
chmod 755 "$R/DEBIAN/postinst" "$R/DEBIAN/prerm" "$R/DEBIAN/postrm"

mkdir -p "$KIMENET"
dpkg-deb --root-owner-group -Zxz --build "$R" "$KIMENET/$CSOMAG.deb"
echo "$KIMENET/$CSOMAG.deb"
