__lazy_modules__ = ["kozgaz_fm.beallitasok", "kozgaz_fm.hang"]

from kozgaz_fm.beallitasok import BEEPITETT_HANGOK
from kozgaz_fm.hang import fajl_lista, hang_nev, hang_ut, mappa_szamai


def test_beepitett_hangok_leteznek():
    for nev in BEEPITETT_HANGOK:
        ut = hang_ut(f"beepitett:{nev}")
        assert ut is not None and ut.suffix == ".mp3" and ut.stat().st_size > 10_000
        assert ut.read_bytes()[:3] in (b"ID3", b"\xff\xfb", b"\xff\xf3")


def test_hang_nev(tmp_path):
    assert hang_nev("beepitett:jelzo") == "Jelzőcsengő"
    assert hang_nev("beepitett:gong") == "Jelzőcsengő"
    assert hang_ut("beepitett:csengo") == hang_ut("beepitett:becsengo")
    assert hang_ut("beepitett:nincs") is None
    assert hang_ut(str(tmp_path / "nincs.mp3")) is None


def test_mappa_es_lista(tmp_path):
    (tmp_path / "al").mkdir()
    for nev in ("b.mp3", "al/a.ogg", "kep.jpg"):
        (tmp_path / nev).write_bytes(b"x")
    assert [s.cim for s in mappa_szamai(tmp_path)] == ["a", "b"]
    lista = tmp_path / "lista.m3u"
    lista.write_text("#EXTM3U\nb.mp3\nal/a.ogg\nnincs.mp3\n", encoding="utf-8")
    assert [s.cim for s in fajl_lista(f"{lista}\n{tmp_path / 'b.mp3'}")] == ["b", "a", "b"]


def test_regi_hangok_atirasa(tmp_path):
    import json

    from kozgaz_fm.beallitasok import Beallitasok
    ut = tmp_path / "beallitasok.json"
    ut.write_text(json.dumps({"hang_becsengo": "beepitett:csengo", "hang_kicsengo": "beepitett:csengo",
                              "hang_jelzo": "beepitett:rovid", "hang_gong": "beepitett:gong",
                              "hang_riasztas": "beepitett:riasztas"}), encoding="utf-8")
    b = Beallitasok.betoltes(ut)
    assert (b.hang_becsengo, b.hang_kicsengo, b.hang_jelzo, b.hang_gong, b.hang_riasztas) == (
        "beepitett:becsengo", "beepitett:kicsengo", "beepitett:jelzo", "beepitett:jelzo", "beepitett:kicsengo")
