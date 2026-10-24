__lazy_modules__ = ["json", "datetime", "pytest", "kozgaz_fm.beallitasok", "kozgaz_fm.orarend", "kozgaz_fm.tartalek",
                    "kozgaz_fm.vezerlo", "kozgaz_fm.webpanel"]

import json
from datetime import datetime, timedelta

import pytest

from kozgaz_fm.beallitasok import Rendkivuli, Szunnap, alapertelmezett
from kozgaz_fm.orarend import Esemeny, Tipus
from kozgaz_fm.tartalek import (
    KIESES_HATAR,
    SZINKRON_MEZOK,
    VISSZA_HATAR,
    Allapotgep,
    TartalekHiba,
    cim_normalizal,
    szinkron_adat,
    szinkron_alkalmaz,
)
from kozgaz_fm.vezerlo import Vezerlo
from kozgaz_fm.webpanel import Panel

KULCS = "titkos-tartalek-kulcs-1234567890"


@pytest.mark.parametrize(("cim", "vart"), [
    ("192.168.1.20", "http://192.168.1.20:8080"),
    ("192.168.1.20:9000/", "http://192.168.1.20:9000"),
    ("http://csengo-gep.local:8080", "http://csengo-gep.local:8080"),
    ("  ", ""),
])
def test_cim_normalizal(cim, vart):
    assert cim_normalizal(cim) == vart


@pytest.mark.parametrize("cim", ["ftp://gep", "http://gep:99999", "http://gep/utvonal", "http://a@gep", "http://"])
def test_hibas_cim(cim):
    with pytest.raises(TartalekHiba):
        cim_normalizal(cim)


def test_atvetel_csak_tobb_kieses_utan_es_visszaadas():
    a = Allapotgep()
    most = datetime(2026, 10, 26, 10, 0)
    assert a.siker(most) is None and a.el
    for _ in range(KIESES_HATAR - 1):
        assert a.kudarc("nem érhető el") is None
    assert not a.atvett
    assert a.kudarc("nem érhető el") == "atvetel" and a.atvett and a.el is False
    assert a.kudarc("nem érhető el") is None
    for _ in range(VISSZA_HATAR - 1):
        assert a.siker(most) is None
    assert a.atvett
    assert a.siker(most) == "visszaadas" and not a.atvett


def test_egy_kieses_kozben_siker_nullaz():
    a = Allapotgep()
    a.kudarc("x")
    a.kudarc("x")
    a.siker(datetime.now())
    a.kudarc("x")
    assert not a.atvett


def test_szinkron_oda_vissza():
    fo = alapertelmezett()
    fo.szunnapok.append(Szunnap("2026-10-23", "2026-11-01", "Őszi szünet"))
    fo.rendkivuli.append(Rendkivuli("Tűzriadó", "2026-11-04", "10:05", tipus="riado"))
    fo.kivetelek["2026-11-05"] = "Rövidített"
    fo.forrasok = []
    fo.web_jelszo = "titok"
    adat = json.loads(json.dumps(szinkron_adat(fo)))
    assert set(adat) == set(SZINKRON_MEZOK)
    assert "web_jelszo" not in adat and "tartalek_kulcs" not in adat and "forrasok" not in adat
    tartalek = alapertelmezett()
    valtozott = szinkron_alkalmaz(tartalek, adat)
    assert set(valtozott) == {"szunnapok", "rendkivuli", "kivetelek"}
    assert tartalek.rendkivuli == fo.rendkivuli and tartalek.szunnapok == fo.szunnapok
    assert szinkron_alkalmaz(tartalek, adat) == []


def test_szinkron_hibas_adatot_elutasit():
    with pytest.raises(TypeError):
        szinkron_alkalmaz(alapertelmezett(), {"jelzo_perc": "sok"})


class AlMuveletek:
    def vegrehajt(self, feladat):
        return feladat()

    def tartalek_eletjel(self, adat, ip):
        return {"szerep": "fo"}


@pytest.mark.parametrize(("tarolt", "kapott", "statusz"), [
    (KULCS, KULCS, 200),
    (KULCS, "rossz", 401),
    (KULCS, "", 401),
    ("", "", 404),
    ("", KULCS, 404),
])
def test_eletjel_kulccsal(tarolt, kapott, statusz):
    panel = Panel(AlMuveletek(), lambda: "", kulcs=lambda: tarolt)
    fejlecek = {"x-kozgaz-fm-kulcs": kapott} if kapott else {}
    valasz = panel.kezel("GET", "/api/v1/tartalek/eletjel", fejlecek, b"", "10.0.0.7")
    assert valasz.statusz == statusz
    if statusz == 200:
        assert json.loads(valasz.torzs) == {"data": {"szerep": "fo"}}


class AlTartalek:
    def __init__(self, passziv: bool) -> None:
        self.passziv = passziv


class AlVezerlo:
    _kezel = Vezerlo._kezel
    _atvetel = Vezerlo._atvetel

    def __init__(self) -> None:
        self.b = alapertelmezett()
        self.tartalek = AlTartalek(True)
        self.riasztas = False
        self._kihagyott = None
        self.csengetesek: list[str] = []
        self.naplo: list[str] = []
        self.zene = type("Zene", (), {"szol": False})()
        self.frissult = type("Jel", (), {"emit": staticmethod(lambda: None)})()

    def log(self, szoveg: str) -> None:
        self.naplo.append(szoveg)

    def _jelez(self, szoveg: str, szint: str = "info") -> None:
        self.naplo.append(szoveg)

    def _szinkron(self) -> None:
        pass

    def csengetes(self, hang: str, leiras: str = "", hangero=None) -> None:
        self.csengetesek.append(leiras)


def test_passziv_tartalek_nem_csenget_de_atvetelkor_potol():
    v = AlVezerlo()
    e = Esemeny(datetime.now() - timedelta(seconds=20), Tipus.BECSENGO, 3)
    v._kezel(e)
    assert v.csengetesek == [] and v._kihagyott is e
    v.tartalek.passziv = False
    v._atvetel()
    assert v.csengetesek == ["3. óra – becsengő"]
    assert any("átvette" in s for s in v.naplo)


def test_regi_kimaradt_csengo_nem_szol_atvetelkor():
    v = AlVezerlo()
    v._kezel(Esemeny(datetime.now() - timedelta(minutes=5), Tipus.KICSENGO, 2))
    v.tartalek.passziv = False
    v._atvetel()
    assert v.csengetesek == []
