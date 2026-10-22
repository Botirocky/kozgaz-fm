__lazy_modules__ = [
    "datetime",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "kozgaz_fm.beallitasok",
    "kozgaz_fm.orarend",
    "kozgaz_fm.ui.elemek",
    "kozgaz_fm.ui.tema",
    "kozgaz_fm.unnepek",
    "kozgaz_fm.vezerlo",
]

from datetime import date, timedelta

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QTextCharFormat
from PySide6.QtWidgets import (
    QCalendarWidget,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
)

from kozgaz_fm.beallitasok import Szunnap
from kozgaz_fm.orarend import napi_rend, szunnap_nev
from kozgaz_fm.ui.elemek import Kartya, Oldal, cimke, gomb, sor
from kozgaz_fm.ui.tema import SZIN
from kozgaz_fm.unnepek import unnepnapok
from kozgaz_fm.vezerlo import Vezerlo


def _qdate(d: date) -> QDate:
    return QDate(d.year, d.month, d.day)


def _pydate(q: QDate) -> date:
    return date(q.year(), q.month(), q.day())


def datum_mezo(d: date) -> QDateEdit:
    m = QDateEdit(_qdate(d))
    m.setCalendarPopup(True)
    m.setDisplayFormat("yyyy. MM. dd.")
    return m


class SzunnapAblak(QDialog):
    def __init__(self, parent, alap: date) -> None:
        super().__init__(parent)
        self.setWindowTitle("Szünnap / tanítási szünet")
        f = QFormLayout(self)
        f.setSpacing(12)
        self.nev = QLineEdit()
        self.nev.setPlaceholderText("pl. Őszi szünet, Igazgatói nap")
        self.tol = datum_mezo(alap)
        self.ig = datum_mezo(alap)
        self.tol.dateChanged.connect(lambda d: self.ig.setDate(max(d, self.ig.date())))
        f.addRow("Megnevezés:", self.nev)
        f.addRow("Első nap:", self.tol)
        f.addRow("Utolsó nap:", self.ig)
        gombok = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        gombok.accepted.connect(self.accept)
        gombok.rejected.connect(self.reject)
        f.addRow(gombok)

    def szunnap(self) -> Szunnap:
        tol, ig = sorted((_pydate(self.tol.date()), _pydate(self.ig.date())))
        return Szunnap(tol.isoformat(), ig.isoformat(), self.nev.text().strip() or "Szünnap")


class KivetelAblak(QDialog):
    def __init__(self, parent, alap: date, rendek: list[str]) -> None:
        super().__init__(parent)
        self.setWindowTitle("Kivételnap")
        f = QFormLayout(self)
        f.setSpacing(12)
        self.datum = datum_mezo(alap)
        self.rend = QComboBox()
        self.rend.addItem("Nincs csengetés", "")
        for nev in rendek:
            self.rend.addItem(nev, nev)
        f.addRow(cimke("Egy adott napon más csengetési rend (pl. rövidített órák), vagy szünnapon is "
                       "legyen csengetés (pl. szombati munkanap).", "halvany", sortores=True))
        f.addRow("Nap:", self.datum)
        f.addRow("Csengetési rend:", self.rend)
        gombok = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        gombok.accepted.connect(self.accept)
        gombok.rejected.connect(self.reject)
        f.addRow(gombok)


