#!/bin/bash
set -euo pipefail

GYOKER="$(cd "$(dirname "$0")/.." && pwd)"
PI="$GYOKER/pi-os"
MUNKA="$PI/munka"
KIMENET="${KIMENET:-$GYOKER/dist}"
ADMIN_JELSZO="${ADMIN_JELSZO:-kozgazfm}"
VNC_JELSZO="${VNC_JELSZO:-$ADMIN_JELSZO}"
ALAP_URL="${ALAP_URL:-https://downloads.raspberrypi.com/raspios_lite_arm64_latest}"
MERET_PLUSZ="${MERET_PLUSZ:-2600M}"
VERZIO="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$GYOKER/src/kozgaz_fm/__init__.py")"
NEV="KozgazFM-OS-$VERZIO-arm64"
KEP="$MUNKA/$NEV.img"
CEL="/mnt/kozgazfm-os"
GYOKER_LOOP=""
BOOT_LOOP=""

jelez() { printf '\n==> %s\n' "$*"; }

if [ "$(id -u)" -ne 0 ]; then
    echo "Root jogosultság kell (használd az epit.sh-t)." >&2
    exit 1
fi

takarit() {
    set +e
    for ut in "$CEL/boot/firmware" "$CEL/dev/pts" "$CEL/dev" "$CEL/proc" "$CEL/sys" "$CEL"; do
        mountpoint -q "$ut" && umount -l "$ut"
    done
    [ -n "$BOOT_LOOP" ] && losetup -d "$BOOT_LOOP"
    [ -n "$GYOKER_LOOP" ] && losetup -d "$GYOKER_LOOP"
    [ -n "${SAJAT_BINFMT:-}" ] && [ -e "$SAJAT_BINFMT" ] && echo -1 > "$SAJAT_BINFMT"
    if [ -n "${HOST_UID:-}" ]; then
        chown "$HOST_UID:${HOST_GID:-$HOST_UID}" "$MUNKA" "$MUNKA"/alap.img.xz* "$KIMENET" "$KIMENET"/KozgazFM-OS-* 2>/dev/null
    fi
}
trap takarit EXIT

jelez "Eszközök telepítése"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends curl ca-certificates xz-utils fdisk parted e2fsprogs dosfstools \
    openssl util-linux >/dev/null
BINFMT=/proc/sys/fs/binfmt_misc
SAJAT_BINFMT=""
if [ "$(uname -m)" != "aarch64" ]; then
    apt-get install -y -qq --no-install-recommends qemu-user-static >/dev/null
    mountpoint -q "$BINFMT" || mount -t binfmt_misc binfmt_misc "$BINFMT"
    if ! grep -qs '^enabled' "$BINFMT"/qemu-aarch64 "$BINFMT"/kozgazfm-aarch64 2>/dev/null; then
        printf '%s' ':kozgazfm-aarch64:M::\x7f\x45\x4c\x46\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\xb7\x00:\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff\xff:/usr/bin/qemu-aarch64-static:F' \
            > "$BINFMT/register"
        SAJAT_BINFMT="$BINFMT/kozgazfm-aarch64"
    fi
fi

KEREK="$(ls "$KIMENET"/kozgaz_fm-"$VERZIO"-py3-none-any.whl 2>/dev/null | head -n1 || true)"
if [ -z "$KEREK" ]; then
    echo "Hiányzik a $KIMENET/kozgaz_fm-$VERZIO-py3-none-any.whl (uv build --wheel)." >&2
    exit 1
fi

jelez "Raspberry Pi OS Lite alapkép"
mkdir -p "$MUNKA" "$KIMENET"
if [ ! -f "$MUNKA/alap.img.xz" ]; then
    VEGSO_URL="$(curl -sSLI -o /dev/null -w '%{url_effective}' "$ALAP_URL")"
    echo "$VEGSO_URL"
    curl -fsSL -o "$MUNKA/alap.img.xz.sha256" "$VEGSO_URL.sha256"
    curl -fSL --progress-bar -o "$MUNKA/alap.img.xz.resz" "$VEGSO_URL"
    mv "$MUNKA/alap.img.xz.resz" "$MUNKA/alap.img.xz"
fi
VART="$(cut -d' ' -f1 "$MUNKA/alap.img.xz.sha256")"
if [ "$(sha256sum "$MUNKA/alap.img.xz" | cut -d' ' -f1)" != "$VART" ]; then
    echo "Az alapkép ellenőrzőösszege hibás, töröld: $MUNKA/alap.img.xz" >&2
    exit 1
fi

