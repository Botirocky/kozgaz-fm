__lazy_modules__ = ["json", "urllib.error", "urllib.parse", "urllib.request", "datetime", "PySide6.QtCore",
                    "kozgaz_fm", "kozgaz_fm.hatter", "kozgaz_fm.zenekeres"]

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer, Signal

from kozgaz_fm import __version__, hatter
from kozgaz_fm.zenekeres import KeresHiba

if TYPE_CHECKING:
    from kozgaz_fm.vezerlo import Vezerlo

KOR_MP = 4
HIBA_KOR_MP = 20
IDOKORLAT_MP = 10
MAX_UJ = 20


class SzerverHiba(Exception):
    pass


def szerver_cim(cim: str) -> str:
    cim = cim.strip().rstrip("/")
    if not cim:
        return ""
    if "://" not in cim:
        cim = f"https://{cim}"
    reszek = urllib.parse.urlsplit(cim)
    if reszek.scheme not in ("http", "https") or not reszek.hostname:
        raise SzerverHiba("A szerver címe http:// vagy https:// kezdetű webcím legyen.")
    return f"{reszek.scheme}://{reszek.netloc}{reszek.path.rstrip('/')}"


def kuld(cim: str, kulcs: str, adat: dict) -> dict:
    keres = urllib.request.Request(f"{cim}/api/gep", data=json.dumps(adat).encode(), method="POST", headers={
        "Content-Type": "application/json", "X-Kozgaz-FM-Kulcs": kulcs, "User-Agent": f"KozgazFM/{__version__}"})
    try:
        with urllib.request.urlopen(keres, timeout=IDOKORLAT_MP) as valasz:
            tartalom = json.loads(valasz.read(1_000_000) or b"{}")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise SzerverHiba("A szerver nem fogadta el a kulcsot.") from None
        raise SzerverHiba(f"A szerver hibát jelzett ({e.code}).") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise SzerverHiba(f"A szerver nem érhető el ({getattr(e, 'reason', e)}).") from None
    except ValueError:
        raise SzerverHiba("A szerver érvénytelen választ küldött.") from None
    if not isinstance(tartalom, dict) or not isinstance(tartalom.get("data"), dict):
        raise SzerverHiba("A szerver érvénytelen választ küldött.")
    return tartalom["data"]


class ZenekeresSzerver(QObject):
    valtozott = Signal()

    def __init__(self, v: "Vezerlo", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.v = v
        self.hiba = ""
        self.utolso: datetime | None = None
        self._tavoli: set[str] = set()
        self._elkuldott: dict[str, dict] = {}
        self._kozvetlen: dict[str, dict] = {}
        self._fut = False
        self._ido = QTimer(self)
        self._ido.setSingleShot(True)
        self._ido.timeout.connect(self._kor)
        self._ido.start(1000)

    @property
    def beallitva(self) -> bool:
        return bool(self.v.b.zenekeres_szerver.strip() and self.v.b.zenekeres_szerver_kulcs.strip())

    def cim(self) -> str:
        try:
            return szerver_cim(self.v.b.zenekeres_szerver)
        except SzerverHiba:
            return ""

    def oldal(self) -> str:
        cim = self.cim()
        return f"{cim}/" if cim and self.v.b.zenekeres_szerver_kulcs.strip() else ""

    def ujraindit(self) -> None:
        self.hiba = ""
        self.utolso = None
        self._elkuldott.clear()
        self.valtozott.emit()
        if not self._fut:
            self._ido.start(200)

    def _beallitasok(self) -> dict:
        b = self.v.b
        ma = datetime.now().date().isoformat()
        return {"aktiv": b.zenekeres, "auto": b.zenekeres_auto, "cim": b.kijelzo_cim, "napi": b.zenekeres_napi,
                "max_perc": b.zenekeres_max_perc,
                "tiltott_telefonok": [t.kulcs for t in b.tiltott_telefonok if t.ig >= ma]}

    def _allapotok(self) -> list[dict]:
        lista = []
        helyek: dict[str, int] = {}
        for n, (_, szam) in enumerate(self.v.zene.kert_sor(), 1):
            if szam.yt:
                helyek.setdefault(szam.yt, n)
        for k in self.v.keresek.lista:
            if k.azon in self._tavoli:
                adat = {**k.nyilvanos(), "hely": helyek.get(k.yt, 0) if k.allapot == "elfogadva" else 0}
                if self._elkuldott.get(k.azon) != adat:
                    lista.append(adat)
        for azon, adat in self._kozvetlen.items():
            if self._elkuldott.get(azon) != adat:
                lista.append(adat)
        return lista

    def _kor(self) -> None:
        if self._fut:
            return
        if not self.beallitva or self.v.tartalek.passziv:
            self._ido.start(KOR_MP * 1000)
            return
        cim = self.cim()
        if not cim:
            self._hibas("A szerver címe hibás.")
            return
        kulcs = self.v.b.zenekeres_szerver_kulcs.strip()
        allapotok = self._allapotok()
        adat = {"beallitasok": self._beallitasok(), "allapotok": allapotok, "verzio": __version__}
        self._fut = True
        hatter.futtat(lambda: kuld(cim, kulcs, adat), lambda v: self._kesz(v, allapotok),
                      lambda e: self._hibas(str(e)))

    def _hibas(self, uzenet: str) -> None:
        self._fut = False
        if uzenet != self.hiba:
            self.v.log(f"Zenekérés-szerver: {uzenet}")
        self.hiba = uzenet
        self.valtozott.emit()
        self._ido.start(HIBA_KOR_MP * 1000)

    def _kesz(self, valasz: dict, elkuldott: list[dict]) -> None:
        self._fut = False
        if self.hiba:
            self.v.log("Zenekérés-szerver: a kapcsolat helyreállt")
        self.hiba = ""
        self.utolso = datetime.now()
        for adat in elkuldott:
            self._elkuldott[adat["azon"]] = adat
        uj = valasz.get("uj")
        for elem in (uj if isinstance(uj, list) else [])[:MAX_UJ]:
            if isinstance(elem, dict):
                self._fogad(elem)
        self._takarit()
        szavazatok = valasz.get("szavazatok")
        if isinstance(szavazatok, dict):
            self.v.zene.kert_rendez({k.yt: int(szavazatok[k.azon]) for k in self.v.keresek.lista
                                     if k.yt and k.azon in szavazatok})
        self.valtozott.emit()
        self._ido.start(200 if self._allapotok() else KOR_MP * 1000)

    def _fogad(self, elem: dict) -> None:
        azon, szoveg, nev, eszkoz, ip = (str(elem.get(m) or "") for m in ("azon", "szoveg", "nev", "eszkoz", "ip"))
        if not azon or not eszkoz or azon in self._tavoli or azon in self._kozvetlen:
            return
        try:
            self.v.zenekeres_uj(szoveg, nev, eszkoz, ip or "szerver", azon=azon)
        except KeresHiba as e:
            self._kozvetlen[azon] = {"azon": azon, "szoveg": szoveg[:150], "cim": "", "allapot": "elutasitva",
                                     "allapot_nev": "Elutasítva", "ok": str(e),
                                     "ido": datetime.now().strftime("%H:%M")}
        else:
            self._tavoli.add(azon)

    def _takarit(self) -> None:
        elok = {k.azon for k in self.v.keresek.lista}
        self._tavoli &= elok
        if len(self._kozvetlen) > 200:
            for azon in list(self._kozvetlen)[:-100]:
                self._kozvetlen.pop(azon, None)
        for azon in list(self._elkuldott):
            if azon not in self._tavoli and azon not in self._kozvetlen:
                self._elkuldott.pop(azon, None)
