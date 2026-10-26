__lazy_modules__ = ["secrets", "collections.abc", "dataclasses", "datetime", "urllib.parse", "kozgaz_fm.szuro"]

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from kozgaz_fm.szuro import KORHATAR, Szuro

MAX_SZOVEG = 150
MAX_NEV = 30
MAX_VARAKOZO = 40
IP_ORANKENT = 20
MEGORZES = timedelta(hours=12)
YOUTUBE_GAZDAK = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}

ALLAPOT_NEVEK = {
    "kereses": "Keresés…",
    "varakozik": "Jóváhagyásra vár",
    "elfogadva": "Elfogadva, hamarosan szól",
    "szol": "Most szól",
    "elutasitva": "Elutasítva",
}


class KeresHiba(Exception):
    def __init__(self, kod: str, uzenet: str) -> None:
        super().__init__(uzenet)
        self.kod = kod


@dataclass
class Keres:
    azon: str
    szoveg: str
    nev: str
    eszkoz: str
    ip: str
    ido: datetime
    allapot: str = "kereses"
    cim: str = ""
    yt: str = ""
    hossz: int = 0
    ok: str = ""

    def nyilvanos(self) -> dict:
        return {"azon": self.azon, "szoveg": self.szoveg, "cim": self.cim, "allapot": self.allapot,
                "allapot_nev": ALLAPOT_NEVEK.get(self.allapot, self.allapot), "ok": self.ok,
                "ido": f"{self.ido:%H:%M}"}

    def admin(self) -> dict:
        return {**self.nyilvanos(), "nev": self.nev, "hossz": self.hossz, "ip": self.ip,
                "link": f"https://www.youtube.com/watch?v={self.yt}" if self.yt else ""}


def youtube_cel(szoveg: str) -> str:
    szoveg = szoveg.strip()
    if "://" not in szoveg and not szoveg.lower().startswith(tuple(YOUTUBE_GAZDAK)):
        return f"ytsearch1:{szoveg}"
    cim = szoveg if "://" in szoveg else f"https://{szoveg}"
    reszek = urlsplit(cim)
    if reszek.scheme not in ("http", "https") or (reszek.hostname or "").lower() not in YOUTUBE_GAZDAK:
        raise KeresHiba("bad_link", "Csak YouTube-link vagy a szám címe adható meg.")
    return cim


def tiltott_e(szoveg: str, tiltott: list[str]) -> bool:
    kis = szoveg.casefold()
    return any(t.strip() and t.strip().casefold() in kis for t in tiltott)


class Keresek:
    def __init__(self, ido: Callable[[], datetime] = datetime.now) -> None:
        self._ido = ido
        self.lista: list[Keres] = []

    def _takarit(self) -> None:
        hatar = self._ido() - MEGORZES
        self.lista = [k for k in self.lista if k.ido >= hatar or k.allapot in ("kereses", "varakozik")]

    def keres(self, azon: str) -> Keres:
        for k in self.lista:
            if k.azon == azon:
                return k
        raise KeresHiba("not_found", "Nincs ilyen kérés.")

    def mai_szam(self, eszkoz: str) -> int:
        ma = self._ido().date()
        return sum(1 for k in self.lista if k.eszkoz == eszkoz and k.ido.date() == ma
                   and not (k.allapot == "elutasitva" and k.ok))

    def maradek(self, eszkoz: str, napi: int) -> int:
        return max(0, napi - self.mai_szam(eszkoz))

    def sajat(self, eszkoz: str) -> list[Keres]:
        ma = self._ido().date()
        return [k for k in reversed(self.lista) if k.eszkoz == eszkoz and k.ido.date() == ma]

    def fuggo(self) -> list[Keres]:
        return [k for k in self.lista if k.allapot in ("kereses", "varakozik")]

    def uj(self, szoveg: str, nev: str, eszkoz: str, ip: str, napi: int, tiltott: list[str],
           szuro: Szuro | None = None) -> Keres:
        self._takarit()
        szoveg = " ".join(str(szoveg or "").split())
        nev = " ".join(str(nev or "").split())
        if not szoveg:
            raise KeresHiba("validation_error", "Írd be a szám címét vagy a YouTube-linkjét.")
        if len(szoveg) > MAX_SZOVEG or len(nev) > MAX_NEV:
            raise KeresHiba("validation_error", f"Legfeljebb {MAX_SZOVEG} karakter lehet a kérés, "
                                                f"{MAX_NEV} a név.")
        youtube_cel(szoveg)
        if tiltott_e(szoveg, tiltott) or tiltott_e(nev, tiltott) or (szuro is not None and szuro.talalat(szoveg, nev)):
            raise KeresHiba("forbidden_word", "Ezt a kérést nem lehet elküldeni.")
        if self.maradek(eszkoz, napi) <= 0:
            raise KeresHiba("daily_limit", f"Ma már nem kérhetsz több számot (napi {napi}).")
        egy_oraja = self._ido() - timedelta(hours=1)
        if sum(1 for k in self.lista if k.ip == ip and k.ido >= egy_oraja) >= IP_ORANKENT:
            raise KeresHiba("rate_limited", "Erről a hálózatról most túl sok kérés jött, próbáld később.")
        if len(self.fuggo()) >= MAX_VARAKOZO:
            raise KeresHiba("queue_full", "Most túl sok kérés vár jóváhagyásra, próbáld később.")
        k = Keres(secrets.token_urlsafe(8), szoveg, nev, eszkoz, ip, self._ido())
        self.lista.append(k)
        return k

    def talalat(self, azon: str, yt: str, cim: str, hossz: int, max_perc: int, tiltott: list[str],
                korhatar: int = 0, szuro: Szuro | None = None, korhatar_tiltas: bool = True) -> Keres:
        k = self.keres(azon)
        if k.allapot != "kereses":
            return k
        k.yt, k.cim, k.hossz = yt, cim, hossz
        if korhatar_tiltas and korhatar >= KORHATAR:
            self._elutasit(k, "Korhatáros videó nem kérhető.")
        elif tiltott_e(cim, tiltott) or (szuro is not None and szuro.talalat(cim)):
            self._elutasit(k, "A szám nem engedélyezett.")
        elif hossz <= 0:
            self._elutasit(k, "Élő adás vagy ismeretlen hosszú videó nem kérhető.")
        elif hossz > max_perc * 60:
            self._elutasit(k, f"Túl hosszú (legfeljebb {max_perc} perc lehet).")
        elif any(m is not k and m.yt == yt and m.allapot in ("varakozik", "elfogadva") for m in self.lista):
            self._elutasit(k, "Ezt a számot már kérték, hamarosan szólhat.")
        else:
            k.allapot = "varakozik"
        return k

    def nem_talalt(self, azon: str, ok: str) -> Keres:
        k = self.keres(azon)
        if k.allapot == "kereses":
            self._elutasit(k, ok)
        return k

    def dont(self, azon: str, elfogad: bool) -> Keres:
        k = self.keres(azon)
        if k.allapot != "varakozik":
            raise KeresHiba("conflict", "Erről a kérésről már döntöttek.")
        if elfogad:
            k.allapot = "elfogadva"
        else:
            self._elutasit(k, "")
        return k

    def szol(self, yt: str) -> Keres | None:
        for k in self.lista:
            if k.yt == yt and k.allapot == "elfogadva":
                k.allapot = "szol"
                return k
        return None

    def _elutasit(self, k: Keres, ok: str) -> None:
        k.allapot = "elutasitva"
        k.ok = ok
