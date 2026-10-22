__lazy_modules__ = ["kozgaz_fm"]

from kozgaz_fm import rendszer


def test_kozgazfm_os_beolvasas(tmp_path) -> None:
    assert rendszer.kozgazfm_os(tmp_path) is None
    (tmp_path / "os-verzio").write_text("KOZGAZFM_OS_VERZIO=0.3.0\nEPITVE=2026-10-22T20:00Z\nhibas sor\n")
    assert rendszer.kozgazfm_os(tmp_path) == {"KOZGAZFM_OS_VERZIO": "0.3.0", "EPITVE": "2026-10-22T20:00Z"}


def test_alap_jelszo_jelzo(tmp_path) -> None:
    assert rendszer.alap_jelszo(tmp_path) is False
    (tmp_path / "alap-jelszo").touch()
    assert rendszer.alap_jelszo(tmp_path) is True