jelez "Kép kicsomagolása és bővítése (+$MERET_PLUSZ)"
xz -dc -T0 "$MUNKA/alap.img.xz" > "$KEP"
truncate -s "+$MERET_PLUSZ" "$KEP"
parted -s "$KEP" resizepart 2 100%
reszek="$(sfdisk -d "$KEP")"
S1="$(echo "$reszek" | awk -F'[=,]' '/img1 /{gsub(/ /,"",$2); print $2}')"
Z1="$(echo "$reszek" | awk -F'[=,]' '/img1 /{gsub(/ /,"",$4); print $4}')"
S2="$(echo "$reszek" | awk -F'[=,]' '/img2 /{gsub(/ /,"",$2); print $2}')"
GYOKER_LOOP="$(losetup --find --show --offset $((S2 * 512)) "$KEP")"
e2fsck -pf "$GYOKER_LOOP" || [ $? -le 1 ]
resize2fs "$GYOKER_LOOP" >/dev/null
BOOT_LOOP="$(losetup --find --show --offset $((S1 * 512)) --sizelimit $((Z1 * 512)) "$KEP")"

mkdir -p "$CEL"
mount "$GYOKER_LOOP" "$CEL"
mount "$BOOT_LOOP" "$CEL/boot/firmware"
mount --bind /dev "$CEL/dev"
mount --bind /dev/pts "$CEL/dev/pts"
mount -t proc proc "$CEL/proc"
mount -t sysfs sys "$CEL/sys"

jelez "Rendszerfájlok másolása"
mv "$CEL/etc/resolv.conf" "$CEL/etc/resolv.conf.eredeti" 2>/dev/null || true
cp /etc/resolv.conf "$CEL/etc/resolv.conf"
printf '#!/bin/sh\nexit 101\n' > "$CEL/usr/sbin/policy-rc.d"
chmod +x "$CEL/usr/sbin/policy-rc.d"
cp -a "$PI/rendszer/." "$CEL/"
chown -R root:root "$CEL/etc" "$CEL/usr/local"
cp "$KEREK" "$CEL/tmp/"
mkdir -p "$CEL/etc/kozgaz-fm"
cat > "$CEL/etc/kozgaz-fm/wayvnc.config" <<EOF
enable_auth=true
username=kozgaz
password=$VNC_JELSZO
rsa_private_key_file=/etc/kozgaz-fm/vnc_rsa.pem
EOF
if [ "$ADMIN_JELSZO" = "kozgazfm" ] || [ "$VNC_JELSZO" = "kozgazfm" ]; then
    touch "$CEL/etc/kozgaz-fm/alap-jelszo"
fi
cat > "$CEL/etc/kozgaz-fm/os-verzio" <<EOF
KOZGAZFM_OS_VERZIO=$VERZIO
EPITVE=$(date -u +%Y-%m-%dT%H:%MZ)
ALAP=$(basename "$(cat "$MUNKA/alap.img.xz.sha256" | awk '{print $2}')")
EOF

jelez "Csomagok és a Közgáz FM telepítése (arm64 chroot – ez eltart egy ideig)"
chroot "$CEL" /usr/bin/env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME=/root VNC_JELSZO="$VNC_JELSZO" \
    /bin/bash -s < "$PI/chroot.sh"

jelez "Rendszergazda-fiók (admin) első indításra"
printf 'admin:%s\n' "$(openssl passwd -6 "$ADMIN_JELSZO")" > "$CEL/boot/firmware/userconf.txt"

jelez "Takarítás"
rm -f "$CEL/usr/sbin/policy-rc.d" "$CEL"/tmp/kozgaz_fm-*.whl "$CEL/etc/resolv.conf"
if [ -e "$CEL/etc/resolv.conf.eredeti" ] || [ -L "$CEL/etc/resolv.conf.eredeti" ]; then
    mv "$CEL/etc/resolv.conf.eredeti" "$CEL/etc/resolv.conf"
fi
rm -rf "$CEL/var/lib/apt/lists/"* "$CEL/var/cache/apt/"*.bin "$CEL/root/.cache"
fstrim -v "$CEL" 2>/dev/null || true
sync
umount "$CEL/boot/firmware" "$CEL/dev/pts" "$CEL/dev" "$CEL/proc" "$CEL/sys" "$CEL"
e2fsck -pf "$GYOKER_LOOP" || [ $? -le 1 ]
losetup -d "$BOOT_LOOP" "$GYOKER_LOOP"
BOOT_LOOP=""
GYOKER_LOOP=""

jelez "Tömörítés: $KIMENET/$NEV.img.xz"
xz -T0 -6 -c "$KEP" > "$KIMENET/$NEV.img.xz"
rm -f "$KEP"
(cd "$KIMENET" && sha256sum "$NEV.img.xz" > "$NEV.img.xz.sha256")
ls -la "$KIMENET/$NEV.img.xz"
jelez "Kész: $NEV.img.xz"
