__lazy_modules__ = ["logging", "sys", "logging.handlers"]

import logging
import sys
from logging.handlers import RotatingFileHandler


def _naplozas() -> None:
    from kozgaz_fm.utvonalak import adat_mappa

    kezelo = RotatingFileHandler(adat_mappa() / "hibanaplo.txt", maxBytes=1_000_000, backupCount=2,
                                 encoding="utf-8")
    kezelo.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[kezelo, logging.StreamHandler()])


def main() -> int:
    if "--version" in sys.argv:
        from kozgaz_fm import __version__

        print(__version__)
        return 0
    if "--pin-torles" in sys.argv:
        from kozgaz_fm.beallitasok import Beallitasok

        b = Beallitasok.betoltes()
        b.admin_pin = ""
        b.mentes()
        print("A rendszergazda PIN törölve. Indítsd újra a Közgáz FM-et.")
        return 0
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    from PySide6.QtWidgets import QApplication

    from kozgaz_fm import APP_ID, APP_NEV, KESZITO, __version__
    from kozgaz_fm.beallitasok import Beallitasok
    from kozgaz_fm.utvonalak import beallitas_fajl

    QApplication.setApplicationName(APP_NEV)
    QApplication.setApplicationVersion(__version__)
    QApplication.setOrganizationName(KESZITO)
    QApplication.setDesktopFileName(APP_ID)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    csatlakozo = QLocalSocket()
    csatlakozo.connectToServer(APP_ID)
    if csatlakozo.waitForConnected(500):
        csatlakozo.write(b"elohoz")
        csatlakozo.flush()
        csatlakozo.waitForBytesWritten(500)
        return 0

    _naplozas()
    from kozgaz_fm import hatter
    from kozgaz_fm.ui.fo_ablak import FoAblak
    from kozgaz_fm.ui.tema import alkalmaz, betutipus, logo_ikon, stilus
    from kozgaz_fm.vezerlo import Vezerlo

    elso_inditas = not beallitas_fajl().exists()
    beallitasok = Beallitasok.betoltes()
    alkalmaz(beallitasok.tema)
    app.setStyle("Fusion")
    app.setFont(betutipus())
    app.setWindowIcon(logo_ikon())
    app.setStyleSheet(stilus())
    if elso_inditas:
        beallitasok.mentes()
    kioszk = "--kioszk" in sys.argv
    vezerlo = Vezerlo(beallitasok)
    ablak = FoAblak(vezerlo, kioszk)

    QLocalServer.removeServer(APP_ID)
    szerver = QLocalServer()
    szerver.listen(APP_ID)
    szerver.newConnection.connect(lambda: (szerver.nextPendingConnection(), ablak.elohoz()))

    vezerlo.indit()
    if kioszk:
        ablak.showFullScreen()
    elif "--talcan" not in sys.argv:
        ablak.show()
    kod = app.exec()
    hatter.leallit()
    return kod


if __name__ == "__main__":
    raise SystemExit(main())
