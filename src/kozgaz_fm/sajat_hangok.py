import re
import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from kozgaz_fm.utvonalak import sajat_hangok_mappa

ELOTAG = "sajat:"
HANGFAJLOK = (".mp3", ".m4a", ".aac", ".ogg", ".oga", ".opus", ".flac", ".wav", ".wma", ".webm")
MAX_MERET = 30 * 1024 * 1024


class SajatHangHiba(Exception):
    pass


@dataclass(frozen=True)
class SajatHang:
    ertek: str
    nev: str
    ut: Path


def _biztonsagos_nev(nev: str) -> str:
    alap = unicodedata.normalize("NFKC", nev).strip()
    alap = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", alap)
    alap = re.sub(r"\s+", " ", alap).strip(" .")
    return alap[:80] or "Saját hang"


def ertek(fajlnev: str) -> str:
    return ELOTAG + fajlnev


def sajat(ertek_: str) -> bool:
    return ertek_.startswith(ELOTAG)


def ut(ertek_: str, mappa: Path | None = None) -> Path | None:
    if not sajat(ertek_):
        return None
    fajlnev = ertek_[len(ELOTAG):]
    if not fajlnev or Path(fajlnev).name != fajlnev:
        return None
    cel = (mappa or sajat_hangok_mappa()) / fajlnev
    return cel if cel.is_file() else None


def nev(ertek_: str) -> str:
    return Path(ertek_[len(ELOTAG):]).stem if sajat(ertek_) else ""


def lista(mappa: Path | None = None) -> list[SajatHang]:
    mappa = mappa or sajat_hangok_mappa()
    if not mappa.is_dir():
        return []
    hangok = [SajatHang(ertek(f.name), f.stem, f) for f in mappa.iterdir()
              if f.is_file() and f.suffix.lower() in HANGFAJLOK]
    return sorted(hangok, key=lambda h: h.nev.casefold())


def _szabad_ut(mappa: Path, tiszta: str, kiterjesztes: str, kiveve: Path | None = None) -> Path:
    cel = mappa / f"{tiszta}{kiterjesztes}"
    sorszam = 2
    while cel.exists() and cel != kiveve:
        cel = mappa / f"{tiszta} ({sorszam}){kiterjesztes}"
        sorszam += 1
    return cel


def hozzaad(forras: Path, uj_nev: str | None = None, mappa: Path | None = None) -> SajatHang:
    mappa = mappa or sajat_hangok_mappa()
    kiterjesztes = forras.suffix.lower()
    if kiterjesztes not in HANGFAJLOK:
        raise SajatHangHiba(f"Ez nem támogatott hangfájl: {forras.name}")
    try:
        meret = forras.stat().st_size
    except OSError as e:
        raise SajatHangHiba(f"A fájl nem olvasható: {forras.name}") from e
    if meret == 0:
        raise SajatHangHiba(f"A fájl üres: {forras.name}")
    if meret > MAX_MERET:
        raise SajatHangHiba(f"A fájl túl nagy (legfeljebb {MAX_MERET // (1024 * 1024)} MB): {forras.name}")
    mappa.mkdir(parents=True, exist_ok=True)
    cel = _szabad_ut(mappa, _biztonsagos_nev(uj_nev or forras.stem), kiterjesztes)
    try:
        shutil.copyfile(forras, cel)
    except OSError as e:
        cel.unlink(missing_ok=True)
        raise SajatHangHiba(f"Nem sikerült bemásolni: {e}") from e
    return SajatHang(ertek(cel.name), cel.stem, cel)


def atnevez(ertek_: str, uj_nev: str, mappa: Path | None = None) -> SajatHang:
    mappa = mappa or sajat_hangok_mappa()
    regi = ut(ertek_, mappa)
    if regi is None:
        raise SajatHangHiba("A hang már nem található.")
    cel = _szabad_ut(mappa, _biztonsagos_nev(uj_nev), regi.suffix.lower(), kiveve=regi)
    if cel != regi:
        try:
            regi.rename(cel)
        except OSError as e:
            raise SajatHangHiba(f"Nem sikerült átnevezni: {e}") from e
    return SajatHang(ertek(cel.name), cel.stem, cel)


def torol(ertek_: str, mappa: Path | None = None) -> None:
    hely = ut(ertek_, mappa)
    if hely is None:
        return
    try:
        hely.unlink(missing_ok=True)
    except OSError as e:
        raise SajatHangHiba(f"Nem sikerült törölni (használatban van?): {e}") from e
