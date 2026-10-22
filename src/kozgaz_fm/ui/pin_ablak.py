__lazy_modules__ = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "kozgaz_fm",
    "kozgaz_fm.ui.elemek",
    "kozgaz_fm.ui.tema",
    "kozgaz_fm.zar",
]

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit, QVBoxLayout, QWidget

from kozgaz_fm import zar
from kozgaz_fm.ui.elemek import cimke
from kozgaz_fm.ui.tema import SZIN
from kozgaz_fm.zar import PinHiba, Zar


def _pin_mezo() -> QLineEdit:
    mezo = QLineEdit()
    mezo.setEchoMode(QLineEdit.EchoMode.Password)
    mezo.setMaxLength(zar.MAX_HOSSZ)
    mezo.setValidator(QRegularExpressionValidator(QRegularExpression(rf"\d{{0,{zar.MAX_HOSSZ}}}")))
    mezo.setAlignment(Qt.AlignmentFlag.AlignCenter)
    mezo.setStyleSheet("font-size: 18pt; letter-spacing: 6px; padding: 8px;")
    mezo.setMinimumWidth(240)
    return mezo


class _PinAlap(QDialog):
    def __init__(self, szulo: QWidget | None, cim: str, leiras: str, gomb_szoveg: str) -> None:
        super().__init__(szulo)
        self.setWindowTitle(cim)
        self.setModal(True)
        self.elrendezes = QVBoxLayout(self)
        self.elrendezes.setContentsMargins(24, 22, 24, 20)
        self.elrendezes.setSpacing(12)
        fejlec = cimke(cim, "alcim")
        self.elrendezes.addWidget(fejlec)
        self.elrendezes.addWidget(cimke(leiras, "halvany", sortores=True))
        self.hiba = cimke("")
        self.hiba.setStyleSheet(f"color: {SZIN['hiba']};")
        self.hiba.setWordWrap(True)
        self.gombok = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok = self.gombok.button(QDialogButtonBox.StandardButton.Ok)
        ok.setText(gomb_szoveg)
        ok.setProperty("szerep", "fo")
        self.gombok.button(QDialogButtonBox.StandardButton.Cancel).setText("Mégse")
        self.gombok.accepted.connect(self._ok)
        self.gombok.rejected.connect(self.reject)

    def _vege(self) -> None:
        self.elrendezes.addWidget(self.hiba)
        self.elrendezes.addWidget(self.gombok)
        self.setFixedWidth(380)

    def _hibat_mutat(self, szoveg: str) -> None:
        self.hiba.setText(szoveg)

    def _ok(self) -> None:
        raise NotImplementedError


class FeloldoAblak(_PinAlap):
    def __init__(self, szulo: QWidget | None, tarolt: str, zar_: Zar) -> None:
        super().__init__(szulo, "Rendszergazda PIN", "Ez az oldal PIN-kóddal védett. Add meg a PIN-t a "
                         "beállítások feloldásához.", "Feloldás")
        self._tarolt = tarolt
        self._zar = zar_
        self.pin = _pin_mezo()
        self.elrendezes.addWidget(self.pin)
        self._vege()
        self.pin.setFocus()

    def _ok(self) -> None:
        try:
            jo = self._zar.probal(self.pin.text(), self._tarolt)
        except PinHiba as e:
            self._hibat_mutat(str(e))
            self.pin.clear()
            return
        if jo:
            self.accept()
            return
        self._hibat_mutat("Hibás PIN.")
        self.pin.clear()
        self.pin.setFocus()


class UjPinAblak(_PinAlap):
    def __init__(self, szulo: QWidget | None) -> None:
        super().__init__(szulo, "PIN-kód beállítása", f"{zar.MIN_HOSSZ}–{zar.MAX_HOSSZ} számjegy. A "
                         "Vezérlőpult (csengetés, zene, bemondás) PIN nélkül is használható marad.", "Mentés")
        self.pin = _pin_mezo()
        self.ujra = _pin_mezo()
        self.elrendezes.addWidget(cimke("Új PIN:"))
        self.elrendezes.addWidget(self.pin)
        self.elrendezes.addWidget(cimke("Még egyszer:"))
        self.elrendezes.addWidget(self.ujra)
        self._vege()
        self.tarolt = ""
        self.pin.setFocus()

    def _ok(self) -> None:
        if not zar.pin_ervenyes(self.pin.text()):
            self._hibat_mutat(f"A PIN {zar.MIN_HOSSZ}–{zar.MAX_HOSSZ} számjegyből álljon.")
            return
        if self.pin.text() != self.ujra.text():
            self._hibat_mutat("A két PIN nem egyezik.")
            self.ujra.clear()
            self.ujra.setFocus()
            return
        self.tarolt = zar.pin_hash(self.pin.text())
        self.accept()
