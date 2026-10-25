__lazy_modules__ = ["datetime", "kozgaz_fm.beallitasok", "kozgaz_fm.naptar_import"]

from datetime import date

import pytest

from kozgaz_fm import naptar_import
from kozgaz_fm.beallitasok import Szunnap, alapertelmezett
from kozgaz_fm.naptar_import import (
    KIHAGY,
    ROVIDITETT,
    SZUNNAP,
    TANITASI_NAP,
    IcsEsemeny,
    ImportHiba,
    alkalmaz,
    besorol,
    ics_beolvas,
    javaslatok,
    letoltes,
)


def ics(*esemenyek: str) -> str:
    return "BEGIN:VCALENDAR\r\nVERSION:2.0\r\n" + "".join(
        f"BEGIN:VEVENT\r\n{e}\r\nEND:VEVENT\r\n" for e in esemenyek) + "END:VCALENDAR\r\n"


NAPTAR = ics(
    "DTSTART;VALUE=DATE:20261023\r\nDTEND;VALUE=DATE:20261102\r\nSUMMARY:Őszi szünet",
    "DTSTART;VALUE=DATE:20261212\r\nDTEND;VALUE=DATE:20261213\r\nSUMMARY:Szombati munkanap (pénteki\r\n  órarend)",
    "DTSTART:20261120T090000\r\nDTEND:20261120T120000\r\nSUMMARY:Rövidített órák\\, szülői értekezlet",
    "DTSTART;VALUE=DATE:20261106\r\nSUMMARY:Iskolai ünnepség",
    "DTSTART;VALUE=DATE:20261201\r\nSTATUS:CANCELLED\r\nSUMMARY:Elmarad",
    "DTSTART;VALUE=DATE:20261301\r\nSUMMARY:Hibás dátum",
    "DTSTART;VALUE=DATE:20260101\r\nDTEND;VALUE=DATE:20270101\r\nSUMMARY:Túl hosszú",
)


def test_ics_beolvas():
    esemenyek = ics_beolvas(NAPTAR)
    assert [(e.nev, e.tol, e.ig) for e in esemenyek] == [
        ("Őszi szünet", date(2026, 10, 23), date(2026, 11, 1)),
        ("Iskolai ünnepség", date(2026, 11, 6), date(2026, 11, 6)),
        ("Rövidített órák, szülői értekezlet", date(2026, 11, 20), date(2026, 11, 20)),
        ("Szombati munkanap (pénteki órarend)", date(2026, 12, 12), date(2026, 12, 12)),
    ]


def test_utc_ido_es_ejfeli_veg():
    e = ics_beolvas(ics("DTSTART:20261123T000000\r\nDTEND:20261125T000000\r\nSUMMARY:Téli próba"))
    assert (e[0].tol, e[0].ig) == (date(2026, 11, 23), date(2026, 11, 24))
    z = ics_beolvas(ics("DTSTART:20261123T100000Z\r\nSUMMARY:Délelőtt"))
    assert z[0].tol == date(2026, 11, 23) == z[0].ig


def test_nem_naptar():
    with pytest.raises(ImportHiba):
        ics_beolvas("<html>nem naptár</html>")


@pytest.mark.parametrize(("nev", "nap", "muvelet", "megjegyzes"), [
    ("Őszi szünet", date(2026, 10, 26), SZUNNAP, ""),
    ("Téli szünidő", date(2026, 12, 28), SZUNNAP, ""),
    ("Tanítás nélküli munkanap", date(2026, 11, 13), SZUNNAP, ""),
    ("Nemzeti ünnep", date(2026, 10, 23), SZUNNAP, ""),
    ("Igazgatói nap", date(2026, 11, 13), SZUNNAP, ""),
    ("Iskolai ünnepség", date(2026, 11, 6), KIHAGY, "rendezvény"),
    ("Szalagavató ünnepély", date(2026, 12, 4), KIHAGY, "rendezvény"),
    ("Rövidített órák", date(2026, 11, 20), ROVIDITETT, "Rövidített"),
    ("Szombati munkanap", date(2026, 12, 12), TANITASI_NAP, "Normál"),
    ("Tanítási nap (szombat)", date(2026, 12, 12), TANITASI_NAP, "Normál"),
    ("Munkanap", date(2026, 12, 9), KIHAGY, "rendezvény"),
    ("Szülői értekezlet", date(2026, 11, 20), KIHAGY, "rendezvény"),
    ("Őszi szünet előtti utolsó tanítási nap", date(2026, 10, 22), KIHAGY, "tanítási nap"),
    ("Téli szünet utáni első tanítási nap", date(2027, 1, 4), KIHAGY, "tanítási nap"),
    ("Szünet előtti tanítás nélküli munkanap", date(2026, 10, 22), SZUNNAP, ""),
])
def test_besorolas(nev, nap, muvelet, megjegyzes):
    j = besorol(IcsEsemeny(nev, nap, nap), alapertelmezett())
    assert (j.muvelet, j.megjegyzes) == (muvelet, megjegyzes)


