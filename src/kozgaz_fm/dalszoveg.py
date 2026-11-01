__lazy_modules__ = ["json", "logging", "re", "threading", "time", "urllib.error", "urllib.parse", "urllib.request",
                    "dataclasses", "pathlib", "kozgaz_fm", "kozgaz_fm.szuro"]

import json
import logging
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from kozgaz_fm import __version__
from kozgaz_fm.szuro import Ertekeles, egyszerusit, ertekel

naplo = logging.getLogger(__name__)

API = "https://lrclib.net/api/search"
FEJLEC = {"User-Agent": f"KozgazFM/{__version__} (https://github.com/Botirocky/kozgaz-fm)"}
IDOKORLAT_MP = 10
PROBALKOZAS = 3
VARAKOZAS_MP = 1.5
MAX_VALASZ = 4 * 1024 * 1024
HOSSZ_TURES_MP = 25
NINCS_MEGORZES_MP = 14 * 24 * 3600

_ZAROJEL = re.compile(r"\([^)]*\)|\[[^\]]*\]|\{[^}]*\}|【[^】]*】")
_VENDEG = re.compile(r"\b(?:ft|feat|featuring)\b\.?.*$", re.IGNORECASE)
_ZAJ = re.compile(r"\b(?:official(?: music| lyric)?(?: video| audio)?|music video|lyric video|lyrics?|videoklip|klip"
                  r"|hd|hq|4k|remaster(?:ed)?)\b\.?\s*$", re.IGNORECASE)
_ELSZAM = re.compile(r"^\s*\d{1,3}\s*[.)_-]+\s*")
_ELVALASZTO = re.compile(r"\s+[-–—:|]\s+")
_SZO = re.compile(r"\w+")


class DalszovegHiba(Exception):
    pass


@dataclass(frozen=True)
class Eredmeny:
    talalt: bool
    ertekeles: Ertekeles = Ertekeles()
    instrumental: bool = False
    forras: str = ""


def cim_bontas(cim: str) -> tuple[str, str]:
    tiszta = _ELSZAM.sub("", _ZAROJEL.sub(" ", cim))
    tiszta = tiszta.split(" | ")[0]
    reszek = [r for r in (_ZAJ.sub(" ", _VENDEG.sub("", r)).strip(" -–—_.,") for r in _ELVALASZTO.split(tiszta)) if r]
    if len(reszek) >= 2:
        return " ".join(reszek[0].split()), " ".join(reszek[-1].split())
    return "", " ".join(reszek[0].split()) if reszek else ""


def _szotar(szoveg: str) -> set[str]:
    return set(_SZO.findall(egyszerusit(szoveg)))


def _lekeres(parameterek: dict[str, str]) -> list[dict]:
    url = f"{API}?{urllib.parse.urlencode(parameterek)}"
    for probalkozas in range(PROBALKOZAS):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=FEJLEC), timeout=IDOKORLAT_MP) as v:
                adat = json.loads(v.read(MAX_VALASZ))
            if not isinstance(adat, list):
                raise DalszovegHiba("A dalszöveg-szolgáltatás érvénytelen választ adott.")
            return adat
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            if isinstance(e, urllib.error.HTTPError) and e.code < 500 and e.code != 429:
                raise DalszovegHiba(f"A dalszöveg-szolgáltatás hibája: {e.code}") from e
            if probalkozas == PROBALKOZAS - 1:
                raise DalszovegHiba(f"A dalszöveg-szolgáltatás nem érhető el: {e}") from e
            time.sleep(VARAKOZAS_MP * (probalkozas + 1))
    return []


def _illik(jelolt: dict, cim_szavak: set[str], keresett: set[str], hossz: int) -> bool:
    cim = _szotar(str(jelolt.get("trackName") or ""))
    eloado = _szotar(str(jelolt.get("artistName") or ""))
    if not cim or not cim <= cim_szavak or not eloado & keresett:
        return False
    tartam = jelolt.get("duration")
    return not (hossz and isinstance(tartam, (int, float)) and abs(tartam - hossz) > HOSSZ_TURES_MP)


def _legrosszabb(jeloltek: list[dict], cim_szavak: set[str], keresett: set[str], hossz: int) -> Eredmeny | None:
    illok = [j for j in jeloltek if isinstance(j, dict) and _illik(j, cim_szavak, keresett, hossz)]
    szoveges = [j for j in illok if j.get("plainLyrics")]
    if szoveges:
        ertekelesek = [ertekel(str(j["plainLyrics"])) for j in szoveges]
        return Eredmeny(True, max(ertekelesek, key=lambda e: e.pont),
                        forras=f"{szoveges[0].get('artistName')} – {szoveges[0].get('trackName')}")
    if any(j.get("instrumental") for j in illok):
        return Eredmeny(True, instrumental=True)
    return None


def vizsgal(cim: str, hossz: int = 0, tobblet: str = "") -> Eredmeny:
    eloado, szam = cim_bontas(cim)
    cim_szavak = _szotar(f"{eloado} {szam}")
    keresett = cim_szavak | _szotar(tobblet)
    if not szam:
        return Eredmeny(False)
    kerdesek: list[dict[str, str]] = []
    if eloado:
        kerdesek.append({"track_name": szam, "artist_name": eloado})
    kerdesek.append({"q": " ".join(f"{eloado} {szam}".split())})
    if tobblet:
        kerdesek.append({"q": " ".join(tobblet.split())})
    for parameterek in kerdesek:
        eredmeny = _legrosszabb(_lekeres(parameterek), cim_szavak, keresett, hossz)
        if eredmeny is not None:
            return eredmeny
    return Eredmeny(False)


class DalszovegTar:
    def __init__(self, ut: Path, ido=time.time) -> None:
        self.ut = ut
        self._ido = ido
        self._zar = threading.Lock()
        try:
            adat = json.loads(ut.read_text(encoding="utf-8"))
            self._adat: dict[str, dict] = adat if isinstance(adat, dict) else {}
        except (OSError, ValueError):
            self._adat = {}

    @staticmethod
    def kulcs(cim: str) -> str:
        eloado, szam = cim_bontas(cim)
        return " | ".join(" ".join(_SZO.findall(egyszerusit(r))) for r in (eloado, szam))

    def keres(self, cim: str) -> Eredmeny | None:
        with self._zar:
            e = self._adat.get(self.kulcs(cim))
        if not isinstance(e, dict):
            return None
        if not e.get("t"):
            return Eredmeny(False) if self._ido() - float(e.get("i", 0)) < NINCS_MEGORZES_MP else None
        try:
            return Eredmeny(True, Ertekeles(**e["e"]), bool(e.get("n")))
        except (KeyError, TypeError):
            return None

    def beir(self, cim: str, eredmeny: Eredmeny) -> None:
        bejegyzes = {"t": eredmeny.talalt, "e": asdict(eredmeny.ertekeles), "n": eredmeny.instrumental,
                     "i": self._ido()}
        with self._zar:
            self._adat[self.kulcs(cim)] = bejegyzes
            try:
                self.ut.parent.mkdir(parents=True, exist_ok=True)
                ideiglenes = self.ut.with_suffix(".tmp")
                ideiglenes.write_text(json.dumps(self._adat, ensure_ascii=False), encoding="utf-8")
                ideiglenes.replace(self.ut)
            except OSError as e:
                naplo.warning("A dalszöveg-tár nem menthető: %s", e)
