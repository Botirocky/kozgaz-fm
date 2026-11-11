import math
import subprocess
import time
from datetime import datetime
from typing import Any

import pytest
from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer, QUrl
from PySide6.QtMultimedia import QMediaPlayer
from rend_minta import minta_beallitas

from kozgaz_fm import atuszas, hang, hangossag
from kozgaz_fm.atuszas import CsendTar, atuszas_hossz_ms, atuszas_kezdet_ms, csend_ertelmez, gorbe_be, gorbe_ki
from kozgaz_fm.beallitasok import Beallitasok, ZeneForras
from kozgaz_fm.hang import Szam, ZeneLejatszo
from kozgaz_fm.orarend import Esemeny, Tipus
from kozgaz_fm.vezerlo import Vezerlo


@pytest.fixture(scope="module", autouse=True)
def alkalmazas():
    return QCoreApplication.instance() or QCoreApplication([])


def varj(ms: int) -> None:
    kor = QEventLoop()
    QTimer.singleShot(ms, kor.quit)
    kor.exec()


def test_gorbe_egyenlo_teljesitmenyu():
    for i in range(101):
        t = i / 100
        assert gorbe_be(t) ** 2 + gorbe_ki(t) ** 2 == pytest.approx(1.0)
    assert gorbe_be(0) == 0 and gorbe_ki(0) == 1
    assert gorbe_be(1) == pytest.approx(1.0) and gorbe_ki(1) == pytest.approx(0.0, abs=1e-12)
    assert gorbe_be(0.5) == pytest.approx(math.sqrt(0.5)) and gorbe_be(0.5) > 0.5
    assert gorbe_be(-1) == 0 and gorbe_ki(2) == pytest.approx(0.0, abs=1e-12)
    ertekek = [gorbe_be(i / 50) for i in range(51)]
    assert ertekek == sorted(ertekek)


def test_atuszas_hossz_hatarai():
    assert atuszas_hossz_ms(True, 5.0) == 5000
    assert atuszas_hossz_ms(False, 5.0) == 0
    assert atuszas_hossz_ms(True, 0) == 0
    assert atuszas_hossz_ms(True, 30) == 12000
    assert atuszas_hossz_ms(True, -3) == 0


def test_atuszas_kezdete_a_csend_elott_van():
    assert atuszas_kezdet_ms(200_000, 0, 5000) == 195_000
    assert atuszas_kezdet_ms(200_000, 3000, 5000) == 192_000
    assert atuszas_kezdet_ms(4000, 3000, 5000) == 0


def test_alapertelmezett_beallitasok(tmp_path):
    b = Beallitasok()
    assert b.atusztatas_be is True and b.atusztatas == 5.0
    b.atusztatas_be = False
    b.atusztatas = 7.5
    ut = tmp_path / "b.json"
    b.mentes(ut)
    uj = Beallitasok.betoltes(ut)
    assert uj.atusztatas_be is False and uj.atusztatas == 7.5


FFMPEG_KIMENET = """Input #0, mp3, from 'x.mp3':
  Duration: 00:03:20.50, start: 0.025057, bitrate: 192 kb/s
[silencedetect @ 0x1] silence_start: 0
[silencedetect @ 0x1] silence_end: 1.85 | silence_duration: 1.85
[silencedetect @ 0x1] silence_start: 100.2
[silencedetect @ 0x1] silence_end: 101.0 | silence_duration: 0.8
[silencedetect @ 0x1] silence_start: 196.5
"""


def test_csend_ertelmezes_eleje_es_vege():
    eleje, vege = csend_ertelmez(FFMPEG_KIMENET)
    assert eleje == pytest.approx(1.85) and vege == pytest.approx(4.0)


def test_csend_ertelmezes_lezart_vegso_csend():
    kimenet = FFMPEG_KIMENET.replace("silence_start: 196.5\n",
                                     "silence_start: 196.5\n[silencedetect @ 0x1] silence_end: 200.5 | x\n")
    assert csend_ertelmez(kimenet)[1] == pytest.approx(4.0)


