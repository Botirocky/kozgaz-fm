__lazy_modules__ = ["wave", "PySide6.QtCore", "PySide6.QtMultimedia", "kozgaz_fm.bemondo", "kozgaz_fm.kimenetek"]

import wave

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtMultimedia import QMediaPlayer

from kozgaz_fm import bemondo
from kozgaz_fm.kimenetek import TobbLejatszo, ZonaKimenet, cel_indexek

ZONAK = [ZonaKimenet("Folyosó", "", True, True, True, 1.0),
         ZonaKimenet("Udvar", "udvar-eszkoz", True, False, False, 0.5),
         ZonaKimenet("Tanári", "tanari-eszkoz", False, False, True, 1.5)]


@pytest.fixture(scope="module", autouse=True)
def alkalmazas():
    return QCoreApplication.instance() or QCoreApplication([])


@pytest.mark.parametrize(("cel", "vart"), [
    ("csengo", [0, 1]), ("zene", [0]), ("bemondas", [0, 2]), ("mind", [0, 1, 2]), ("elso", [0]),
    ("zona:2", [2]), ("zona:9", []), ("zona:x", []), ("ismeretlen", []),
])
def test_cel_indexek(cel, vart):
    assert cel_indexek(ZONAK, cel) == vart


def test_tobb_lejatszo_aktiv_es_hangero():
    t = TobbLejatszo(zonak=ZONAK)
    assert [z.nev for z in t.aktiv("bemondas")] == ["Folyosó", "Tanári"]
    t.setVolume(0.8)
    hangerok = [round(k.volume(), 3) for _l, k, _z in t._tagok]
    assert hangerok == [0.8, 0.4, 1.0]
    assert t.aktiv("zene") == [ZONAK[0]] and t._fo == 0
    assert t.aktiv("ismeretlen") == [] and t._fo == -1
    assert t.playbackState() == QMediaPlayer.PlaybackState.StoppedState and t.position() == 0


def test_helyben_frissit_vagy_ujraepit():
    t = TobbLejatszo(zonak=ZONAK)
    regi = [lejatszo for lejatszo, _k, _z in t._tagok]
    atnevezve = [ZonaKimenet("Aula", "", True, True, True, 2.0), *ZONAK[1:]]
    assert not t.ujraepitendo(atnevezve)
    t.zonak(atnevezve)
    assert [lejatszo for lejatszo, _k, _z in t._tagok] == regi and t.zona_lista[0].nev == "Aula"
    uj_eszkoz = [*ZONAK[:2], ZonaKimenet("Tanári", "masik-eszkoz")]
    assert t.ujraepitendo(uj_eszkoz)
    t.zonak(uj_eszkoz)
    assert [lejatszo for lejatszo, _k, _z in t._tagok] != regi and len(t._tagok) == 3


def test_jelzes_csak_az_elso_aktiv_zonatol():
    t = TobbLejatszo(zonak=ZONAK)
    kapott = []
    t.positionChanged.connect(kapott.append)
    t.aktiv("bemondas")
    t._tagok[2][0].positionChanged.emit(111)
    t._tagok[0][0].positionChanged.emit(222)
    t.aktiv("zona:2")
    t._tagok[2][0].positionChanged.emit(333)
    assert kapott == [222, 333]


def test_espeak_wav(tmp_path):
    if bemondo.espeak_ut() is None:
        pytest.skip("nincs espeak-ng")
    ut = bemondo.espeak_wav("Kedves diákok, ez egy próba.", tmp_path / "proba.wav")
    with wave.open(str(ut)) as f:
        assert f.getnframes() > 1000


def test_bemondo_zona_modban_hangfajlt_ad(tmp_path, monkeypatch):
    monkeypatch.setattr(bemondo, "espeak_ut", lambda: "/usr/bin/espeak-ng")
    monkeypatch.setattr(bemondo, "gyorsitotar_mappa", lambda: tmp_path)
    monkeypatch.setattr(bemondo, "espeak_wav", lambda szoveg, ut: ut)
    monkeypatch.setattr(bemondo.hatter, "futtat", lambda fv, siker=None, hiba=None: siker(fv()))
    b = bemondo.Bemondo()
    b.zona_mod = True
    kesz, fajlok = [], []
    b.kesz.connect(lambda: kesz.append(1))
    b.hangfajl_kesz.connect(fajlok.append)
    assert b.mond("Figyelem!") is True
    assert len(fajlok) == 1 and fajlok[0].endswith(".wav") and not b.beszel and kesz == []


