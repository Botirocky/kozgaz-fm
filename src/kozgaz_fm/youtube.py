__lazy_modules__ = ["logging", "dataclasses", "pathlib", "re", "unicodedata"]

import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

naplo = logging.getLogger(__name__)

HANG_FORMATUM = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"
KITERJESZTESEK = (".m4a", ".webm", ".opus", ".mp3", ".ogg")


KORHATAR_JELEK = ("confirm your age", "age-restricted", "age restricted", "inappropriate for some users")


class Korhataros(Exception):
    pass


def _korhataros_hiba(hiba: Exception) -> bool:
    szoveg = str(hiba).lower()
    return any(j in szoveg for j in KORHATAR_JELEK)


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


def letoltes(azonosito: str, mappa: Path, korhatar_tiltas: bool = False) -> Path:
    import yt_dlp
    from yt_dlp.utils import DownloadError

    meglevo = gyorsitott(azonosito, mappa)
    if meglevo:
        return meglevo
    mappa.mkdir(parents=True, exist_ok=True)
    with yt_dlp.YoutubeDL(_opciok(format=HANG_FORMATUM, outtmpl=str(mappa / "%(id)s.%(ext)s"),
                                  overwrites=False, retries=3)) as ydl:
        try:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={azonosito}", download=False)
        except DownloadError as hiba:
            if korhatar_tiltas and _korhataros_hiba(hiba):
                raise Korhataros(azonosito) from hiba
            raise
        if korhatar_tiltas and info and int(info.get("age_limit") or 0) >= 18:
            raise Korhataros(info.get("title") or azonosito)
        ydl.process_ie_result(info, download=True)
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


def egy_szam(cel: str) -> tuple[str, str, int, int] | None:
    import yt_dlp
    from yt_dlp.utils import DownloadError

    kereses = cel.startswith("ytsearch")
    with yt_dlp.YoutubeDL(_opciok(extract_flat="in_playlist", noplaylist=True,
                                  allowed_extractors=["youtube", "youtube:search", "youtube:tab"])) as ydl:
        try:
            info = ydl.extract_info(cel, download=False)
        except DownloadError as hiba:
            if _korhataros_hiba(hiba):
                return None if kereses else ("", "", 0, 18)
            raise
        if not info:
            return None
        elemek = info.get("entries")
        if elemek is not None:
            if not kereses:
                return None
            talalt = next((e for e in elemek if e and e.get("id")), None)
            if talalt is None:
                return None
            try:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={talalt['id']}", download=False) or talalt
            except DownloadError as hiba:
                if not _korhataros_hiba(hiba):
                    raise
                return talalt["id"], talalt.get("title") or talalt["id"], int(talalt.get("duration") or 0), 18
    korhatar = int(info.get("age_limit") or 0)
    if info.get("is_live") or info.get("live_status") in ("is_live", "is_upcoming"):
        return info["id"], info.get("title") or info["id"], 0, korhatar
    return info["id"], info.get("title") or info["id"], int(info.get("duration") or 0), korhatar


RADIO_JELEK = ("radio edit", "radio version", "radio mix", "radio cut")
CIM_ZAJ = re.compile(r"[\(\[][^\)\]]*[\)\]]|\b(official|video|audio|lyrics?|hd|4k|music|clip|visualizer|"
                     r"remaster(ed)?|extended|version|full|album)\b", re.IGNORECASE)


def _szavak(szoveg: str) -> list[str]:
    alap = unicodedata.normalize("NFKD", szoveg.lower())
    alap = "".join(c for c in alap if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", alap)


def radio_alap_cim(cim: str) -> str:
    return " ".join(CIM_ZAJ.sub(" ", cim).split())


def radio_edit_valaszt(elemek: list[dict], eredeti_cim: str, max_mp: int) -> dict | None:
    fontos = {w for w in _szavak(radio_alap_cim(eredeti_cim)) if len(w) > 2}
    for e in elemek:
        if not e or not e.get("id"):
            continue
        cim = e.get("title") or ""
        szoveg = " ".join(_szavak(cim))
        if not any(j in szoveg for j in RADIO_JELEK):
            continue
        hossz = int(e.get("duration") or 0)
        if hossz <= 0 or hossz > max_mp:
            continue
        if fontos and len(fontos & set(_szavak(cim))) * 2 < len(fontos):
            continue
        return e
    return None


def radio_edit(eredeti_cim: str, max_mp: int) -> tuple[str, str, int, int] | None:
    import yt_dlp

    kereses = f"ytsearch8:{radio_alap_cim(eredeti_cim)} radio edit"
    with yt_dlp.YoutubeDL(_opciok(extract_flat="in_playlist", noplaylist=True,
                                  allowed_extractors=["youtube", "youtube:search", "youtube:tab"])) as ydl:
        info = ydl.extract_info(kereses, download=False) or {}
    talalt = radio_edit_valaszt(list(info.get("entries") or []), eredeti_cim, max_mp)
    if talalt is None:
        return None
    teljes = egy_szam(f"https://www.youtube.com/watch?v={talalt['id']}")
    if teljes is None or not teljes[0] or not 0 < teljes[2] <= max_mp:
        return None
    return teljes
