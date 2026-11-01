__lazy_modules__ = ["datetime", "json", "pathlib", "pytest", "PySide6.QtCore", "kozgaz_fm.beallitasok",
                    "kozgaz_fm.hang", "kozgaz_fm.tartalek", "kozgaz_fm.vezerlo", "kozgaz_fm.webpanel",
                    "kozgaz_fm.zenekeres"]

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication

from kozgaz_fm.beallitasok import Beallitasok, TiltottSzam, TiltottTelefon, ZeneForras, alapertelmezett
from kozgaz_fm.hang import Szam, ZeneLejatszo
from kozgaz_fm.tartalek import szinkron_adat, szinkron_alkalmaz
from kozgaz_fm.vezerlo import Vezerlo
from kozgaz_fm.webpanel import ESZKOZ_SUTI, Panel, WebMuveletek
from kozgaz_fm.zenekeres import TELEFON_TILTAS_NAP, Keresek, KeresHiba, telefon_kulcs

CSRF = {"x-kozgaz-fm": "1", "host": "panel.local:8080"}


@pytest.fixture(scope="module", autouse=True)
def app():
    return QCoreApplication.instance() or QCoreApplication([])


class Modvezerlo:
    _tiltas_frissit = Vezerlo._tiltas_frissit
    telefon_tiltott = Vezerlo.telefon_tiltott
    _szam_tiltas = Vezerlo._szam_tiltas
    most_szolo_tiltasa = Vezerlo.most_szolo_tiltasa
    zenekeres_szam_tiltas = Vezerlo.zenekeres_szam_tiltas
    szam_feloldas = Vezerlo.szam_feloldas
    zenekeres_levesz = Vezerlo.zenekeres_levesz
    zenekeres_telefon_tiltas = Vezerlo.zenekeres_telefon_tiltas
    telefon_feloldas = Vezerlo.telefon_feloldas

    class _Jel:
        def emit(self) -> None:
            pass

    def __init__(self) -> None:
        self.b = alapertelmezett()
        self.keresek = Keresek()
        self.zene = ZeneLejatszo()
        self.zene.forras = ZeneForras("mappa", "Teszt", "x")
        self.zene._jatszd = lambda index: setattr(self.zene, "index", index % max(len(self.zene.szamok), 1))
        self.zene.megallit = lambda elhalkitas=True: setattr(self.zene, "_szol", False)
        self.keresek_valtoztak = self._Jel()
        self.naplo: list[str] = []
        self.mentesek = 0

    def log(self, szoveg: str) -> None:
        self.naplo.append(szoveg)

    def mentes(self) -> None:
        self.mentesek += 1


@pytest.fixture
def v() -> Modvezerlo:
    return Modvezerlo()


def _kert(v: Modvezerlo, yt: str, cim: str = "", eszkoz: str = "telefon-1") -> str:
    k = v.keresek.uj(f"kérés {yt}", "10.B", eszkoz, "10.0.0.5", 5, [])
    v.keresek.talalat(k.azon, yt, cim or f"Előadó - {yt}", 200, 7, [])
    v.keresek.dont(k.azon, True)
    v.zene.szamok.append(Szam(k.cim, yt=yt, kert=True))
    return k.azon


def test_most_szolo_tiltasa_tovabblep_es_megmarad(v):
    v.zene.szamok = [Szam("Rossz - Szám", yt="r"), Szam("Jó - Szám", yt="j")]
    v.zene._szol = True
    v.most_szolo_tiltasa("teszt")
    assert [s.yt for s in v.zene.szamok] == ["j"]
    assert [(t.cim, t.yt) for t in v.b.tiltott_szamok] == [("Rossz - Szám", "r")]
    assert v.mentesek == 1 and "teszt" in v.naplo[-1]


def test_most_szolo_tiltasa_ha_nem_szol_zene(v):
    v.zene.szamok = [Szam("a")]
    with pytest.raises(KeresHiba) as hiba:
        v.most_szolo_tiltasa()
    assert hiba.value.kod == "conflict" and not v.b.tiltott_szamok


def test_tiltas_cim_alapjan_mas_feltoltest_is_kiszur(v):
    v.zene.szamok = [Szam("Előadó - Dal (Official Video)", yt="a"), Szam("Előadó - Dal [HD]", yt="b"),
                     Szam("Más - Dal", yt="c")]
    v.zene.index = 2
    v._szam_tiltas("Előadó - Dal (Official Video)", "a", "")
    assert [s.yt for s in v.zene.szamok] == ["c"] and v.zene.index == 0


def test_tiltott_szam_nem_toltodik_be_ujra(v):
    v._szam_tiltas("Előadó - Dal", "a", "")
    maradt, kiszurt = v.zene._szurt([Szam("Előadó - Dal", yt="a"), Szam("Előadó - Másik", yt="b")])
    assert [s.yt for s in maradt] == ["b"] and kiszurt == 1


