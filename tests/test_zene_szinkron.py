import json
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from kozgaz_fm import zene_szinkron
from kozgaz_fm.zenekeres_szerver import SzerverHiba

KULCS = "k" * 32


@pytest.fixture
def szerver(tmp_path):
    gyoker = tmp_path / "szerver"
    gyoker.mkdir()
    kerelmek = []

    class Kezelo(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            kerelmek.append(self.path)
            if self.headers.get("X-Kozgaz-FM-Kulcs") != KULCS:
                self.send_response(401)
                self.end_headers()
                return
            ut = urllib.parse.urlsplit(self.path)
            if ut.path == "/api/zenek":
                lista = [{"ut": f.relative_to(gyoker).as_posix(), "meret": f.stat().st_size,
                          "ido": int(f.stat().st_mtime)}
                         for f in sorted(gyoker.rglob("*")) if f.is_file()]
                test = json.dumps({"data": lista + [{"ut": "../kilog.mp3", "meret": 1, "ido": 1}]}).encode()
            elif ut.path == "/api/zenek/fajl":
                nev = urllib.parse.parse_qs(ut.query)["ut"][0]
                test = (gyoker / nev).read_bytes()
                tartomany = self.headers.get("Range", "")
                if tartomany.startswith("bytes="):
                    kezdet = int(tartomany[6:].rstrip("-"))
                    test = test[kezdet:]
                    self.send_response(206)
                    self.send_header("Content-Length", str(len(test)))
                    self.end_headers()
                    self.wfile.write(test)
                    return
            else:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Length", str(len(test)))
            self.end_headers()
            self.wfile.write(test)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Kezelo)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}", gyoker, kerelmek
    httpd.shutdown()


def test_biztonsagos_ut():
    assert zene_szinkron.biztonsagos_ut("Album/Dal.mp3") is not None
    for rossz in ("", "../x.mp3", "/etc/passwd", "a/../../x", ".rejtett.mp3", "a\\b.mp3", "a/./b.mp3"):
        assert zene_szinkron.biztonsagos_ut(rossz) is None


def test_szinkron_letolt_kihagy_torol(szerver, tmp_path):
    cim, gyoker, kerelmek = szerver
    (gyoker / "Mappa").mkdir()
    (gyoker / "Egy – dal.mp3").write_bytes(b"a" * 1000)
    (gyoker / "Mappa" / "Kettő.mp3").write_bytes(b"b" * 3000)
    helyi = tmp_path / "helyi"
    sajat = helyi / "sajat.mp3"
    helyi.mkdir()
    sajat.write_bytes(b"sajat")

    e = zene_szinkron.szinkron(cim, KULCS, helyi)
    assert (e.osszes, e.uj, e.torolt, e.hibas) == (2, 2, 0, 0)
    assert (helyi / "Egy – dal.mp3").read_bytes() == b"a" * 1000
    assert (helyi / "Mappa" / "Kettő.mp3").read_bytes() == b"b" * 3000
    assert not (tmp_path / "kilog.mp3").exists()

    kerelmek.clear()
    e = zene_szinkron.szinkron(cim, KULCS, helyi)
    assert (e.uj, e.torolt) == (0, 0)
    assert all("/fajl" not in k for k in kerelmek)

    (gyoker / "Mappa" / "Kettő.mp3").unlink()
    (gyoker / "Mappa").rmdir()
    e = zene_szinkron.szinkron(cim, KULCS, helyi)
    assert e.torolt == 1
    assert not (helyi / "Mappa").exists()
    assert sajat.read_bytes() == b"sajat"


def test_felbeszakadt_letoltes_ujrakezd(szerver, tmp_path):
    cim, gyoker, _ = szerver
    (gyoker / "Dal.mp3").write_bytes(b"x" * 5000)
    helyi = tmp_path / "helyi"
    helyi.mkdir()
    (helyi / "Dal.mp3.resz").write_bytes(b"x" * 6000)
    e = zene_szinkron.szinkron(cim, KULCS, helyi)
    assert e.uj == 1
    assert (helyi / "Dal.mp3").read_bytes() == b"x" * 5000
    assert not (helyi / "Dal.mp3.resz").exists()


def test_folytatja_a_reszt(szerver, tmp_path):
    cim, gyoker, _ = szerver
    tartalom = bytes(range(256)) * 40
    (gyoker / "Dal.mp3").write_bytes(tartalom)
    helyi = tmp_path / "helyi"
    helyi.mkdir()
    (helyi / "Dal.mp3.resz").write_bytes(tartalom[:4000])
    e = zene_szinkron.szinkron(cim, KULCS, helyi)
    assert e.uj == 1 and e.bajt == len(tartalom) - 4000
    assert (helyi / "Dal.mp3").read_bytes() == tartalom


def test_megszakitas_nem_torol(szerver, tmp_path):
    cim, gyoker, _ = szerver
    (gyoker / "A.mp3").write_bytes(b"a")
    helyi = tmp_path / "helyi"
    zene_szinkron.szinkron(cim, KULCS, helyi)
    (gyoker / "A.mp3").unlink()
    (gyoker / "B.mp3").write_bytes(b"b")
    e = zene_szinkron.szinkron(cim, KULCS, helyi, megszakit=lambda: True)
    assert (e.uj, e.torolt) == (0, 0)
    assert (helyi / "A.mp3").exists()


def test_rossz_kulcs(szerver, tmp_path):
    cim, _, _ = szerver
    with pytest.raises(SzerverHiba, match="kulcs"):
        zene_szinkron.szinkron(cim, "rossz", tmp_path / "helyi")


def test_ures_szerverlista_nem_torol(szerver, tmp_path):
    cim, gyoker, _ = szerver
    (gyoker / "A.mp3").write_bytes(b"a")
    helyi = tmp_path / "helyi"
    zene_szinkron.szinkron(cim, KULCS, helyi)
    (gyoker / "A.mp3").unlink()
    with pytest.raises(SzerverHiba, match="üres"):
        zene_szinkron.szinkron(cim, KULCS, helyi)
    assert (helyi / "A.mp3").exists()
