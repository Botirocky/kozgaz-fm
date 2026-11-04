from PySide6.QtWidgets import QMessageBox

from kozgaz_fm.ui.elemek import Kartya, Oldal, cimke, gomb
from kozgaz_fm.ui.tema import SZIN
from kozgaz_fm.vezerlo import Vezerlo


class RiasztasOldal(Oldal):
    def __init__(self, v: Vezerlo) -> None:
        super().__init__("Riasztás")
        self.v = v
        k = Kartya("Riasztás")
        k.add(cimke("Folyamatos riasztó hang minden hangszóróban, teljes hangerővel, amíg valaki le nem állítja. "
                    "A szünetzene azonnal elhallgat, és a riasztás alatt nincs csengetés és bemondás.",
                    "halvany", sortores=True))
        self.allapot = cimke("", sortores=True)
        k.add(self.allapot)
        self.gomb = gomb("Riasztás indítása", "riasztas", "veszely", "Riasztó hang a leállításig, megerősítés után")
        self.gomb.setMinimumHeight(64)
        self.gomb.clicked.connect(self._kattintas)
        k.add(self.gomb)
        self.add(k)
        t = Kartya("Tudnivalók")
        t.add(cimke("Előre beállított tűzriadó-gyakorlat: Naptár → Rendkívüli események → Hozzáadás, típusa "
                    "Tűzriadó-gyakorlat. A megadott időpontban magától indul, és a beállított idő után leáll.\n"
                    "A riasztó hangja a Csengetési rend oldalon cserélhető.\n"
                    "A webpanelről (telefonról) is indítható és leállítható.", "halvany", sortores=True))
        self.add(t)
        self.elrendezes.addStretch(1)
        v.riasztas_valtozott.connect(self._valtozott)
        self._valtozott(v.riasztas)

    def _kattintas(self) -> None:
        if self.v.riasztas:
            self.v.riasztas_leallit()
            return
        valasz = QMessageBox.warning(self, "Riasztás", "Biztosan elindítod a riasztó hangot?\n\n"
                                     "A zene leáll, a riasztás a leállításig szól.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                     QMessageBox.StandardButton.Cancel)
        if valasz == QMessageBox.StandardButton.Yes:
            self.v.riasztas_indit()

    def _valtozott(self, be: bool) -> None:
        self.gomb.setText("Riasztás leállítása" if be else "Riasztás indítása")
        self.gomb.setProperty("allapot", "aktiv" if be else "")
        self.gomb.style().unpolish(self.gomb)
        self.gomb.style().polish(self.gomb)
        self.allapot.setText("A riasztás most szól." if be else "Most nincs riasztás.")
        self.allapot.setStyleSheet(f"color: {SZIN['hiba']}; font-weight: 600;" if be else "")
