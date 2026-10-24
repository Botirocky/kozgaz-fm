__lazy_modules__ = ["datetime", "pytest", "kozgaz_fm.beallitasok", "kozgaz_fm.orarend", "kozgaz_fm.vezerlo"]

from datetime import date, datetime

import pytest

from kozgaz_fm.beallitasok import Beallitasok, Bemondas, Rendkivuli, Szunnap, alapertelmezett
from kozgaz_fm.orarend import (
    CSENGOK,
    Esemeny,
    Szakasz,
    Tipus,
    allapot,
    kovetkezo_esemeny,
    napi_esemenyek,
    zene_ablakban,
)
from kozgaz_fm.vezerlo import Vezerlo

HETFO = date(2026, 10, 19)


@pytest.fixture
def b() -> Beallitasok:
    return alapertelmezett()


def dt(nap: date, ido: str) -> datetime:
    ora, perc = map(int, ido.split(":"))
    return datetime(nap.year, nap.month, nap.day, ora, perc)


def tipusok(b: Beallitasok, nap: date, *keresett: Tipus) -> list[Esemeny]:
    return [e for e in napi_esemenyek(b, nap) if e.tipus in keresett]


def test_rendkivuli_csengetes_szunnapon_is(b):
    b.szunnapok.append(Szunnap(HETFO.isoformat(), HETFO.isoformat(), "Igazgatói nap"))
    b.rendkivuli.append(Rendkivuli("Ünnepség", HETFO.isoformat(), "10:00", hang="beepitett:gong"))
    esemenyek = napi_esemenyek(b, HETFO)
    assert [(e.tipus, e.ido, e.leiras) for e in esemenyek] == [(Tipus.RENDKIVULI, dt(HETFO, "10:00"), "Ünnepség")]


def test_masik_nap_es_kikapcsolt_nem_szamit(b):
    b.rendkivuli.append(Rendkivuli("Holnap", "2026-10-20", "10:00"))
    b.rendkivuli.append(Rendkivuli("Ki", HETFO.isoformat(), "10:00", aktiv=False))
    assert tipusok(b, HETFO, Tipus.RENDKIVULI, Tipus.RIADO, Tipus.CSEND) == []


def test_riado_magatol_leall(b):
    b.rendkivuli.append(Rendkivuli("Tűzriadó", HETFO.isoformat(), "10:05", tipus="riado", riado_perc=4))
    riado = tipusok(b, HETFO, Tipus.RIADO, Tipus.RIADO_VEGE)
    assert [(e.tipus, e.ido) for e in riado] == [(Tipus.RIADO, dt(HETFO, "10:05")),
                                                 (Tipus.RIADO_VEGE, dt(HETFO, "10:09"))]
    assert riado[1].leiras == "Tűzriadó – vége"


def test_kezi_leallitasig_tarto_riadonak_nincs_vege(b):
    b.rendkivuli.append(Rendkivuli("Tűzriadó", HETFO.isoformat(), "10:05", tipus="riado", riado_perc=0))
    assert [e.tipus for e in tipusok(b, HETFO, Tipus.RIADO, Tipus.RIADO_VEGE)] == [Tipus.RIADO]


def test_riado_nem_latszik_kovetkezo_csengokent(b):
    b.rendkivuli.append(Rendkivuli("Tűzriadó", HETFO.isoformat(), "08:20", tipus="riado"))
    kovetkezo = kovetkezo_esemeny(b, dt(HETFO, "08:10"))
    assert kovetkezo is not None and kovetkezo.tipus in CSENGOK and kovetkezo.ido == dt(HETFO, "08:45")


def test_csendes_idoszak_nema_csengo_zene_es_bemondas_nelkul(b):
    b.bemondasok.append(Bemondas("Reggeli", "09:45"))
    b.bemondasok.append(Bemondas("Délutáni", "12:35"))
    b.rendkivuli.append(Rendkivuli("Érettségi", HETFO.isoformat(), "08:50", tipus="csend", ig="10:40"))
    esemenyek = napi_esemenyek(b, HETFO)
    csendben = [e for e in esemenyek if dt(HETFO, "08:50") <= e.ido < dt(HETFO, "10:40")]
    assert [(e.tipus, e.ido) for e in csendben] == [(Tipus.ZENE_LEALL, dt(HETFO, "08:50")),
                                                    (Tipus.CSEND, dt(HETFO, "08:50"))]
    assert [e.bemondas.nev for e in esemenyek if e.tipus is Tipus.BEMONDAS and e.bemondas] == ["Délutáni"]
    assert any(e.tipus is Tipus.CSEND_VEGE and e.ido == dt(HETFO, "10:40") for e in esemenyek)
    assert any(e.tipus is Tipus.KICSENGO and e.ido == dt(HETFO, "08:45") for e in esemenyek)


