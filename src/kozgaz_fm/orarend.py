__lazy_modules__ = ["dataclasses", "datetime", "enum", "kozgaz_fm.beallitasok"]

from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from enum import StrEnum

from kozgaz_fm.beallitasok import Beallitasok, Bemondas, Csengetesirend, Rendkivuli


class Tipus(StrEnum):
    JELZO = "jelző"
    BECSENGO = "becsengő"
    KICSENGO = "kicsengő"
    ZENE_INDUL = "zene indul"
    ZENE_LEALL = "zene leáll"
    BEMONDAS = "bemondás"
    RENDKIVULI = "rendkívüli csengetés"
    RIADO = "riadó"
    RIADO_VEGE = "riadó vége"
    CSEND = "csendes időszak"
    CSEND_VEGE = "csendes időszak vége"


CSENGOK = (Tipus.JELZO, Tipus.BECSENGO, Tipus.KICSENGO)
KULONLEGES = (Tipus.RENDKIVULI, Tipus.RIADO, Tipus.CSEND)


@dataclass(frozen=True, order=True)
class Esemeny:
    ido: datetime
    tipus: Tipus = field(compare=False)
    ora: int = field(default=0, compare=False)
    bemondas: Bemondas | None = field(default=None, compare=False, hash=False)
    rendkivuli: Rendkivuli | None = field(default=None, compare=False, hash=False)
    hangero: int | None = field(default=None, compare=False)

    @property
    def leiras(self) -> str:
        if self.tipus is Tipus.BEMONDAS and self.bemondas:
            return f"Bemondás: {self.bemondas.nev}"
        if self.rendkivuli:
            if self.tipus in (Tipus.RIADO_VEGE, Tipus.CSEND_VEGE):
                return f"{self.rendkivuli.nev} – vége"
            return self.rendkivuli.nev
        if self.tipus in CSENGOK:
            return f"{self.ora}. óra – {self.tipus}" + (" (halkan)" if self.hangero else "")
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
    csend: str = ""

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


def napi_orak(b: Beallitasok, nap: date) -> list[tuple[datetime, datetime]]:
    rend = napi_rend(b, nap)
    return _idopontok(rend, nap) if rend else []


def _idopontok(rend: Csengetesirend, nap: date) -> list[tuple[datetime, datetime]]:
    parok = [(datetime.combine(nap, ido(o.kezdet)), datetime.combine(nap, ido(o.vege))) for o in rend.orak]
    return sorted(p for p in parok if p[1] > p[0])


def _jelzo_ido(b: Beallitasok, kezdet: datetime, elozo_vege: datetime | None) -> datetime | None:
    if not b.jelzo or b.jelzo_perc <= 0:
        return None
    jelzo = kezdet - timedelta(minutes=b.jelzo_perc)
    if elozo_vege is not None and jelzo <= elozo_vege:
        return None
    return jelzo


def csendes_idoszakok(b: Beallitasok, nap: date) -> list[tuple[datetime, datetime, Rendkivuli]]:
    iso = nap.isoformat()
    eredmeny = []
    for r in b.rendkivuli:
        if not r.aktiv or r.tipus != "csend" or r.datum != iso or not r.ig:
            continue
        kezdet, vege = datetime.combine(nap, ido(r.tol)), datetime.combine(nap, ido(r.ig))
        if vege > kezdet:
            eredmeny.append((kezdet, vege, r))
    return sorted(eredmeny, key=lambda c: c[0])


def _csendben(csendek: list[tuple[datetime, datetime, Rendkivuli]], mikor: datetime) -> Rendkivuli | None:
    return next((r for kezdet, vege, r in csendek if kezdet <= mikor < vege), None)


def _zene_csend_nelkul(parok: list[tuple[datetime, datetime, int]],
                       csendek: list[tuple[datetime, datetime, Rendkivuli]]) -> list[tuple[datetime, datetime, int]]:
    for kezdet, vege, _ in csendek:
        maradek = []
        for indul, leall, szam in parok:
            if leall <= kezdet or indul >= vege:
                maradek.append((indul, leall, szam))
                continue
            if indul < kezdet:
                maradek.append((indul, kezdet, szam))
            if leall > vege:
                maradek.append((vege, leall, szam))
        parok = maradek
    return [p for p in parok if p[1] - p[0] >= timedelta(seconds=30)]


