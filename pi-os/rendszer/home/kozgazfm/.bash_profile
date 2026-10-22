if [ -z "$WAYLAND_DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    mkdir -p "$HOME/.cache"
    exec labwc > "$HOME/.cache/labwc.log" 2>&1
fi