def test_csend_ertelmezes_kozepso_csend_nem_szamit():
    kimenet = "Duration: 00:03:20.00,\nsilence_start: 100\nsilence_end: 102 | silence_duration: 2\n"
    assert csend_ertelmez(kimenet) == (0.0, 0.0)
    assert csend_ertelmez("") == (0.0, 0.0)


def test_csend_ertelmezes_csupa_csend_nem_vagodik():
    kimenet = "Duration: 00:00:10.00,\nsilence_start: 0\nsilence_end: 10 | silence_duration: 10\n"
    assert csend_ertelmez(kimenet) == (0.0, 0.0)


def test_csend_ertelmezes_felso_korlat():
    kimenet = "Duration: 00:10:00.00,\nsilence_start: 0\nsilence_end: 45 | d\nsilence_start: 560\n"
    eleje, vege = csend_ertelmez(kimenet)
    assert eleje == atuszas.CSEND_MAX_MP and vege == atuszas.CSEND_MAX_MP


def test_valodi_csendvagas(tmp_path):
    ffmpeg = hangossag.ffmpeg_ut()
    if ffmpeg is None:
        pytest.skip("nincs ffmpeg")
    hang_fajl = tmp_path / "csendes.wav"
    subprocess.run([ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-filter_complex",
                    "anullsrc=r=44100:cl=mono:d=1.5[a];sine=frequency=440:duration=8:sample_rate=44100[b];"
                    "anullsrc=r=44100:cl=mono:d=2.5[c];[a][b][c]concat=n=3:v=0:a=1", str(hang_fajl)], check=True)
    eleje, vege = atuszas.csend_meres(hang_fajl, ffmpeg)
    assert eleje == pytest.approx(1.5, abs=0.15)
    assert vege == pytest.approx(2.5, abs=0.2)


def test_csendtar_mentes_es_ervenytelenites(tmp_path):
    fajl = tmp_path / "zene.mp3"
    fajl.write_bytes(b"a" * 10)
    tar = CsendTar(tmp_path / "csend.json")
    assert tar.keres(fajl) is None
    tar.beir(fajl, 1.25, 3.5)
    assert CsendTar(tmp_path / "csend.json").keres(fajl) == (1.25, 3.5)
    fajl.write_bytes(b"b" * 20)
    assert CsendTar(tmp_path / "csend.json").keres(fajl) is None
    assert tar.keres(tmp_path / "nincs.mp3") is None


class AlLejatszo:
    def __init__(self, nev: str, hossz: int = 0, allapot=QMediaPlayer.PlaybackState.StoppedState) -> None:
        self.nev = nev
        self._hossz = hossz
        self.allapot = allapot
        self.hang = 0.0
        self.pozicio = 0
        self.forras = QUrl()
        self.naplo: list[str] = []

    def duration(self) -> int:
        return self._hossz

    def position(self) -> int:
        return self.pozicio

    def setPosition(self, ertek: int) -> None:
        self.pozicio = ertek
        self.naplo.append(f"pozicio:{ertek}")

    def playbackState(self):
        return self.allapot

    def setSource(self, url: QUrl) -> None:
        self.forras = url
        self.naplo.append("forras")

    def source(self) -> QUrl:
        return self.forras

    def play(self) -> None:
        self.allapot = QMediaPlayer.PlaybackState.PlayingState
        self.naplo.append("play")

    def pause(self) -> None:
        self.allapot = QMediaPlayer.PlaybackState.PausedState

    def stop(self) -> None:
        self.allapot = QMediaPlayer.PlaybackState.StoppedState
        self.naplo.append("stop")

    def setVolume(self, ertek: float) -> None:
        self.hang = ertek

    def volume(self) -> float:
        return self.hang


