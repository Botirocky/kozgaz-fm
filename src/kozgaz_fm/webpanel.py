__lazy_modules__ = [
    "json",
    "logging",
    "secrets",
    "socket",
    "threading",
    "time",
    "collections.abc",
    "concurrent.futures",
    "dataclasses",
    "datetime",
    "http.server",
    "urllib.parse",
    "PySide6.QtCore",
    "kozgaz_fm",
    "kozgaz_fm.orarend",
    "kozgaz_fm.utvonalak",
    "kozgaz_fm.zar",
]

import json
import logging
import secrets
import socket
import threading
import time
from collections.abc import Callable, Mapping
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from PySide6.QtCore import QObject, Signal

from kozgaz_fm import __version__, rendszer, sajat_hangok
from kozgaz_fm.orarend import CSENGOK, KULONLEGES, Szakasz, Tipus, allapot
from kozgaz_fm.utvonalak import csomag_mappa
from kozgaz_fm.zar import PinHiba, Zar

naplo = logging.getLogger(__name__)

SUTI = "kfm_munkamenet"
ELETTARTAM = 12 * 3600
MAX_MUNKAMENET = 64
MAX_TOREK = 8192
VALASZ_IDO = 5.0
MAX_BEMONDAS = 500
ALAP_PORT = 8080

STATIKUS = {
    "/": ("web/panel.html", "text/html; charset=utf-8"),
    "/panel.css": ("web/panel.css", "text/css; charset=utf-8"),
    "/panel.js": ("web/panel.js", "text/javascript; charset=utf-8"),
    "/logo.png": ("kepek/logo.png", "image/png"),
}

