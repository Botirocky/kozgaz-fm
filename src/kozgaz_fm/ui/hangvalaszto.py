from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QWidget,
)

from kozgaz_fm import sajat_hangok
from kozgaz_fm.beallitasok import BEEPITETT_HANGOK
from kozgaz_fm.hang import HANGFAJLOK, hang_nev
from kozgaz_fm.sajat_hangok import SajatHangHiba
from kozgaz_fm.ui.elemek import Kartya, cimke, gomb, ikon_gomb, sor
from kozgaz_fm.ui.tema import ikon
from kozgaz_fm.vezerlo import Vezerlo

HOZZAADAS = "__hozzaadas__"
MEZO_NEVEK = {"hang_becsengo": "becsengő", "hang_kicsengo": "kicsengő", "hang_jelzo": "jelzőcsengő",
              "hang_gong": "bemondás előtti gong", "hang_riasztas": "riasztás"}


def _szuro() -> str:
    return "Hangfájlok (" + " ".join(f"*{k}" for k in HANGFAJLOK) + ")"


def sajat_hangok_tallozasa(szulo: QWidget, v: Vezerlo, tobb: bool = True) -> list[sajat_hangok.SajatHang]:
    if tobb:
        utak, _ = QFileDialog.getOpenFileNames(szulo, "Saját hangok hozzáadása", "", _szuro())
    else:
        ut, _ = QFileDialog.getOpenFileName(szulo, "Saját hang hozzáadása", "", _szuro())
        utak = [ut] if ut else []
    hozzaadva, hibak = [], []
    for ut in utak:
        try:
            hozzaadva.append(v.sajat_hang_hozzaadas(Path(ut)))
        except SajatHangHiba as e:
            hibak.append(str(e))
    if hibak:
        QMessageBox.warning(szulo, "Saját hangok", "\n".join(hibak))
    return hozzaadva


class HangValaszto(QWidget):
    valtozott = Signal(str)

    def __init__(self, v: Vezerlo, ertek: str, mezo: str | None = None) -> None:
        super().__init__()
        self.v = v
        self._ertek = ertek
        self._mezo = mezo
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
        v.hangok_valtoztak.connect(self._feltolt)
        self._feltolt()

    def ertek(self) -> str:
        return self._ertek

    def beallit(self, ertek: str) -> None:
        self._ertek = ertek
        self._feltolt()

    def _feltolt(self) -> None:
        if self._mezo:
            self._ertek = getattr(self.v.b, self._mezo)
        self.lista.blockSignals(True)
        self.lista.clear()
        for kulcs, nev in BEEPITETT_HANGOK.items():
            self.lista.addItem(nev, f"beepitett:{kulcs}")
        sajatok = sajat_hangok.lista()
        if sajatok:
            self.lista.insertSeparator(self.lista.count())
            zene = ikon("zene")
            for h in sajatok:
                self.lista.addItem(zene, h.nev, h.ertek)
        if self.lista.findData(self._ertek) < 0 and not self._ertek.startswith("beepitett:"):
            self.lista.addItem(f"Hiányzó: {hang_nev(self._ertek)}", self._ertek)
        self.lista.insertSeparator(self.lista.count())
        self.lista.addItem(ikon("plusz"), "Saját hang hozzáadása…", HOZZAADAS)
        self.lista.setCurrentIndex(max(0, self.lista.findData(self._ertek)))
        self.lista.blockSignals(False)

    def _valasztas(self, _index: int) -> None:
        adat = self.lista.currentData()
        if adat == HOZZAADAS:
            uj = sajat_hangok_tallozasa(self, self.v, tobb=False)
            if not uj:
                self._feltolt()
                return
            adat = uj[0].ertek
        self._ertek = adat
        self.valtozott.emit(adat)
        self._feltolt()

    def _proba(self) -> None:
        if self.v.csengo.szol:
            self.v.csengo.megallit()
            return
        if not self.v.csengo.lejatszas(self._ertek, self.v.b.csengo_hangero):
            QMessageBox.warning(self, "Meghallgatás", "Ez a hangfájl nem található.")