class NaptarOldal(Oldal):
    def __init__(self, v: Vezerlo) -> None:
        super().__init__("Naptár", "Tanítási szünetek, ünnepnapok és kivételnapok. Szünnapon nincs csengetés "
                         "és szünetzene, kivételnapon a megadott rend érvényes.")
        self.v = v
        racs = QGridLayout()
        racs.setSpacing(16)
        racs.addWidget(self._naptar_kartya(), 0, 0, 2, 1)
        racs.addWidget(self._szunnap_kartya(), 0, 1)
        racs.addWidget(self._kivetel_kartya(), 1, 1)
        racs.setColumnStretch(0, 1)
        racs.setColumnStretch(1, 1)
        self.add(racs)
        self.elrendezes.addStretch(1)
        self.frissit()

    def _naptar_kartya(self) -> Kartya:
        k = Kartya("Áttekintés")
        self.naptar = QCalendarWidget()
        self.naptar.setGridVisible(False)
        self.naptar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        self.naptar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.naptar.setMinimumHeight(340)
        self.naptar.selectionChanged.connect(self._nap_info)
        self.naptar.currentPageChanged.connect(lambda *_: self._szinez())
        self.info = cimke("", "alcim", sortores=True)
        jelmagyarazat = cimke(f"<span style='color:{SZIN['hiba']}'>■</span> szünnap   "
                              f"<span style='color:{SZIN['kiemelt']}'>■</span> kivételnap   "
                              f"<span style='color:{SZIN['halvany']}'>■</span> nincs csengetés", "halvany")
        k.add(self.naptar)
        k.add(self.info)
        k.add(jelmagyarazat)
        return k

    def _szunnap_kartya(self) -> Kartya:
        k = Kartya("Szünnapok és tanítási szünetek")
        self.szunnapok = QListWidget()
        self.szunnapok.setMinimumHeight(200)
        uj = gomb("Hozzáadás", "plusz", "fo")
        uj.clicked.connect(self._uj_szunnap)
        unnep = gomb("Ünnepnapok betöltése", "naptar", tipp="A következő 12 hónap magyar munkaszüneti napjai")
        unnep.clicked.connect(self._unnepek)
        torol = gomb("", "kuka", tipp="Kijelölt törlése")
        torol.clicked.connect(self._szunnap_torol)
        k.add(self.szunnapok)
        k.add(sor(uj, unnep, None, torol))
        return k

    def _kivetel_kartya(self) -> Kartya:
        k = Kartya("Kivételnapok")
        self.kivetelek = QListWidget()
        self.kivetelek.setMinimumHeight(150)
        uj = gomb("Hozzáadás", "plusz")
        uj.clicked.connect(self._uj_kivetel)
        torol = gomb("", "kuka", tipp="Kijelölt törlése")
        torol.clicked.connect(self._kivetel_torol)
        k.add(self.kivetelek)
        k.add(sor(uj, None, torol))
        return k

    def frissit(self) -> None:
        b = self.v.b
        ma = date.today().isoformat()
        b.szunnapok.sort(key=lambda s: s.tol)
        self.szunnapok.clear()
        for sz in b.szunnapok:
            idoszak = sz.tol if sz.tol == sz.ig else f"{sz.tol} – {sz.ig}"
            elem = QListWidgetItem(f"{sz.nev}\n{idoszak}")
            if sz.ig < ma:
                elem.setForeground(QColor(SZIN["halvany"]))
            self.szunnapok.addItem(elem)
        self.kivetelek.clear()
        self._kivetel_kulcsok = sorted(b.kivetelek)
        for d in self._kivetel_kulcsok:
            elem = QListWidgetItem(f"{d}   →   {b.kivetelek[d] or 'Nincs csengetés'}")
            if d < ma:
                elem.setForeground(QColor(SZIN["halvany"]))
            self.kivetelek.addItem(elem)
        self._szinez()
        self._nap_info()

    def _szinez(self) -> None:
        b = self.v.b
        self.naptar.setDateTextFormat(QDate(), QTextCharFormat())
        ev, honap = self.naptar.yearShown(), self.naptar.monthShown()
        elso = date(ev, honap, 1) - timedelta(days=7)
        for i in range(50):
            nap = elso + timedelta(days=i)
            f = QTextCharFormat()
            if nap.isoformat() in b.kivetelek:
                f.setForeground(QColor(SZIN["kiemelt"]))
                f.setFontWeight(700)
            elif szunnap_nev(b, nap) is not None:
                f.setForeground(QColor(SZIN["hiba"]))
                f.setFontWeight(700)
            elif napi_rend(b, nap) is None:
                f.setForeground(QColor(SZIN["halvany"]))
            else:
                continue
            self.naptar.setDateTextFormat(_qdate(nap), f)

    def _nap_info(self) -> None:
        b = self.v.b
        nap = _pydate(self.naptar.selectedDate())
        rend = napi_rend(b, nap)
        sz = szunnap_nev(b, nap)
        if nap.isoformat() in b.kivetelek:
            szoveg = f"Kivételnap: {rend.nev if rend else 'nincs csengetés'}"
        elif sz is not None:
            szoveg = f"Szünnap: {sz}"
        elif rend is None:
            szoveg = "Nincs csengetés"
        else:
            szoveg = f"{rend.nev} csengetési rend ({len(rend.orak)} óra)"
        self.info.setText(f"{nap:%Y. %m. %d.} – {szoveg}")

    def _uj_szunnap(self) -> None:
        ablak = SzunnapAblak(self, _pydate(self.naptar.selectedDate()))
        if ablak.exec() == QDialog.DialogCode.Accepted:
            self.v.b.szunnapok.append(ablak.szunnap())
            self.v.mentes()
            self.frissit()

    def _unnepek(self) -> None:
        b = self.v.b
        ma = date.today()
        meglevo = {(s.tol, s.ig) for s in b.szunnapok}
        uj = 0
        for ev in (ma.year, ma.year + 1):
            for nap, nev in unnepnapok(ev):
                if ma <= nap <= ma + timedelta(days=366) and (nap.isoformat(), nap.isoformat()) not in meglevo:
                    b.szunnapok.append(Szunnap(nap.isoformat(), nap.isoformat(), nev))
                    uj += 1
        self.v.mentes()
        self.frissit()
        QMessageBox.information(self, "Ünnepnapok", f"{uj} új ünnepnap hozzáadva. A tanítási szüneteket "
                                "(őszi, téli, tavaszi, nyári) a „Hozzáadás” gombbal add meg.")

    def _szunnap_torol(self) -> None:
        i = self.szunnapok.currentRow()
        if 0 <= i < len(self.v.b.szunnapok):
            self.v.b.szunnapok.pop(i)
            self.v.mentes()
            self.frissit()

    def _uj_kivetel(self) -> None:
        ablak = KivetelAblak(self, _pydate(self.naptar.selectedDate()), [r.nev for r in self.v.b.rendek])
        if ablak.exec() == QDialog.DialogCode.Accepted:
            self.v.b.kivetelek[_pydate(ablak.datum.date()).isoformat()] = ablak.rend.currentData() or ""
            self.v.mentes()
            self.frissit()

    def _kivetel_torol(self) -> None:
        i = self.kivetelek.currentRow()
        if 0 <= i < len(self._kivetel_kulcsok):
            self.v.b.kivetelek.pop(self._kivetel_kulcsok[i], None)
            self.v.mentes()
            self.frissit()
