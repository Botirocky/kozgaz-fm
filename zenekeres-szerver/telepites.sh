#!/usr/bin/env bash
# Közgáz FM zenekérő szerver – telepítés / frissítés egy lépésben (Debian/Ubuntu).
#
#   ./telepites.sh                      telepítés vagy frissítés
#   ./telepites.sh /ut/a/zenekhez       ugyanez, a zenemappa megadásával
#   ./telepites.sh --funnel [mappa]     ráadásul Tailscale Funnellel kívülről is elérhetővé teszi
#
# Többször is futtatható: a meglévő .env-et és adatokat nem bántja.
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

FUNNEL=0
ZENE=""
for arg in "$@"; do
    case "$arg" in
        --funnel) FUNNEL=1 ;;
        -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
        *) ZENE="$arg" ;;
    esac
done

lepes() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
hiba()  { printf '\033[1;31mHIBA: %s\033[0m\n' "$*" >&2; exit 1; }

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    command -v sudo >/dev/null || hiba "sudo kell (vagy futtasd rootként)."
    SUDO="sudo"
fi

# --- 1. Docker ---------------------------------------------------------------
if ! command -v docker >/dev/null; then
    lepes "Docker telepítése"
    command -v curl >/dev/null || { $SUDO apt-get update && $SUDO apt-get install -y curl; }
    curl -fsSL https://get.docker.com | $SUDO sh
    [ -n "$SUDO" ] && $SUDO usermod -aG docker "$USER" || true
fi
DOCKER="docker"
docker info >/dev/null 2>&1 || DOCKER="$SUDO docker"
$DOCKER compose version >/dev/null 2>&1 || hiba "Hiányzik a 'docker compose' (docker-compose-plugin csomag)."

# --- 2. .env -----------------------------------------------------------------
env_ertek() { grep -E "^$1=" .env 2>/dev/null | tail -n1 | cut -d= -f2- || true; }
env_beallit() {
    if grep -qE "^$1=" .env; then
        sed -i "s|^$1=.*|$1=$2|" .env
    else
        printf '%s=%s\n' "$1" "$2" >> .env
    fi
}

if [ ! -f .env ]; then
    lepes ".env létrehozása"
    cp .env.minta .env
    chmod 600 .env
fi
if [ -z "$(env_ertek KFM_GEP_KULCS)" ]; then
    if command -v openssl >/dev/null; then
        KULCS="$(openssl rand -hex 24)"
    else
        KULCS="$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')"
    fi
    env_beallit KFM_GEP_KULCS "$KULCS"
    echo "Új szerverkulcs generálva."
fi
if [ -n "$ZENE" ]; then
    [ -d "$ZENE" ] || hiba "Nincs ilyen mappa: $ZENE"
    env_beallit ZENEKERES_ZENE "$(readlink -f "$ZENE")"
fi

# --- 3. Mappák és jogok ------------------------------------------------------
ADAT="$(env_ertek ZENEKERES_ADAT)"; ADAT="${ADAT:-./adat}"
ZENEMAPPA="$(env_ertek ZENEKERES_ZENE)"; ZENEMAPPA="${ZENEMAPPA:-./zene}"
PORT="$(env_ertek ZENEKERES_PORT)"; PORT="${PORT:-8100}"

lepes "Adatmappa: $ADAT"
mkdir -p "$ADAT" 2>/dev/null || $SUDO mkdir -p "$ADAT"
$SUDO chown 33:33 "$ADAT"          # a konténerben futó PHP (www-data) írja
[ -d "$ZENEMAPPA" ] || mkdir -p "$ZENEMAPPA"

# --- 4. Indítás --------------------------------------------------------------
lepes "Konténer építése és indítása"
$DOCKER compose up -d --build

lepes "Állapot ellenőrzése"
ok=0
for _ in $(seq 1 30); do
    if curl -fsS "http://127.0.0.1:$PORT/egeszseg" >/dev/null 2>&1; then ok=1; break; fi
    sleep 2
done
[ "$ok" = 1 ] || { $DOCKER compose logs --tail 50; hiba "A szerver nem válaszol a $PORT-es porton."; }
echo "A szerver fut: http://127.0.0.1:$PORT"

# --- 5. Tailscale Funnel (opcionális) ----------------------------------------
CIM="(nincs – futtasd --funnel kapcsolóval, vagy állíts be fordított proxyt)"
if [ "$FUNNEL" = 1 ]; then
    lepes "Tailscale Funnel"
    if ! command -v tailscale >/dev/null; then
        curl -fsSL https://tailscale.com/install.sh | $SUDO sh
    fi
    $SUDO tailscale status >/dev/null 2>&1 || $SUDO tailscale up
    $SUDO tailscale funnel --bg --https=443 "http://127.0.0.1:$PORT"
    NEV="$($SUDO tailscale status --json 2>/dev/null | grep -m1 '"DNSName"' | cut -d'"' -f4 | sed 's/\.$//')"
    [ -n "$NEV" ] && CIM="https://$NEV"
fi

# --- Összegzés ---------------------------------------------------------------
lepes "Kész"
cat <<OSSZ
A programban: Zene → Zenekérés diákoktól
  Zenekérő szerver: $CIM
  Szerver kulcsa:   $(env_ertek KFM_GEP_KULCS)

Zenemappa: $ZENEMAPPA
Frissítés: git pull && ./telepites.sh
OSSZ