def test_rovid_rend_nelkul_kihagy():
    b = alapertelmezett()
    b.rendek = [r for r in b.rendek if r.nev == "Normál"]
    j = besorol(IcsEsemeny("Rövidített órák", date(2026, 11, 20), date(2026, 11, 20)), b)
    assert j.muvelet == KIHAGY and "Rövidített" in j.megjegyzes


def test_alkalmaz_es_duplikacio():
    b = alapertelmezett()
    b.szunnapok.append(Szunnap("2026-10-23", "2026-11-01", "Őszi szünet (kézi)"))
    lista = javaslatok(NAPTAR, b, tol=date(2026, 10, 1))
    kivalasztott = [j for j in lista if j.muvelet != KIHAGY]
    assert alkalmaz(b, kivalasztott) == (0, 2, 0)
    assert b.kivetelek == {"2026-11-20": "Rövidített", "2026-12-12": "Normál"}
    tobb_napos = javaslatok(ics("DTSTART;VALUE=DATE:20261119\r\nDTEND;VALUE=DATE:20261124\r\n"
                                "SUMMARY:Rövidített hét"), b, tol=date(2026, 10, 1))
    alkalmaz(b, tobb_napos)
    assert "2026-11-21" not in b.kivetelek and b.kivetelek["2026-11-23"] == "Rövidített"


def test_multbeli_esemenyek_kimaradnak():
    lista = javaslatok(NAPTAR, alapertelmezett(), tol=date(2026, 11, 10))
    assert [j.esemeny.nev for j in lista] == ["Rövidített órák, szülői értekezlet",
                                              "Szombati munkanap (pénteki órarend)"]


@pytest.mark.parametrize("cim", ["file:///etc/passwd", "ftp://pelda.hu/a.ics", "javascript:alert(1)", "https://"])
def test_letoltes_csak_http(cim):
    with pytest.raises(ImportHiba, match="http"):
        letoltes(cim)


class _Valasz:
    def __init__(self, adat: bytes):
        self.adat = adat

    def read(self, n):
        return self.adat[:n]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_letoltes_webcal_es_meretkorlat(monkeypatch):
    hivott = []
    monkeypatch.setattr(naptar_import.urllib.request, "urlopen",
                        lambda keres, timeout: hivott.append(keres.full_url) or _Valasz(NAPTAR.encode()))
    assert "Őszi szünet" in letoltes("webcal://naptar.pelda.hu/suli.ics")
    assert hivott == ["https://naptar.pelda.hu/suli.ics"]
    monkeypatch.setattr(naptar_import.urllib.request, "urlopen",
                        lambda keres, timeout: _Valasz(b"x" * (naptar_import.MAX_MERET + 10)))
    with pytest.raises(ImportHiba, match="túl nagy"):
        letoltes("https://pelda.hu/nagy.ics")


def test_kezi_kivetelt_nem_ir_felul():
    b = alapertelmezett()
    b.kivetelek["2026-11-20"] = "Normál"
    lista = javaslatok(ics("DTSTART;VALUE=DATE:20261120\r\nSUMMARY:Rövidített órák"), b, tol=date(2026, 10, 1))
    assert alkalmaz(b, lista) == (0, 0, 1) and b.kivetelek["2026-11-20"] == "Normál"


def test_sok_folytatosor_gyorsan():
    import time
    szoveg = ics("DTSTART;VALUE=DATE:20261120\r\nSUMMARY:x" + "\r\n y" * 300_000)
    kezdet = time.perf_counter()
    e = ics_beolvas(szoveg)
    assert time.perf_counter() - kezdet < 2 and e[0].nev.startswith("xyyy")
