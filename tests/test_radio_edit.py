from kozgaz_fm.youtube import radio_alap_cim, radio_edit_valaszt

EREDETI = "Avicii - Levels (Official Video) [Extended Mix]"


def elem(azon, cim, hossz):
    return {"id": azon, "title": cim, "duration": hossz}


def test_alap_cim_zaj_nelkul():
    assert radio_alap_cim(EREDETI) == "Avicii - Levels"


def test_a_radio_editet_valasztja():
    elemek = [elem("a", "Avicii - Levels (Extended Mix)", 600), elem("b", "Avicii - Levels (Radio Edit)", 200)]
    assert radio_edit_valaszt(elemek, EREDETI, 420)["id"] == "b"


def test_tul_hosszu_radio_edit_nem_jo():
    assert radio_edit_valaszt([elem("a", "Avicii - Levels (Radio Edit)", 500)], EREDETI, 420) is None


def test_mas_szam_radio_editje_nem_jo():
    assert radio_edit_valaszt([elem("a", "Calvin Harris - Summer (Radio Edit)", 200)], EREDETI, 420) is None


def test_radio_jelzes_nelkul_nem_jo():
    assert radio_edit_valaszt([elem("a", "Avicii - Levels (Short)", 200)], EREDETI, 420) is None


def test_ekezet_es_radio_version():
    elemek = [elem("a", "Ákos – Ilyenek voltunk (rádió verzió)", 200),
              elem("b", "Ákos - Ilyenek voltunk - Radio Version", 210)]
    assert radio_edit_valaszt(elemek, "Ákos - Ilyenek voltunk (Hosszú változat)", 420)["id"] == "b"
