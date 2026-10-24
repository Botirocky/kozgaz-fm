__lazy_modules__ = [
    "json",
    "secrets",
    "typing",
    "urllib.error",
    "urllib.parse",
    "urllib.request",
    "dataclasses",
    "datetime",
    "PySide6.QtCore",
    "kozgaz_fm",
    "kozgaz_fm.beallitasok",
]

import json
import secrets
import typing
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, is_dataclass
from datetime import datetime

from PySide6.QtCore import QObject, QTimer, Signal

from kozgaz_fm import __version__, hatter
from kozgaz_fm.beallitasok import Beallitasok, _ertek

FEJLEC = "X-Kozgaz-FM-Kulcs"
ELETJEL_MS = 5000
KERES_IDO = 8.0
KIESES_HATAR = 3
VISSZA_HATAR = 2
SZINKRON_MP = 300
PORT = 8080

SZEREPEK = {"": "Kikapcsolva", "fo": "Ez a fő gép", "tartalek": "Ez a tartalék gép"}

SZINKRON_MEZOK = (
    "rendek", "het", "kivetelek", "szunnapok", "rendkivuli", "bemondasok", "bemondas_sablonok",
    "jelzo", "jelzo_perc", "kicsengo", "zene_szunetben", "zene_min_szunet", "zene_kesleltetes",
    "zene_leall_elotte", "reggeli_zene", "reggeli_zene_tol", "ma_nincs_csengetes", "ma_nincs_zene",
)


_NYITO = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class TartalekHiba(Exception):
    pass


def uj_kulcs() -> str:
    return secrets.token_urlsafe(24)


def cim_normalizal(cim: str) -> str:
    cim = cim.strip()
    if not cim:
        return ""
    if "://" not in cim:
        cim = f"http://{cim}"
    reszek = urllib.parse.urlsplit(cim)
    try:
        port = reszek.port
    except ValueError:
        port = -1
    if reszek.scheme not in ("http", "https") or not reszek.hostname or reszek.path not in ("", "/") \
            or reszek.query or reszek.username or port == -1:
        raise TartalekHiba("A cím formája: 192.168.1.20:8080 vagy http://csengo-gep:8080")
    gazda = f"[{reszek.hostname}]" if ":" in reszek.hostname else reszek.hostname
    return f"{reszek.scheme}://{gazda}:{PORT if port is None else port}"


def szinkron_adat(b: Beallitasok) -> dict:
    adat = {}
    for mezo in SZINKRON_MEZOK:
        ertek = getattr(b, mezo)
        if isinstance(ertek, list):
            adat[mezo] = [asdict(e) if is_dataclass(e) and not isinstance(e, type) else e for e in ertek]
        else:
            adat[mezo] = ertek
    return json.loads(json.dumps(adat, ensure_ascii=False))


def szinkron_alkalmaz(b: Beallitasok, adat: dict) -> list[str]:
    tipusok = typing.get_type_hints(Beallitasok)
    ujak = {}
    for mezo in SZINKRON_MEZOK:
        if mezo in adat:
            ujak[mezo] = _ertek(tipusok[mezo], adat[mezo])
    valtozott = [m for m, e in ujak.items() if e != getattr(b, m)]
    for mezo in valtozott:
        setattr(b, mezo, ujak[mezo])
    return valtozott


def lekeres(alap: str, ut: str, kulcs: str) -> dict:
    keres = urllib.request.Request(f"{alap}/api/v1/tartalek/{ut}",
                                   headers={FEJLEC: kulcs, "X-Kozgaz-FM": "1", "Accept": "application/json"})
    try:
        with _NYITO.open(keres, timeout=KERES_IDO) as valasz:
            return json.loads(valasz.read(1_000_000))["data"]
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise TartalekHiba("nem fogadta el a kulcsot") from None
        raise TartalekHiba(f"hibát jelzett ({e.code})") from None
    except TimeoutError:
        raise TartalekHiba("nem válaszolt időben") from None
    except OSError:
        raise TartalekHiba("nem érhető el a hálózaton") from None
    except (ValueError, KeyError, TypeError):
        raise TartalekHiba("érthetetlen választ adott") from None


def _probal(alap: str, ut: str, kulcs: str) -> tuple[dict | None, str]:
    try:
        return lekeres(alap, ut, kulcs), ""
    except TartalekHiba as e:
        return None, str(e)


class Allapotgep:
    def __init__(self) -> None:
        self.hibas_sor = 0
        self.sikeres_sor = 0
        self.el: bool | None = None
        self.atvett = False
        self.utolso_jel: datetime | None = None
        self.hiba = ""

    def siker(self, most: datetime) -> str | None:
        self.hibas_sor = 0
        self.sikeres_sor += 1
        self.utolso_jel = most
        self.hiba = ""
        self.el = True
        if self.atvett and self.sikeres_sor >= VISSZA_HATAR:
            self.atvett = False
            return "visszaadas"
        return None

    def kudarc(self, hiba: str) -> str | None:
        self.sikeres_sor = 0
        self.hibas_sor += 1
        self.hiba = hiba
        if self.hibas_sor >= KIESES_HATAR:
            self.el = False
            if not self.atvett:
                self.atvett = True
                return "atvetel"
        return None

    def alaphelyzet(self) -> None:
        self.__init__()


