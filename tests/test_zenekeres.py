__lazy_modules__ = [
    "json",
    "datetime",
    "pytest",
    "PySide6.QtMultimedia",
    "kozgaz_fm.hang",
    "kozgaz_fm.webpanel",
    "kozgaz_fm.zenekeres",
]

import json
from datetime import datetime, timedelta

import pytest
from PySide6.QtMultimedia import QMediaPlayer

from kozgaz_fm.hang import Szam, ZeneLejatszo
from kozgaz_fm.webpanel import ESZKOZ_SUTI, Panel
from kozgaz_fm.zenekeres import IP_ORANKENT, MAX_VARAKOZO, Keresek, KeresHiba, tiltott_e, youtube_cel

CSRF = {"x-kozgaz-fm": "1", "host": "panel.local:8080"}


class Ora:
    def __init__(self) -> None:
        self.most = datetime(2026, 10, 26, 10, 0)

    def __call__(self) -> datetime:
        return self.most


@pytest.fixture
def ora() -> Ora:
    return Ora()


@pytest.fixture
def k(ora: Ora) -> Keresek:
    return Keresek(ora)


@pytest.mark.parametrize(("szoveg", "vart"), [
    ("Queen Don't Stop Me Now", "ytsearch1:Queen Don't Stop Me Now"),
    ("https://www.youtube.com/watch?v=abc", "https://www.youtube.com/watch?v=abc"),
    ("youtu.be/abc", "https://youtu.be/abc"),
    ("music.youtube.com/watch?v=abc", "https://music.youtube.com/watch?v=abc"),
])
def test_youtube_cel(szoveg, vart):
    assert youtube_cel(szoveg) == vart


@pytest.mark.parametrize("szoveg", [
    "https://evil.example/watch?v=abc",
    "http://youtube.com.evil.example/x",
    "youtube.com.evil.example/x",
    "file:///etc/passwd",
    "ftp://youtube.com/x",
    "https://youtube.com@evil.example/",
])
def test_csak_youtube_link(szoveg):
    with pytest.raises(KeresHiba):
        youtube_cel(szoveg)


def test_tiltott_kis_nagybetu_fuggetlen():
    assert tiltott_e("Valami CSÚNYA cím", ["csúnya"])
    assert not tiltott_e("Rendes cím", ["", "  ", "csúnya"])


def test_uj_keres_es_talalat(k):
    keres = k.uj("  Queen   Bohemian  ", "10.B", "eszkoz-1", "10.0.0.5", 3, [])
    assert keres.szoveg == "Queen Bohemian" and keres.allapot == "kereses"
    k.talalat(keres.azon, "yt1", "Queen – Bohemian Rhapsody", 360, 7, [])
    assert keres.allapot == "varakozik"
    assert [x.azon for x in k.fuggo()] == [keres.azon]
    k.dont(keres.azon, True)
    assert keres.allapot == "elfogadva" and k.fuggo() == []
    with pytest.raises(KeresHiba):
        k.dont(keres.azon, False)
    assert k.szol("yt1") is keres and keres.allapot == "szol"


@pytest.mark.parametrize(("cim", "hossz", "ok"), [
    ("Csúnya dal", 200, "nem engedélyezett"),
    ("Hosszú mix", 3600, "Túl hosszú"),
    ("Élő adás", 0, "Élő adás"),
])
def test_talalat_automatikus_elutasitas(k, cim, hossz, ok):
    keres = k.uj("valami", "", "e", "ip", 3, [])
    k.talalat(keres.azon, "yt", cim, hossz, 7, ["csúnya"])
    assert keres.allapot == "elutasitva" and ok in keres.ok


def test_dupla_keres_elutasitva(k):
    elso = k.uj("a", "", "e1", "ip", 3, [])
    k.talalat(elso.azon, "yt", "Cím", 100, 7, [])
    masodik = k.uj("b", "", "e2", "ip", 3, [])
    k.talalat(masodik.azon, "yt", "Cím", 100, 7, [])
    assert masodik.allapot == "elutasitva" and "már kérték" in masodik.ok


