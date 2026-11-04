__lazy_modules__ = ["contextlib", "json", "os", "time", "urllib.error", "urllib.parse", "urllib.request", "dataclasses",
                    "datetime", "pathlib", "PySide6.QtCore", "kozgaz_fm", "kozgaz_fm.hatter",
                    "kozgaz_fm.zenekeres_szerver"]

import contextlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer, Signal

from kozgaz_fm import __version__, hatter
from kozgaz_fm.zenekeres_szerver import SzerverHiba, szerver_cim

if TYPE_CHECKING:
    from kozgaz_fm.vezerlo import Vezerlo

LISTA_FAJL = ".kozgaz-fm-szinkron.json"
RESZ = ".resz"
IDOKORLAT_MP = 30
DARAB = 256 * 1024
ELSO_KOR_MP = 20
KOR_PERC = 30
FORRAS_NEV = "Zenék a szerverről"


@dataclass
class Eredmeny:
    osszes: int = 0
    uj: int = 0
    torolt: int = 0
    hibas: int = 0
    bajt: int = 0


def alap_mappa() -> Path:
    return Path.home() / "Közgáz FM zenék"


def _keres(cim: str, kulcs: str, ut: str, parameter: dict | None = None) -> urllib.request.Request:
    lekerdezes = f"?{urllib.parse.urlencode(parameter)}" if parameter else ""
    return urllib.request.Request(f"{cim}{ut}{lekerdezes}", headers={
        "X-Kozgaz-FM-Kulcs": kulcs, "User-Agent": f"KozgazFM/{__version__}"})


def _hiba(e: Exception) -> SzerverHiba:
    if isinstance(e, urllib.error.HTTPError):
        if e.code in (401, 403):
            return SzerverHiba("A szerver nem fogadta el a kulcsot.")
        if e.code == 503:
            return SzerverHiba("A szerveren nem érhető el a zenemappa (ki van húzva a pendrive?).")
        return SzerverHiba(f"A szerver hibát jelzett ({e.code}).")
    return SzerverHiba(f"A szerver nem érhető el ({getattr(e, 'reason', e)}).")


def biztonsagos_ut(ut: str) -> PurePosixPath | None:
    if not isinstance(ut, str) or not ut or "\\" in ut or "\0" in ut:
        return None
    reszek = ut.split("/")
    if any(r in ("", ".", "..") or r.startswith(".") for r in reszek):
        return None
    return PurePosixPath(*reszek)


def lista(cim: str, kulcs: str) -> list[dict]:
    try:
        with urllib.request.urlopen(_keres(cim, kulcs, "/api/zenek"), timeout=IDOKORLAT_MP) as valasz:
            adat = json.loads(valasz.read(20_000_000) or b"{}")
    except urllib.error.HTTPError as e:
        raise _hiba(e) from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise _hiba(e) from None
    except ValueError:
        raise SzerverHiba("A szerver érvénytelen választ küldött.") from None
    elemek = adat.get("data") if isinstance(adat, dict) else None
    if not isinstance(elemek, list):
        raise SzerverHiba("A szerver érvénytelen választ küldött.")
    return [e for e in elemek if isinstance(e, dict) and biztonsagos_ut(e.get("ut", ""))
            and isinstance(e.get("meret"), int) and isinstance(e.get("ido"), int)]


def letolt(cim: str, kulcs: str, ut: str, cel: Path, meret: int, kbps: int = 0) -> int:
    ideiglenes = cel.with_name(cel.name + RESZ)
    cel.parent.mkdir(parents=True, exist_ok=True)
    megvan = ideiglenes.stat().st_size if ideiglenes.exists() else 0
    if megvan > meret:
        ideiglenes.unlink()
        megvan = 0
    keres = _keres(cim, kulcs, "/api/zenek/fajl", {"ut": ut})
    if megvan:
        keres.add_header("Range", f"bytes={megvan}-")
    kezdet = time.monotonic()
    atvitt = 0
    try:
        with urllib.request.urlopen(keres, timeout=IDOKORLAT_MP) as valasz:
            if megvan and valasz.status != 206:
                megvan = 0
            with open(ideiglenes, "ab" if megvan else "wb") as f:
                while darab := valasz.read(DARAB):
                    f.write(darab)
                    atvitt += len(darab)
                    if kbps > 0:
                        varni = atvitt / (kbps * 1024) - (time.monotonic() - kezdet)
                        if varni > 0:
                            time.sleep(varni)
    except urllib.error.HTTPError as e:
        raise _hiba(e) from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise _hiba(e) from None
    if ideiglenes.stat().st_size != meret:
        raise SzerverHiba(f"Hiányos letöltés: {ut}")
    os.replace(ideiglenes, cel)
    return atvitt


def _jegyzek_olvas(mappa: Path) -> dict[str, list[int]]:
    try:
        adat = json.loads((mappa / LISTA_FAJL).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in adat.items() if isinstance(v, list) and len(v) == 2} if isinstance(adat, dict) else {}


def _jegyzek_ir(mappa: Path, jegyzek: dict[str, list[int]]) -> None:
    ut = mappa / LISTA_FAJL
    ideiglenes = ut.with_name(ut.name + ".tmp")
    ideiglenes.write_text(json.dumps(jegyzek, ensure_ascii=False, indent=0), encoding="utf-8")
    os.replace(ideiglenes, ut)


