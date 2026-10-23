__lazy_modules__ = ["json", "http.client", "pytest", "kozgaz_fm", "kozgaz_fm.webpanel", "kozgaz_fm.zar"]

import http.client
import json

import pytest

from kozgaz_fm import zar
from kozgaz_fm.webpanel import Munkamenetek, Panel, WebHiba, WebSzerver, _egesz, _logikai

JELSZO = "folyoso-2026"
CSRF = {"x-kozgaz-fm": "1", "host": "panel.local:8080"}


class Ora:
    def __init__(self) -> None:
        self.most = 1000.0

    def __call__(self) -> float:
        return self.most


class AlMuveletek:
    def __init__(self) -> None:
        self.hivasok: list[tuple[str, dict, str]] = []
        self.naplo: list[str] = []

    def vegrehajt(self, feladat):
        return feladat()

    def naploz(self, szoveg: str) -> None:
        self.naplo.append(szoveg)

    def allapot(self, adat: dict, ip: str) -> dict:
        self.hivasok.append(("allapot", adat, ip))
        return {"szakasz": "2. óra"}

    def csengetes(self, adat: dict, ip: str) -> dict:
        self.hivasok.append(("csengetes", adat, ip))
        if adat.get("hang") == "rossz":
            raise WebHiba(422, "validation_error", "Ismeretlen csengőhang.")
        return {"szakasz": "2. óra"}


@pytest.fixture(scope="module")
def tarolt() -> str:
    return zar.jelszo_hash(JELSZO, kor=1000)


@pytest.fixture
def ora() -> Ora:
    return Ora()


@pytest.fixture
def muveletek() -> AlMuveletek:
    return AlMuveletek()


@pytest.fixture
def panel(muveletek: AlMuveletek, tarolt: str, ora: Ora) -> Panel:
    return Panel(muveletek, lambda: tarolt, ora)


def _json(valasz) -> dict:
    return json.loads(valasz.torzs)


def _belep(panel: Panel, jelszo: str = JELSZO):
    return panel.kezel("POST", "/api/v1/munkamenet", CSRF, json.dumps({"jelszo": jelszo}).encode(), "10.0.0.5")


def _suti(valasz) -> dict[str, str]:
    token = valasz.fejlecek["Set-Cookie"].split(";")[0]
    return {**CSRF, "cookie": f"masik=1; {token}"}


@pytest.mark.parametrize("jelszo, vart", [
    ("12345678", True),
    ("hosszú jelszó ékezettel", True),
    ("rovid", False),
    (" szokozzel-kezd", False),
    ("x" * 129, False),
])
def test_jelszo_ervenyes(jelszo: str, vart: bool) -> None:
    assert zar.jelszo_ervenyes(jelszo) is vart


def test_jelszo_hash_ellenorizheto(tarolt: str) -> None:
    assert JELSZO not in tarolt
    assert zar.pin_ellenoriz(JELSZO, tarolt)
    assert not zar.pin_ellenoriz("folyoso-2025", tarolt)
    assert not zar.pin_ellenoriz("\udcff", tarolt)
    with pytest.raises(zar.PinHiba):
        zar.jelszo_hash("rovid")


def test_munkamenet_lejar_es_hasznalattal_megujul(ora: Ora) -> None:
    m = Munkamenetek(ora, elettartam=100)
    token = m.uj()
    ora.most += 90
    assert m.ervenyes(token)
    ora.most += 90
    assert m.ervenyes(token)
    ora.most += 101
    assert not m.ervenyes(token)
    assert not m.ervenyes("")
    assert not m.ervenyes("hamis")


def test_munkamenetek_szama_korlatos(ora: Ora) -> None:
    m = Munkamenetek(ora)
    elso = m.uj()
    for _ in range(100):
        ora.most += 1
        m.uj()
    assert len(m) <= 64
    assert not m.ervenyes(elso)


