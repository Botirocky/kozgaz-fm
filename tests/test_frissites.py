import hashlib
import io
from datetime import datetime, timedelta

import pytest

from kozgaz_fm import frissites
from kozgaz_fm.frissites import FrissitesHiba, Kiadas


def kiadas(verzio="9.9.0", **eszkozok) -> Kiadas:
    alap = {"SHA256SUMS.txt": "https://x/SHA256SUMS.txt"}
    alap.update(eszkozok)
    return Kiadas(verzio, f"v{verzio}", "", "https://x", alap)


def test_verzio_kulcs():
    assert frissites.verzio_kulcs("0.10.0") > frissites.verzio_kulcs("0.9.9")
    assert frissites.verzio_kulcs("v1.2.3-beta") == (1, 2, 3)
    assert kiadas("9.9.0").uj and not kiadas("0.0.1").uj


def test_csomag_neve():
    k = kiadas(**{"KozgazFM-9.9.0-telepito.exe": "u1", "KozgazFM-9.9.0-linux-x86_64.tar.gz": "u2",
                  "kozgaz_fm-9.9.0-py3-none-any.whl": "u3"})
    assert frissites.csomag_neve(k, "windows") == "KozgazFM-9.9.0-telepito.exe"
    assert frissites.csomag_neve(k, "venv") == "kozgaz_fm-9.9.0-py3-none-any.whl"
    assert frissites.csomag_neve(k, "fejlesztoi") is None


def test_fejlesztoi_mod():
    assert frissites.telepitesi_mod() == "fejlesztoi"
    with pytest.raises(FrissitesHiba):
        frissites.telepit(__import__("pathlib").Path("x"), "fejlesztoi")


def test_biztonsagos_ido():
    most = datetime(2026, 10, 22, 16, 0)
    assert frissites.biztonsagos_ido("tanítás után", most + timedelta(hours=15), most, False, False)
    assert not frissites.biztonsagos_ido("óra", None, most, False, False)
    assert not frissites.biztonsagos_ido("szünnap", None, most, True, False)
    assert not frissites.biztonsagos_ido("tanítás után", most + timedelta(minutes=20), most, False, False)


class _Valasz(io.BytesIO):
    headers = {"Content-Length": "0"}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_letoltes_ellenorzi_az_osszeget(tmp_path, monkeypatch):
    monkeypatch.setenv("KOZGAZ_FM_ADAT", str(tmp_path))
    tartalom = b"csomag"
    jo = hashlib.sha256(tartalom).hexdigest()
    k = kiadas(**{"a.whl": "https://x/a.whl"})
    monkeypatch.setattr(frissites, "_get", lambda url: f"{jo}  a.whl\n".encode())
    monkeypatch.setattr(frissites.urllib.request, "urlopen", lambda *a, **kw: _Valasz(tartalom))
    ut = frissites.letoltes(k, "a.whl")
    assert ut.read_bytes() == tartalom
    monkeypatch.setattr(frissites, "_get", lambda url: f"{'0' * 64}  a.whl\n".encode())
    ut.unlink()
    with pytest.raises(FrissitesHiba):
        frissites.letoltes(k, "a.whl")
    assert not list((tmp_path / "gyorsitotar" / "frissites").glob("*.resz"))
