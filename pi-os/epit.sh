#!/bin/bash
set -euo pipefail

GYOKER="$(cd "$(dirname "$0")/.." && pwd)"
KONTEXTUS="${DOCKER_KONTEXTUS:-default}"

sugo() {
    cat <<SUGO
Közgáz FM OS – Raspberry Pi lemezkép építése

Használat:
  pi-os/epit.sh                  építés (Docker, privilegizált Debian-konténer, arm64-emulációval)
  pi-os/epit.sh --tiszta         a letöltött alapkép és a félkész fájlok törlése
  pi-os/epit.sh --help           ez a súgó

Környezeti változók:
  ADMIN_JELSZO     az „admin” rendszergazda jelszava (alap: kozgazfm)
  VNC_JELSZO       a távoli asztal (VNC, felhasználó: kozgaz) jelszava (alap: az ADMIN_JELSZO)
  DOCKER_KONTEXTUS Docker-kontextus (alap: default)

Eredmény: dist/KozgazFM-OS-<verzió>-arm64.img.xz – Raspberry Pi Imagerrel írható SD-kártyára.
SUGO
}

case "${1:-}" in
    -h|--help) sugo; exit 0 ;;
    --tiszta) rm -rf "$GYOKER/pi-os/munka"; echo "Törölve: pi-os/munka"; exit 0 ;;
    "") ;;
    *) sugo; exit 1 ;;
esac

cd "$GYOKER"
rm -f dist/kozgaz_fm-*.whl
uv build --wheel -o dist -q

if [ "$(id -u)" -eq 0 ] && [ "$(uname -m)" = "aarch64" ]; then
    exec "$GYOKER/pi-os/belso.sh"
fi

exec docker --context "$KONTEXTUS" run --rm --privileged \
    -v /dev:/dev -v "$GYOKER":/munka \
    -e ADMIN_JELSZO -e VNC_JELSZO -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
    debian:trixie /munka/pi-os/belso.sh
