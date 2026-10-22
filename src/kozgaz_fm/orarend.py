from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import StrEnum

from kozgaz_fm.beallitasok import Beallitasok, Bemondas, Csengetesirend


class Tipus(StrEnum):
    JELZO = "jelző"
    BECSENGO = "becsengő"
    KICSENGO = "kicsengő"
    ZENE_INDUL = "zene indul"
    ZENE_LEALL = "zene leáll"
    BEMONDAS = "bemondás"


CSENGOK = (Tipus.JELZO, Tipus.BECSENGO, Tipus.KICSENGO)


@dataclass(frozen=True, order=True)
class Esemeny:
    ido: datetime
    tipus: Tipus = field(compare=False)
    ora: int = field(default=0, compare=False)
    bemondas: Bemondas | None = field(default=None, compare=False, hash=False)

    @property
    def leiras(self) -> str:
        if self.tipus is Tipus.BEMONDAS and self.bemondas:
            return f"Bemondás: {self.bemondas.nev}"
        if self.tipus in CSENGOK:
            return f"{self.ora}. óra – {self.tipus}"
        return self.tipus.value.capitalize()


class Szakasz(StrEnum):
    ORA = "óra"
    SZUNET = "szünet"
    REGGEL = "tanítás előtt"
    VEGE = "tanítás után"
    SZUNNAP = "szünnap"
    NINCS = "nincs csengetés"


@dataclass(frozen=True)
class Allapot:
    szakasz: Szakasz
    ora: int = 0
    kezdet: datetime | None = None
    vege: datetime | None = None
    kovetkezo: Esemeny | None = None
    szunnap_nev: str = ""

    def hatralevo(self, most: datetime) -> timedelta | None:
        if self.vege is None:
            return None
        return max(self.vege - most, timedelta())

    def haladas(self, most: datetime) -> float:
        if self.kezdet is None or self.vege is None or self.vege <= self.kezdet:
            return 0.0
        return min(1.0, max(0.0, (most - self.kezdet) / (self.vege - self.kezdet)))

    @property
    def cim(self) -> str:
        if self.szakasz is Szakasz.ORA:
            return f"{self.ora}. óra"
        if self.szakasz is Szakasz.SZUNET:
            return f"Szünet ({self.ora}. óra után)"
        if self.szakasz is Szakasz.SZUNNAP:
            return self.szunnap_nev or "Szünnap"
        return self.szakasz.value.capitalize()


def ido(szoveg: str) -> time:
    ora, perc = szoveg.strip().split(":")[:2]
    return time(int(ora), int(perc))


def szunnap_nev(b: Beallitasok, nap: date) -> str | None:
    iso = nap.isoformat()
    for sz in b.szunnapok:
        if sz.tol <= iso <= (sz.ig or sz.tol):
            return sz.nev or "Szünnap"
    return None


def napi_rend(b: Beallitasok, nap: date) -> Csengetesirend | None:
    iso = nap.isoformat()
    if b.ma_nincs_csengetes == iso:
        return None
    if iso in b.kivetelek:
        return b.rend(b.kivetelek[iso])
    if szunnap_nev(b, nap) is not None:
        return None
    nev = b.het[nap.weekday()] if nap.weekday() < len(b.het) else ""
    return b.rend(nev) if nev else None


def _idopontok(rend: Csengetesirend, nap: date) -> list[tuple[datetime, datetime]]:
    parok = [(datetime.combine(nap, ido(o.kezdet)), datetime.combine(nap, ido(o.vege))) for o in rend.orak]
    return sorted(p for p in parok if p[1] > p[0])


def _jelzo_ido(b: Beallitasok, kezdet: datetime, elozo_vege: datetime | None) -> datetime | None:
    if b.jelzo_perc <= 0:
        return None
    jelzo = kezdet - timedelta(minutes=b.jelzo_perc)
    if elozo_vege is not None and jelzo <= elozo_vege:
        return None
    return jelzo


