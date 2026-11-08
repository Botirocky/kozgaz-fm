from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication

from kozgaz_fm import hang
from kozgaz_fm.beallitasok import ZeneForras
from kozgaz_fm.hang import Szam, ZeneLejatszo


@pytest.fixture
def zene(monkeypatch) -> ZeneLejatszo:
    QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setattr(hang.hatter, "futtat", lambda fv, siker=None, hiba=None: siker and siker(fv()))
    z = ZeneLejatszo()
    z.forras = ZeneForras("mappa", "Teszt", "x")
    monkeypatch.setattr(z, "_forrast_indit", lambda *a, **k: None)
    monkeypatch.setattr(z, "_elore_letolt", lambda: None)
    z.szamok = [Szam(c, Path(c)) for c in "abcde"]
    z._szol = True
    return z


def cimek(z: ZeneLejatszo) -> list[str]:
    return [s.cim for s in z.szamok]


def test_a_kert_zenek_kerese_sorrendjeben_jonnek_aztan_folytatodik_az_alap(zene):
    zene._jatszd(1)
    zene.beszur(Szam("k1", helyi=Path("k1.mp3"), yt="1"))
    zene.beszur(Szam("k2", helyi=Path("k2.mp3"), yt="2"))
    assert [s.cim for _i, s in zene.kert_sor()] == ["k1", "k2"]
    lejatszott = []
    for _ in range(4):
        zene._jatszd(zene.index + 1)
        lejatszott.append(zene.most_cim)
    assert lejatszott == ["k1", "k2", "c", "d"]
    assert cimek(zene) == list("abcde")


def test_lejatszott_keres_kikerul_es_nem_jon_vissza(zene):
    zene._jatszd(0)
    zene.beszur(Szam("k", helyi=Path("k.mp3"), yt="1"))
    zene._jatszd(zene.index + 1)
    assert zene.most_kert() and zene.most_cim == "k"
    for _ in range(6):
        zene._jatszd(zene.index + 1)
        assert zene.most_cim != "k"


def test_keres_kozben_erkezo_keres_a_sor_vegere_kerul(zene):
    zene._jatszd(2)
    zene.beszur(Szam("k1", helyi=Path("k1.mp3"), yt="1"))
    zene._jatszd(zene.index + 1)
    zene.beszur(Szam("k2", helyi=Path("k2.mp3"), yt="2"))
    zene.beszur(Szam("k3", helyi=Path("k3.mp3"), yt="3"))
    sorrend = []
    for _ in range(3):
        zene._jatszd(zene.index + 1)
        sorrend.append(zene.most_cim)
    assert sorrend == ["k2", "k3", "d"]


def test_alap_pozicio_kert_zene_alatt_az_utolso_alap_szamon_marad(zene):
    zene._jatszd(2)
    zene.beszur(Szam("k", helyi=Path("k.mp3"), yt="1"))
    zene._jatszd(zene.index + 1)
    alap = zene.alap_lista()
    assert [s.cim for _i, s in alap] == list("abcde")
    assert zene.szamok[zene.alap_pozicio()].cim == "c"


def test_tarolt_lista_nem_viszi_a_kereseket(zene):
    zene._jatszd(0)
    zene.beszur(Szam("k", helyi=Path("k.mp3"), yt="1"))
    zene._jatszd(zene.index + 1)
    zene._tarol()
    sajat, _hely, _ido = zene._tarolt[("mappa", "x")]
    assert "k" not in [s.cim for s in sajat]


def test_induló_kert_zene_kikerul_a_varakozok_kozul_es_jelez(zene):
    zene._jatszd(0)
    zene.beszur(Szam("k", helyi=Path("k.mp3"), yt="1"))
    jelzes = []
    zene.lista_valtozott.connect(lambda: jelzes.append(1))
    zene._jatszd(zene.index + 1)
    assert zene.kert_sor() == [] and jelzes


def test_szavazat_szerint_rendez_a_most_szolot_nem_mozditja(zene):
    zene._jatszd(1)
    for n in "123":
        zene.beszur(Szam(f"k{n}", helyi=Path(f"k{n}.mp3"), yt=n))
    jelek = []
    zene.lista_valtozott.connect(lambda: jelek.append(1))
    zene.kert_rendez({"3": 2, "2": 1})
    assert [s.cim for _i, s in zene.kert_sor()] == ["k3", "k2", "k1"]
    assert [s.szavazat for _i, s in zene.kert_sor()] == [2, 1, 0]
    assert zene.most_cim == "b" and jelek
    jelek.clear()
    zene.kert_rendez({"3": 2, "2": 1})
    assert not jelek
    zene.kert_rendez({"1": 1, "2": 1, "3": 1})
    assert [s.cim for _i, s in zene.kert_sor()] == ["k3", "k2", "k1"]