def test_belepes_utan_mukodik_a_muvelet(panel: Panel, muveletek: AlMuveletek) -> None:
    valasz = _belep(panel)
    assert valasz.statusz == 204
    suti = valasz.fejlecek["Set-Cookie"]
    assert "HttpOnly" in suti and "SameSite=Strict" in suti
    eredmeny = panel.kezel("POST", "/api/v1/csengetes", _suti(valasz), b'{"hang": "kicsengo"}', "10.0.0.5")
    assert eredmeny.statusz == 200
    assert _json(eredmeny) == {"data": {"szakasz": "2. óra"}}
    assert muveletek.hivasok == [("csengetes", {"hang": "kicsengo"}, "10.0.0.5")]
    assert muveletek.naplo == ["Webpanel: belépés (10.0.0.5)"]


def test_belepes_nelkul_401(panel: Panel, muveletek: AlMuveletek) -> None:
    valasz = panel.kezel("POST", "/api/v1/csengetes", CSRF, b"{}", "10.0.0.5")
    assert valasz.statusz == 401
    assert _json(valasz)["error"]["code"] == "unauthorized"
    assert muveletek.hivasok == []


def test_hibas_jelszo_es_kitiltas(panel: Panel, muveletek: AlMuveletek, ora: Ora) -> None:
    for _ in range(zar.MAX_HIBA):
        assert _belep(panel, "nem-ez-az").statusz == 401
    tiltott = _belep(panel)
    assert tiltott.statusz == 429
    assert int(tiltott.fejlecek["Retry-After"]) > 0
    ora.most += zar.TILTAS_MP + 1
    assert _belep(panel).statusz == 204
    assert muveletek.naplo.count("Webpanel: hibás jelszó (10.0.0.5)") == zar.MAX_HIBA


def test_kikapcsolt_jelszonal_nincs_belepes(muveletek: AlMuveletek, ora: Ora) -> None:
    panel = Panel(muveletek, lambda: "", ora)
    assert _belep(panel).statusz == 503


@pytest.mark.parametrize("fejlecek", [
    {"host": "panel.local:8080"},
    {"x-kozgaz-fm": "0", "host": "panel.local:8080"},
    {**CSRF, "origin": "http://gonosz.example"},
])
def test_kereszt_oldali_keres_tiltva(panel: Panel, fejlecek: dict) -> None:
    valasz = panel.kezel("POST", "/api/v1/munkamenet", fejlecek, json.dumps({"jelszo": JELSZO}).encode(), "1.2.3.4")
    assert valasz.statusz == 403


def test_azonos_origin_engedett(panel: Panel) -> None:
    fejlecek = {**CSRF, "origin": "http://panel.local:8080"}
    assert panel.kezel("POST", "/api/v1/munkamenet", fejlecek, json.dumps({"jelszo": JELSZO}).encode(),
                       "1.2.3.4").statusz == 204


@pytest.mark.parametrize("torzs, statusz", [
    (b"nem json", 400),
    (b"[1, 2]", 400),
    (b'{"jelszo": 5}', 422),
    (b"{}", 422),
])
def test_hibas_belepesi_torzs(panel: Panel, torzs: bytes, statusz: int) -> None:
    assert panel.kezel("POST", "/api/v1/munkamenet", CSRF, torzs, "1.2.3.4").statusz == statusz


def test_ismeretlen_utvonal_es_metodus(panel: Panel) -> None:
    fejlecek = _suti(_belep(panel))
    assert panel.kezel("GET", "/api/v1/nincs", fejlecek, b"", "x").statusz == 404
    assert panel.kezel("GET", "/api/v1/csengetes", fejlecek, b"", "x").statusz == 405
    assert panel.kezel("GET", "/../../etc/passwd", fejlecek, b"", "x").statusz == 404
    assert panel.kezel("POST", "/", fejlecek, b"", "x").statusz == 405


def test_muvelet_hibaja_szabvanyos_valasz(panel: Panel) -> None:
    valasz = panel.kezel("POST", "/api/v1/csengetes", _suti(_belep(panel)), b'{"hang": "rossz"}', "x")
    assert valasz.statusz == 422
    assert _json(valasz) == {"error": {"code": "validation_error", "message": "Ismeretlen csengőhang."}}


