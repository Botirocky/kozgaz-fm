import os
import sys
from pathlib import Path


def _alap(windows_valtozo: str, xdg_valtozo: str, xdg_alap: str) -> Path:
    if sys.platform.startswith("win"):
        return Path(os.environ.get(windows_valtozo) or Path.home() / "AppData" / "Roaming") / "KozgazFM"
    return Path(os.environ.get(xdg_valtozo) or Path.home() / xdg_alap) / "kozgaz-fm"


def adat_mappa() -> Path:
    egyedi = os.environ.get("KOZGAZ_FM_ADAT")
    mappa = Path(egyedi) if egyedi else _alap("APPDATA", "XDG_CONFIG_HOME", ".config")
    mappa.mkdir(parents=True, exist_ok=True)
    return mappa


def gyorsitotar_mappa() -> Path:
    egyedi = os.environ.get("KOZGAZ_FM_ADAT")
    mappa = Path(egyedi) / "gyorsitotar" if egyedi else _alap("LOCALAPPDATA", "XDG_CACHE_HOME", ".cache")
    mappa.mkdir(parents=True, exist_ok=True)
    return mappa


def beallitas_fajl() -> Path:
    return adat_mappa() / "beallitasok.json"


def sajat_hangok_mappa() -> Path:
    return adat_mappa() / "hangok"


def naplo_fajl() -> Path:
    return adat_mappa() / "naplo.txt"


def csomag_mappa() -> Path:
    return Path(__file__).resolve().parent


def beepitett_hang(nev: str) -> Path:
    return csomag_mappa() / "hangok" / f"{nev}.wav"
