from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFileDialog, QHBoxLayout, QWidget

from kozgaz_fm.beallitasok import BEEPITETT_HANGOK
from kozgaz_fm.hang import HANGFAJLOK, hang_nev
from kozgaz_fm.ui.elemek import ikon_gomb
from kozgaz_fm.vezerlo import Vezerlo

TALLOZAS = "__tallozas__"


class HangValaszto(QWidget):
    valtozott = Signal(str)

    def __init__(self, v: Vezerlo, ertek: str) -> None:
        super().__init__()
        self.v = v
        self._ertek = ertek
        e = QHBoxLayout(self)
        e.setContentsMargins(0, 0, 0, 0)
        e.setSpacing(8)
        self.lista = QComboBox()
        self.lista.setMinimumWidth(220)
        self.lista.activated.connect(self._valasztas)
        self.proba = ikon_gomb("lejatszas", "Meghallgatás", meret=16)
        self.proba.setProperty("szerep", "")
        self.proba.clicked.connect(self._proba)
        e.addWidget(self.lista, 1)
        e.addWidget(self.proba)
        self._feltolt()

    def ertek(self) -> str:
        return self._ertek

    def beallit(self, ertek: str) -> None:
        self._ertek = ertek
        self._feltolt()

    def _feltolt(self) -> None:
        self.lista.blockSignals(True)
        self.lista.clear()
        for kulcs, nev in BEEPITETT_HANGOK.items():
            self.lista.addItem(nev, f"beepitett:{kulcs}")
        if not self._ertek.startswith("beepitett:"):
            self.lista.addItem(f"Saját: {hang_nev(self._ertek)}", self._ertek)
        self.lista.addItem("Saját hangfájl tallózása…", TALLOZAS)
        self.lista.setCurrentIndex(max(0, self.lista.findData(self._ertek)))
        self.lista.blockSignals(False)

    def _valasztas(self, _index: int) -> None:
        adat = self.lista.currentData()
        if adat == TALLOZAS:
            szuro = "Hangfájlok (" + " ".join(f"*{k}" for k in HANGFAJLOK) + ")"
            ut, _ = QFileDialog.getOpenFileName(self, "Csengőhang kiválasztása", "", szuro)
            if not ut:
                self._feltolt()
                return
            adat = ut
        self._ertek = adat
        self._feltolt()
        self.valtozott.emit(adat)

    def _proba(self) -> None:
        if self.v.csengo.szol:
            self.v.csengo.megallit()
            return
        self.v.csengo.lejatszas(self._ertek, self.v.b.csengo_hangero)
