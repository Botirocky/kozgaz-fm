__lazy_modules__ = [
    "datetime",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "kozgaz_fm.orarend",
    "kozgaz_fm.ui.elemek",
    "kozgaz_fm.ui.tema",
    "kozgaz_fm.ui.vezerlopult",
    "kozgaz_fm.vezerlo",
]

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QProgressBar, QVBoxLayout, QWidget

from kozgaz_fm.orarend import Szakasz, allapot
from kozgaz_fm.ui.elemek import cimke, sor
from kozgaz_fm.ui.tema import SOTET as SZIN
from kozgaz_fm.ui.tema import logo_pixmap
from kozgaz_fm.ui.vezerlopult import HONAPOK, NAPOK, idotartam
from kozgaz_fm.vezerlo import Vezerlo


class Kijelzo(QWidget):
    def __init__(self, v: Vezerlo) -> None:
        super().__init__()
        self.v = v
        self.setWindowTitle("Közgáz FM – kijelző")
        self.setCursor(Qt.CursorShape.BlankCursor)
        self.setStyleSheet(f"background: {SZIN['hatter']};")
        e = QVBoxLayout(self)
        e.setContentsMargins(80, 60, 80, 60)
        e.setSpacing(18)
        self.logo = cimke()
        self.cim = cimke(v.b.kijelzo_cim)
        self.cim.setStyleSheet(f"font-size: 30pt; font-weight: 800; color: {SZIN['kek']};")
        self.datum = cimke()
        self.datum.setStyleSheet(f"font-size: 22pt; color: {SZIN['halvany']};")
        e.addLayout(sor(self.logo, self.cim, None, self.datum, terkoz=24))
        e.addStretch(1)
        self.ora = cimke()
        self.ora.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.szakasz = cimke()
        self.szakasz.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hatra = cimke()
        self.hatra.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.halad = QProgressBar()
        self.halad.setTextVisible(False)
        self.halad.setRange(0, 1000)
        self.halad.setFixedHeight(18)
        e.addWidget(self.ora)
        e.addWidget(self.szakasz)
        e.addWidget(self.hatra)
        e.addWidget(self.halad)
        e.addStretch(1)
        self.zene = cimke()
        self.zene.setStyleSheet(f"font-size: 20pt; color: {SZIN['kiemelt']};")
        self.kovetkezo = cimke()
        self.kovetkezo.setStyleSheet(f"font-size: 20pt; color: {SZIN['halvany']};")
        e.addLayout(sor(self.zene, None, self.kovetkezo))
        v.zene.szam_valtozott.connect(self._szam)

    def _szam(self, cim: str, _forras: str = "") -> None:
        self.zene.setText(f"Most szól: {cim}")

    def _meretez(self) -> None:
        m = self.height() or 1080
        self.logo.setPixmap(logo_pixmap(max(80, m // 9)))
        self.ora.setStyleSheet(f"font-size: {max(60, m // 6)}px; font-weight: 800; color: {SZIN['szoveg']};")
        self.szakasz.setStyleSheet(f"font-size: {max(30, m // 16)}px; font-weight: 750; color: {SZIN['kiemelt']};")
        self.hatra.setStyleSheet(f"font-size: {max(24, m // 22)}px; color: {SZIN['szoveg']};")

    def showEvent(self, esemeny) -> None:
        super().showEvent(esemeny)
        self._meretez()
        self.frissit()

    def resizeEvent(self, esemeny) -> None:
        super().resizeEvent(esemeny)
        self._meretez()

    def frissit(self) -> None:
        if not self.isVisible():
            return
        most = datetime.now()
        a = allapot(self.v.b, most)
        self.cim.setText(self.v.b.kijelzo_cim)
        self.datum.setText(f"{HONAPOK[most.month - 1]} {most.day}., {NAPOK[most.weekday()]}")
        self.ora.setText(f"{most:%H:%M}")
        self.szakasz.setText("RIASZTÁS" if self.v.riasztas else a.cim)
        hatra = a.hatralevo(most)
        if a.szakasz is Szakasz.ORA:
            self.hatra.setText(f"Kicsengetésig {idotartam(hatra)}")
        elif a.szakasz in (Szakasz.SZUNET, Szakasz.REGGEL):
            self.hatra.setText(f"Becsengetésig {idotartam(hatra)}")
        else:
            self.hatra.setText("")
        self.halad.setVisible(a.szakasz in (Szakasz.ORA, Szakasz.SZUNET))
        self.halad.setValue(int(a.haladas(most) * 1000))
        if not self.v.zene.szol:
            self.zene.setText("")
        elif not self.zene.text() and self.v.zene.most_cim:
            self.zene.setText(f"Most szól: {self.v.zene.most_cim}")
        if a.kovetkezo and a.kovetkezo.ido.date() == most.date():
            self.kovetkezo.setText(f"Következő csengetés: {a.kovetkezo.ido:%H:%M}")
        else:
            self.kovetkezo.setText("")

    def keyPressEvent(self, esemeny: QKeyEvent) -> None:
        if esemeny.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Q):
            self.close()
        else:
            super().keyPressEvent(esemeny)

    def mouseDoubleClickEvent(self, esemeny: QMouseEvent) -> None:
        self.close()
