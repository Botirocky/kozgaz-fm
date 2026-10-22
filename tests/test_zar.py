__lazy_modules__ = ["pytest", "kozgaz_fm", "kozgaz_fm.zar"]

import pytest

from kozgaz_fm import zar
from kozgaz_fm.zar import PinHiba, Zar


@pytest.fixture
def tarolt() -> str:
    return zar.pin_hash("4821", kor=1000)


@pytest.mark.parametrize("pin, vart", [
    ("1234", True),
    ("12345678", True),
    ("123", False),
    ("123456789", False),
    ("12a4", False),
    (" 1234", False),
    ("", False),
])
def test_pin_ervenyes(pin: str, vart: bool) -> None:
    assert zar.pin_ervenyes(pin) is vart


def test_hash_nem_tartalmazza_a_pint_es_sozott() -> None:
    elso = zar.pin_hash("4821", kor=1000)
    masodik = zar.pin_hash("4821", kor=1000)
    assert "4821" not in elso
    assert elso != masodik
    assert elso.startswith("pbkdf2_sha256$1000$")


def test_ervenytelen_pin_nem_hashelheto() -> None:
    with pytest.raises(PinHiba):
        zar.pin_hash("12")


@pytest.mark.parametrize("pin, vart", [("4821", True), ("4822", False), ("", False), ("48210", False)])
def test_pin_ellenoriz(tarolt: str, pin: str, vart: bool) -> None:
    assert zar.pin_ellenoriz(pin, tarolt) is vart


@pytest.mark.parametrize("hibas", ["", "valami", "pbkdf2_sha256$x$y$z", "md5$1$aa$bb", "pbkdf2_sha256$1000$zz$zz"])
def test_serult_tarolt_ertek_nem_old_fel(hibas: str) -> None:
    assert zar.pin_ellenoriz("4821", hibas) is False


class Ora:
    def __init__(self) -> None:
        self.most = 1000.0

    def __call__(self) -> float:
        return self.most


def test_tul_sok_hiba_utan_tiltas_majd_lejar(tarolt: str) -> None:
    ora = Ora()
    z = Zar(ido=ora)
    for _ in range(zar.MAX_HIBA):
        assert z.probal("0000", tarolt) is False
    with pytest.raises(PinHiba, match="várj"):
        z.probal("4821", tarolt)
    assert z.hatralevo_tiltas() == zar.TILTAS_MP
    ora.most += zar.TILTAS_MP + 1
    assert z.hatralevo_tiltas() == 0
    assert z.probal("4821", tarolt) is True


def test_sikeres_probalkozas_nullazza_a_hibakat(tarolt: str) -> None:
    z = Zar(ido=Ora())
    for _ in range(zar.MAX_HIBA - 1):
        z.probal("0000", tarolt)
    assert z.probal("4821", tarolt) is True
    for _ in range(zar.MAX_HIBA - 1):
        assert z.probal("0000", tarolt) is False
    assert z.probal("4821", tarolt) is True


def test_ures_tarolt_ertek_eseten_nincs_zar() -> None:
    assert zar.van_pin("") is False
    assert zar.van_pin(zar.pin_hash("1234", kor=1000)) is True