def test_napi_korlat_eszkozonkent(k, ora):
    for _ in range(2):
        k.uj("szám", "", "e1", "ip", 2, [])
    with pytest.raises(KeresHiba) as hiba:
        k.uj("szám", "", "e1", "ip", 2, [])
    assert hiba.value.kod == "daily_limit"
    assert k.maradek("e1", 2) == 0 and k.maradek("e2", 2) == 2
    ora.most += timedelta(days=1)
    assert k.maradek("e1", 2) == 2


def test_ip_korlat(k, ora):
    for i in range(IP_ORANKENT):
        k.uj("szám", "", f"e{i}", "10.0.0.9", 3, [])
    with pytest.raises(KeresHiba) as hiba:
        k.uj("szám", "", "uj-eszkoz", "10.0.0.9", 3, [])
    assert hiba.value.kod == "rate_limited"
    ora.most += timedelta(hours=1, minutes=1)
    k.uj("szám", "", "uj-eszkoz", "10.0.0.9", 3, [])


def test_varakozo_sor_korlatos(k):
    for i in range(MAX_VARAKOZO):
        k.uj("szám", "", f"e{i}", f"ip{i}", 3, [])
    with pytest.raises(KeresHiba) as hiba:
        k.uj("szám", "", "masik", "masik-ip", 3, [])
    assert hiba.value.kod == "queue_full"


@pytest.mark.parametrize(("szoveg", "nev", "kod"), [
    ("", "", "validation_error"),
    ("x" * 151, "", "validation_error"),
    ("szám", "y" * 31, "validation_error"),
    ("csúnya szám", "", "forbidden_word"),
    ("szám", "csúnya név", "forbidden_word"),
    ("https://evil.example/", "", "bad_link"),
])
def test_hibas_keres(k, szoveg, nev, kod):
    with pytest.raises(KeresHiba) as hiba:
        k.uj(szoveg, nev, "e", "ip", 3, ["csúnya"])
    assert hiba.value.kod == kod


def test_regi_lezart_keresek_torlodnek(k, ora):
    regi = k.uj("régi", "", "e1", "ip", 3, [])
    k.nem_talalt(regi.azon, "nincs")
    fuggo = k.uj("függő", "", "e2", "ip", 3, [])
    ora.most += timedelta(hours=13)
    k.uj("új", "", "e3", "ip", 3, [])
    assert regi not in k.lista and fuggo in k.lista


def test_nyilvanos_adatban_nincs_ip_es_eszkoz(k):
    adat = k.uj("szám", "Béla", "titkos-eszkoz", "10.0.0.5", 3, []).nyilvanos()
    assert "10.0.0.5" not in json.dumps(adat) and "titkos-eszkoz" not in json.dumps(adat)


class AlLejatszo:
    beszur = ZeneLejatszo.beszur
    spotify_mod = False

    def __init__(self, cimek: list[str], index: int = 0, szol: bool = True) -> None:
        self.forras = object()
        self.szamok = [Szam(c) for c in cimek]
        self._fuggo_kert: list[Szam] = []
        self.index = index
        self._szol = szol
        allapot = QMediaPlayer.PlaybackState.PlayingState if szol else QMediaPlayer.PlaybackState.StoppedState
        self.lejatszo = type("L", (), {"playbackState": lambda _s: allapot})()
        self.lista_valtozott = type("J", (), {"emit": lambda _s: None})()

    def _elore_letolt(self) -> None:
        pass


def test_kert_szamok_sorban_a_kovetkezo_helyre():
    z = AlLejatszo(["a", "b", "c"], index=1)
    assert z.beszur(Szam("k1", yt="1"))
    assert z.beszur(Szam("k2", yt="2"))
    assert [s.cim for s in z.szamok] == ["a", "b", "k1", "k2", "c"]
    assert all(s.kert for s in z.szamok[2:4])


def test_megallitott_lejatszonal_a_kert_szam_jon_eloszor():
    z = AlLejatszo(["a", "b"], index=1, szol=False)
    z.beszur(Szam("k", yt="1"))
    assert [s.cim for s in z.szamok] == ["a", "k", "b"]


