set -euo pipefail
export DEBIAN_FRONTEND=noninteractive LC_ALL=C.UTF-8

apt-get update
apt-get -y -o Dpkg::Options::=--force-confold upgrade
apt-get install -y --no-install-recommends \
    labwc wayvnc dbus-user-session \
    pipewire pipewire-pulse pipewire-alsa wireplumber \
    python3-venv python3-pip \
    libegl1 libgl1 libgles2 libxkbcommon0 libxkbcommon-x11-0 libwayland-client0 libwayland-cursor0 \
    libwayland-egl1 libfontconfig1 libdbus-1-3 libxcb-cursor0 \
    fonts-noto-core fonts-dejavu-core \
    speech-dispatcher speech-dispatcher-espeak-ng espeak-ng libspeechd2 \
    unattended-upgrades locales openssl ca-certificates curl

id kozgazfm >/dev/null 2>&1 || useradd -m -s /bin/bash -G audio,video,render,input kozgazfm
passwd -l kozgazfm >/dev/null

sed -i 's/^# *hu_HU.UTF-8 UTF-8/hu_HU.UTF-8 UTF-8/' /etc/locale.gen
locale-gen
update-locale LANG=hu_HU.UTF-8
ln -sf /usr/share/zoneinfo/Europe/Budapest /etc/localtime
echo "Europe/Budapest" > /etc/timezone
cat > /etc/default/keyboard <<'EOF'
XKBMODEL="pc105"
XKBLAYOUT="hu"
XKBVARIANT=""
XKBOPTIONS=""
BACKSPACE="guess"
EOF
echo "kozgaz-fm" > /etc/hostname
sed -i 's/\braspberrypi\b/kozgaz-fm/g' /etc/hosts
if [ -f /etc/speech-dispatcher/speechd.conf ]; then
    sed -i 's/^#\? *DefaultLanguage .*/DefaultLanguage "hu"/' /etc/speech-dispatcher/speechd.conf
fi

python3 -m venv /opt/kozgaz-fm/venv
/opt/kozgaz-fm/venv/bin/pip install --no-cache-dir --upgrade pip
/opt/kozgaz-fm/venv/bin/pip install --no-cache-dir /tmp/kozgaz_fm-*.whl
ln -sf /opt/kozgaz-fm/venv/bin/kozgaz-fm /usr/local/bin/kozgaz-fm
/opt/kozgaz-fm/venv/bin/kozgaz-fm --version

set +e
if curl -fsSL https://dtcooper.github.io/raspotify/key.asc -o /usr/share/keyrings/raspotify.asc; then
    echo "deb [signed-by=/usr/share/keyrings/raspotify.asc] https://dtcooper.github.io/raspotify raspotify main" \
        > /etc/apt/sources.list.d/raspotify.list
    if apt-get update && apt-get install -y --no-install-recommends raspotify; then
        systemctl disable raspotify.service
        systemctl mask raspotify.service
    else
        echo "FIGYELEM: a raspotify (Spotify Connect) nem települt, a Spotify-forrás a Pi-n nem lesz elérhető."
        rm -f /etc/apt/sources.list.d/raspotify.list
    fi
else
    echo "FIGYELEM: a raspotify-tároló nem érhető el, Spotify Connect nélkül készül a kép."
fi
set -e

mkdir -p /home/kozgazfm/.config/systemd/user/default.target.wants
ln -sf ../kozgaz-fm-spotify.service /home/kozgazfm/.config/systemd/user/default.target.wants/kozgaz-fm-spotify.service
mkdir -p /home/kozgazfm/.config/systemd/user/timers.target.wants
ln -sf ../kozgaz-fm-or.timer /home/kozgazfm/.config/systemd/user/timers.target.wants/kozgaz-fm-or.timer
CMDLINE=/boot/firmware/cmdline.txt
if [ -f "$CMDLINE" ] && ! grep -q 'logo.nologo' "$CMDLINE"; then
    sed -i '1 s/$/ quiet loglevel=3 logo.nologo consoleblank=0 vt.global_cursor_default=0/' "$CMDLINE"
fi
CONFIG=/boot/firmware/config.txt
if [ -f "$CONFIG" ] && ! grep -q '^disable_splash=1' "$CONFIG"; then
    printf '\n[all]\ndisable_splash=1\n' >> "$CONFIG"
fi
chown -R kozgazfm:kozgazfm /opt/kozgaz-fm /home/kozgazfm
chown root:kozgazfm /etc/kozgaz-fm/wayvnc.config
chmod 640 /etc/kozgaz-fm/wayvnc.config
systemctl enable kozgaz-fm-elso-inditas.service
systemctl enable unattended-upgrades.service || true
systemctl set-default multi-user.target

apt-get -y autoremove
apt-get clean
