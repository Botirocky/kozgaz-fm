import contextlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

from kozgaz_fm import APP_ID, APP_NEV

FUTTATAS_KULCS = r"Software\Microsoft\Windows\CurrentVersion\Run"
WINDOWS = sys.platform.startswith("win")


def inditasi_parancs() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --talcan'
    return f'"{sys.executable}" -m kozgaz_fm --talcan'


def _linux_autostart() -> Path:
    alap = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return alap / "autostart" / f"{APP_ID}.desktop"


def automatikus_inditas() -> bool:
    if WINDOWS:
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, FUTTATAS_KULCS) as kulcs:
                winreg.QueryValueEx(kulcs, APP_NEV)
                return True
        except OSError:
            return False
    return _linux_autostart().exists()


def automatikus_inditas_beallit(be: bool) -> None:
    if WINDOWS:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, FUTTATAS_KULCS, 0, winreg.KEY_SET_VALUE) as kulcs:
            if be:
                winreg.SetValueEx(kulcs, APP_NEV, 0, winreg.REG_SZ, inditasi_parancs())
            else:
                with contextlib.suppress(FileNotFoundError):
                    winreg.DeleteValue(kulcs, APP_NEV)
        return
    ut = _linux_autostart()
    if be:
        ut.parent.mkdir(parents=True, exist_ok=True)
        ut.write_text(
            "[Desktop Entry]\nType=Application\n"
            f"Name={APP_NEV}\nExec={inditasi_parancs()}\nIcon={APP_ID}\n"
            "X-GNOME-Autostart-enabled=true\nTerminal=false\n",
            encoding="utf-8",
        )
    else:
        ut.unlink(missing_ok=True)


def ido_szinkronban() -> bool | None:
    if WINDOWS or not shutil.which("timedatectl"):
        return None
    try:
        kimenet = subprocess.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"], capture_output=True,
                                 text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    ertek = kimenet.stdout.strip()
    return None if not ertek else ertek == "yes"


def gep_ujrainditas() -> None:
    subprocess.Popen(["shutdown", "/r", "/t", "5"] if WINDOWS else ["systemctl", "reboot"])


def gep_leallitas() -> None:
    subprocess.Popen(["shutdown", "/s", "/t", "5"] if WINDOWS else ["systemctl", "poweroff"])