BIZTONSAG = {
    "Content-Security-Policy": "default-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; "
                               "form-action 'self'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}

UTVONALAK = {
    ("GET", "/api/v1/allapot"): "allapot",
    ("POST", "/api/v1/csengetes"): "csengetes",
    ("POST", "/api/v1/zene/inditas"): "zene_inditas",
    ("POST", "/api/v1/zene/leallitas"): "zene_leallitas",
    ("POST", "/api/v1/zene/kovetkezo"): "zene_kovetkezo",
    ("PATCH", "/api/v1/zene"): "zene_allitas",
    ("POST", "/api/v1/bemondas"): "bemondas",
    ("DELETE", "/api/v1/bemondas"): "bemondas_leallitas",
    ("POST", "/api/v1/riasztas"): "riasztas_inditas",
    ("DELETE", "/api/v1/riasztas"): "riasztas_leallitas",
    ("PATCH", "/api/v1/ma"): "ma_allitas",
}


class WebHiba(Exception):
    def __init__(self, statusz: int, kod: str, uzenet: str, fejlecek: dict[str, str] | None = None) -> None:
        super().__init__(uzenet)
        self.statusz = statusz
        self.kod = kod
        self.uzenet = uzenet
        self.fejlecek = fejlecek or {}


@dataclass
class Valasz:
    statusz: int
    torzs: bytes = b""
    tipus: str = "application/json; charset=utf-8"
    fejlecek: dict[str, str] = field(default_factory=dict)


def _json_valasz(statusz: int, adat, fejlecek: dict[str, str] | None = None) -> Valasz:
    return Valasz(statusz, json.dumps(adat, ensure_ascii=False).encode(), fejlecek=fejlecek or {})


def _hiba_valasz(e: WebHiba) -> Valasz:
    return _json_valasz(e.statusz, {"error": {"code": e.kod, "message": e.uzenet}}, e.fejlecek)


def _suti(fejlecek: Mapping[str, str]) -> str:
    for darab in fejlecek.get("cookie", "").split(";"):
        nev, _, ertek = darab.strip().partition("=")
        if nev == SUTI:
            return ertek
    return ""


def _suti_fejlec(token: str, elettartam: int) -> str:
    return f"{SUTI}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={elettartam}"


class Munkamenetek:
    def __init__(self, ido: Callable[[], float] = time.monotonic, elettartam: int = ELETTARTAM) -> None:
        self._ido = ido
        self._elettartam = elettartam
        self._lista: dict[str, float] = {}
        self._zar = threading.Lock()

    def uj(self) -> str:
        token = secrets.token_urlsafe(32)
        with self._zar:
            most = self._ido()
            self._lista = {t: lej for t, lej in self._lista.items() if lej > most}
            while len(self._lista) >= MAX_MUNKAMENET:
                self._lista.pop(min(self._lista, key=self._lista.__getitem__))
            self._lista[token] = most + self._elettartam
        return token

    def ervenyes(self, token: str) -> bool:
        if not token:
            return False
        with self._zar:
            lejar = self._lista.get(token)
            most = self._ido()
            if lejar is None or lejar <= most:
                self._lista.pop(token, None)
                return False
            self._lista[token] = most + self._elettartam
            return True

    def torol(self, token: str) -> None:
        with self._zar:
            self._lista.pop(token, None)

    def urit(self) -> None:
        with self._zar:
            self._lista.clear()

    def __len__(self) -> int:
        return len(self._lista)


class Panel:
    def __init__(self, muveletek, jelszo: Callable[[], str], ido: Callable[[], float] = time.monotonic) -> None:
        self.muveletek = muveletek
        self._jelszo = jelszo
        self.munkamenetek = Munkamenetek(ido)
        self._zar = Zar(ido)
        self._belepes_zar = threading.Lock()
        self._fajlok: dict[str, bytes] = {}

    def kezel(self, metodus: str, cel: str, fejlecek: Mapping[str, str], torzs: bytes, ip: str) -> Valasz:
        try:
            return self._kezel(metodus, urlsplit(cel).path, fejlecek, torzs, ip)
        except WebHiba as e:
            return _hiba_valasz(e)
        except Exception:
            naplo.exception("Webpanel-hiba: %s %s", metodus, cel)
            return _hiba_valasz(WebHiba(500, "internal_error", "Belső hiba történt, a részletek a hibanaplóban."))

    def _kezel(self, metodus: str, ut: str, fejlecek: Mapping[str, str], torzs: bytes, ip: str) -> Valasz:
        if ut in STATIKUS:
            if metodus not in ("GET", "HEAD"):
                raise WebHiba(405, "method_not_allowed", "Ez a cím csak olvasható.", {"Allow": "GET, HEAD"})
            return self._statikus(ut)
        if not ut.startswith("/api/v1/"):
            raise WebHiba(404, "not_found", "Nincs ilyen oldal.")
        if metodus != "GET":
            self._keresztoldal(fejlecek)
        adat = _torzs(torzs)
        token = _suti(fejlecek)
        if ut == "/api/v1/munkamenet":
            return self._munkamenet(metodus, adat, token, ip)
        nev = UTVONALAK.get((metodus, ut))
        if nev is None:
            if any(u == ut for _m, u in UTVONALAK):
                raise WebHiba(405, "method_not_allowed", "Ez a művelet itt nem használható.")
            raise WebHiba(404, "not_found", "Nincs ilyen művelet.")
        if not self.munkamenetek.ervenyes(token):
            raise WebHiba(401, "unauthorized", "Jelentkezz be újra.")
        muvelet = getattr(self.muveletek, nev)
        return _json_valasz(200, {"data": self.muveletek.vegrehajt(lambda: muvelet(adat, ip))})

    def _keresztoldal(self, fejlecek: Mapping[str, str]) -> None:
        if fejlecek.get("x-kozgaz-fm") != "1":
            raise WebHiba(403, "forbidden", "A kérés nem a webpanelről jött.")
        eredet = fejlecek.get("origin")
        if eredet and urlsplit(eredet).netloc != fejlecek.get("host", ""):
            raise WebHiba(403, "forbidden", "Más oldalról érkező kérés.")

    def _munkamenet(self, metodus: str, adat: dict, token: str, ip: str) -> Valasz:
        if metodus == "GET":
            return _json_valasz(200, {"data": {"belepve": self.munkamenetek.ervenyes(token)}})
        if metodus == "DELETE":
            self.munkamenetek.torol(token)
            return Valasz(204, fejlecek={"Set-Cookie": _suti_fejlec("", 0)})
        if metodus != "POST":
            raise WebHiba(405, "method_not_allowed", "Ez a művelet itt nem használható.")
        jelszo = adat.get("jelszo")
        if not isinstance(jelszo, str) or not jelszo:
            raise WebHiba(422, "validation_error", "Add meg a jelszót.")
        tarolt = self._jelszo()
        if not tarolt:
            raise WebHiba(503, "disabled", "A webpanel nincs bekapcsolva.")
        with self._belepes_zar:
            try:
                jo = self._zar.probal(jelszo, tarolt)
            except PinHiba as e:
                raise WebHiba(429, "too_many_attempts", str(e),
                              {"Retry-After": str(self._zar.hatralevo_tiltas())}) from None
        if not jo:
            self._naploz(f"Webpanel: hibás jelszó ({ip})")
            raise WebHiba(401, "wrong_password", "Hibás jelszó.")
        self._naploz(f"Webpanel: belépés ({ip})")
        return Valasz(204, fejlecek={"Set-Cookie": _suti_fejlec(self.munkamenetek.uj(), ELETTARTAM)})

    def _naploz(self, szoveg: str) -> None:
        naploz = getattr(self.muveletek, "naploz", None)
        if naploz is not None:
            self.muveletek.vegrehajt(lambda: naploz(szoveg))

    def _statikus(self, ut: str) -> Valasz:
        nev, tipus = STATIKUS[ut]
        if nev not in self._fajlok:
            self._fajlok[nev] = (csomag_mappa() / nev).read_bytes()
        return Valasz(200, self._fajlok[nev], tipus)


def _torzs(torzs: bytes) -> dict:
    if not torzs:
        return {}
    try:
        adat = json.loads(torzs)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise WebHiba(400, "invalid_json", "Hibás kérés (nem JSON).") from None
    if not isinstance(adat, dict):
        raise WebHiba(400, "invalid_json", "Hibás kérés (objektum kell).")
    return adat


def _kezelo(panel: Panel) -> type[BaseHTTPRequestHandler]:
    class Kezelo(BaseHTTPRequestHandler):
        server_version = "KozgazFM"
        sys_version = ""
        timeout = 10

        def log_message(self, format: str, *args) -> None:
            naplo.debug("webpanel %s: " + format, self.address_string(), *args)

        def _futtat(self, metodus: str) -> None:
            try:
                hossz = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                hossz = -1
            if hossz < 0 or hossz > MAX_TOREK:
                valasz = _hiba_valasz(WebHiba(413 if hossz > 0 else 400, "bad_request", "Túl nagy vagy hibás kérés."))
                self.close_connection = True
            else:
                torzs = self.rfile.read(hossz) if hossz else b""
                fejlecek = {k.lower(): v for k, v in self.headers.items()}
                valasz = panel.kezel(metodus, self.path, fejlecek, torzs, self.client_address[0])
            self.send_response(valasz.statusz)
            for nev, ertek in {**BIZTONSAG, **valasz.fejlecek}.items():
                self.send_header(nev, ertek)
            if valasz.statusz != 204:
                self.send_header("Content-Type", valasz.tipus)
                self.send_header("Content-Length", str(len(valasz.torzs)))
            self.end_headers()
            if metodus != "HEAD" and valasz.statusz != 204:
                self.wfile.write(valasz.torzs)

        def do_GET(self) -> None:
            self._futtat("GET")

        def do_HEAD(self) -> None:
            self._futtat("HEAD")

        def do_POST(self) -> None:
            self._futtat("POST")

        def do_PATCH(self) -> None:
            self._futtat("PATCH")

        def do_DELETE(self) -> None:
            self._futtat("DELETE")

        def do_PUT(self) -> None:
            self._futtat("PUT")

    return Kezelo


class WebSzerver:
    def __init__(self, panel: Panel) -> None:
        self.panel = panel
        self._szerver: ThreadingHTTPServer | None = None
        self._szal: threading.Thread | None = None

    @property
    def fut(self) -> bool:
        return self._szerver is not None

    @property
    def port(self) -> int:
        return self._szerver.server_address[1] if self._szerver else 0

    def indit(self, port: int, cim: str = "0.0.0.0") -> None:
        self.leallit()
        szerver = ThreadingHTTPServer((cim, port), _kezelo(self.panel))
        szerver.daemon_threads = True
        self._szerver = szerver
        self._szal = threading.Thread(target=szerver.serve_forever, kwargs={"poll_interval": 0.5},
                                      name="webpanel", daemon=True)
        self._szal.start()

    def leallit(self) -> None:
        szerver, self._szerver = self._szerver, None
        if szerver is None:
            return
        szerver.shutdown()
        szerver.server_close()
        if self._szal is not None:
            self._szal.join(timeout=2)
            self._szal = None


class _Fosszal(QObject):
    kerelem = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.kerelem.connect(self._futtat)

    def _futtat(self, csomag) -> None:
        feladat, jovo = csomag
        if not jovo.set_running_or_notify_cancel():
            return
        try:
            jovo.set_result(feladat())
        except BaseException as e:
            jovo.set_exception(e)

    def vegrehajt(self, feladat: Callable):
        if threading.current_thread() is threading.main_thread():
            return feladat()
        jovo: Future = Future()
        self.kerelem.emit((feladat, jovo))
        try:
            return jovo.result(timeout=VALASZ_IDO)
        except FutureTimeout:
            jovo.cancel()
            raise WebHiba(503, "busy", "A program most nem válaszol, próbáld újra.") from None


def _logikai(adat: dict, kulcs: str) -> bool | None:
    if kulcs not in adat:
        return None
    if not isinstance(adat[kulcs], bool):
        raise WebHiba(422, "validation_error", f"A(z) „{kulcs}” mező igen/nem értéket vár.")
    return adat[kulcs]


def _egesz(adat: dict, kulcs: str, also: int, felso: int) -> int | None:
    if kulcs not in adat:
        return None
    ertek = adat[kulcs]
    if isinstance(ertek, bool) or not isinstance(ertek, int) or not also <= ertek <= felso:
        raise WebHiba(422, "validation_error", f"A(z) „{kulcs}” mező {also} és {felso} közötti egész szám.")
    return ertek


class WebMuveletek(_Fosszal):
    def __init__(self, v) -> None:
        super().__init__(v)
        self.v = v

    def naploz(self, szoveg: str) -> None:
        self.v.log(szoveg)

    def _hangok(self) -> list[tuple[str, str, str]]:
        b = self.v.b
        hangok = [("becsengo", "Becsengő", b.hang_becsengo), ("kicsengo", "Kicsengő", b.hang_kicsengo),
                  ("jelzo", "Jelzőcsengő", b.hang_jelzo), ("gong", "Gong", b.hang_gong)]
        return hangok + [(h.ertek, h.nev, h.ertek) for h in sajat_hangok.lista()]

    def allapot(self, _adat: dict | None = None, _ip: str = "") -> dict:
        v, b = self.v, self.v.b
        most = datetime.now()
        a = allapot(b, most)
        hatra = a.hatralevo(most)
        mire = ""
        if a.szakasz is Szakasz.ORA:
            mire = "kicsengetésig"
        elif a.szakasz in (Szakasz.SZUNET, Szakasz.REGGEL):
            mire = "becsengetésig"
        kovetkezo = None
        if a.kovetkezo:
            nap = "ma" if a.kovetkezo.ido.date() == most.date() else f"{a.kovetkezo.ido:%m.%d.}"
            kovetkezo = {"ido": f"{a.kovetkezo.ido:%H:%M}", "nap": nap, "leiras": a.kovetkezo.leiras}
        menetrend = [{"ido": f"{e.ido:%H:%M}", "leiras": e.leiras if e.tipus is not Tipus.ZENE_INDUL else "Szünetzene",
                      "tipus": "csengo" if e.tipus in CSENGOK else e.tipus.name.lower(), "mult": e.ido <= most}
                     for e in v.mai_esemenyek()
                     if e.tipus in CSENGOK or e.tipus in KULONLEGES or e.tipus in (Tipus.BEMONDAS, Tipus.ZENE_INDUL)]
        aktiv = v.aktiv_forras()
        ma = date.today().isoformat()
        return {
            "ido": most.isoformat(timespec="seconds"),
            "verzio": __version__,
            "cim": b.kijelzo_cim,
            "szakasz": a.cim,
            "csend": a.csend,
            "hatra_mp": int(hatra.total_seconds()) if hatra is not None and mire else None,
            "hatra_mire": mire,
            "hossz_mp": int((a.vege - a.kezdet).total_seconds()) if mire and a.kezdet and a.vege else None,
            "kovetkezo": kovetkezo,
            "riasztas": v.riasztas,
            "csengo_szol": v.csengo.szol,
            "bemondas_szol": v.bemondo.beszel,
            "zene": {
                "szol": v.zene.szol,
                "cim": v.zene.most_cim if v.zene.szol else "",
                "forras": b.forrasok.index(aktiv) if aktiv is not None else None,
                "forrasok": [{"index": i, "nev": f.nev, "tipus": f.tipus} for i, f in enumerate(b.forrasok)
                             if f.aktiv],
                "hangero": b.zene_hangero,
            },
            "ma": {
                "csengetes": b.ma_nincs_csengetes != ma,
                "zene": b.ma_nincs_zene != ma,
                "rend": b.kivetelek.get(ma, ""),
                "rendek": [r.nev for r in b.rendek],
            },
            "hangok": [{"azonosito": azon, "nev": nev} for azon, nev, _e in self._hangok()],
            "menetrend": menetrend,
        }

    def _riasztas_kozben(self) -> None:
        if self.v.riasztas:
            raise WebHiba(409, "alarm_active", "Riasztás közben ez nem lehetséges.")

    def csengetes(self, adat: dict, ip: str) -> dict:
        self._riasztas_kozben()
        azon = adat.get("hang", "becsengo")
        talalat = next(((nev, ertek) for a, nev, ertek in self._hangok() if a == azon), None)
        if talalat is None:
            raise WebHiba(422, "validation_error", "Ismeretlen csengőhang.")
        nev, ertek = talalat
        self.v.csengetes(ertek, f"{nev}, webpanelről ({ip})")
        return self.allapot()

    def zene_inditas(self, _adat: dict, ip: str) -> dict:
        self._riasztas_kozben()
        if self.v.aktiv_forras() is None:
            raise WebHiba(409, "no_source", "Nincs kiválasztott zeneforrás.")
        self.v.log(f"Webpanel ({ip}): zene indítása")
        self.v.zene_indit()
        return self.allapot()

    def zene_leallitas(self, _adat: dict, ip: str) -> dict:
        self.v.log(f"Webpanel ({ip}): zene leállítása")
        self.v.zene_leallit()
        return self.allapot()

    def zene_kovetkezo(self, _adat: dict, ip: str) -> dict:
        if self.v.zene.szol:
            self.v.log(f"Webpanel ({ip}): következő szám")
            self.v.zene.kovetkezo()
        return self.allapot()

    def zene_allitas(self, adat: dict, ip: str) -> dict:
        b = self.v.b
        forras = _egesz(adat, "forras", 0, max(0, len(b.forrasok) - 1))
        hangero = _egesz(adat, "hangero", 0, 100)
        if forras is not None:
            if not b.forrasok or not b.forrasok[forras].aktiv:
                raise WebHiba(422, "validation_error", "Ez a zeneforrás nem választható.")
            self.v.log(f"Webpanel ({ip}): zeneforrás – {b.forrasok[forras].nev}")
            self.v.forras_valtas(forras)
        if hangero is not None and hangero != b.zene_hangero:
            b.zene_hangero = hangero
            self.v.zene.hangero(hangero)
            self.v.mentes_kesobb()
            self.v.frissult.emit()
        return self.allapot()

    def bemondas(self, adat: dict, ip: str) -> dict:
        self._riasztas_kozben()
        szoveg = adat.get("szoveg")
        gong = _logikai(adat, "gong")
        if not isinstance(szoveg, str) or not szoveg.strip():
            raise WebHiba(422, "validation_error", "Írd be, mit olvasson fel a rendszer.")
        if len(szoveg) > MAX_BEMONDAS:
            raise WebHiba(422, "validation_error", f"A bemondás legfeljebb {MAX_BEMONDAS} karakter lehet.")
        self.v.log(f"Webpanel ({ip}): bemondás")
        self.v.gyors_bemondas(szoveg.strip(), True if gong is None else gong)
        return self.allapot()

    def bemondas_leallitas(self, _adat: dict, ip: str) -> dict:
        self.v.log(f"Webpanel ({ip}): bemondás leállítása")
        self.v.bemondas_leallit()
        return self.allapot()

    def riasztas_inditas(self, _adat: dict, ip: str) -> dict:
        self.v.log(f"Webpanel ({ip}): riasztás indítása")
        self.v.riasztas_indit()
        return self.allapot()

    def riasztas_leallitas(self, _adat: dict, ip: str) -> dict:
        self.v.log(f"Webpanel ({ip}): riasztás leállítása")
        self.v.riasztas_leallit()
        return self.allapot()

    def ma_allitas(self, adat: dict, ip: str) -> dict:
        b = self.v.b
        csengetes = _logikai(adat, "csengetes")
        zene = _logikai(adat, "zene")
        rend = adat.get("rend")
        if rend is not None and (not isinstance(rend, str) or (rend and b.rend(rend) is None)):
            raise WebHiba(422, "validation_error", "Ismeretlen csengetési rend.")
        if csengetes is not None:
            self.v.log(f"Webpanel ({ip}): mai csengetés {'be' if csengetes else 'ki'}")
            self.v.ma_kapcsolo("ma_nincs_csengetes", not csengetes)
        if zene is not None:
            self.v.log(f"Webpanel ({ip}): mai szünetzene {'be' if zene else 'ki'}")
            self.v.ma_kapcsolo("ma_nincs_zene", not zene)
        if rend is not None:
            self.v.log(f"Webpanel ({ip}): mai rend módosítása")
            self.v.ma_rend(rend)
        self.v.frissult.emit()
        return self.allapot()


class WebPanel:
    def __init__(self, v) -> None:
        self.v = v
        self.muveletek = WebMuveletek(v)
        self.panel = Panel(self.muveletek, lambda: v.b.web_jelszo)
        self.szerver = WebSzerver(self.panel)
        self._jelszo: str | None = None
        self.hiba = ""

    @property
    def fut(self) -> bool:
        return self.szerver.fut

    def cimek(self) -> list[str]:
        if not self.fut:
            return []
        port = "" if self.szerver.port == 80 else f":{self.szerver.port}"
        cimek = [f"http://{rendszer.ip_cim()}{port}"]
        if rendszer.kozgazfm_os() is not None:
            cimek.append(f"http://{socket.gethostname()}.local{port}")
        return cimek

    def alkalmaz(self) -> None:
        b = self.v.b
        if b.web_jelszo != self._jelszo:
            if self._jelszo is not None:
                self.panel.munkamenetek.urit()
            self._jelszo = b.web_jelszo
        if not (b.web_panel and b.web_jelszo):
            if self.fut:
                self.leallit()
                self.v.log("Webpanel leállítva")
            self.hiba = ""
            return
        if self.fut and self.szerver.port == b.web_port:
            return
        try:
            self.szerver.indit(b.web_port)
        except OSError as e:
            self.hiba = f"A webpanel portja ({b.web_port}) nem használható: {e.strerror or e}."
            self.v.log(f"HIBA: a webpanel nem indult el – {self.hiba}")
            return
        self.hiba = ""
        self.v.log(f"Webpanel elindult: {', '.join(self.cimek())}")

    def leallit(self) -> None:
        self.szerver.leallit()
