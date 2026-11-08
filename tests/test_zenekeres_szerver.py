import json
from datetime import datetime
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication

from kozgaz_fm import zenekeres_szerver
from kozgaz_fm.beallitasok import alapertelmezett
from kozgaz_fm.hang import Szam
from kozgaz_fm.zenekeres import Keresek, KeresHiba
from kozgaz_fm.zenekeres_szerver import SzerverHiba, ZenekeresSzerver, szerver_cim


@pytest.mark.parametrize(("be", "ki"), [
    ("", ""),
    ("zene.iskola.hu", "https://zene.iskola.hu"),
    ("https://radio.example.org/", "https://radio.example.org"),
    ("http://10.0.0.5:8100/kfm/", "http://10.0.0.5:8100/kfm"),
])
def test_szerver_cim(be, ki):
    assert szerver_cim(be) == ki


def test_szerver_cim_hibas():
    with pytest.raises(SzerverHiba):
        szerver_cim("ftp://valami")


class AlVezerlo:
    def __init__(self) -> None:
        self.b = alapertelmezett()
        self.b.zenekeres = True
        self.b.zenekeres_szerver = "https://zene.example"
        self.b.zenekeres_szerver_kulcs = "k" * 32
        self.keresek = Keresek()
        self.tartalek = SimpleNamespace(passziv=False)
        self.sor: list = []
        self.pontok: list[dict] = []
        self.zene = SimpleNamespace(kert_sor=lambda: self.sor, kert_rendez=self.pontok.append)
        self.naplo: list[str] = []

    def log(self, szoveg: str) -> None:
        self.naplo.append(szoveg)

    def zenekeres_uj(self, szoveg, nev, eszkoz, ip, azon=""):
        if "tilos" in szoveg:
            raise KeresHiba("forbidden_word", "Ezt a kérést nem lehet elküldeni.")
        return self.keresek.uj(szoveg, nev, eszkoz, ip, 3, [], azon=azon)


@pytest.fixture
def sz():
    _app = QCoreApplication.instance() or QCoreApplication([])
    s = ZenekeresSzerver(AlVezerlo())
    s._ido.stop()
    return s


def test_uj_keresek_es_allapot_visszajelzes(sz):
    sz._kesz({"uj": [{"azon": "a1", "szoveg": "Queen", "nev": "10.B", "eszkoz": "e" * 64, "ip": "1.2.3.4"},
                     {"azon": "a2", "szoveg": "tilos szám", "nev": "", "eszkoz": "f" * 64}]}, [])
    assert [k.azon for k in sz.v.keresek.lista] == ["a1"]
    allapotok = {a["azon"]: a for a in sz._allapotok()}
    assert allapotok["a1"]["allapot"] == "kereses"
    assert allapotok["a2"]["allapot"] == "elutasitva" and allapotok["a2"]["ok"]
    sz._kesz({"uj": [{"azon": "a1", "szoveg": "Queen", "eszkoz": "e" * 64}]}, list(allapotok.values()))
    assert len(sz.v.keresek.lista) == 1 and sz._allapotok() == []
    sz.v.keresek.lista[0].allapot = "varakozik"
    assert [a["allapot"] for a in sz._allapotok()] == ["varakozik"]


def test_hely_a_sorban(sz):
    sz._kesz({"uj": [{"azon": "a1", "szoveg": "Queen", "eszkoz": "e" * 64}]}, [])
    k = sz.v.keresek.lista[0]
    k.allapot, k.yt = "elfogadva", "yt1"
    sz.v.sor = [(4, Szam("Más", yt="yt0", kert=True)), (5, Szam("Queen", yt="yt1", kert=True))]
    assert sz._allapotok()[0]["hely"] == 2
    k.allapot = "szol"
    assert sz._allapotok()[0]["hely"] == 0


def test_szavazatok_yt_szerint_a_lejatszonak(sz):
    sz._kesz({"uj": [{"azon": "a1", "szoveg": "Queen", "eszkoz": "e" * 64}]}, [])
    sz.v.keresek.lista[0].yt = "yt1"
    sz._kesz({"uj": [], "szavazatok": {"a1": 3, "ismeretlen": 9}}, [])
    assert sz.v.pontok == [{"yt1": 3}]


def test_ugyanaz_az_azonosito_ketszer_nem(sz):
    k = Keresek()
    k.uj("Queen", "", "e", "ip", 3, [], azon="x")
    with pytest.raises(KeresHiba):
        k.uj("Queen", "", "e", "ip", 3, [], azon="x")


def test_beallitasok_a_szervernek(sz):
    ma = datetime.now().date().isoformat()
    sz.v.b.tiltott_telefonok = [SimpleNamespace(kulcs="a" * 32, ig=ma),
                                SimpleNamespace(kulcs="b" * 32, ig="2000-01-01")]
    adat = sz._beallitasok()
    assert adat["aktiv"] and adat["tiltott_telefonok"] == ["a" * 32]


def test_kuld_rossz_kulcs(monkeypatch):
    import urllib.error

    def nyit(*_a, **_k):
        raise urllib.error.HTTPError("https://zene.example/api/gep", 401, "x", {}, None)

    monkeypatch.setattr(zenekeres_szerver.urllib.request, "urlopen", nyit)
    with pytest.raises(SzerverHiba, match="kulcs"):
        zenekeres_szerver.kuld("https://zene.example", "k", {})


def test_kuld_valasz(monkeypatch):
    class Valasz:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def read(self, _n):
            return json.dumps({"data": {"uj": []}}).encode()

    kapott = {}

    def nyit(keres, timeout):
        kapott["fejlec"] = keres.get_header("X-kozgaz-fm-kulcs")
        return Valasz()

    monkeypatch.setattr(zenekeres_szerver.urllib.request, "urlopen", nyit)
    assert zenekeres_szerver.kuld("https://zene.example", "titok", {}) == {"uj": []}
    assert kapott["fejlec"] == "titok"