def _rendkivuli_esemenyek(b: Beallitasok, nap: date) -> list[Esemeny]:
    iso = nap.isoformat()
    esemenyek: list[Esemeny] = []
    for r in b.rendkivuli:
        if not r.aktiv or r.datum != iso:
            continue
        kezdet = datetime.combine(nap, ido(r.tol))
        if r.tipus == "csengetes":
            esemenyek.append(Esemeny(kezdet, Tipus.RENDKIVULI, rendkivuli=r))
        elif r.tipus == "riado":
            esemenyek.append(Esemeny(kezdet, Tipus.RIADO, rendkivuli=r))
            if r.riado_perc > 0:
                esemenyek.append(Esemeny(kezdet + timedelta(minutes=r.riado_perc), Tipus.RIADO_VEGE, rendkivuli=r))
    for kezdet, vege, r in csendes_idoszakok(b, nap):
        esemenyek.append(Esemeny(kezdet, Tipus.CSEND, rendkivuli=r))
        esemenyek.append(Esemeny(vege, Tipus.CSEND_VEGE, rendkivuli=r))
    return esemenyek


def napi_esemenyek(b: Beallitasok, nap: date) -> list[Esemeny]:
    csengok: list[Esemeny] = []
    zene_parok: list[tuple[datetime, datetime, int]] = []
    rend = napi_rend(b, nap)
    orak = _idopontok(rend, nap) if rend else []
    zene_ma = b.zene_szunetben and b.ma_nincs_zene != nap.isoformat()
    elozo_vege: datetime | None = None
    for szam, (kezdet, vege) in enumerate(orak, start=1):
        jelzo = _jelzo_ido(b, kezdet, elozo_vege)
        if jelzo:
            csengok.append(Esemeny(jelzo, Tipus.JELZO, szam))
        csengok.append(Esemeny(kezdet, Tipus.BECSENGO, szam))
        if b.kicsengo:
            csengok.append(Esemeny(vege, Tipus.KICSENGO, szam))
        if zene_ma:
            ablak = _zene_ablak(b, elozo_vege, jelzo or kezdet)
            if ablak:
                zene_parok.append((*ablak, szam - 1))
        elozo_vege = vege
    csendek = csendes_idoszakok(b, nap)
    esemenyek: list[Esemeny] = []
    for e in csengok:
        csend = _csendben(csendek, e.ido)
        if csend is None:
            esemenyek.append(e)
        elif csend.csengo_hangero > 0:
            esemenyek.append(replace(e, hangero=csend.csengo_hangero))
    for indul, leall, szam in _zene_csend_nelkul(zene_parok, csendek):
        esemenyek.append(Esemeny(indul, Tipus.ZENE_INDUL, szam))
        esemenyek.append(Esemeny(leall, Tipus.ZENE_LEALL, szam))
    esemenyek.extend(_rendkivuli_esemenyek(b, nap))
    for bem in b.bemondasok:
        if not bem.aktiv:
            continue
        if bem.datum:
            if bem.datum != nap.isoformat():
                continue
        elif nap.weekday() not in bem.napok or szunnap_nev(b, nap) is not None:
            continue
        mikor = datetime.combine(nap, ido(bem.ido))
        if _csendben(csendek, mikor) is None:
            esemenyek.append(Esemeny(mikor, Tipus.BEMONDAS, bemondas=bem))
    return sorted(esemenyek, key=lambda e: (e.ido, _sorrend(e.tipus)))


def _sorrend(tipus: Tipus) -> int:
    return [Tipus.ZENE_LEALL, Tipus.CSEND, Tipus.KICSENGO, Tipus.JELZO, Tipus.BECSENGO, Tipus.RENDKIVULI,
            Tipus.RIADO_VEGE, Tipus.RIADO, Tipus.BEMONDAS, Tipus.CSEND_VEGE, Tipus.ZENE_INDUL].index(tipus)


def _zene_ablak(b: Beallitasok, elozo_vege: datetime | None,
                kovetkezo_csengo: datetime) -> tuple[datetime, datetime] | None:
    leall = kovetkezo_csengo - timedelta(seconds=b.zene_leall_elotte)
    if elozo_vege is None:
        if not b.reggeli_zene:
            return None
        indul = datetime.combine(kovetkezo_csengo.date(), ido(b.reggeli_zene_tol))
    else:
        if kovetkezo_csengo - elozo_vege < timedelta(minutes=b.zene_min_szunet):
            return None
        indul = elozo_vege + timedelta(seconds=b.zene_kesleltetes)
    if leall - indul < timedelta(seconds=30):
        return None
    return indul, leall


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
    a = _allapot(b, most)
    csend = _csendben(csendes_idoszakok(b, most.date()), most)
    return replace(a, csend=csend.nev) if csend else a


def _allapot(b: Beallitasok, most: datetime) -> Allapot:
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