def napi_esemenyek(b: Beallitasok, nap: date) -> list[Esemeny]:
    esemenyek: list[Esemeny] = []
    rend = napi_rend(b, nap)
    orak = _idopontok(rend, nap) if rend else []
    zene_ma = b.zene_szunetben and b.ma_nincs_zene != nap.isoformat()
    elozo_vege: datetime | None = None
    for szam, (kezdet, vege) in enumerate(orak, start=1):
        jelzo = _jelzo_ido(b, kezdet, elozo_vege)
        if jelzo:
            esemenyek.append(Esemeny(jelzo, Tipus.JELZO, szam))
        esemenyek.append(Esemeny(kezdet, Tipus.BECSENGO, szam))
        if b.kicsengo:
            esemenyek.append(Esemeny(vege, Tipus.KICSENGO, szam))
        if zene_ma:
            esemenyek.extend(_zene_ablak(b, szam, elozo_vege, jelzo or kezdet))
        elozo_vege = vege
    for bem in b.bemondasok:
        if not bem.aktiv:
            continue
        if bem.datum:
            if bem.datum != nap.isoformat():
                continue
        elif nap.weekday() not in bem.napok or szunnap_nev(b, nap) is not None:
            continue
        esemenyek.append(Esemeny(datetime.combine(nap, ido(bem.ido)), Tipus.BEMONDAS, bemondas=bem))
    return sorted(esemenyek, key=lambda e: (e.ido, _sorrend(e.tipus)))


def _sorrend(tipus: Tipus) -> int:
    return [Tipus.ZENE_LEALL, Tipus.KICSENGO, Tipus.JELZO, Tipus.BECSENGO, Tipus.BEMONDAS,
            Tipus.ZENE_INDUL].index(tipus)


def _zene_ablak(b: Beallitasok, szam: int, elozo_vege: datetime | None,
                kovetkezo_csengo: datetime) -> list[Esemeny]:
    leall = kovetkezo_csengo - timedelta(seconds=b.zene_leall_elotte)
    if elozo_vege is None:
        if not b.reggeli_zene:
            return []
        indul = datetime.combine(kovetkezo_csengo.date(), ido(b.reggeli_zene_tol))
    else:
        if kovetkezo_csengo - elozo_vege < timedelta(minutes=b.zene_min_szunet):
            return []
        indul = elozo_vege + timedelta(seconds=b.zene_kesleltetes)
    if leall - indul < timedelta(seconds=30):
        return []
    return [Esemeny(indul, Tipus.ZENE_INDUL, szam - 1), Esemeny(leall, Tipus.ZENE_LEALL, szam - 1)]


def zene_ablakban(b: Beallitasok, most: datetime) -> bool:
    nyitva = False
    for e in napi_esemenyek(b, most.date()):
        if e.ido > most:
            break
        if e.tipus is Tipus.ZENE_INDUL:
            nyitva = True
        elif e.tipus is Tipus.ZENE_LEALL:
            nyitva = False
    return nyitva


def kovetkezo_esemeny(b: Beallitasok, most: datetime, csak_csengo: bool = True, napok: int = 14) -> Esemeny | None:
    for eltolas in range(napok):
        nap = most.date() + timedelta(days=eltolas)
        for e in napi_esemenyek(b, nap):
            if e.ido > most and (not csak_csengo or e.tipus in CSENGOK):
                return e
    return None


def allapot(b: Beallitasok, most: datetime) -> Allapot:
    nap = most.date()
    kovetkezo = kovetkezo_esemeny(b, most)
    rend = napi_rend(b, nap)
    if rend is None:
        nev = szunnap_nev(b, nap)
        if nev is not None and nap.isoformat() not in b.kivetelek:
            return Allapot(Szakasz.SZUNNAP, kovetkezo=kovetkezo, szunnap_nev=nev)
        return Allapot(Szakasz.NINCS, kovetkezo=kovetkezo)
    orak = _idopontok(rend, nap)
    if not orak:
        return Allapot(Szakasz.NINCS, kovetkezo=kovetkezo)
    if most < orak[0][0]:
        return Allapot(Szakasz.REGGEL, vege=orak[0][0], kovetkezo=kovetkezo)
    for szam, (kezdet, vege) in enumerate(orak, start=1):
        if kezdet <= most < vege:
            return Allapot(Szakasz.ORA, szam, kezdet, vege, kovetkezo)
        if szam < len(orak) and vege <= most < orak[szam][0]:
            return Allapot(Szakasz.SZUNET, szam, vege, orak[szam][0], kovetkezo)
    return Allapot(Szakasz.VEGE, kovetkezo=kovetkezo)


def rend_generalas(elso: str, darab: int, ora_hossz: int, szunet: int, nagyszunet_utan: int = 3,
                   nagyszunet: int = 15) -> list[tuple[str, str]]:
    kezdet = datetime.combine(date.today(), ido(elso))
    eredmeny = []
    for szam in range(1, darab + 1):
        vege = kezdet + timedelta(minutes=ora_hossz)
        eredmeny.append((kezdet.strftime("%H:%M"), vege.strftime("%H:%M")))
        kezdet = vege + timedelta(minutes=nagyszunet if szam == nagyszunet_utan else szunet)
    return eredmeny
