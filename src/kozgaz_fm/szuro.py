__lazy_modules__ = ["re", "unicodedata", "collections.abc", "dataclasses"]

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

KORHATAR = 18

ALAP_SZAVAK = (
    "explicit", "fuck*", "motherfuck*", "shit", "shitty", "bitch*", "nigga*",
    "kurva*", "geci*", "fasz", "faszom", "faszt", "faszfej*", "faszkalap*", "faszság*",
    "bazd*", "baszd*", "baszo*", "baszt*", "baszni", "baszik", "baszott", "kibasz*", "elbasz*", "megbasz*",
    "picsa*", "pöcs", "pöcsfej*", "segg*", "ribanc*", "köcsög*", "buzi*", "szar", "szaros", "szarság*",
)

EROS_SZAVAK = (
    "fuck*", "fuk", "fuks", "fucc*", "motherfuck*", "mothafuck*", "muthafuck*", "cunt*", "nigger*", "faggot*",
    "kurva*", "kurvá*", "geci*", "fasz*", "basz*", "bazd*", "bazm*", "kibasz*", "elbasz*", "megbasz*", "lebasz*",
    "felbasz*", "rabasz*", "szetbasz*", "buzi*",
)
KOZEPES_SZAVAK = (
    "shit*", "bullshit*", "bitch*", "biatch*", "asshole*", "pussy", "pussies", "dick", "dicks", "dickhead*", "cock",
    "cocks", "cocksuck*", "whore*", "slut*", "nigga*", "fag", "fags", "ribanc*", "kocsog*", "picsa*", "picsat",
    "picsad*", "pina", "pinat", "pinad", "pinaja*", "pocs", "pocsom", "pocsod", "pocsfej*", "seggfej*", "szopd*",
    "szopj*", "szopo*", "lofasz*",
)
ENYHE_SZAVAK = (
    "damn", "goddamn", "ass", "asses", "bastard*", "crap", "hoe", "hoes", "szar", "szart", "szaros*", "szarsag*",
    "szarni", "szarik", "szarok", "segg", "seggem", "segged", "segget", "seggbe", "fasza",
)
KIVETELEK = ("baszk*", "faszin*", "fasza", "fasziz*", "shitake*")

SULY_EROS = 5
SULY_KOZEPES = 3
SULY_ENYHE = 1
MIN_SZAVAK = 100

ERZEKENYSEGEK = {
    "szigoru": "Szigorú",
    "normal": "Normál",
    "laza": "Laza",
}
HATAROK = {
    "szigoru": (2, 3.0),
    "normal": (5, 5.0),
    "laza": (15, 20.0),
}
_ROVIDITETT = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s",
                             "!": "i"})
_SZO = re.compile(r"[\w@$*#]+(?:!+[\w@$*#]+)*")


def egyszerusit(szoveg: str) -> str:
    bontott = unicodedata.normalize("NFKD", szoveg)
    return "".join(c for c in bontott if not unicodedata.combining(c)).casefold()


def _szolista_re(szavak: Iterable[str]) -> re.Pattern:
    egesz = []
    for szo in szavak:
        szo = egyszerusit(szo)
        egesz.append(re.escape(szo[:-1]) + r"\w*" if szo.endswith("*") else re.escape(szo))
    return re.compile("(?:" + "|".join(egesz) + ")")


_EROS_RE = _szolista_re(EROS_SZAVAK)
_KOZEPES_RE = _szolista_re(KOZEPES_SZAVAK)
_ENYHE_RE = _szolista_re(ENYHE_SZAVAK)
_KIVETEL_RE = _szolista_re(KIVETELEK)
_TOVEK = tuple(dict.fromkeys(egyszerusit(s).rstrip("*") for s in (*EROS_SZAVAK, *KOZEPES_SZAVAK, *ENYHE_SZAVAK)))


