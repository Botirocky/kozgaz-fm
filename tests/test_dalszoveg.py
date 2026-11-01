__lazy_modules__ = ["json", "pathlib", "urllib.error", "pytest", "PySide6.QtCore", "kozgaz_fm.dalszoveg",
                    "kozgaz_fm.dalszoveg_or", "kozgaz_fm.hang", "kozgaz_fm.szuro"]

import io
import json
import urllib.error
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication

from kozgaz_fm import dalszoveg, hang
from kozgaz_fm.beallitasok import ZeneForras
from kozgaz_fm.dalszoveg import DalszovegHiba, DalszovegTar, Eredmeny, cim_bontas, vizsgal
from kozgaz_fm.dalszoveg_or import DalszovegOr
from kozgaz_fm.hang import Szam, ZeneLejatszo
from kozgaz_fm.szuro import Ertekeles

TRAGAR = " ".join(["fuck"] * 20)
TISZTA = " ".join(["szép"] * 200)


@pytest.fixture(scope="module", autouse=True)
def app():
    return QCoreApplication.instance() or QCoreApplication([])


def _jelolt(cim="Stan", eloado="Eminem", szoveg=TISZTA, hossz=400.0, instrumental=False):
    return {"trackName": cim, "artistName": eloado, "duration": hossz, "plainLyrics": szoveg,
            "instrumental": instrumental}


def _api(monkeypatch, *valaszok):
    sor = list(valaszok)
    hivasok = []

    def lekeres(parameterek):
        hivasok.append(parameterek)
        return sor.pop(0) if sor else []

    monkeypatch.setattr(dalszoveg, "_lekeres", lekeres)
    return hivasok


@pytest.mark.parametrize(("cim", "vart"), [
    ("Eminem - Stan (Long Version) ft. Dido", ("Eminem", "Stan")),
    ("Queen – Don't Stop Me Now [Official Video]", ("Queen", "Don't Stop Me Now")),
    ("01. Quimby - Most múlik pontosan", ("Quimby", "Most múlik pontosan")),
    ("Video Killed the Radio Star", ("", "Video Killed the Radio Star")),
    ("The Buggles - Video Killed the Radio Star | HD", ("The Buggles", "Video Killed the Radio Star")),
    ("Dua Lipa - Levitating Official Music Video", ("Dua Lipa", "Levitating")),
])
def test_cim_bontas(cim, vart):
    assert cim_bontas(cim) == vart


def test_vizsgal_a_legtragarabb_valtozatot_nezi(monkeypatch):
    _api(monkeypatch, [_jelolt(szoveg=TISZTA), _jelolt(szoveg=TRAGAR)])
    e = vizsgal("Eminem - Stan")
    assert e.talalt and e.ertekeles.eros == 20


def test_vizsgal_masik_eloadot_nem_fogad_el(monkeypatch):
    _api(monkeypatch, [_jelolt(eloado="Valaki Más", szoveg=TRAGAR)], [])
    assert not vizsgal("Eminem - Stan").talalt


def test_vizsgal_masik_cimet_nem_fogad_el(monkeypatch):
    _api(monkeypatch, [_jelolt(cim="Stan Remix Más Cím", szoveg=TRAGAR)], [])
    assert not vizsgal("Eminem - Stan").talalt


def test_vizsgal_hosszeltereset_kiszuri(monkeypatch):
    _api(monkeypatch, [_jelolt(hossz=100.0, szoveg=TRAGAR)], [])
    assert not vizsgal("Eminem - Stan", hossz=400).talalt
    _api(monkeypatch, [_jelolt(hossz=410.0, szoveg=TRAGAR)])
    assert vizsgal("Eminem - Stan", hossz=400).talalt


def test_vizsgal_keresoszo_adhatja_az_eloadot_de_a_cimet_nem(monkeypatch):
    hivasok = _api(monkeypatch, [_jelolt()])
    assert vizsgal("Stan", tobblet="Eminem Stan").talalt
    assert hivasok == [{"q": "Stan"}]
    _api(monkeypatch, [], [_jelolt(cim="Másik Szám", szoveg=TRAGAR)])
    assert not vizsgal("Stan", tobblet="Eminem Másik Szám").talalt


def test_vizsgal_instrumentalis(monkeypatch):
    _api(monkeypatch, [_jelolt(szoveg=None, instrumental=True)])
    e = vizsgal("Eminem - Stan")
    assert e.talalt and e.instrumental and not e.ertekeles.tragar()


