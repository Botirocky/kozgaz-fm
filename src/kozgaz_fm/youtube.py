__lazy_modules__ = ["logging", "dataclasses", "pathlib"]

import logging
from dataclasses import dataclass
from pathlib import Path

naplo = logging.getLogger(__name__)

HANG_FORMATUM = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"
KITERJESZTESEK = (".m4a", ".webm", ".opus", ".mp3", ".ogg")


@dataclass(frozen=True)
class YtSzam:
    azonosito: str
    cim: str


class _Nema:
    def debug(self, uzenet: str) -> None:
        pass

    def info(self, uzenet: str) -> None:
        pass

    def warning(self, uzenet: str) -> None:
        naplo.debug("yt-dlp: %s", uzenet)

    def error(self, uzenet: str) -> None:
        naplo.warning("yt-dlp: %s", uzenet)


def _opciok(**tobb) -> dict:
    return {"quiet": True, "no_warnings": True, "noprogress": True, "logger": _Nema(),
            "js_runtimes": {"deno": {}, "node": {}, "bun": {}}, "socket_timeout": 20, **tobb}


def cim_ertelmezes(cim: str) -> str:
    cim = cim.strip()
    if cim.startswith(("http://", "https://", "www.", "youtube.com", "youtu.be", "music.youtube.com")):
        return cim if cim.startswith("http") else "https://" + cim
    return f"ytsearch25:{cim}"


def lista(cim: str, max_db: int = 500) -> list[YtSzam]:
    import yt_dlp

    with yt_dlp.YoutubeDL(_opciok(extract_flat="in_playlist", playlistend=max_db)) as ydl:
        info = ydl.extract_info(cim_ertelmezes(cim), download=False)
    if not info:
        return []
    elemek = info.get("entries")
    if elemek is None:
        return [YtSzam(info["id"], info.get("title") or info["id"])]
    eredmeny = []
    for e in elemek:
        if not e or not e.get("id") or e.get("title") in ("[Private video]", "[Deleted video]"):
            continue
        eredmeny.append(YtSzam(e["id"], e.get("title") or e["id"]))
    return eredmeny


def gyorsitott(azonosito: str, mappa: Path) -> Path | None:
    for kit in KITERJESZTESEK:
        ut = mappa / f"{azonosito}{kit}"
        if ut.exists() and ut.stat().st_size > 0:
            return ut
    return None


def letoltes(azonosito: str, mappa: Path) -> Path:
    import yt_dlp

    meglevo = gyorsitott(azonosito, mappa)
    if meglevo:
        return meglevo
    mappa.mkdir(parents=True, exist_ok=True)
    with yt_dlp.YoutubeDL(_opciok(format=HANG_FORMATUM, outtmpl=str(mappa / "%(id)s.%(ext)s"),
                                  overwrites=False, retries=3)) as ydl:
        ydl.download([f"https://www.youtube.com/watch?v={azonosito}"])
    ut = gyorsitott(azonosito, mappa)
    if ut is None:
        raise RuntimeError(f"A letöltés nem hozott létre fájlt: {azonosito}")
    return ut


def gyorsitotar_meret(mappa: Path) -> int:
    return sum(f.stat().st_size for f in mappa.glob("*") if f.is_file())


def gyorsitotar_urites(mappa: Path) -> None:
    for f in mappa.glob("*"):
        if f.is_file():
            f.unlink(missing_ok=True)


def egy_szam(cel: str) -> tuple[str, str, int] | None:
    import yt_dlp

    kereses = cel.startswith("ytsearch")
    with yt_dlp.YoutubeDL(_opciok(extract_flat="in_playlist", noplaylist=True)) as ydl:
        info = ydl.extract_info(cel, download=False)
    if not info:
        return None
    elemek = info.get("entries")
    if elemek is not None:
        if not kereses:
            return None
        info = next((e for e in elemek if e and e.get("id")), None)
        if info is None:
            return None
    if info.get("is_live") or info.get("live_status") in ("is_live", "is_upcoming"):
        return info["id"], info.get("title") or info["id"], 0
    return info["id"], info.get("title") or info["id"], int(info.get("duration") or 0)
