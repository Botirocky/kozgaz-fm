__lazy_modules__ = ["datetime", "pytest", "PySide6.QtCore", "kozgaz_fm.beallitasok", "kozgaz_fm.hang",
                    "kozgaz_fm.orarend", "kozgaz_fm.vezerlo"]

from datetime import date, datetime

import pytest
from PySide6.QtCore import QCoreApplication

from kozgaz_fm import hang
from kozgaz_fm.beallitasok import Beallitasok, Musorblokk, ZeneForras, alapertelmezett
from kozgaz_fm.hang import Szam, ZeneLejatszo
from kozgaz_fm.orarend import Esemeny, Tipus, musorblokk, zene_szunet
from kozgaz_fm.vezerlo import Vezerlo

HETFO = date(2026, 10, 19)
PENTEK = date(2026, 10, 23)


@pytest.fixture(scope="module", autouse=True)
def app():
    return QCoreApplication.instance() or QCoreApplication([])


@pytest.fixture
def b() -> Beallitasok:
    b = alapertelmezett()
    b.forrasok = [ZeneForras("mappa", "Alap", "/a"), ZeneForras("mappa", "Nyugi", "/n"),
                  ZeneForras("youtube", "Buli", "x")]
    b.musorblokkok = [
        Musorblokk("Pénteki buli", "Buli", napok=[4]),
        Musorblokk("Reggel", "Nyugi", szunetek=[0]),
        Musorblokk("Nagyszünet", "Buli", szunetek=[3]),
    ]
    b.reggeli_zene = True
    return b


def dt(nap: date, ido: str) -> datetime:
    ora, perc = map(int, ido.split(":"))
    return datetime(nap.year, nap.month, nap.day, ora, perc)


def test_zene_szunet_sorszama(b):
    assert zene_szunet(b, dt(HETFO, "07:40")) == 0
    assert zene_szunet(b, dt(HETFO, "08:20")) is None
    assert zene_szunet(b, dt(HETFO, "10:40")) == 3


def test_blokk_valasztas_sorrend_es_nap(b):
    assert musorblokk(b, 0, 0).nev == "Reggel"
    assert musorblokk(b, 0, 3).nev == "Nagyszünet"
    assert musorblokk(b, 0, 1) is None
    assert musorblokk(b, 4, 0).nev == "Pénteki buli"


def test_kikapcsolt_vagy_hianyzo_forras_nem_szamit(b):
    b.forrasok[2].aktiv = False
    assert musorblokk(b, 4, 0).nev == "Reggel"
    b.musorblokkok[1].aktiv = False
    assert musorblokk(b, 4, 0) is None
    b.musorblokkok.append(Musorblokk("Régi", "Törölt forrás"))
    assert musorblokk(b, 0, 1) is None


def test_mentes_es_betoltes(tmp_path, b):
    ut = tmp_path / "b.json"
    b.szuro_szavak = ["valami*"]
    b.mentes(ut)
    uj = Beallitasok.betoltes(ut)
    assert uj.musorblokkok == b.musorblokkok and uj.szuro_szavak == ["valami*"] and uj.szuro_alap


class AlVezerlo:
    _kezel = Vezerlo._kezel
    _blokk_forras = Vezerlo._blokk_forras
    aktiv_forras = Vezerlo.aktiv_forras
    jelenlegi_forras = Vezerlo.jelenlegi_forras
    forras_valtas = Vezerlo.forras_valtas
    tartalek = type("Tartalek", (), {"passziv": False})()

    def __init__(self, b: Beallitasok) -> None:
        self.b = b
        self.riasztas = False
        self.naplo: list[str] = []
        self.musor_blokk = None
        self._musor_kezi = False
        self._auto_zene = False
        self.forrasok: list[str] = []
        self.inditva = 0
        v = self

        class Zene:
            szol = False

            def forras_beallitas(self, f):
                v.forrasok.append(f.nev if f else "")

            def indit(self):
                v.inditva += 1

        self.zene = Zene()

    def log(self, szoveg: str) -> None:
        self.naplo.append(szoveg)

    @property
    def frissult(self):
        return type("Jel", (), {"emit": staticmethod(lambda: None)})


def test_szunetzene_indulaskor_a_blokk_forrasa_szol(b):
    v = AlVezerlo(b)
    v._kezel(Esemeny(dt(HETFO, "10:35"), Tipus.ZENE_INDUL, 3))
    v._kezel(Esemeny(dt(HETFO, "09:40"), Tipus.ZENE_INDUL, 2))
    assert v.forrasok == ["Buli", "Alap"] and v.inditva == 2
    assert "Nagyszünet" in v.naplo[0] and v.naplo[1] == "Szünetzene indul"


def test_kezi_valasztas_a_szunet_vegeig_felulirja(b, monkeypatch):
    b.mentes = lambda *_: None
    v = AlVezerlo(b)
    most = dt(HETFO, "10:40")
    assert v.jelenlegi_forras(most).nev == "Buli" and v.musor_blokk.nev == "Nagyszünet"
    v.forras_valtas(1)
    assert v._musor_kezi and v.jelenlegi_forras(most).nev == "Nyugi" and v.musor_blokk is None
    v._kezel(Esemeny(dt(HETFO, "11:35"), Tipus.ZENE_INDUL, 4))
    assert not v._musor_kezi


def test_forrasvaltaskor_megjegyzi_a_sort(monkeypatch):
    monkeypatch.setattr(hang.hatter, "futtat", lambda fv, siker=None, hiba=None: None)
    z = ZeneLejatszo()
    a, n = ZeneForras("youtube", "A", "a"), ZeneForras("youtube", "N", "n")
    z.forras = a
    z.szamok = [Szam("1", yt="1"), Szam("2", yt="2"), Szam("k", yt="k", kert=True), Szam("3", yt="3")]
    z.index = 1
    z.forras_beallitas(n)
    assert z.szamok == [] and [s.cim for s in z._fuggo_kert] == ["k"]
    z.forras_beallitas(a)
    assert [s.cim for s in z.szamok] == ["k", "3", "1", "2"] and z.index == 0
