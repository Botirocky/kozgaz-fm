__lazy_modules__ = ["json", "datetime", "kozgaz_fm.beallitasok", "kozgaz_fm.kghsz", "kozgaz_fm.naptar_import"]

import json
from datetime import date

import pytest

from kozgaz_fm import kghsz
from kozgaz_fm.beallitasok import Csengetesirend, Ora, alapertelmezett, ora_lista
from kozgaz_fm.naptar_import import KIHAGY, SZUNNAP, IcsEsemeny, ImportHiba, alkalmaz, besorol, esemeny_javaslatok

RENDES = "".join(f"<tr><td>{i}. &oacute;ra</td><td>{k} - {v}</td></tr>" for i, k, v in (
    (1, "07:30", "08:15"), (2, "08:25", "09:10"))) + "<tr><td>eb&eacute;dsz&uuml;net</td><td>13:00 - 13:20</td></tr>"
HAZIREND = ("<p>Az ebédszünetben 13:20-ig.</p><p><strong>Csengetési órarend</strong></p><table><tbody>"
            "<tr><td><p>Az óra sorszáma</p></td><td><p>kezdete</p></td><td><p>vége</p></td></tr>"
            "<tr><td><p>1.</p></td><td><p>07:30</p></td><td><p>08:15</p></td></tr>"
            "<tr><td colspan='3'><p>Ebédszünet</p></td></tr>"
            "<tr><td><p>2.</p></td><td><p>08:25</p></td><td><p>09:10</p></td></tr>"
            "<tr><td><p>3.</p></td><td><p>15:10</p></td><td><p>15:55</p></td></tr>"
            "</tbody></table><p>Óraközi szünetek</p>")
TANEV = """<h2>A 2026-2027. tanév</h2><p><strong>Szorgalmi&nbsp;időszak</strong></p><table><tbody>
<tr><td>Első tanítási nap</td><td>2026. szeptember 1. (kedd)</td></tr>
<tr><td>Utolsó tanítási nap</td><td>2027. június 15. (kedd)</td></tr>
<tr><td><p>Tanításmentes munkanap</p><p>ebből:</p></td><td>5 nap</td></tr></tbody></table>
<p><strong>Tanítási szünetek</strong></p><table><tbody>
<tr><td>Őszi szünet</td><td>&nbsp;</td></tr>
<tr><td colspan="2"><p>A szünet előtti utolsó tanítási nap 2026. október 22. (csütörtök)</p>
<p>a szünet utáni első tanítási nap 2026. november 02. (hétfő)</p></td></tr>
<tr><td><span>Téli szünet</span></td><td>&nbsp;</td></tr>
<tr><td colspan="2"><p>A szünet előtti utolsó tanítási nap 2026. december 18. (péntek)</p>
<p>a szünet utáni első tanítási nap 2027. január 4. (hétfő)</p></td></tr></tbody></table>
<p><strong>Tanításmentes munkanapok&nbsp;</strong></p><table><tbody>
<tr><td><strong>sorszám</strong></td><td>Határidő</td><td>Megnevezés</td></tr>
<tr><td>2.</td><td>2026. november 30.</td><td>Pályaorientációs nap</td></tr>
<tr><td>5.</td><td>2027. április 30.</td><td>Ballagás</td></tr></tbody></table>
<p><strong>Érettségi vizsganapok (május-június)</strong></p><table><tbody>
<tr><td>1.</td><td>2027. május 3.</td><td>Ez nem munkaszünet</td></tr></tbody></table>"""


def oldal(**adat) -> str:
    tartalom = json.dumps({"props": {"pageProps": adat}}, ensure_ascii=False)
    return f'<html><script id="__NEXT_DATA__" type="application/json">{tartalom}</script></html>'


def test_csengetesi_rend_a_hazirendbol_es_rovid_masolat_kimarad():
    normal, rovid = kghsz.csengetesi_rend(oldal(data={"ringNormal": RENDES, "ringShort": RENDES}),
                                          oldal(data={"info": HAZIREND}))
    assert normal == ora_lista(("07:30", "08:15"), ("08:25", "09:10"), ("15:10", "15:55"))
    assert rovid is None


def test_csengetesi_rend_hazirend_nelkul_es_valodi_rovid():
    mas = "<tr><td>1. óra</td><td>8:00 - 08:30</td></tr>"
    normal, rovid = kghsz.csengetesi_rend(oldal(data={"ringNormal": RENDES, "ringShort": mas}), None)
    assert normal == ora_lista(("07:30", "08:15"), ("08:25", "09:10"))
    assert rovid == ora_lista(("08:00", "08:30"))


def test_csengetesi_rend_olvashatatlan():
    with pytest.raises(ImportHiba):
        kghsz.csengetesi_rend(oldal(data={"ringNormal": "<p>hamarosan</p>"}), None)
    with pytest.raises(ImportHiba):
        kghsz.csengetesi_rend("<html></html>", None)


def test_tanev_esemenyek():
    assert kghsz.tanev_esemenyek(oldal(data={"currentInfo": TANEV})) == [
        IcsEsemeny("Nyári szünet", date(2027, 6, 16), date(2027, 8, 31)),
        IcsEsemeny("Őszi szünet", date(2026, 10, 23), date(2026, 11, 1)),
        IcsEsemeny("Téli szünet", date(2026, 12, 19), date(2027, 1, 3)),
        IcsEsemeny("Tanításmentes munkanap: Pályaorientációs nap", date(2026, 11, 30), date(2026, 11, 30)),
        IcsEsemeny("Tanításmentes munkanap: Ballagás", date(2027, 4, 30), date(2027, 4, 30)),
    ]


