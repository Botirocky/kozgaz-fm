import wave

from kozgaz_fm.beallitasok import BEEPITETT_HANGOK
from kozgaz_fm.hang import fajl_lista, hang_nev, hang_ut, mappa_szamai


def test_beepitett_hangok_leteznek():
    for nev in BEEPITETT_HANGOK:
        ut = hang_ut(f"beepitett:{nev}")
        assert ut is not None and ut.exists()
        with wave.open(str(ut)) as f:
            assert f.getnframes() > 0


def test_hang_nev(tmp_path):
    assert hang_nev("beepitett:gong") == "Gong"
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