@pytest.fixture
def zene(monkeypatch, tmp_path) -> Any:
    monkeypatch.setattr(hang.hatter, "futtat", lambda fv, siker=None, hiba=None: siker and siker(fv()))
    monkeypatch.setattr(atuszas, "csend_meres", lambda ut, ffmpeg=None: (0.0, 0.0))
    z: Any = ZeneLejatszo()
    z.forras = ZeneForras("mappa", "Teszt", "x")
    a, b = tmp_path / "a.mp3", tmp_path / "b.mp3"
    a.write_bytes(b"a")
    b.write_bytes(b"b")
    z.szamok = [Szam("a", a), Szam("b", b)]
    z.index = 0
    z.csend_tar = CsendTar(tmp_path / "csend.json")
    z.csend_tar.beir(a, 0.0, 4.0)
    z.csend_tar.beir(b, 2.0, 0.0)
    z.fo = AlLejatszo("fo", 200_000, QMediaPlayer.PlaybackState.PlayingState)
    z.ki = AlLejatszo("ki")
    z.lejatszo = z.kimenet = z.fo
    z._kifuto = z._kifuto_kimenet = z.ki
    z._szol = True
    z.atusztatas_mp = 5.0
    z.hangero_ertek = 100
    return z


def inditasok(zene: ZeneLejatszo, monkeypatch) -> list:
    lista: list = []
    monkeypatch.setattr(zene, "_forrast_indit", lambda url, ms=None: lista.append((url.toLocalFile(), ms)))
    return lista


def test_atuszas_a_vegi_csend_elott_indul(zene, monkeypatch):
    lista = inditasok(zene, monkeypatch)
    zene._pozicio(190_999)
    assert not lista and zene.lejatszo is zene.fo
    zene._pozicio(191_000)
    assert lista == [(str(zene.szamok[1].helyi), 5000)]
    assert zene.lejatszo is zene.ki and zene._kifuto is zene.fo and zene.index == 1


def test_atuszas_csend_nelkul_a_szam_vege_elott_indul(zene, monkeypatch):
    zene.szamok[0].helyi.write_bytes(b"uj")
    lista = inditasok(zene, monkeypatch)
    zene._pozicio(194_999)
    assert not lista
    zene._pozicio(195_000)
    assert len(lista) == 1


def test_atuszas_kikapcsolva_nincs_keveres_es_csendvagas(zene, monkeypatch):
    lista = inditasok(zene, monkeypatch)
    zene.atusztatas_be = False
    zene._pozicio(199_000)
    assert not lista and zene.lejatszo is zene.fo
    assert zene._csend_ms(zene.szamok[1].helyi) == (0, 0)


def test_atuszas_nulla_hosszal_nincs(zene, monkeypatch):
    lista = inditasok(zene, monkeypatch)
    zene.atusztatas_mp = 0
    zene._pozicio(199_000)
    assert not lista


def test_uj_szam_az_eleji_csend_utan_indul(zene):
    url = QUrl.fromLocalFile(str(zene.szamok[1].helyi))
    zene._forrast_indit_most(zene._indito_jel, url, None)
    assert zene.fo.naplo == ["forras", "pozicio:2000", "play"]


def test_csendes_eleju_szam_vagas_nelkul_indul_ha_ki_van_kapcsolva(zene):
    zene.atusztatas_be = False
    url = QUrl.fromLocalFile(str(zene.szamok[1].helyi))
    zene._forrast_indit_most(zene._indito_jel, url, None)
    assert zene.fo.naplo == ["forras", "play"]


def test_kezi_valtas_rovid_atuszassal(zene, monkeypatch):
    lista = inditasok(zene, monkeypatch)
    zene._vedelem._ig = 0.0
    zene._jatszd(1)
    assert lista == [(str(zene.szamok[1].helyi), int(atuszas.KEZI_ATUSZTATAS_MP * 1000))]
    assert zene.lejatszo is zene.ki and zene._kifuto is zene.fo