def test_kilepes_ervenyteleniti_a_munkamenetet(panel: Panel) -> None:
    fejlecek = _suti(_belep(panel))
    assert _json(panel.kezel("GET", "/api/v1/munkamenet", fejlecek, b"", "x"))["data"]["belepve"] is True
    assert panel.kezel("DELETE", "/api/v1/munkamenet", fejlecek, b"", "x").statusz == 204
    assert panel.kezel("GET", "/api/v1/allapot", fejlecek, b"", "x").statusz == 401


def test_jelszocsere_utan_mindenki_kilep(panel: Panel) -> None:
    fejlecek = _suti(_belep(panel))
    panel.munkamenetek.urit()
    assert panel.kezel("GET", "/api/v1/allapot", fejlecek, b"", "x").statusz == 401


def test_statikus_fajlok(panel: Panel) -> None:
    oldal = panel.kezel("GET", "/?v=1", {}, b"", "x")
    assert oldal.statusz == 200
    assert oldal.tipus.startswith("text/html")
    assert b"panel.js" in oldal.torzs
    for ut in ("/panel.css", "/panel.js", "/logo.png"):
        assert panel.kezel("GET", ut, {}, b"", "x").statusz == 200


def test_valodi_http_szerver(panel: Panel) -> None:
    szerver = WebSzerver(panel)
    szerver.indit(0, "127.0.0.1")
    try:
        kapcsolat = http.client.HTTPConnection("127.0.0.1", szerver.port, timeout=5)
        kapcsolat.request("GET", "/")
        valasz = kapcsolat.getresponse()
        valasz.read()
        assert valasz.status == 200
        assert "frame-ancestors 'none'" in valasz.getheader("Content-Security-Policy", "")
        assert valasz.getheader("X-Content-Type-Options") == "nosniff"

        kapcsolat = http.client.HTTPConnection("127.0.0.1", szerver.port, timeout=5)
        kapcsolat.request("POST", "/api/v1/munkamenet", json.dumps({"jelszo": JELSZO}),
                          {"X-Kozgaz-FM": "1", "Content-Type": "application/json"})
        valasz = kapcsolat.getresponse()
        valasz.read()
        assert valasz.status == 204
        suti = valasz.getheader("Set-Cookie", "").split(";")[0]

        kapcsolat = http.client.HTTPConnection("127.0.0.1", szerver.port, timeout=5)
        kapcsolat.request("GET", "/api/v1/allapot", headers={"Cookie": suti})
        valasz = kapcsolat.getresponse()
        assert valasz.status == 200
        assert json.loads(valasz.read()) == {"data": {"szakasz": "2. óra"}}

        kapcsolat = http.client.HTTPConnection("127.0.0.1", szerver.port, timeout=5)
        kapcsolat.request("POST", "/api/v1/csengetes", b"x" * 9000, {"X-Kozgaz-FM": "1", "Cookie": suti})
        valasz = kapcsolat.getresponse()
        valasz.read()
        assert valasz.status == 413
    finally:
        szerver.leallit()
    assert not szerver.fut


@pytest.mark.parametrize("adat, vart", [({}, None), ({"x": True}, True), ({"x": False}, False)])
def test_logikai_mezo(adat: dict, vart: bool | None) -> None:
    assert _logikai(adat, "x") is vart


@pytest.mark.parametrize("ertek", ["1", 1.5, True, -1, 101, None])
def test_egesz_mezo_hibas(ertek) -> None:
    with pytest.raises(WebHiba) as hiba:
        _egesz({"x": ertek}, "x", 0, 100)
    assert hiba.value.statusz == 422


def test_egesz_mezo_jo() -> None:
    assert _egesz({"x": 0}, "x", 0, 100) == 0
    assert _egesz({}, "x", 0, 100) is None
