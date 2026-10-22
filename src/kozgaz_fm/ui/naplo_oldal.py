__lazy_modules__ = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "kozgaz_fm.ui.elemek",
    "kozgaz_fm.utvonalak",
    "kozgaz_fm.vezerlo",
]

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QFont, QTextCursor
from PySide6.QtWidgets import QFileDialog, QPlainTextEdit

from kozgaz_fm.ui.elemek import Kartya, Oldal, gomb, sor
from kozgaz_fm.utvonalak import adat_mappa, naplo_fajl
from kozgaz_fm.vezerlo import Vezerlo


class NaploOldal(Oldal):
    def __init__(self, v: Vezerlo) -> None:
        super().__init__("Napló", "Minden csengetés, zene és bemondás nyoma. A teljes napló fájlban is megmarad.")
        self.v = v
        k = Kartya()
        self.szoveg = QPlainTextEdit()
        self.szoveg.setReadOnly(True)
        self.szoveg.setMinimumHeight(480)
        betu = QFont("monospace")
        betu.setStyleHint(QFont.StyleHint.Monospace)
        self.szoveg.setFont(betu)
        self.szoveg.setPlainText("\n".join(v.naplo))
        mappa = gomb("Adatmappa megnyitása", "mappa")
        mappa.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(adat_mappa()))))
        export = gomb("Napló mentése…", "le")
        export.clicked.connect(self._export)
        torol = gomb("Kijelzés törlése", "kuka")
        torol.clicked.connect(self.szoveg.clear)
        k.add(self.szoveg)
        k.add(sor(mappa, export, None, torol))
        self.add(k, 1)
        v.naplo_bejegyzes.connect(self._uj)

    def _uj(self, sor_: str) -> None:
        self.szoveg.appendPlainText(sor_)
        self.szoveg.moveCursor(QTextCursor.MoveOperation.End)

    def _export(self) -> None:
        ut, _ = QFileDialog.getSaveFileName(self, "Napló mentése", "kozgaz-fm-naplo.txt", "Szöveg (*.txt)")
        if not ut:
            return
        try:
            tartalom = naplo_fajl().read_text(encoding="utf-8")
        except FileNotFoundError:
            tartalom = "\n".join(self.v.naplo)
        with open(ut, "w", encoding="utf-8") as f:
            f.write(tartalom)
