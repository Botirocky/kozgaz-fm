from pathlib import Path

import pytest

from kozgaz_fm import sajat_hangok
from kozgaz_fm.sajat_hangok import SajatHangHiba


@pytest.fixture
def forras(tmp_path: Path) -> Path:
    ut = tmp_path / "forras" / "Iskolai csengő.mp3"
    ut.parent.mkdir()
    ut.write_bytes(b"ID3" + b"\0" * 100)
    return ut


@pytest.fixture
def mappa(tmp_path: Path) -> Path:
    return tmp_path / "hangok"


def test_hozzaad_bemasolja_es_listazza(forras: Path, mappa: Path) -> None:
    hang = sajat_hangok.hozzaad(forras, mappa=mappa)
    assert hang.ertek == "sajat:Iskolai csengő.mp3"
    assert hang.ut.read_bytes() == forras.read_bytes()
    forras.unlink()
    assert [h.nev for h in sajat_hangok.lista(mappa)] == ["Iskolai csengő"]
    assert sajat_hangok.ut(hang.ertek, mappa) == hang.ut


def test_azonos_nev_sorszamot_kap(forras: Path, mappa: Path) -> None:
    elso = sajat_hangok.hozzaad(forras, mappa=mappa)
    masodik = sajat_hangok.hozzaad(forras, mappa=mappa)
    assert elso.nev == "Iskolai csengő"
    assert masodik.nev == "Iskolai csengő (2)"


@pytest.mark.parametrize("nev, vart", [
    ("../../titok", "titok"),
    ('Rossz:név*?"', "Rossznév"),
    ("   ", "Saját hang"),
])
def test_veszelyes_nev_megtisztul(forras: Path, mappa: Path, nev: str, vart: str) -> None:
    hang = sajat_hangok.hozzaad(forras, nev, mappa=mappa)
    assert hang.ut.parent == mappa
    assert hang.nev == vart


def test_nem_hangfajl_es_ures_fajl_elutasitva(tmp_path: Path, mappa: Path) -> None:
    szoveg = tmp_path / "jegyzet.txt"
    szoveg.write_text("x")
    with pytest.raises(SajatHangHiba):
        sajat_hangok.hozzaad(szoveg, mappa=mappa)
    ures = tmp_path / "ures.wav"
    ures.touch()
    with pytest.raises(SajatHangHiba):
        sajat_hangok.hozzaad(ures, mappa=mappa)


def test_ut_nem_lep_ki_a_mappabol(mappa: Path) -> None:
    mappa.mkdir()
    (mappa.parent / "kivul.mp3").write_bytes(b"x")
    assert sajat_hangok.ut("sajat:../kivul.mp3", mappa) is None
    assert sajat_hangok.ut("beepitett:csengo", mappa) is None


def test_atnevez_es_torol(forras: Path, mappa: Path) -> None:
    hang = sajat_hangok.hozzaad(forras, mappa=mappa)
    uj = sajat_hangok.atnevez(hang.ertek, "Nagyszünet", mappa=mappa)
    assert uj.ertek == "sajat:Nagyszünet.mp3"
    assert not hang.ut.exists()
    assert sajat_hangok.atnevez(uj.ertek, "Nagyszünet", mappa=mappa) == uj
    sajat_hangok.torol(uj.ertek, mappa=mappa)
    assert sajat_hangok.lista(mappa) == []


def test_hang_ut_es_nev_kezeli_a_sajat_hangot(forras: Path, mappa: Path, monkeypatch) -> None:
    from kozgaz_fm import hang

    monkeypatch.setattr(sajat_hangok, "sajat_hangok_mappa", lambda: mappa)
    uj = sajat_hangok.hozzaad(forras)
    assert hang.hang_ut(uj.ertek) == uj.ut
    assert hang.hang_nev(uj.ertek) == "Iskolai csengő"
    sajat_hangok.torol(uj.ertek)
    assert hang.hang_ut(uj.ertek) is None