def _cenzurazott(szo: str) -> str:
    if len(szo) < 3 or not szo[0].isalpha():
        return szo
    minta = re.compile("".join("." if c in "*#_" else re.escape(c) for c in szo))
    return next((t for t in _TOVEK if len(t) >= len(szo) and minta.fullmatch(t[:len(szo)])), szo.replace("_", ""))


def _nyers_szavak(szoveg: str) -> list[str]:
    return [s for s in _SZO.findall(egyszerusit(szoveg)) if any(c.isalpha() for c in s)]


def szavak_kibontva(szoveg: str) -> list[str]:
    eredmeny = []
    for nyers in _nyers_szavak(szoveg):
        szo = nyers.translate(_ROVIDITETT) if not nyers.isalpha() else nyers
        if any(c in szo for c in "*#_"):
            szo = _cenzurazott(szo)
        szo = re.sub(r"(.)\1{2,}", r"\1", szo)
        eredmeny.append(szo)
    return eredmeny


def _fokozat(szo: str) -> int:
    if _KIVETEL_RE.fullmatch(szo) and not _ENYHE_RE.fullmatch(szo):
        return 0
    if _EROS_RE.fullmatch(szo) and not _ENYHE_RE.fullmatch(szo):
        return SULY_EROS
    if _KOZEPES_RE.fullmatch(szo):
        return SULY_KOZEPES
    if _ENYHE_RE.fullmatch(szo):
        return SULY_ENYHE
    return 0


@dataclass(frozen=True)
class Ertekeles:
    szavak: int = 0
    eros: int = 0
    kozepes: int = 0
    enyhe: int = 0

    @property
    def pont(self) -> int:
        return self.eros * SULY_EROS + self.kozepes * SULY_KOZEPES + self.enyhe * SULY_ENYHE

    @property
    def suruseg(self) -> float:
        return self.pont * 100 / max(self.szavak, MIN_SZAVAK)

    def tragar(self, erzekenyseg: str = "normal") -> bool:
        max_eros, max_suruseg = HATAROK.get(erzekenyseg, HATAROK["normal"])
        return self.eros >= max_eros or self.suruseg >= max_suruseg

    def szoveg(self) -> str:
        return (f"{self.eros} erős, {self.kozepes} közepes, {self.enyhe} enyhe szó {self.szavak} szóból "
                f"({self.suruseg:.1f} pont/100 szó)")


def ertekel(szoveg: str) -> Ertekeles:
    szavak = szavak_kibontva(szoveg)
    darab = {SULY_EROS: 0, SULY_KOZEPES: 0, SULY_ENYHE: 0, 0: 0}
    for szo in szavak:
        darab[_fokozat(szo)] += 1
    return Ertekeles(len(szavak), darab[SULY_EROS], darab[SULY_KOZEPES], darab[SULY_ENYHE])


def _minta(szo: str) -> str | None:
    szo = egyszerusit(" ".join(szo.split()))
    elotag = szo.endswith("*")
    szo = szo.rstrip("*").strip()
    if not szo:
        return None
    return r"(?<!\w)" + re.escape(szo) + ("" if elotag else r"(?!\w)")


class Szuro:
    def __init__(self, szavak: Iterable[str] = (), alap: bool = True) -> None:
        self.szavak = tuple(s.strip() for s in szavak if s.strip())
        self.alap = alap
        mintak = [m for m in map(_minta, (*self.szavak, *(ALAP_SZAVAK if alap else ()))) if m]
        self._re = re.compile("|".join(mintak)) if mintak else None

    @property
    def kulcs(self) -> tuple:
        return self.szavak, self.alap

    def __bool__(self) -> bool:
        return self._re is not None

    def talalat(self, *szovegek: str) -> str | None:
        if self._re is None:
            return None
        for szoveg in szovegek:
            if not szoveg:
                continue
            if m := self._re.search(egyszerusit(szoveg)):
                return m.group(0)
            kibontott = szavak_kibontva(szoveg)
            if kibontott != _nyers_szavak(szoveg) and (m := self._re.search(" ".join(kibontott))):
                return m.group(0)
        return None
