__lazy_modules__ = [
    "collections.abc",
    "datetime",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "kozgaz_fm",
    "kozgaz_fm.orarend",
    "kozgaz_fm.ui.elemek",
    "kozgaz_fm.ui.tema",
    "kozgaz_fm.vezerlo",
]

from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QFrame, QProgressBar, QTextBrowser, QVBoxLayout

from kozgaz_fm import __version__, frissites
from kozgaz_fm.orarend import allapot
from kozgaz_fm.ui.elemek import cimke, gomb, sor
from kozgaz_fm.ui.tema import SZIN, szam_betu
from kozgaz_fm.vezerlo import Vezerlo

HONAPOK = ["január", "február", "március", "április", "május", "június", "július", "augusztus", "szeptember",
           "október", "november", "december"]


def _datum(iso: str) -> str:
    try:
        nap = datetime.strptime(iso, "%Y-%m-%d")
    except ValueError:
        return ""
    return f"{nap.year}. {HONAPOK[nap.month - 1]} {nap.day}."


class FrissitesAblak(QDialog):
    def __init__(self, szulo, v: Vezerlo, jogosultsag: Callable[[], bool]) -> None:
        super().__init__(szulo)
        self.v = v
        self.f = v.frissito
        self._jogosultsag = jogosultsag
        self.setWindowTitle("Frissítés")
        self.setMinimumSize(600, 560)
        e = QVBoxLayout(self)
        e.setContentsMargins(28, 24, 28, 22)
        e.setSpacing(14)
        self.cim = cimke("", "cim")
        e.addWidget(self.cim)
        verziok = QFrame()
        verziok.setProperty("szerep", "kartya")
        ve = QVBoxLayout(verziok)
        ve.setContentsMargins(18, 14, 18, 14)
        ve.setSpacing(4)
        self.verzio_sor = cimke()
        self.verzio_sor.setFont(szam_betu(13))
        self.datum_sor = cimke("", "halvany")
        ve.addWidget(self.verzio_sor)
        ve.addWidget(self.datum_sor)
        e.addWidget(verziok)
        e.addWidget(cimke("Mi változott?", "szekcio"))
        self.ujdonsagok = QTextBrowser()
        self.ujdonsagok.setOpenExternalLinks(True)
        e.addWidget(self.ujdonsagok, 1)
        self.figyelmeztetes = cimke("", sortores=True)
        self.figyelmeztetes.setStyleSheet(f"color: {SZIN['figyelem']};")
        e.addWidget(self.figyelmeztetes)
        self.allapot = cimke("", "halvany", sortores=True)
        e.addWidget(self.allapot)
        self.halad = QProgressBar()
        self.halad.setRange(0, 1000)
        self.halad.setTextVisible(False)
        self.halad.hide()
        e.addWidget(self.halad)
        self.telepit_gomb = gomb("Telepítés most", "le", "fo")
        self.telepit_gomb.clicked.connect(self._telepites)
        self.keres_gomb = gomb("Keresés újra", "frissites")
        self.keres_gomb.clicked.connect(lambda: self.f.kereses(kezi=True))
        self.oldal_gomb = gomb("Kiadási oldal", "kulso")
        self.oldal_gomb.clicked.connect(self._oldal)
        kesobb = gomb("Később")
        kesobb.clicked.connect(self.reject)
        e.addLayout(sor(self.oldal_gomb, self.keres_gomb, None, kesobb, self.telepit_gomb))
        self.f.kiadas_valtozott.connect(lambda _k: self._frissit())
        self.f.allapot_valtozott.connect(self._allapot)
        self.f.halad.connect(self._halad)
        self._frissit()

    def _frissit(self) -> None:
        k = self.f.kiadas
        self.allapot.setText(self.f.allapot)
        if k is None:
            self.cim.setText("A program naprakész")
            self.verzio_sor.setText(f"Telepített verzió: {__version__}")
            self.datum_sor.setText("Új verzió esetén itt jelenik meg, mi változott.")
            self.ujdonsagok.setMarkdown("")
            self.ujdonsagok.setPlaceholderText("Nincs újabb kiadás.")
            self.figyelmeztetes.hide()
            self.telepit_gomb.setEnabled(False)
            self.oldal_gomb.setEnabled(False)
            return
        self.cim.setText("Új verzió érhető el")
        self.verzio_sor.setText(f"{__version__}  →  {k.verzio}")
        datum = _datum(k.datum)
        self.datum_sor.setText(f"Kiadva: {datum}" if datum else k.cim)
        self.ujdonsagok.setMarkdown(k.leiras or "A kiadáshoz nincs leírás.")
        self.oldal_gomb.setEnabled(bool(k.oldal))
        if not self.f.tamogatott:
            self.figyelmeztetes.setText("Ennél a futtatási módnál nincs beépített telepítés. Töltsd le a kiadási "
                                        "oldalról.")
            self.figyelmeztetes.show()
            self.telepit_gomb.setEnabled(False)
            return
        most = datetime.now()
        a = allapot(self.v.b, most)
        kovetkezo = a.kovetkezo.ido if a.kovetkezo else None
        if frissites.biztonsagos_ido(a.szakasz.value, kovetkezo, most, self.v.zene.szol, self.v.riasztas):
            self.figyelmeztetes.setText("A telepítés után a program magától újraindul (pár másodpercig nincs "
                                        "csengetés).")
            self.figyelmeztetes.setStyleSheet(f"color: {SZIN['halvany']};")
        else:
            self.figyelmeztetes.setText("Most tanítási idő van, vagy hamarosan csengetés lesz. Javasolt tanítás után "
                                        "telepíteni – az automatikus frissítés magától kivárja ezt.")
            self.figyelmeztetes.setStyleSheet(f"color: {SZIN['figyelem']};")
        self.figyelmeztetes.show()
        self.telepit_gomb.setEnabled(not self.f.fut)

    def _allapot(self, szoveg: str) -> None:
        self.allapot.setText(szoveg)
        if not self.f.fut:
            self.keres_gomb.setEnabled(True)
            self.telepit_gomb.setEnabled(self.f.kiadas is not None and self.f.tamogatott)
            self.halad.hide()

    def _halad(self, arany: float) -> None:
        self.halad.show()
        self.halad.setValue(int(arany * 1000))

    def _telepites(self) -> None:
        if self.f.kiadas is None or not self._jogosultsag():
            return
        self.telepit_gomb.setEnabled(False)
        self.keres_gomb.setEnabled(False)
        self.halad.setValue(0)
        self.halad.show()
        self.f.telepites()

    def _oldal(self) -> None:
        if self.f.kiadas and self.f.kiadas.oldal:
            QDesktopServices.openUrl(QUrl(self.f.kiadas.oldal))

    def keyPressEvent(self, esemeny) -> None:
        if esemeny.key() == Qt.Key.Key_Escape and self.f.fut:
            return
        super().keyPressEvent(esemeny)
