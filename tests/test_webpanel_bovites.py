__lazy_modules__ = ["datetime", "pytest", "kozgaz_fm.beallitasok", "kozgaz_fm.vezerlo", "kozgaz_fm.webpanel"]

from datetime import datetime

import pytest

from kozgaz_fm.beallitasok import ALAP_SABLONOK, Rendkivuli, alapertelmezett
from kozgaz_fm.vezerlo import Vezerlo
from kozgaz_fm.webpanel import WebHiba, WebMuveletek


class AlZene:
    def __init__(self, szamok: list[str] | None = None, szol: bool = True) -> None:
        self.szamok = [type("Szam", (), {"cim": c})() for c in (szamok or [])]
        self.szol = szol
        self.ugrasok: list[int] = []
        self.leallitva = False

    def ugras(self, index: int) -> None:
        self.ugrasok.append(index)


class AlVezerlo:
    aktiv_csend = Vezerlo.aktiv_csend
    csend_most = Vezerlo.csend_most
    csend_vege = Vezerlo.csend_vege

    def __init__(self) -> None:
        self.b = alapertelmezett()
        self.zene = AlZene()
        self.riasztas = False
        self.naplo: list[str] = []
        self.mentesek = 0

    def log(self, szoveg: str) -> None:
        self.naplo.append(szoveg)

    def mentes(self) -> None:
        self.mentesek += 1

    def zene_leallit(self) -> None:
        self.zene.szol = False


class AlMuveletek:
    zene_ugras = WebMuveletek.zene_ugras
    sablonok_mentese = WebMuveletek.sablonok_mentese
    csend_inditas = WebMuveletek.csend_inditas
    csend_leallitas = WebMuveletek.csend_leallitas
    _riasztas_kozben = WebMuveletek._riasztas_kozben

    def __init__(self) -> None:
        self.v = AlVezerlo()

    def allapot(self) -> dict:
        return {"ok": True}


@pytest.fixture
def m() -> AlMuveletek:
    return AlMuveletek()


def test_alap_sablonok_megvannak():
    assert alapertelmezett().bemondas_sablonok == ALAP_SABLONOK
    assert alapertelmezett().bemondas_sablonok is not ALAP_SABLONOK


def test_sablonok_mentese_tisztit_es_dupla_nelkul(m):
    m.sablonok_mentese({"sablonok": ["  Első  ", "Második", "Első"]}, "10.0.0.5")
    assert m.v.b.bemondas_sablonok == ["Első", "Második"]
    assert m.v.mentesek == 1


@pytest.mark.parametrize("adat", [
    {},
    {"sablonok": "szöveg"},
    {"sablonok": [""]},
    {"sablonok": [5]},
    {"sablonok": ["x" * 501]},
    {"sablonok": ["x"] * 31},
])
def test_hibas_sablonok(m, adat):
    with pytest.raises(WebHiba) as hiba:
        m.sablonok_mentese(adat, "ip")
    assert hiba.value.statusz == 422


def test_ugras_a_sorban(m):
    m.v.zene = AlZene(["A", "B", "C"])
    m.zene_ugras({"index": 2, "cim": "C"}, "ip")
    assert m.v.zene.ugrasok == [2]


def test_ugras_valtozott_sorban_409(m):
    m.v.zene = AlZene(["A", "B", "C"])
    with pytest.raises(WebHiba) as hiba:
        m.zene_ugras({"index": 2, "cim": "B"}, "ip")
    assert hiba.value.statusz == 409 and m.v.zene.ugrasok == []


def test_ugras_rossz_index(m):
    m.v.zene = AlZene(["A"])
    with pytest.raises(WebHiba) as hiba:
        m.zene_ugras({"index": 5, "cim": "A"}, "ip")
    assert hiba.value.statusz == 422


def test_csend_inditasa_es_leallitasa(m):
    m.csend_inditas({"perc": 30, "hangero": 30}, "10.0.0.5")
    csend = m.v.aktiv_csend()
    assert csend is not None and csend.csengo_hangero == 30 and not m.v.zene.szol
    with pytest.raises(WebHiba) as hiba:
        m.csend_inditas({"perc": 30}, "ip")
    assert hiba.value.statusz == 409
    m.csend_leallitas({}, "ip")
    assert m.v.aktiv_csend() is None
    with pytest.raises(WebHiba) as hiba:
        m.csend_leallitas({}, "ip")
    assert hiba.value.statusz == 409


@pytest.mark.parametrize("perc", [None, 0, 4, 241, "30", True])
def test_csend_hibas_perc(m, perc):
    with pytest.raises(WebHiba) as hiba:
        m.csend_inditas({} if perc is None else {"perc": perc}, "ip")
    assert hiba.value.statusz == 422


def test_csend_riasztas_kozben_nem(m):
    m.v.riasztas = True
    with pytest.raises(WebHiba) as hiba:
        m.csend_inditas({"perc": 30}, "ip")
    assert hiba.value.statusz == 409


def test_csend_vege_rovidebbre_vagja_az_utemezettet():
    v = AlVezerlo()
    ma = datetime.now().date().isoformat()
    v.b.rendkivuli.append(Rendkivuli("Érettségi", ma, "00:00", tipus="csend", ig="23:59"))
    elotte = datetime.now().strftime("%H:%M")
    if elotte in ("00:00", "23:59"):
        pytest.skip("éjfél körül a perc-kerekítés miatt nem mérhető")
    assert v.csend_vege()
    assert v.b.rendkivuli[0].ig in (elotte, datetime.now().strftime("%H:%M"))
    assert v.aktiv_csend() is None