class Tartalek(QObject):
    valtozott = Signal()
    atvetel = Signal()
    visszaadas = Signal()
    szinkronizalt = Signal(list)

    def __init__(self, b: Beallitasok, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.b = b
        self.allapot = Allapotgep()
        self.partner: dict = {}
        self._fut = False
        self._utolso_szinkron: datetime | None = None
        self._ido = QTimer(self)
        self._ido.setInterval(ELETJEL_MS)
        self._ido.timeout.connect(self._eletjel)

    @property
    def szerep(self) -> str:
        return self.b.tartalek_mod if self.b.tartalek_kulcs and self.b.tartalek_cim else ""

    @property
    def passziv(self) -> bool:
        return self.szerep == "tartalek" and not self.allapot.atvett

    def leiras(self) -> tuple[str, str]:
        a, szerep = self.allapot, self.szerep
        if not szerep:
            if self.b.tartalek_mod:
                return "Add meg a közös kulcsot és a másik gép címét.", "figyelem"
            return "", ""
        jel = f" (utolsó jel: {a.utolso_jel:%H:%M:%S})" if a.utolso_jel else ""
        if szerep == "fo":
            if a.el:
                return f"A tartalék gép készenlétben{jel}", "szol"
            if a.el is False:
                return f"A tartalék gép {a.hiba}", "figyelem"
            return "Kapcsolódás a tartalék géphez…", "halvany"
        if a.atvett:
            return f"A fő gép {a.hiba} – ez a gép csenget helyette", "hiba"
        if a.hibas_sor:
            return f"A fő gép {a.hiba} ({a.hibas_sor}/{KIESES_HATAR}. próba)", "figyelem"
        if a.el:
            return f"A fő gép működik, ez a gép készenlétben vár{jel}", "kek"
        return "Kapcsolódás a fő géphez…", "halvany"

    def alkalmaz(self) -> None:
        if self.szerep:
            if not self._ido.isActive():
                self.allapot.alaphelyzet()
                self._ido.start()
                QTimer.singleShot(500, self._eletjel)
        else:
            self._ido.stop()
            atvett = self.allapot.atvett
            self.allapot.alaphelyzet()
            self.partner = {}
            if atvett:
                self.visszaadas.emit()
        self.valtozott.emit()

    def leallit(self) -> None:
        self._ido.stop()

    def _eletjel(self) -> None:
        if self._fut or not self.szerep:
            return
        self._fut = True
        cim, kulcs = self.b.tartalek_cim, self.b.tartalek_kulcs
        hatter.futtat(lambda: _probal(cim, "eletjel", kulcs), self._jel_jott, lambda e: self._jel_hiba(str(e)))

    def _jel_jott(self, eredmeny: tuple[dict | None, str]) -> None:
        adat, hiba = eredmeny
        if adat is None:
            self._jel_hiba(hiba)
            return
        self._fut = False
        self.partner = adat if isinstance(adat, dict) else {}
        esemeny = self.allapot.siker(datetime.now())
        if esemeny == "visszaadas":
            self.visszaadas.emit()
        self.valtozott.emit()
        if self.szerep == "tartalek" and self.partner.get("szerep") == "fo":
            most = datetime.now()
            if self._utolso_szinkron is None or (most - self._utolso_szinkron).total_seconds() >= SZINKRON_MP:
                self.szinkron()

    def _jel_hiba(self, hiba: str) -> None:
        self._fut = False
        esemeny = self.allapot.kudarc(hiba)
        if esemeny == "atvetel" and self.szerep == "tartalek":
            self.atvetel.emit()
        self.valtozott.emit()

    def szinkron(self) -> None:
        if self.szerep != "tartalek":
            return
        self._utolso_szinkron = datetime.now()
        cim, kulcs = self.b.tartalek_cim, self.b.tartalek_kulcs
        hatter.futtat(lambda: lekeres(cim, "beallitasok", kulcs), self._szinkron_jott,
                      lambda e: setattr(self.allapot, "hiba", f"Szinkron: {e}"))

    def _szinkron_jott(self, adat: dict) -> None:
        try:
            valtozott = szinkron_alkalmaz(self.b, adat)
        except (TypeError, ValueError, AttributeError) as e:
            self.allapot.hiba = f"Szinkron: hibás adat ({e})"
            self.valtozott.emit()
            return
        self.szinkronizalt.emit(valtozott)


def eletjel(b: Beallitasok, atvett: bool, riasztas: bool) -> dict:
    return {"szerep": b.tartalek_mod, "verzio": __version__, "ido": datetime.now().isoformat(timespec="seconds"),
            "atvett": atvett, "riasztas": riasztas}