def test_betoltetlen_listanal_fuggoben_marad():
    z = AlLejatszo([])
    z.beszur(Szam("k", yt="1"))
    assert z.szamok == [] and [s.cim for s in z._fuggo_kert] == ["k"]


def test_spotify_mellett_nem_szurhato_be():
    z = AlLejatszo(["a"])
    z.spotify_mod = True
    assert not z.beszur(Szam("k", yt="1"))


class AlMuveletek:
    def __init__(self) -> None:
        self.hivasok: list[tuple[str, str]] = []

    def vegrehajt(self, feladat):
        return feladat()

    def zenekeres_allapot(self, adat: dict, ip: str, eszkoz: str) -> dict:
        self.hivasok.append(("allapot", eszkoz))
        return {"aktiv": True}

    def zenekeres_kuldes(self, adat: dict, ip: str, eszkoz: str) -> dict:
        self.hivasok.append(("kuldes", eszkoz))
        if adat.get("szoveg") == "sok":
            raise KeresHiba("daily_limit", "Ma már nem kérhetsz.")
        return {"aktiv": True}


@pytest.fixture
def panel() -> tuple[Panel, AlMuveletek]:
    m = AlMuveletek()
    return Panel(m, lambda: "nincs-jelszo"), m


def test_publikus_vegpont_belepes_nelkul_es_eszkoz_suti(panel):
    p, m = panel
    valasz = p.kezel("GET", "/api/v1/zenekeres", {}, b"", "10.0.0.5")
    assert valasz.statusz == 200
    suti = valasz.fejlecek["Set-Cookie"]
    assert suti.startswith(f"{ESZKOZ_SUTI}=") and "HttpOnly" in suti
    eszkoz = suti.split(";")[0].split("=", 1)[1]
    valasz = p.kezel("POST", "/api/v1/zenekeres", {**CSRF, "cookie": f"{ESZKOZ_SUTI}={eszkoz}"},
                     b'{"szoveg": "Queen"}', "10.0.0.5")
    assert valasz.statusz == 201 and "Set-Cookie" not in valasz.fejlecek
    assert m.hivasok == [("allapot", eszkoz), ("kuldes", eszkoz)]


def test_hamis_eszkoz_suti_helyett_uj(panel):
    p, m = panel
    valasz = p.kezel("GET", "/api/v1/zenekeres", {"cookie": f"{ESZKOZ_SUTI}=rovid"}, b"", "ip")
    assert "Set-Cookie" in valasz.fejlecek and m.hivasok[0][1] != "rovid"


def test_publikus_post_csrf_nelkul_403(panel):
    p, m = panel
    valasz = p.kezel("POST", "/api/v1/zenekeres", {"host": "panel.local:8080"}, b'{"szoveg": "x"}', "ip")
    assert valasz.statusz == 403 and m.hivasok == []


def test_publikus_hiba_kodja(panel):
    p, _ = panel
    valasz = p.kezel("POST", "/api/v1/zenekeres", CSRF, b'{"szoveg": "sok"}', "ip")
    assert valasz.statusz == 429 and json.loads(valasz.torzs)["error"]["code"] == "daily_limit"


def test_admin_dontes_belepest_ker(panel):
    p, _ = panel
    valasz = p.kezel("POST", "/api/v1/zenekeres/dontes", CSRF, b'{"azon": "x", "elfogad": true}', "ip")
    assert valasz.statusz == 401


def test_automatikus_elutasitas_nem_fogy_a_keretbol(k):
    keres = k.uj("szám", "", "e1", "ip", 1, [])
    k.talalat(keres.azon, "yt", "Hosszú", 3600, 7, [])
    assert k.maradek("e1", 1) == 1
    masik = k.uj("szám", "", "e1", "ip", 1, [])
    k.talalat(masik.azon, "yt2", "Jó", 100, 7, [])
    k.dont(masik.azon, False)
    assert k.maradek("e1", 1) == 0