def _ures_mappak_torlese(mappa: Path) -> None:
    for gyoker, _, _ in sorted(os.walk(mappa), key=lambda e: -len(e[0])):
        ut = Path(gyoker)
        if ut != mappa:
            with contextlib.suppress(OSError):
                ut.rmdir()


def szinkron(cim: str, kulcs: str, mappa: Path, kbps: int = 0,
             jelez: Callable[[int, int, str], None] | None = None,
             megszakit: Callable[[], bool] | None = None) -> Eredmeny:
    tavoli = lista(cim, kulcs)
    mappa.mkdir(parents=True, exist_ok=True)
    jegyzek = _jegyzek_olvas(mappa)
    e = Eredmeny(osszes=len(tavoli))
    meglevo = set()
    for i, elem in enumerate(tavoli, 1):
        if megszakit and megszakit():
            break
        ut = elem["ut"]
        resz = biztonsagos_ut(ut)
        if resz is None:
            continue
        meglevo.add(ut)
        cel = mappa / Path(*resz.parts)
        if jegyzek.get(ut) == [elem["meret"], elem["ido"]] and cel.is_file() and cel.stat().st_size == elem["meret"]:
            continue
        if ut not in jegyzek and cel.is_file() and cel.stat().st_size == elem["meret"]:
            jegyzek[ut] = [elem["meret"], elem["ido"]]
            _jegyzek_ir(mappa, jegyzek)
            continue
        if jelez:
            jelez(i, len(tavoli), ut)
        try:
            e.bajt += letolt(cim, kulcs, ut, cel, elem["meret"], kbps)
        except SzerverHiba:
            e.hibas += 1
            continue
        with contextlib.suppress(OSError):
            os.utime(cel, (elem["ido"], elem["ido"]))
        jegyzek[ut] = [elem["meret"], elem["ido"]]
        _jegyzek_ir(mappa, jegyzek)
        e.uj += 1
    else:
        for ut in [u for u in jegyzek if u not in meglevo]:
            resz = biztonsagos_ut(ut)
            if resz is not None:
                try:
                    (mappa / Path(*resz.parts)).unlink(missing_ok=True)
                    e.torolt += 1
                except OSError:
                    continue
            jegyzek.pop(ut, None)
        if e.torolt:
            _jegyzek_ir(mappa, jegyzek)
            _ures_mappak_torlese(mappa)
    return e


class ZeneSzinkron(QObject):
    valtozott = Signal()
    _halad = Signal(int, int, str)

    def __init__(self, v: "Vezerlo", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.v = v
        self.hiba = ""
        self.utolso: datetime | None = None
        self.eredmeny: Eredmeny | None = None
        self.allapot = ""
        self.fut = False
        self._leall = False
        self._halad.connect(self._haladas)
        self._ido = QTimer(self)
        self._ido.setSingleShot(True)
        self._ido.timeout.connect(self.indit)
        self._ido.start(ELSO_KOR_MP * 1000)

    def mappa(self) -> Path:
        b = self.v.b
        return Path(b.zene_szinkron_mappa) if b.zene_szinkron_mappa.strip() else alap_mappa()

    def beallitva(self) -> bool:
        b = self.v.b
        return bool(b.zene_szinkron and b.zenekeres_szerver.strip() and b.zenekeres_szerver_kulcs.strip())

    def leallit(self) -> None:
        self._leall = True

    def indit(self) -> None:
        if self.fut:
            return
        self._ido.start(KOR_PERC * 60 * 1000)
        if not self.beallitva():
            return
        try:
            cim = szerver_cim(self.v.b.zenekeres_szerver)
        except SzerverHiba as e:
            self._hibas(e)
            return
        kulcs = self.v.b.zenekeres_szerver_kulcs.strip()
        mappa = self.mappa()
        kbps = self.v.b.zene_szinkron_kbps
        self.fut = True
        self._leall = False
        self.allapot = "A zenék listájának lekérése…"
        self.valtozott.emit()
        hatter.futtat(lambda: szinkron(cim, kulcs, mappa, kbps, self._halad.emit, lambda: self._leall),
                      lambda e: self._kesz(e, mappa), self._hibas)

    def _haladas(self, i: int, osszes: int, ut: str) -> None:
        self.allapot = f"Letöltés: {i}/{osszes} – {PurePosixPath(ut).name}"
        self.valtozott.emit()

    def _hibas(self, e: Exception) -> None:
        self.fut = False
        uzenet = str(e)
        if uzenet != self.hiba:
            self.v.log(f"Zenék a szerverről: {uzenet}")
        self.hiba = uzenet
        self.allapot = ""
        self.valtozott.emit()

    def _kesz(self, e: Eredmeny, mappa: Path) -> None:
        self.fut = False
        self.hiba = ""
        self.allapot = ""
        self.eredmeny = e
        self.utolso = datetime.now()
        if e.uj or e.torolt:
            self.v.log(f"Zenék a szerverről: {e.uj} új, {e.torolt} törölt szám ({e.bajt / 1_048_576:.1f} MB)")
        if e.hibas:
            self.v.log(f"Zenék a szerverről: {e.hibas} számot nem sikerült letölteni, a következő körben újra próbálja")
        self.v.szerver_zenek_frissultek(mappa, bool(e.uj or e.torolt))
        self.valtozott.emit()