def test_tiltott_szam_nem_kerheto(v):
    k = v.keresek.uj("x", "", "e", "ip", 3, [])
    v.keresek.talalat(k.azon, "yt", "Cím", 100, 7, [], tiltott_szam=True)
    assert k.allapot == "elutasitva" and "letiltotta" in k.ok


def test_feloldas_utan_ujra_mehet(v):
    v._szam_tiltas("Előadó - Dal", "a", "")
    assert v.zene.tiltott_e("a", "Előadó - Dal")
    v.szam_feloldas(v.b.tiltott_szamok[0].azon)
    assert not v.zene.tiltott_e("a", "Előadó - Dal") and not v.b.tiltott_szamok
    with pytest.raises(KeresHiba):
        v.szam_feloldas("nincs")


def test_ures_kulcs_nem_tilt_mindent(v):
    v._szam_tiltas("!!!", "", "")
    assert not v.zene.tiltott_e("", "Bármi - Más") and not v.zene.tiltott_e("", "???")


def test_levetel_kiveszi_a_sorbol_es_nem_kerheto_ujra(v):
    v.zene.szamok = [Szam("alap", yt="base")]
    azon = _kert(v, "kert")
    v.zenekeres_levesz(azon, "teszt")
    assert [s.yt for s in v.zene.szamok] == ["base"]
    assert v.keresek.keres(azon).allapot == "levett"
    with pytest.raises(KeresHiba):
        v.zenekeres_levesz(azon)
    ujra = v.keresek.uj("újra", "", "e2", "ip2", 3, [])
    v.keresek.talalat(ujra.azon, "kert", "Előadó - kert", 200, 7, [])
    assert ujra.allapot == "elutasitva" and "levették" in ujra.ok


def test_levetel_a_most_szolot_is_tovabblepteti(v):
    v.zene.szamok = [Szam("alap", yt="base")]
    azon = _kert(v, "kert")
    v.zene.index = 1
    v.zene._szol = True
    v.zene.szamok[1].kert = False
    v.keresek.szol("kert")
    assert v.keresek.keres(azon).allapot == "szol"
    v.zenekeres_levesz(azon)
    assert [s.yt for s in v.zene.szamok] == ["base"] and v.zene.index == 0
    assert v.keresek.keres(azon).allapot == "levett"


def test_levetel_fuggo_kertet_is_torli(v):
    v.zene._fuggo_kert = [Szam("f", yt="kert", kert=True)]
    azon = _kert(v, "kert")
    v.zene.szamok.clear()
    v.zenekeres_levesz(azon)
    assert v.zene._fuggo_kert == []


def test_levetel_nem_adja_vissza_a_keretet(v):
    azon = _kert(v, "kert")
    assert v.keresek.mai_szam("telefon-1") == 1
    v.zenekeres_levesz(azon)
    assert v.keresek.mai_szam("telefon-1") == 1


def test_telefon_tiltas_torli_a_fuggoket_es_tilt(v):
    v.zene.szamok = [Szam("alap", yt="base")]
    a = _kert(v, "a")
    fuggo = v.keresek.uj("b", "", "telefon-1", "ip", 5, [])
    masik = _kert(v, "m", eszkoz="telefon-2")
    v.zenekeres_telefon_tiltas(a, "teszt")
    assert v.keresek.keres(a).allapot == "levett" and fuggo.allapot == "elutasitva"
    assert v.keresek.keres(masik).allapot == "elfogadva"
    assert sorted(s.yt for s in v.zene.szamok) == ["base", "m"]
    assert v.telefon_tiltott("telefon-1") and not v.telefon_tiltott("telefon-2")
    t = v.b.tiltott_telefonok[0]
    assert t.ig == (date.today() + timedelta(days=TELEFON_TILTAS_NAP)).isoformat()


def test_telefon_nyers_azonositoja_nem_tarolodik(v):
    a = _kert(v, "a", eszkoz="titkos-suti-ertek")
    v.zenekeres_telefon_tiltas(a)
    assert v.b.tiltott_telefonok[0].kulcs == telefon_kulcs("titkos-suti-ertek")
    assert "titkos-suti-ertek" not in json.dumps(v.keresek.keres(a).admin())


def test_telefon_tiltas_lejar_es_feloldhato(v):
    v.b.tiltott_telefonok = [TiltottTelefon(telefon_kulcs("regi"), "", (date.today() - timedelta(days=1)).isoformat()),
                             TiltottTelefon(telefon_kulcs("uj"), "", date.today().isoformat())]
    assert not v.telefon_tiltott("regi") and v.telefon_tiltott("uj")
    v.telefon_feloldas(telefon_kulcs("uj"))
    assert not v.telefon_tiltott("uj")
    with pytest.raises(KeresHiba):
        v.telefon_feloldas("nincs")