def test_csendes_idoszak_halk_csengovel(b):
    b.rendkivuli.append(Rendkivuli("Mérés", HETFO.isoformat(), "08:50", tipus="csend", ig="09:45",
                                   csengo_hangero=25))
    csengok = [e for e in tipusok(b, HETFO, *CSENGOK) if dt(HETFO, "08:50") <= e.ido < dt(HETFO, "09:45")]
    assert [(e.tipus, e.hangero) for e in csengok] == [(Tipus.JELZO, 25), (Tipus.BECSENGO, 25), (Tipus.KICSENGO, 25)]
    assert csengok[1].leiras == "2. óra – becsengő (halkan)"
    assert all(e.hangero is None for e in tipusok(b, HETFO, *CSENGOK) if e.ido >= dt(HETFO, "09:45"))


def test_zene_a_csendes_idoszak_kore_vagva(b):
    b.zene_min_szunet = 11
    b.zene_kesleltetes = 0
    b.zene_leall_elotte = 0
    b.rendkivuli.append(Rendkivuli("Bejelentés", HETFO.isoformat(), "10:40", tipus="csend", ig="10:44"))
    zene = [(e.tipus, e.ido.strftime("%H:%M")) for e in tipusok(b, HETFO, Tipus.ZENE_INDUL, Tipus.ZENE_LEALL)]
    assert zene == [(Tipus.ZENE_INDUL, "10:35"), (Tipus.ZENE_LEALL, "10:40"),
                    (Tipus.ZENE_INDUL, "10:44"), (Tipus.ZENE_LEALL, "10:48")]
    assert not zene_ablakban(b, dt(HETFO, "10:42"))
    assert zene_ablakban(b, dt(HETFO, "10:45"))


def test_hibas_csendes_idoszak_nem_szamit(b):
    b.rendkivuli.append(Rendkivuli("Fordított", HETFO.isoformat(), "11:00", tipus="csend", ig="10:00"))
    b.rendkivuli.append(Rendkivuli("Vég nélkül", HETFO.isoformat(), "11:00", tipus="csend"))
    assert tipusok(b, HETFO, Tipus.CSEND, Tipus.CSEND_VEGE) == []


def test_allapot_mutatja_a_csendes_idoszakot(b):
    b.rendkivuli.append(Rendkivuli("Érettségi", HETFO.isoformat(), "08:00", tipus="csend", ig="12:00"))
    a = allapot(b, dt(HETFO, "09:00"))
    assert a.szakasz is Szakasz.ORA and a.csend == "Érettségi"
    assert allapot(b, dt(HETFO, "12:00")).csend == ""


def test_mentes_es_betoltes(tmp_path, b):
    b.rendkivuli.append(Rendkivuli("Tűzriadó", HETFO.isoformat(), "10:05", tipus="riado", riado_perc=2))
    ut = tmp_path / "beallitasok.json"
    b.mentes(ut)
    assert Beallitasok.betoltes(ut).rendkivuli == b.rendkivuli


class AlVezerlo:
    _kezel = Vezerlo._kezel

    def __init__(self) -> None:
        self.riasztas = False
        self._auto_riado = False
        self.naplo: list[str] = []
        self.csengetesek: list[tuple[str, str, int | None]] = []

    def log(self, szoveg: str) -> None:
        self.naplo.append(szoveg)

    def riasztas_indit(self) -> None:
        self.riasztas = True
        self._auto_riado = False

    def riasztas_leallit(self) -> None:
        self.riasztas = False

    def csengetes(self, hang: str, leiras: str = "", hangero: int | None = None) -> None:
        self.csengetesek.append((hang, leiras, hangero))

    @property
    def frissult(self):
        return type("Jel", (), {"emit": staticmethod(lambda: None)})


def test_vezerlo_riado_indul_es_magatol_leall():
    r = Rendkivuli("Tűzriadó", HETFO.isoformat(), "10:05", tipus="riado", riado_perc=3)
    v = AlVezerlo()
    v._kezel(Esemeny(dt(HETFO, "10:05"), Tipus.RIADO, rendkivuli=r))
    assert v.riasztas and v._auto_riado
    v._kezel(Esemeny(dt(HETFO, "10:08"), Tipus.RIADO_VEGE, rendkivuli=r))
    assert not v.riasztas


def test_vezerlo_kezi_riasztast_nem_allitja_le_a_gyakorlat_vege():
    r = Rendkivuli("Tűzriadó", HETFO.isoformat(), "10:05", tipus="riado", riado_perc=3)
    v = AlVezerlo()
    v.riasztas_indit()
    v._kezel(Esemeny(dt(HETFO, "10:08"), Tipus.RIADO_VEGE, rendkivuli=r))
    assert v.riasztas


def test_vezerlo_halk_csengetes():
    v = AlVezerlo()
    v.b = alapertelmezett()
    v.zene = type("Zene", (), {"szol": False})()
    v._kezel(Esemeny(dt(HETFO, "09:40"), Tipus.KICSENGO, 2, hangero=20))
    assert v.csengetesek == [("beepitett:csengo", "2. óra – kicsengő (halkan)", 20)]
