__lazy_modules__ = ["pathlib", "pytest", "PySide6.QtCore", "kozgaz_fm.hang", "kozgaz_fm.szuro", "kozgaz_fm.youtube",
                    "kozgaz_fm.zenekeres"]

from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication

from kozgaz_fm import hang, youtube
from kozgaz_fm.beallitasok import ZeneForras
from kozgaz_fm.hang import Szam, ZeneLejatszo
from kozgaz_fm.szuro import Szuro
from kozgaz_fm.zenekeres import Keresek, KeresHiba


@pytest.fixture(scope="module", autouse=True)
def app():
    return QCoreApplication.instance() or QCoreApplication([])


@pytest.mark.parametrize(("cim", "vart"), [
    ("Rapper – Szám (Explicit)", "explicit"),
    ("KURVA jó nyár", "kurva"),
    ("Kúrva", "kurva"),
    ("Valami fuckin' song", "fuck"),
    ("Szarvasbőgés a Bakonyban", None),
    ("Pocsolya dal", None),
    ("Baszk népdal", None),
    ("Queen – Don't Stop Me Now", None),
])
def test_alap_lista(cim, vart):
    assert Szuro().talalat(cim) == vart


def test_sajat_szavak_egesz_szo_es_szokezdet():
    s = Szuro(["bunkó*", "Rossz Banda", ""], alap=False)
    assert s.talalat("A bunkók dala") == "bunko"
    assert s.talalat("rossz  banda – live") is None
    assert s.talalat("ROSSZ BANDA – live") == "rossz banda"
    assert s.talalat("Rossz Bandák") is None
    assert Szuro(["szar"], alap=False).talalat("szarka") is None


def test_ures_szuro_mindent_atenged():
    s = Szuro([], alap=False)
    assert not s and s.talalat("kurva") is None


def test_tobb_szoveg_kozul_barmelyik():
    assert Szuro(["tiltott előadó"], alap=False).talalat("Jó cím", "Tiltott Előadó") == "tiltott eloado"


def _szinkron(monkeypatch):
    monkeypatch.setattr(hang.hatter, "futtat", lambda fv, siker=None, hiba=None: siker and siker(fv()))


def test_betolteskor_kiszuri_a_mappa_szamait(tmp_path: Path, monkeypatch):
    _szinkron(monkeypatch)
    for nev in ("Jó szám.mp3", "Rossz (Explicit).mp3"):
        (tmp_path / nev).write_bytes(b"x")
    (tmp_path / "Tiltott Előadó").mkdir()
    (tmp_path / "Tiltott Előadó" / "Ártatlan.mp3").write_bytes(b"x")
    z = ZeneLejatszo()
    z.keveres = False
    z.szuro_beallitas(Szuro(["tiltott előadó"]), False)
    uzenetek = []
    z.kiszurve.connect(uzenetek.append)
    z.forras_beallitas(ZeneForras("mappa", "Mappa", str(tmp_path)))
    assert [s.cim for s in z.szamok] == ["Jó szám"]
    assert "2 számot" in uzenetek[0]


def test_szuro_valtozasa_a_betoltott_sorbol_is_kivesz():
    z = ZeneLejatszo()
    z.forras = ZeneForras("youtube", "Lista", "x")
    z.szamok = [Szam("a"), Szam("Rossz kurva"), Szam("c"), Szam("d", kert=True)]
    z.index = 2
    z.szuro_beallitas(Szuro(), True)
    assert [s.cim for s in z.szamok] == ["a", "c", "d"] and z.szamok[z.index].cim == "c"


def test_nem_szolo_sornal_a_kovetkezo_marad_a_helyen():
    z = ZeneLejatszo()
    z.forras = ZeneForras("youtube", "Lista", "x")
    z.szamok = [Szam("a"), Szam("Rossz kurva"), Szam("c")]
    z.index = 1
    z.szuro_beallitas(Szuro(), True)
    assert [s.cim for s in z.szamok] == ["a", "c"] and z.szamok[z.index].cim == "c"


def test_korhatarosat_kiveszi_es_tovabblep(monkeypatch):
    z = ZeneLejatszo()
    z.forras = ZeneForras("youtube", "Lista", "x")
    z.szamok = [Szam("a", yt="1"), Szam("b", yt="2"), Szam("c", yt="3")]
    z.index = 1
    z._szol = True
    z._varakozo = ("2", z._generacio, 1)
    jatszott = []
    monkeypatch.setattr(z, "_jatszd", jatszott.append)
    z._letoltes_hiba(z.szamok[1], youtube.Korhataros("b"))
    assert [s.cim for s in z.szamok] == ["a", "c"] and jatszott == [1] and "2" in z._korhatarosak


def test_elotoltott_korhataros_csak_kikerul(monkeypatch):
    z = ZeneLejatszo()
    z.forras = ZeneForras("youtube", "Lista", "x")
    z.szamok = [Szam("a", yt="1"), Szam("b", yt="2"), Szam("c", yt="3")]
    z.index = 2
    jatszott = []
    monkeypatch.setattr(z, "_jatszd", jatszott.append)
    z._letoltes_hiba(z.szamok[0], youtube.Korhataros("a"))
    assert [s.cim for s in z.szamok] == ["b", "c"] and z.index == 1 and jatszott == []


def test_spotify_explicit_atugras(monkeypatch):
    z = ZeneLejatszo()
    z.szuro = Szuro()
    hivasok = []
    monkeypatch.setattr(z, "_spotify_hivas", lambda muvelet, siker=None: hivasok.append(muvelet))
    assert z._spotify_szurt({"cim": "Dal", "eloado": "Valaki", "explicit": True})
    assert not z._spotify_szurt({"cim": "Dal", "eloado": "Valaki", "explicit": False})
    assert len(hivasok) == 1


def test_keres_szovege_es_talalata_a_szuron():
    k = Keresek()
    with pytest.raises(KeresHiba):
        k.uj("kurva jó szám", "", "e", "ip", 3, [], Szuro())
    keres = k.uj("valami", "", "e", "ip", 3, [], Szuro())
    k.talalat(keres.azon, "yt", "Valami (Explicit)", 200, 7, [], 0, Szuro())
    assert keres.allapot == "elutasitva"


def test_korhataros_keres_elutasitva():
    k = Keresek()
    keres = k.uj("valami", "", "e", "ip", 3, [])
    k.talalat(keres.azon, "yt", "Valami", 200, 7, [], 18)
    assert keres.allapot == "elutasitva" and "Korhatáros" in keres.ok
    masik = k.uj("valami más", "", "e", "ip", 3, [])
    k.talalat(masik.azon, "yt2", "Valami más", 200, 7, [], 18, korhatar_tiltas=False)
    assert masik.allapot == "varakozik"