def test_tiltott_telefon_nem_kerhet(monkeypatch):
    v = Modvezerlo()
    v.b.zenekeres = True
    v.b.tiltott_telefonok = [TiltottTelefon(telefon_kulcs("e"), "", date.today().isoformat())]
    with pytest.raises(KeresHiba) as hiba:
        Vezerlo.zenekeres_uj(v, "szám", "", "e", "ip")
    assert hiba.value.kod == "device_blocked"
    assert v.keresek.lista == []


def test_szam_tiltas_keres_nelkuli_azonositoval(v):
    k = v.keresek.uj("x", "", "e", "ip", 3, [])
    with pytest.raises(KeresHiba) as hiba:
        v.zenekeres_szam_tiltas(k.azon)
    assert hiba.value.kod == "conflict"


def test_beallitasok_mentese_es_betoltese(tmp_path: Path):
    b = alapertelmezett()
    b.tiltott_szamok = [TiltottSzam("a1", "Előadó - Dal", "yt", "2026-11-01")]
    b.tiltott_telefonok = [TiltottTelefon("k1", "10.B", "2026-11-08")]
    ut = tmp_path / "b.json"
    b.mentes(ut)
    uj = Beallitasok.betoltes(ut)
    assert uj.tiltott_szamok == b.tiltott_szamok and uj.tiltott_telefonok == b.tiltott_telefonok


def test_tartalek_a_szamtiltast_atveszi_a_telefont_nem():
    fo = alapertelmezett()
    fo.tiltott_szamok = [TiltottSzam("a1", "Előadó - Dal", "yt", "2026-11-01")]
    fo.tiltott_telefonok = [TiltottTelefon("k1")]
    tartalek = alapertelmezett()
    assert "tiltott_szamok" in szinkron_alkalmaz(tartalek, szinkron_adat(fo))
    assert tartalek.tiltott_szamok == fo.tiltott_szamok and tartalek.tiltott_telefonok == []


class ApiMuveletek:
    zenekeres_levetel = WebMuveletek.zenekeres_levetel
    zenekeres_szam_tiltas = WebMuveletek.zenekeres_szam_tiltas
    zenekeres_telefon_tiltas = WebMuveletek.zenekeres_telefon_tiltas
    zenekeres_telefon_feloldas = WebMuveletek.zenekeres_telefon_feloldas
    zene_tiltas = WebMuveletek.zene_tiltas
    zene_tiltas_feloldas = WebMuveletek.zene_tiltas_feloldas
    _szoveg_mezo = staticmethod(WebMuveletek._szoveg_mezo)

    def __init__(self, v) -> None:
        self.v = v

    def vegrehajt(self, feladat):
        return feladat()

    def allapot(self) -> dict:
        return {"rendben": True}


@pytest.fixture
def api(v):
    p = Panel(ApiMuveletek(v), lambda: "jelszo")
    token = p.munkamenetek.uj()
    return p, {**CSRF, "cookie": f"kfm_munkamenet={token}"}


@pytest.mark.parametrize(("metodus", "ut"), [
    ("POST", "/api/v1/zene/tiltas"),
    ("DELETE", "/api/v1/zene/tiltas"),
    ("POST", "/api/v1/zenekeres/levetel"),
    ("POST", "/api/v1/zenekeres/szam-tiltas"),
    ("POST", "/api/v1/zenekeres/telefon-tiltas"),
    ("DELETE", "/api/v1/zenekeres/telefon-tiltas"),
])
def test_moderalas_bejelentkezes_nelkul_tilos(api, metodus, ut):
    p, _ = api
    assert p.kezel(metodus, ut, CSRF, b"{}", "ip").statusz == 401


def test_publikus_suti_nem_elegendo(api):
    p, _ = api
    fejlec = {**CSRF, "cookie": f"{ESZKOZ_SUTI}=" + "a" * 24}
    assert p.kezel("POST", "/api/v1/zene/tiltas", fejlec, b"{}", "ip").statusz == 401


def test_api_szam_tiltas_es_hibak(api, v):
    p, f = api
    v.zene.szamok = [Szam("Rossz - Szám", yt="r"), Szam("Jó - Szám", yt="j")]
    v.zene._szol = True
    assert p.kezel("POST", "/api/v1/zene/tiltas", f, b"{}", "1.2.3.4").statusz == 200
    assert "webpanel, 1.2.3.4" in v.naplo[-1]
    azon = v.b.tiltott_szamok[0].azon
    assert p.kezel("DELETE", "/api/v1/zene/tiltas", f, json.dumps({"azon": azon}).encode(), "ip").statusz == 200
    assert p.kezel("DELETE", "/api/v1/zene/tiltas", f, b"{}", "ip").statusz == 422
    assert p.kezel("DELETE", "/api/v1/zene/tiltas", f, b'{"azon": "nincs"}', "ip").statusz == 404
    assert p.kezel("POST", "/api/v1/zenekeres/levetel", f, b'{"azon": 5}', "ip").statusz == 422