def test_tanev_szerkezet_valtozas():
    with pytest.raises(ImportHiba):
        kghsz.tanev_esemenyek(oldal(data={"currentInfo": "<p>Feltöltés alatt</p>"}))


def test_tanitasmentes_szunnap():
    b = alapertelmezett()
    assert besorol(IcsEsemeny("Tanításmentes munkanap: Ballagás", date(2027, 4, 30), date(2027, 4, 30)),
                   b).muvelet == SZUNNAP


def test_honlapi_esemenyek_multat_es_hibasat_kihagy():
    html = oldal(events=[
        {"title": "Régi", "startDate": "2025-05-05T08:00:00.000Z", "endDate": "2025-05-06T12:00:00.000Z"},
        {"title": "Érettségi szünet", "startDate": "2027-05-03T08:00:00.000Z", "endDate": "2027-05-04T12:00:00.000Z"},
        {"title": "Sportnap", "startDate": "2027-02-02T07:00:00.000Z", "endDate": None},
        {"title": "Hibás", "startDate": "nem dátum"},
        {"startDate": "2027-02-03T07:00:00.000Z"},
    ])
    assert kghsz.honlapi_esemenyek(html, date(2026, 11, 1)) == [
        IcsEsemeny("Érettségi szünet", date(2027, 5, 3), date(2027, 5, 4)),
        IcsEsemeny("Sportnap", date(2027, 2, 2), date(2027, 2, 2)),
    ]


def test_osszevon_atfedo_szunet_a_tanev_rendjebol_marad():
    b = alapertelmezett()
    tanev = [IcsEsemeny("Téli szünet", date(2026, 12, 19), date(2027, 1, 3))]
    honlapi = [
        IcsEsemeny("Téli szünet", date(2026, 12, 21), date(2027, 1, 1)),
        IcsEsemeny("Érettségi szünet", date(2027, 5, 3), date(2027, 5, 4)),
        IcsEsemeny("Karácsonyi műsor", date(2026, 12, 20), date(2026, 12, 20)),
    ]
    eredmeny = kghsz.osszevon(tanev, honlapi, b)
    assert [e.nev for e in eredmeny] == ["Téli szünet", "Karácsonyi műsor", "Érettségi szünet"]
    assert eredmeny[0].tol == date(2026, 12, 19)


def test_rend_alkalmaz_csak_a_megadottat_irja_felul():
    b = alapertelmezett()
    b.rend("Normál").orak = [Ora("08:00", "08:45")]
    rovid_elotte = list(b.rend("Rövidített").orak)
    adatok = kghsz.IskolaiAdatok(ora_lista(("07:30", "08:15")), None, [])
    assert kghsz.rend_atvetel(b, adatok) == ["Normál"]
    assert kghsz.rend_alkalmaz(b, adatok) == ["Normál"]
    assert b.rend("Normál").orak == ora_lista(("07:30", "08:15"))
    assert b.rend("Rövidített").orak == rovid_elotte
    assert kghsz.rend_atvetel(b, adatok) == []


def test_rend_alkalmaz_hianyzo_rendet_felvesz():
    b = alapertelmezett()
    b.rendek = [Csengetesirend("Normál", ora_lista(("07:30", "08:15")))]
    adatok = kghsz.IskolaiAdatok(ora_lista(("07:30", "08:15")), ora_lista(("07:30", "08:00")), [])
    assert kghsz.rend_alkalmaz(b, adatok) == ["Rövidített"]
    assert b.rend("Rövidített").orak == ora_lista(("07:30", "08:00"))


def test_letoltes_kimarado_opcionalis_oldalakkal(monkeypatch):
    oldalak = {
        kghsz.OLDAL_CSENGETES: oldal(data={"ringNormal": RENDES, "ringShort": RENDES}),
        kghsz.OLDAL_TANEV: oldal(data={"currentInfo": TANEV}),
    }

    def letolt(ut: str) -> str:
        if ut not in oldalak:
            raise ImportHiba("nem érhető el")
        return oldalak[ut]

    monkeypatch.setattr(kghsz, "_letolt", letolt)
    b = alapertelmezett()
    b.szunnapok = []
    adatok = kghsz.letoltes(b, date(2026, 11, 1))
    assert adatok.normal == ora_lista(("07:30", "08:15"), ("08:25", "09:10")) and adatok.rovid is None
    javaslat = esemeny_javaslatok(adatok.esemenyek, b, date(2026, 11, 1))
    assert all(j.muvelet == SZUNNAP for j in javaslat) and not [j for j in javaslat if j.muvelet == KIHAGY]
    assert alkalmaz(b, javaslat)[0] == 5
    assert alkalmaz(b, javaslat)[0] == 0


def test_alapertelmezett_az_iskola_rendje():
    b = alapertelmezett()
    normal = b.rend("Normál").orak
    assert (len(normal), normal[0].kezdet, normal[-1].vege) == (9, "07:30", "15:55")
    assert any(s.nev == "Téli szünet" and s.tol == "2026-12-19" for s in b.szunnapok)