def test_bemondo_megallitas_eldobja_a_kesot(tmp_path, monkeypatch):
    monkeypatch.setattr(bemondo, "espeak_ut", lambda: "/usr/bin/espeak-ng")
    monkeypatch.setattr(bemondo, "gyorsitotar_mappa", lambda: tmp_path)
    fuggo = []
    monkeypatch.setattr(bemondo.hatter, "futtat", lambda fv, siker=None, hiba=None: fuggo.append(siker))
    b = bemondo.Bemondo()
    b.zona_mod = True
    kesz, fajlok = [], []
    b.kesz.connect(lambda: kesz.append(1))
    b.hangfajl_kesz.connect(fajlok.append)
    b.mond("Figyelem!")
    assert b.beszel
    b.megallit()
    fuggo[0](tmp_path / "keso.wav")
    assert kesz == [1] and fajlok == [] and not b.beszel


def test_vezerlo_zona_kimenetek():
    from kozgaz_fm.beallitasok import Zona, alapertelmezett
    from kozgaz_fm.vezerlo import Vezerlo

    class Csonk:
        zona_kimenetek = Vezerlo.zona_kimenetek

        def __init__(self, b):
            self.b = b

    b = alapertelmezett()
    b.kimenet = "fo-eszkoz"
    assert Csonk(b).zona_kimenetek() == [ZonaKimenet("Alapértelmezett", "fo-eszkoz")]
    b.zonak = [Zona("Udvar", "u", zene=False, hangero=250), Zona("", "t", csengo=False, hangero=50)]
    z = Csonk(b).zona_kimenetek()
    assert z[0] == ZonaKimenet("Udvar", "u", True, False, True, 1.0)
    assert z[1].nev == "2. zóna" and z[1].szorzo == 0.5 and not z[1].csengo


def test_riasztas_nem_halkul_a_zonakban():
    t = TobbLejatszo(zonak=ZONAK)
    t.setVolume(1.0)
    t.aktiv("csengo")
    assert [round(k.volume(), 3) for _l, k, _z in t._tagok] == [1.0, 0.5, 1.0]
    t.aktiv("mind")
    assert [round(k.volume(), 3) for _l, k, _z in t._tagok] == [1.0, 1.0, 1.0]
    t.aktiv("csengo")
    assert round(t._tagok[1][1].volume(), 3) == 0.5


def test_elenged_minden_zonaban(tmp_path):
    hang = tmp_path / "a.wav"
    hang.write_bytes(b"RIFF")
    t = TobbLejatszo(zonak=ZONAK)
    t.aktiv("mind")
    from PySide6.QtCore import QUrl
    t.setSource(QUrl.fromLocalFile(str(hang)))
    t.aktiv("zene")
    assert t.forrasok() == {str(hang)}
    t.elenged()
    assert t.forrasok() == set()


def test_csengo_zonacsere_a_vegen_lep_ervenybe():
    from kozgaz_fm.hang import CsengoLejatszo

    c = CsengoLejatszo()
    c.zonak(ZONAK)
    c._aktiv = True
    uj = [ZonaKimenet("Csak egy", "masik")]
    c.zonak(uj)
    assert c.lejatszo.zona_lista == tuple(ZONAK)
    kesz = []
    c.kesz.connect(lambda: kesz.append(1))
    c._aktiv = False
    c._kesz_jelzes()
    assert c.lejatszo.zona_lista == tuple(uj) and kesz == [1]


def test_zene_hiba_ha_nincs_zene_zona():
    from kozgaz_fm.beallitasok import ZeneForras
    from kozgaz_fm.hang import ZeneLejatszo

    z = ZeneLejatszo()
    z.zonak([ZonaKimenet("Tanári", "t", zene=False)])
    z.forras = ZeneForras("mappa", "x", "/nincs")
    hibak = []
    z.hiba.connect(hibak.append)
    z.indit()
    assert "sincs bekapcsolva a zene" in hibak[0] and not z.szol


def test_espeak_hiba_utan_rendszer_felolvaso(tmp_path, monkeypatch):
    monkeypatch.setattr(bemondo, "espeak_ut", lambda: "/usr/bin/espeak-ng")
    monkeypatch.setattr(bemondo, "gyorsitotar_mappa", lambda: tmp_path)

    def hibas(fv, siker=None, hiba=None):
        hiba(OSError("nincs magyar hang"))
    monkeypatch.setattr(bemondo.hatter, "futtat", hibas)
    b = bemondo.Bemondo()
    b.zona_mod = True
    kimondott = []
    monkeypatch.setattr(b, "_kimond", lambda sz: kimondott.append(sz) or True)
    assert b.mond("Figyelem!") and kimondott == ["Figyelem!"]
