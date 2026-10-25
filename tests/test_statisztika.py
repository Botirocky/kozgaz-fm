__lazy_modules__ = ["csv", "datetime", "kozgaz_fm.statisztika"]

import csv
from datetime import date, datetime, timedelta

import pytest

from kozgaz_fm.statisztika import Statisztika

T = datetime(2026, 10, 20, 10, 0, 0)


@pytest.fixture
def stat(tmp_path):
    s = Statisztika(tmp_path / "stat.sqlite")
    yield s
    s.bezar()


def test_lejatszas_hossza_es_kert_jeloles(stat):
    stat.szam_kezd("A dal", "Mappa", most=T)
    stat.szam_kezd("B dal", "Mappa", kert=True, most=T + timedelta(minutes=3))
    stat.szam_vege(T + timedelta(minutes=5, seconds=30))
    stat.szam_vege(T + timedelta(minutes=9))
    stat.szam_kezd("A dal", "YouTube", most=T + timedelta(days=1))
    stat.szam_vege(T + timedelta(days=1, minutes=4))
    o = stat.osszegzes(T.date(), T.date() + timedelta(days=1))
    assert o["zene"] == {"szamok": 3, "perc": 10, "kert": 1}
    assert o["legtobbet"][0] == {"cim": "A dal", "darab": 2, "kert": False}
    assert o["legtobbet"][1] == {"cim": "B dal", "darab": 1, "kert": True}
    assert [n["zene_perc"] for n in o["napok"]] == [6, 4]


def test_csengetes_pontossag(stat):
    stat.csengetes("becsengo", "1. óra", tervezett=T, most=T + timedelta(milliseconds=300))
    stat.csengetes("kicsengo", "1. óra vége", tervezett=T + timedelta(minutes=45),
                   most=T + timedelta(minutes=45, seconds=3))
    stat.csengetes("kezi", "Kézi csengetés", most=T + timedelta(minutes=50))
    stat.csengetes("becsengo", "korai", tervezett=T + timedelta(hours=1),
                   most=T + timedelta(hours=1) - timedelta(seconds=4))
    c = stat.osszegzes(T.date(), T.date())["csengetes"]
    assert c == {"darab": 4, "kezi": 1, "atlag_keses_ms": 2433, "max_keses_ms": 3000, "kesett": 1}


def test_ures_idoszak(stat):
    o = stat.osszegzes(date(2026, 9, 1), date(2026, 9, 3))
    assert o["zene"] == {"szamok": 0, "perc": 0, "kert": 0} and o["legtobbet"] == []
    assert o["csengetes"]["atlag_keses_ms"] is None and o["csengetes"]["darab"] == 0
    assert [n["nap"] for n in o["napok"]] == ["2026-09-01", "2026-09-02", "2026-09-03"]


def test_keresek_szamlalasa(stat):
    for eredmeny in ("erkezett", "erkezett", "erkezett", "elfogadva", "elutasitva"):
        stat.keres(eredmeny, most=T)
    assert stat.osszegzes(T.date(), T.date())["keresek"] == {"erkezett": 3, "elfogadva": 1, "elutasitva": 1}


def test_idoszak_hatarai(stat):
    stat.szam_kezd("tegnap este", most=datetime(2026, 10, 19, 23, 59, 59))
    stat.szam_kezd("ma reggel", most=datetime(2026, 10, 20, 0, 0, 0))
    stat.szam_vege(datetime(2026, 10, 20, 0, 1, 0))
    o = stat.osszegzes(date(2026, 10, 20), date(2026, 10, 20))
    assert [t["cim"] for t in o["legtobbet"]] == ["ma reggel"]


def test_csv_export_es_keplet_vedelem(stat, tmp_path):
    stat.szam_kezd("=HYPERLINK(\"x\")", "Mappa", most=T)
    stat.szam_kezd("Normál dal", "YouTube", kert=True, most=T + timedelta(minutes=2))
    stat.szam_vege(T + timedelta(minutes=5))
    fajl = tmp_path / "ki.csv"
    assert stat.csv_export(T.date(), T.date(), fajl) == 2
    assert fajl.read_bytes().startswith(b"\xef\xbb\xbf")
    with open(fajl, encoding="utf-8-sig", newline="") as f:
        sorok = list(csv.reader(f, delimiter=";"))
    assert sorok[0][0] == "Dátum" and sorok[1][2].startswith("'=")
    assert sorok[2] == ["2026-10-20", "10:02:00", "Normál dal", "YouTube", "igen", "180"]


def test_takaritas(stat):
    stat.szam_kezd("régi", most=T - timedelta(days=500))
    stat.szam_vege(T - timedelta(days=500))
    stat.csengetes("kezi", most=T - timedelta(days=500))
    stat.szam_kezd("új", most=T)
    stat.szam_vege(T + timedelta(minutes=1))
    stat.takarit(most=T)
    o = stat.osszegzes(T.date() - timedelta(days=600), T.date())
    assert [t["cim"] for t in o["legtobbet"]] == ["új"] and o["csengetes"]["darab"] == 0


def test_ujranyitas_megorzi_az_adatot(tmp_path):
    s = Statisztika(tmp_path / "stat.sqlite")
    s.szam_kezd("megmarad", most=T)
    s.bezar()
    s2 = Statisztika(tmp_path / "stat.sqlite")
    assert s2.osszegzes(T.date(), T.date())["zene"]["szamok"] == 1
    s2.bezar()
