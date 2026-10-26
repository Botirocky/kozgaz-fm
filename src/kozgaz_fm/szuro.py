__lazy_modules__ = ["re", "unicodedata", "collections.abc"]

import re
import unicodedata
from collections.abc import Iterable

KORHATAR = 18

ALAP_SZAVAK = (
    "explicit", "fuck*", "motherfuck*", "shit", "shitty", "bitch*", "nigga*",
    "kurva*", "geci*", "fasz", "faszom", "faszt", "faszfej*", "faszkalap*", "faszság*",
    "bazd*", "baszd*", "baszo*", "baszt*", "baszni", "baszik", "baszott", "kibasz*", "elbasz*", "megbasz*",
    "picsa*", "pöcs", "pöcsfej*", "segg*", "ribanc*", "köcsög*", "buzi*", "szar", "szaros", "szarság*",
)


def egyszerusit(szoveg: str) -> str:
    bontott = unicodedata.normalize("NFKD", szoveg)
    return "".join(c for c in bontott if not unicodedata.combining(c)).casefold()


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
            if szoveg and (m := self._re.search(egyszerusit(szoveg))):
                return m.group(0)
        return None
