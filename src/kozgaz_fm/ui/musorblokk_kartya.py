__lazy_modules__ = [
    "PySide6.QtCore",
    "PySide6.QtWidgets",
    "kozgaz_fm.beallitasok",
    "kozgaz_fm.orarend",
    "kozgaz_fm.ui.elemek",
    "kozgaz_fm.ui.tema",
    "kozgaz_fm.vezerlo",
]

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QRadioButton,
)

from kozgaz_fm.beallitasok import NAPOK, Beallitasok, Musorblokk
from kozgaz_fm.orarend import szunet_nev
from kozgaz_fm.ui.elemek import Kartya, cimke, gomb, sor
from kozgaz_fm.ui.tema import SZIN, ikon
from kozgaz_fm.vezerlo import Vezerlo


def szunetek_szama(b: Beallitasok) -> int:
    return max((len(r.orak) for r in b.rendek), default=8)


def blokk_leiras(m: Musorblokk) -> str:
    napok = "minden nap" if len(m.napok) == 7 else ", ".join(NAPOK[i][:3] for i in sorted(m.napok))
    szunetek = "minden szünetben" if not m.szunetek else ", ".join(szunet_nev(s) for s in sorted(m.szunetek))
    return f"{napok} · {szunetek}"


class MusorblokkAblak(QDialog):
    def __init__(self, parent, b: Beallitasok, m: Musorblokk | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Műsorblokk")
        self.setMinimumWidth(620)
        nevek = [f.nev for f in b.forrasok if f.aktiv]
        m = m or Musorblokk("", nevek[0] if nevek else "")
        f = QFormLayout(self)
        f.setSpacing(12)
        self.nev = QLineEdit(m.nev)
        self.nev.setPlaceholderText("pl. Nagyszüneti kérések, Reggeli nyugi, Pénteki buli")
        self.forras = QComboBox()
        for nev in nevek:
            self.forras.addItem(nev, nev)
        if m.forras and m.forras not in nevek:
            self.forras.addItem(f"{m.forras} (nincs ilyen bekapcsolt forrás)", m.forras)
        self.forras.setCurrentIndex(max(0, self.forras.findData(m.forras)))
        self.napok = [QCheckBox(n) for n in NAPOK]
        for i, k in enumerate(self.napok):
            k.setChecked(i in m.napok)
        self.mind = QRadioButton("Minden szünetben")
        self.valasztott = QRadioButton("Csak ezekben:")
        csoport = QButtonGroup(self)
        csoport.addButton(self.mind)
        csoport.addButton(self.valasztott)
        (self.valasztott if m.szunetek else self.mind).setChecked(True)
        self.szunetek: list[QCheckBox] = []
        racs = QGridLayout()
        racs.setHorizontalSpacing(14)
        for s in range(szunetek_szama(b)):
            k = QCheckBox(szunet_nev(s))
            k.setChecked(s in m.szunetek)
            k.toggled.connect(lambda be: be and self.valasztott.setChecked(True))
            self.szunetek.append(k)
            racs.addWidget(k, s // 4, s % 4)
        f.addRow("Megnevezés:", self.nev)
        f.addRow("Ez a forrás szóljon:", self.forras)
        napok = QGridLayout()
        napok.setHorizontalSpacing(14)
        for i, k in enumerate(self.napok):
            napok.addWidget(k, i // 4, i % 4)
        f.addRow("Napok:", napok)
        f.addRow(self.mind)
        f.addRow(self.valasztott)
        f.addRow(racs)
        f.addRow(cimke("A „Tanítás előtt” a reggeli zene (ha be van kapcsolva), az „1. szünet” az 1. óra utáni, "
                       "és így tovább. Rövidített napokon is a szünet sorszáma számít, nem az időpont.",
                       "halvany", sortores=True))
        gombok = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        gombok.accepted.connect(self._ok)
        gombok.rejected.connect(self.reject)
        f.addRow(gombok)
        self.aktiv = m.aktiv

    def _ok(self) -> None:
        if not self.forras.currentData():
            QMessageBox.warning(self, "Műsorblokk", "Előbb adj hozzá egy zeneforrást.")
            return
        if not any(k.isChecked() for k in self.napok):
            QMessageBox.warning(self, "Műsorblokk", "Jelölj ki legalább egy napot.")
            return
        if self.valasztott.isChecked() and not any(k.isChecked() for k in self.szunetek):
            QMessageBox.warning(self, "Műsorblokk", "Jelölj ki legalább egy szünetet.")
            return
        self.accept()

    def blokk(self) -> Musorblokk:
        return Musorblokk(
            nev=self.nev.text().strip() or self.forras.currentData(),
            forras=self.forras.currentData(),
            napok=[i for i, k in enumerate(self.napok) if k.isChecked()],
            szunetek=[i for i, k in enumerate(self.szunetek) if k.isChecked()] if self.valasztott.isChecked() else [],
            aktiv=self.aktiv,
        )


class MusorblokkKartya(Kartya):
    def __init__(self, v: Vezerlo) -> None:
        super().__init__("Műsorblokkok")
        self.v = v
        self.add(cimke("Szünetenként és naponként más zeneforrás szólhat, pl. reggel nyugodt lista, a "
                       "nagyszünetben a slágerek, pénteken külön lista. Ha egyik blokk sem illik, a kiválasztott "
                       "forrás szól. Ütközésnél a lista elején álló blokk nyer.", "halvany", sortores=True))
        self.lista = QListWidget()
        self.lista.setMinimumHeight(160)
        self.lista.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lista.itemDoubleClicked.connect(lambda _: self._szerkeszt())
        self.lista.itemChanged.connect(self._aktiv_valtozott)
        uj = gomb("Új blokk", "plusz", "fo")
        uj.clicked.connect(self._uj)
        szerkeszt = gomb("Szerkesztés")
        szerkeszt.clicked.connect(self._szerkeszt)
        fel = gomb("", "fel", tipp="Feljebb (előnyt kap)")
        fel.clicked.connect(lambda: self._mozgat(-1))
        le = gomb("", "le", tipp="Lejjebb")
        le.clicked.connect(lambda: self._mozgat(1))
        torol = gomb("", "kuka", tipp="Blokk törlése")
        torol.clicked.connect(self._torol)
        self.add(self.lista)
        self.add(sor(uj, szerkeszt, None, fel, le, torol))
        self.frissit()

    def frissit(self, valasztott: int | None = None) -> None:
        b = self.v.b
        nevek = {f.nev for f in b.forrasok if f.aktiv}
        self.lista.blockSignals(True)
        self.lista.clear()
        for m in b.musorblokkok:
            hiany = "" if m.forras in nevek else "  (a forrás nincs meg vagy ki van kapcsolva)"
            elem = QListWidgetItem(ikon("zene", SZIN["szoveg"]), f"{m.nev} → {m.forras}{hiany}\n{blokk_leiras(m)}")
            elem.setFlags(elem.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            elem.setCheckState(Qt.CheckState.Checked if m.aktiv else Qt.CheckState.Unchecked)
            self.lista.addItem(elem)
        if not b.musorblokkok:
            self.lista.addItem("Nincs műsorblokk: minden szünetben a kiválasztott forrás szól.")
        if valasztott is not None:
            self.lista.setCurrentRow(valasztott)
        self.lista.blockSignals(False)

    def _kijelolt(self) -> int:
        i = self.lista.currentRow()
        return i if 0 <= i < len(self.v.b.musorblokkok) else -1

    def _aktiv_valtozott(self, elem: QListWidgetItem) -> None:
        i = self.lista.row(elem)
        if 0 <= i < len(self.v.b.musorblokkok):
            self.v.b.musorblokkok[i].aktiv = elem.checkState() == Qt.CheckState.Checked
            self.v.mentes()

    def _uj(self) -> None:
        if not any(f.aktiv for f in self.v.b.forrasok):
            QMessageBox.information(self, "Műsorblokk", "Előbb adj hozzá legalább két zeneforrást fent.")
            return
        ablak = MusorblokkAblak(self, self.v.b)
        if ablak.exec() == QDialog.DialogCode.Accepted:
            self.v.b.musorblokkok.append(ablak.blokk())
            self.v.mentes()
            self.frissit(len(self.v.b.musorblokkok) - 1)

    def _szerkeszt(self) -> None:
        i = self._kijelolt()
        if i < 0:
            return
        ablak = MusorblokkAblak(self, self.v.b, self.v.b.musorblokkok[i])
        if ablak.exec() == QDialog.DialogCode.Accepted:
            self.v.b.musorblokkok[i] = ablak.blokk()
            self.v.mentes()
            self.frissit(i)

    def _mozgat(self, irany: int) -> None:
        i = self._kijelolt()
        j = i + irany
        m = self.v.b.musorblokkok
        if i < 0 or not 0 <= j < len(m):
            return
        m[i], m[j] = m[j], m[i]
        self.v.mentes()
        self.frissit(j)

    def _torol(self) -> None:
        i = self._kijelolt()
        if i < 0:
            return
        m = self.v.b.musorblokkok
        if QMessageBox.question(self, "Törlés", f"Törlöd a(z) „{m[i].nev}” blokkot?") == QMessageBox.StandardButton.Yes:
            m.pop(i)
            self.v.mentes()
            self.frissit()