def test_kezi_valtas_allo_zenenel_nincs_atuszas(zene, monkeypatch):
    lista = inditasok(zene, monkeypatch)
    zene.fo.allapot = QMediaPlayer.PlaybackState.StoppedState
    zene._jatszd(1)
    assert lista == [(str(zene.szamok[1].helyi), None)] and zene.lejatszo is zene.fo


def test_csengo_gyors_leallitas_atuszas_kozben(zene, monkeypatch):
    inditasok(zene, monkeypatch)
    zene._pozicio(191_000)
    zene.fo.hang = 0.3
    zene.kimenet.setVolume(0.6)
    zene._kifuto_kimenet.setVolume(0.8)
    zene._kifuto_alap = 0.8
    ki, fo = zene._kifuto, zene.lejatszo
    fo.allapot = QMediaPlayer.PlaybackState.PlayingState
    kezdet = time.monotonic()
    zene.megallit(elhalkitas=False, gyors=True)
    assert not zene._szol
    assert zene._animacio.duration() == int(atuszas.CSENGO_ELHALKITAS_MP * 1000)
    assert zene._kifuto_animacio.duration() == int(atuszas.CSENGO_ELHALKITAS_MP * 1000)
    varj(500)
    assert time.monotonic() - kezdet < 1.5
    assert fo.hang == pytest.approx(0.0, abs=1e-9) and ki.hang == pytest.approx(0.0, abs=1e-9)
    assert fo.allapot == QMediaPlayer.PlaybackState.StoppedState
    assert ki.allapot == QMediaPlayer.PlaybackState.StoppedState


def test_gyors_leallitas_folytonos_hangerovel(zene):
    zene.kimenet.setVolume(0.4)
    szintek: list[float] = []
    zene._animacio.valueChanged.connect(lambda _v: szintek.append(zene.kimenet.volume()))
    zene.megallit(elhalkitas=False, gyors=True)
    varj(400)
    assert szintek[0] == pytest.approx(0.4, abs=0.05)
    assert all(a >= b - 1e-9 for a, b in zip(szintek, szintek[1:], strict=False))
    assert szintek[-1] == pytest.approx(0.0, abs=1e-9)


def test_normal_leallitas_hosszu_elhalkitassal(zene):
    zene.elhalkitas_mp = 3.0
    zene.megallit()
    assert zene._animacio.duration() == 3000 and zene._gorbe == "ki"


class AlVezerlo:
    _kezel = Vezerlo._kezel
    tartalek = type("Tartalek", (), {"passziv": False})()

    def __init__(self) -> None:
        self.riasztas = False
        self.b = minta_beallitas()
        self._auto_zene = True
        self.esemenyek: list[str] = []
        v = self

        class Zene:
            szol = True

            def megallit(self, **kw):
                v.esemenyek.append(f"megallit:{sorted(kw.items())}")

        self.zene = Zene()

    def log(self, szoveg: str) -> None:
        pass

    def csengetes(self, hang, leiras="", hangero=None, **kw) -> None:
        self.esemenyek.append(f"csengetes:{kw['tervezett'].strftime('%H:%M:%S')}")

    @property
    def frissult(self):
        return type("Jel", (), {"emit": staticmethod(lambda: None)})


@pytest.mark.parametrize("tipus", [Tipus.BECSENGO, Tipus.JELZO])
def test_csengo_idozitese_nem_csuszik(tipus):
    v = AlVezerlo()
    ido = datetime(2026, 11, 9, 8, 0, 0)
    kezdet = time.monotonic()
    v._kezel(Esemeny(ido, tipus, 1))
    assert time.monotonic() - kezdet < 0.2
    assert v.esemenyek == ["megallit:[('elhalkitas', False), ('gyors', True)]", "csengetes:08:00:00"]
    assert v._auto_zene is False
