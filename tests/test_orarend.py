from datetime import date, datetime

import pytest

from kozgaz_fm.beallitasok import Beallitasok, Bemondas, Szunnap, alapertelmezett
from kozgaz_fm.orarend import (
    Szakasz,
    Tipus,
    allapot,
    kovetkezo_esemeny,
    napi_esemenyek,
    napi_rend,
    rend_generalas,
    zene_ablakban,
)
from kozgaz_fm.unnepek import husvet, unnepnapok

HETFO = date(2026, 10, 19)


@pytest.fixture
def b() -> Beallitasok:
    return alapertelmezett()


def dt(nap: date, ido: str) -> datetime:
    ora, perc = map(int, ido.split(":"))
    return datetime(nap.year, nap.month, nap.day, ora, perc)


def test_hetvegen_nincs_csengetes(b):
    assert napi_esemenyek(b, date(2026, 10, 24)) == []
    assert allapot(b, dt(date(2026, 10, 24), "10:00")).szakasz is Szakasz.NINCS


def test_hetkoznap_csengok(b):
    esemenyek = napi_esemenyek(b, HETFO)
    csengok = [e for e in esemenyek if e.tipus in (Tipus.BECSENGO, Tipus.KICSENGO, Tipus.JELZO)]
    assert len(csengok) == 8 * 3
    elso = esemenyek[0]
    assert elso.tipus is Tipus.JELZO and elso.ido == dt(HETFO, "07:58")


def test_zene_csak_hosszu_szunetben(b):
    b.zene_min_szunet = 11
    zene = [e for e in napi_esemenyek(b, HETFO) if e.tipus is Tipus.ZENE_INDUL]
    assert [e.ora for e in zene] == [3]


def test_zene_ablak_idopontjai(b):
    esemenyek = [e for e in napi_esemenyek(b, HETFO) if e.ora == 3 and e.tipus.name.startswith("ZENE")]
    indul, leall = esemenyek
    assert indul.ido == datetime(2026, 10, 19, 10, 35, 10)
    assert leall.ido == datetime(2026, 10, 19, 10, 47, 40)
    assert zene_ablakban(b, datetime(2026, 10, 19, 10, 40))
    assert not zene_ablakban(b, datetime(2026, 10, 19, 10, 48))


def test_reggeli_zene(b):
    b.reggeli_zene = True
    elso = napi_esemenyek(b, HETFO)[0]
    assert elso.tipus is Tipus.ZENE_INDUL and elso.ido == dt(HETFO, "07:30")


def test_allapot_ora_es_szunet(b):
    a = allapot(b, dt(HETFO, "08:10"))
    assert a.szakasz is Szakasz.ORA and a.ora == 1 and a.cim == "1. óra"
    sz = allapot(b, dt(HETFO, "10:40"))
    assert sz.szakasz is Szakasz.SZUNET and sz.ora == 3
    assert sz.hatralevo(dt(HETFO, "10:40")).total_seconds() == 600
    assert allapot(b, dt(HETFO, "07:00")).szakasz is Szakasz.REGGEL
    assert allapot(b, dt(HETFO, "16:00")).szakasz is Szakasz.VEGE


def test_szunnap_es_kivetel(b):
    b.szunnapok.append(Szunnap("2026-10-19", "2026-10-21", "Őszi szünet"))
    assert napi_rend(b, HETFO) is None
    assert allapot(b, dt(HETFO, "09:00")).cim == "Őszi szünet"
    b.kivetelek["2026-10-20"] = "Rövidített"
    assert napi_rend(b, date(2026, 10, 20)).nev == "Rövidített"


def test_ma_nincs_csengetes(b):
    b.ma_nincs_csengetes = HETFO.isoformat()
    assert napi_esemenyek(b, HETFO) == []
    assert napi_esemenyek(b, date(2026, 10, 20))


def test_bemondas_napokon(b):
    b.bemondasok.append(Bemondas("Himnusz", "07:50", napok=[0]))
    assert any(e.tipus is Tipus.BEMONDAS for e in napi_esemenyek(b, HETFO))
    assert not any(e.tipus is Tipus.BEMONDAS for e in napi_esemenyek(b, date(2026, 10, 20)))


def test_kovetkezo_esemeny_atlep_napot(b):
    e = kovetkezo_esemeny(b, dt(date(2026, 10, 23), "16:00"))
    assert e.ido == dt(date(2026, 10, 26), "07:58")


def test_jelzo_nem_esik_szunet_ele(b):
    b.jelzo_perc = 15
    jelzok = [e for e in napi_esemenyek(b, HETFO) if e.tipus is Tipus.JELZO]
    assert len(jelzok) == 1


def test_jelzo_kikapcsolhato(b):
    b.jelzo = False
    assert not [e for e in napi_esemenyek(b, HETFO) if e.tipus is Tipus.JELZO]
    b.jelzo = True
    assert [e for e in napi_esemenyek(b, HETFO) if e.tipus is Tipus.JELZO]


def test_rend_generalas():
    orak = rend_generalas("08:00", 4, 45, 10, nagyszunet_utan=2, nagyszunet=20)
    assert orak == [("08:00", "08:45"), ("08:55", "09:40"), ("10:00", "10:45"), ("10:55", "11:40")]


def test_unnepek():
    assert husvet(2026) == date(2026, 4, 5)
    assert husvet(2027) == date(2027, 3, 28)
    assert len(unnepnapok(2026)) == 12


def test_mentes_betoltes(tmp_path, b):
    b.bemondasok.append(Bemondas("Teszt", "09:00", tartalom="Szia"))
    b.kivetelek["2026-12-18"] = "Rövidített"
    ut = tmp_path / "b.json"
    b.mentes(ut)
    b.mentes(ut)
    vissza = Beallitasok.betoltes(ut)
    assert vissza == b
    ut.write_text("{hibás", encoding="utf-8")
    assert Beallitasok.betoltes(ut) == b
