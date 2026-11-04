__lazy_modules__ = ["re", "subprocess", "sys", "unicodedata", "pathlib", "kozgaz_fm.hangossag", "kozgaz_fm.utvonalak",
                    "kozgaz_fm.youtube"]

import re
import subprocess
import sys
import unicodedata
from pathlib import Path

from kozgaz_fm import youtube
from kozgaz_fm.hangossag import ffmpeg_ut
from kozgaz_fm.utvonalak import gyorsitotar_mappa


def alap_mappa() -> Path:
    return Path.home() / "Közgáz FM kért számok"


def fajlnev(cim: str) -> str:
    tiszta = unicodedata.normalize("NFC", cim)
    tiszta = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", tiszta)
    tiszta = re.sub(r"\s+", " ", tiszta).strip(" .")
    return (tiszta[:120] or "Kért szám") + ".mp3"


def mentes(yt: str, cim: str, mappa: Path) -> Path | None:
    cel = mappa / fajlnev(cim)
    if cel.exists():
        return None
    program = ffmpeg_ut()
    if program is None:
        raise RuntimeError("nincs ffmpeg, MP3 nem készíthető")
    forras = youtube.letoltes(yt, gyorsitotar_mappa() / "youtube")
    mappa.mkdir(parents=True, exist_ok=True)
    ideiglenes = cel.with_suffix(".tmp.mp3")
    opciok = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if sys.platform == "win32" else {}
    eredmeny = subprocess.run([program, "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", str(forras),
                               "-vn", "-codec:a", "libmp3lame", "-q:a", "2", "-metadata", f"title={cim}",
                               "-metadata", "comment=Közgáz FM – kért szám", str(ideiglenes)],
                              capture_output=True, text=True, errors="replace", timeout=600, **opciok)
    if eredmeny.returncode != 0 or not ideiglenes.exists():
        ideiglenes.unlink(missing_ok=True)
        raise RuntimeError((eredmeny.stderr.strip().splitlines() or ["az ffmpeg hibát jelzett"])[-1][:200])
    ideiglenes.replace(cel)
    return cel
