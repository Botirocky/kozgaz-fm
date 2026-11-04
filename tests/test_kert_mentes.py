import shutil
import subprocess

import pytest

from kozgaz_fm import kert_mentes


def test_fajlnev_tiszta():
    assert kert_mentes.fajlnev('AC/DC: "Back" in Black?') == "ACDC Back in Black.mp3"
    assert kert_mentes.fajlnev("   ") == "Kért szám.mp3"


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="nincs ffmpeg")
def test_mentes_mp3(tmp_path, monkeypatch):
    forras = tmp_path / "forras.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", str(forras)],
                   check=True)
    monkeypatch.setattr(kert_mentes.youtube, "letoltes", lambda yt, mappa: forras)
    cel = tmp_path / "ki"
    ut = kert_mentes.mentes("abcdefghijk", "Próba – Dal", cel)
    assert ut == cel / "Próba – Dal.mp3" and ut.stat().st_size > 1000
    assert kert_mentes.mentes("abcdefghijk", "Próba – Dal", cel) is None
