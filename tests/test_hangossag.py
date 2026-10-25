__lazy_modules__ = ["math", "subprocess", "PySide6.QtCore", "kozgaz_fm.hangossag"]

import math
import subprocess

import pytest
from PySide6.QtCore import QCoreApplication

from kozgaz_fm import hangossag
from kozgaz_fm.hangossag import Kiegyenlito, Tar, erosites_db, kimenet_ertelmez, meres, szorzo

KIMENET = """[Parsed_ebur128_0 @ 0x1] t: 3.1  TARGET:-23 LUFS    M: -9.0 S: -9.2     I: -9.4 LUFS
[Parsed_ebur128_0 @ 0x1] Summary:

  Integrated loudness:
    I:          -7.6 LUFS
    Threshold: -17.7 LUFS

  True peak:
    Peak:        0.8 dBFS
"""


@pytest.fixture(scope="module", autouse=True)
def alkalmazas():
    return QCoreApplication.instance() or QCoreApplication([])


def test_kimenet_ertelmez_az_osszegzest_veszi():
    assert kimenet_ertelmez(KIMENET) == (-7.6, 0.8)
    lufs, csucs = kimenet_ertelmez("Summary:\n    I:         -inf LUFS\n    Peak:       -inf dBFS\n")
    assert lufs == float("-inf") and csucs == float("-inf")
    with pytest.raises(hangossag.HangossagHiba):
        kimenet_ertelmez("semmi")


@pytest.mark.parametrize(("lufs", "csucs", "vart"), [
    (-7.6, 0.8, -8.4),
    (-16.0, -3.0, 0.0),
    (-22.0, -10.0, 6.0),
    (-22.0, -4.0, 3.0),
    (-40.0, -20.0, 6.0),
    (2.0, 3.0, -18.0),
    (-5.0, 1.0, -11.0),
    (float("-inf"), float("-inf"), 0.0),
    (-70.0, -50.0, 0.0),
])
def test_erosites(lufs, csucs, vart):
    assert erosites_db(lufs, csucs) == pytest.approx(vart)


def test_erosites_korlatok():
    assert erosites_db(30.0, 0.0) == hangossag.MAX_CSOKKENTES_DB
    assert szorzo(0) == 1.0 and szorzo(-20) == pytest.approx(0.1) and szorzo(6) == pytest.approx(1.995, rel=1e-3)


def test_tar_ervenyteleniti_ha_valtozik_a_fajl(tmp_path):
    hang = tmp_path / "a.mp3"
    hang.write_bytes(b"x")
    tar = Tar(tmp_path / "tar.json")
    assert tar.keres(hang) is None
    tar.beir(hang, -12.5, -1.0)
    assert tar.keres(hang) == (-12.5, -1.0)
    tar.mentes()
    uj = Tar(tmp_path / "tar.json")
    assert uj.keres(hang) == (-12.5, -1.0) and uj.darab() == 1
    hang.write_bytes(b"masik tartalom")
    assert uj.keres(hang) is None
    (tmp_path / "tar.json").write_text("{szemet", encoding="utf-8")
    assert Tar(tmp_path / "tar.json").darab() == 0


def _szinkron(ke: Kiegyenlito, monkeypatch, meresek: dict) -> list[str]:
    sorrend: list[str] = []

    def mer(ut, ffmpeg=None, **_kw):
        sorrend.append(ut.name)
        if ut.name not in meresek:
            raise hangossag.HangossagHiba("nem hangfájl")
        return meresek[ut.name]

    monkeypatch.setattr(hangossag, "meres", mer)
    monkeypatch.setattr(hangossag, "ffmpeg_ut", lambda: "/bin/ffmpeg")
    return sorrend


def test_kiegyenlito_sorrend_es_szorzo(tmp_path, monkeypatch):
    fajlok = {n: tmp_path / n for n in ("a.mp3", "b.mp3", "c.mp3", "hibas.mp3")}
    for f in fajlok.values():
        f.write_bytes(f.name.encode())
    ke = Kiegyenlito(tar=Tar(tmp_path / "tar.json"))
    sorrend = _szinkron(ke, monkeypatch, {"a.mp3": (-8.0, 0.0), "b.mp3": (-16.0, -2.0), "c.mp3": (-24.0, -12.0)})
    ke._fut = "foglalt"
    ke.kell(fajlok["a.mp3"])
    ke.kell(fajlok["b.mp3"])
    ke.kell(fajlok["hibas.mp3"])
    ke.kell(fajlok["c.mp3"], elore=True)
    ke.kell(fajlok["a.mp3"])
    assert [p.name for p in ke._sor] == ["c.mp3", "a.mp3", "b.mp3", "hibas.mp3"]
    ke._fut = None
    monkeypatch.setattr(ke._vegrehajto, "submit", lambda fv, *a: fv(*a))
    ke._kovetkezo()
    assert sorrend == ["c.mp3", "a.mp3", "b.mp3", "hibas.mp3"] and ke.varakozik() == 0
    assert ke.szorzo(fajlok["a.mp3"]) == pytest.approx(szorzo(-8.0))
    assert ke.szorzo(fajlok["b.mp3"]) == 1.0
    assert ke.szorzo(fajlok["c.mp3"]) == pytest.approx(szorzo(6.0))
    assert ke.szorzo(fajlok["hibas.mp3"]) == 1.0
    ke.kell(fajlok["hibas.mp3"])
    assert sorrend.count("hibas.mp3") == 1
    ke.bekapcsolva = False
    assert ke.szorzo(fajlok["a.mp3"]) == 1.0
    ke.leallit()


def test_kiegyenlito_ffmpeg_nelkul_nem_sorol(tmp_path, monkeypatch):
    monkeypatch.setattr(hangossag, "ffmpeg_ut", lambda: None)
    ke = Kiegyenlito(tar=Tar(tmp_path / "tar.json"))
    f = tmp_path / "a.mp3"
    f.write_bytes(b"x")
    ke.kell(f, elore=True)
    assert ke.varakozik() == 0 and not ke.elerheto
    ke.leallit()


def test_valodi_meres_szinuszon(tmp_path):
    ffmpeg = hangossag.ffmpeg_ut()
    if ffmpeg is None:
        pytest.skip("nincs ffmpeg")
    hang = tmp_path / "szinusz.wav"
    subprocess.run([ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                    "sine=frequency=1000:duration=5:sample_rate=48000", "-af", "volume=-6dB", str(hang)], check=True)
    lufs, csucs = meres(hang, ffmpeg)
    assert -29 < lufs < -25 and -27 < csucs < -21
    assert erosites_db(lufs, csucs) == hangossag.MAX_EMELES_DB and not math.isnan(lufs)


def test_leallitas_megoli_a_futo_merest(tmp_path, monkeypatch):
    ke = Kiegyenlito(tar=Tar(tmp_path / "tar.json"))

    class Folyamat:
        megolve = False

        def kill(self):
            Folyamat.megolve = True

    ke._folyamat_jelol(Folyamat())
    ke.leallit()
    assert Folyamat.megolve and ke._leallitva
    ke.kell(tmp_path / "a.mp3", elore=True)
    assert ke.varakozik() == 0


def test_parancs_alacsony_prioritassal(tmp_path):
    parancs, opciok = hangossag._parancs("/bin/ffmpeg", tmp_path / "-furcsa.mp3")
    i = parancs.index("-i")
    assert parancs[i + 1] == str(tmp_path / "-furcsa.mp3")
    if hangossag.sys.platform != "win32" and hangossag.shutil.which("nice"):
        assert parancs[:3][1:] == ["-n", "15"] and "preexec_fn" not in opciok