class _Valasz(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_lekeres_ujraprobal_majd_hibat_ad(monkeypatch):
    hivasok = []

    def urlopen(_keres, timeout):
        hivasok.append(timeout)
        raise urllib.error.HTTPError("u", 503, "busy", {}, None)

    monkeypatch.setattr(dalszoveg.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(dalszoveg, "VARAKOZAS_MP", 0)
    with pytest.raises(DalszovegHiba):
        dalszoveg._lekeres({"q": "x"})
    assert len(hivasok) == dalszoveg.PROBALKOZAS


def test_lekeres_nem_lista_valasz_hiba(monkeypatch):
    monkeypatch.setattr(dalszoveg.urllib.request, "urlopen",
                        lambda _k, timeout: _Valasz(json.dumps({"message": "busy"}).encode()))
    with pytest.raises(DalszovegHiba):
        dalszoveg._lekeres({"q": "x"})


def test_tar_megorzi_es_lejar_a_nem_talalt(tmp_path: Path):
    ido = [1000.0]
    ut = tmp_path / "t" / "dalszoveg.json"
    tar = DalszovegTar(ut, lambda: ido[0])
    assert tar.keres("Eminem - Stan") is None
    tar.beir("Eminem - Stan", Eredmeny(True, Ertekeles(100, 7, 0, 0)))
    tar.beir("Senki - Semmi", Eredmeny(False))
    uj = DalszovegTar(ut, lambda: ido[0])
    assert uj.keres("EMINEM - Stan (Official Video)").ertekeles.eros == 7
    assert uj.keres("Senki - Semmi").talalt is False
    ido[0] += dalszoveg.NINCS_MEGORZES_MP + 1
    assert uj.keres("Senki - Semmi") is None
    assert uj.keres("Eminem - Stan") is not None
    assert "fuck" not in ut.read_text(encoding="utf-8")


def test_tar_serult_fajl(tmp_path: Path):
    ut = tmp_path / "d.json"
    ut.write_text("nem json", encoding="utf-8")
    assert DalszovegTar(ut).keres("a - b") is None


@pytest.fixture
def zene(monkeypatch) -> ZeneLejatszo:
    monkeypatch.setattr(hang.hatter, "futtat", lambda fv, siker=None, hiba=None: siker and siker(fv()))
    z = ZeneLejatszo()
    z.forras = ZeneForras("mappa", "Teszt", "x")
    return z


def _or(zene, tmp_path, monkeypatch, itelet) -> DalszovegOr:
    monkeypatch.setattr("kozgaz_fm.dalszoveg_or.hatter.futtat",
                        lambda fv, siker=None, hiba=None: siker and siker(fv()))
    monkeypatch.setattr("kozgaz_fm.dalszoveg_or.dalszoveg.vizsgal", lambda cim, hossz, tobblet: itelet(cim))
    o = DalszovegOr(zene, DalszovegTar(tmp_path / "d.json"))
    o._ora.stop()
    return o


def _itelet(cim: str) -> Eredmeny:
    return Eredmeny(True, Ertekeles(100, 20, 0, 0) if "rossz" in cim else Ertekeles(100, 0, 0, 0))


def test_or_kiveszi_a_tragar_szamot_de_a_kertet_nem(zene, tmp_path, monkeypatch):
    zene.szamok = [Szam("jó 1"), Szam("rossz 1"), Szam("rossz kért", kert=True), Szam("jó 2")]
    zene.index = 3
    uzenetek = []
    zene.kiszurve.connect(uzenetek.append)
    o = _or(zene, tmp_path, monkeypatch, _itelet)
    for _ in range(5):
        o.tick()
    assert [s.cim for s in zene.szamok] == ["jó 1", "rossz kért", "jó 2"]
    assert zene.szamok[zene.index].cim == "jó 2"
    assert len(uzenetek) == 1 and "rossz 1" in uzenetek[0]


def test_or_hiba_utan_szunetet_tart(zene, tmp_path, monkeypatch):
    zene.szamok = [Szam("a - b")]
    hivasok = []

    def futtat(fv, siker=None, hiba=None):
        hivasok.append(1)
        hiba(DalszovegHiba("nem elérhető"))

    o = _or(zene, tmp_path, monkeypatch, _itelet)
    monkeypatch.setattr("kozgaz_fm.dalszoveg_or.hatter.futtat", futtat)
    o.tick()
    o.tick()
    assert len(hivasok) == 1 and [s.cim for s in zene.szamok] == ["a - b"]
    assert o.tar.keres("a - b") is None


def test_or_kikapcsolva_nem_kerdez(zene, tmp_path, monkeypatch):
    zene.szamok = [Szam("rossz")]
    o = _or(zene, tmp_path, monkeypatch, _itelet)
    o.beallit(False, "normal")
    o.tick()
    assert len(zene.szamok) == 1 and o.tar.keres("rossz") is None


def test_or_erzekenyseg_valtasra_ujraitel(zene, tmp_path, monkeypatch):
    zene.szamok = [Szam("kicsit"), Szam("masik")]
    enyhen = Eredmeny(True, Ertekeles(300, 2, 0, 0))
    o = _or(zene, tmp_path, monkeypatch, lambda c: enyhen)
    o.tick()
    o.tick()
    assert len(zene.szamok) == 2
    o.beallit(True, "szigoru")
    o.tick()
    assert zene.szamok == []
