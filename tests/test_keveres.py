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
    return z


def test_ujrakever_a_mostanit_es_a_kerteket_helyben_hagyja(zene, monkeypatch):
    monkeypatch.setattr(hang.random, "shuffle", lambda lista: lista.reverse())
    zene.szamok = [Szam("lejátszott"), Szam("most"), Szam("a"), Szam("kért", kert=True), Szam("b"), Szam("c")]
    zene.index = 1
    jelzes = []
    zene.lista_valtozott.connect(lambda: jelzes.append(1))
    assert zene.ujrakever()
    assert [s.cim for s in zene.szamok] == ["lejátszott", "most", "kért", "c", "b", "a"]
    assert zene.index == 1 and jelzes


def test_ujrakever_rovid_sornal_es_spotifynal_nem(zene):
    zene.szamok = [Szam("a"), Szam("b")]
    assert not zene.ujrakever()
    zene.szamok = [Szam("a"), Szam("b"), Szam("c")]
    zene.forras = ZeneForras("spotify", "Spotify", "x")
    assert not zene.ujrakever()