class SajatHangokKartya(Kartya):
    def __init__(self, v: Vezerlo) -> None:
        super().__init__("Saját hangok")
        self.v = v
        self.add(cimke("Tegyél be saját csengőhangot, dallamot vagy jingle-t (MP3, WAV, M4A, OGG…). A program "
                       "bemásolja a saját mappájába, így az eredeti fájlt nyugodtan áthelyezheted. A betett hangok "
                       "minden csengő-listában megjelennek.", "halvany", sortores=True))
        self.lista = QListWidget()
        self.lista.setMinimumHeight(150)
        self.lista.itemDoubleClicked.connect(lambda _e: self._proba())
        self.lista.currentRowChanged.connect(lambda _s: self._gombok())
        self.add(self.lista)
        self.ures = cimke("Még nincs saját hang. A „Hozzáadás…” gombbal tehetsz be.", "halvany")
        self.add(self.ures)
        hozzaad = gomb("Hozzáadás…", "plusz", "fo")
        hozzaad.clicked.connect(self._hozzaad)
        self.proba = gomb("Meghallgatás", "lejatszas")
        self.proba.clicked.connect(self._proba)
        self.atnevez = gomb("Átnevezés")
        self.atnevez.clicked.connect(self._atnevez)
        self.torol = gomb("", "kuka", tipp="Törlés")
        self.torol.clicked.connect(self._torol)
        self.add(sor(hozzaad, self.proba, self.atnevez, self.torol, None))
        v.hangok_valtoztak.connect(self.frissit)
        self.frissit()

    def _kivalasztott(self) -> str | None:
        elem = self.lista.currentItem()
        return elem.data(Qt.ItemDataRole.UserRole) if elem else None

    def frissit(self, valasztott: str | None = None) -> None:
        elozo = valasztott or self._kivalasztott()
        self.lista.blockSignals(True)
        self.lista.clear()
        zene = ikon("zene")
        for h in sajat_hangok.lista():
            hasznalat = [MEZO_NEVEK.get(m, m) for m in self.v.sajat_hang_hasznalat(h.ertek)]
            felirat = h.nev + (f"   (használja: {', '.join(hasznalat)})" if hasznalat else "")
            elem = QListWidgetItem(zene, felirat)
            elem.setData(Qt.ItemDataRole.UserRole, h.ertek)
            elem.setToolTip(str(h.ut))
            self.lista.addItem(elem)
            if h.ertek == elozo:
                self.lista.setCurrentItem(elem)
        if self.lista.currentRow() < 0 and self.lista.count():
            self.lista.setCurrentRow(0)
        self.lista.blockSignals(False)
        ures = self.lista.count() == 0
        self.lista.setVisible(not ures)
        self.ures.setVisible(ures)
        self._gombok()

    def _gombok(self) -> None:
        van = self._kivalasztott() is not None
        for g in (self.proba, self.atnevez, self.torol):
            g.setEnabled(van)

    def _hozzaad(self) -> None:
        uj = sajat_hangok_tallozasa(self, self.v)
        if uj:
            self.frissit(uj[-1].ertek)

    def _proba(self) -> None:
        ertek = self._kivalasztott()
        if ertek is None:
            return
        if self.v.csengo.szol:
            self.v.csengo.megallit()
            return
        self.v.csengo.lejatszas(ertek, self.v.b.csengo_hangero)

    def _atnevez(self) -> None:
        ertek = self._kivalasztott()
        if ertek is None:
            return
        nev, ok = QInputDialog.getText(self, "Átnevezés", "Új név:", text=sajat_hangok.nev(ertek))
        if not ok or not nev.strip():
            return
        try:
            hang = self.v.sajat_hang_atnevezes(ertek, nev)
        except SajatHangHiba as e:
            QMessageBox.warning(self, "Átnevezés", str(e))
            return
        self.frissit(hang.ertek)

    def _torol(self) -> None:
        ertek = self._kivalasztott()
        if ertek is None:
            return
        hasznalat = [MEZO_NEVEK.get(m, m) for m in self.v.sajat_hang_hasznalat(ertek)]
        kerdes = f"Törlöd ezt a hangot: „{sajat_hangok.nev(ertek)}”?"
        if hasznalat:
            kerdes += (f"\n\nEz most a(z) {', '.join(hasznalat)} hangja – helyette a beépített alaphang "
                       "fog szólni.")
        if QMessageBox.question(self, "Törlés", kerdes) != QMessageBox.StandardButton.Yes:
            return
        try:
            self.v.sajat_hang_torles(ertek)
        except SajatHangHiba as e:
            QMessageBox.warning(self, "Törlés", str(e))

