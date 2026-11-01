__lazy_modules__ = [
    "pathlib",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "kozgaz_fm",
    "kozgaz_fm.kghsz",
    "kozgaz_fm.naptar_import",
    "kozgaz_fm.ui.elemek",
    "kozgaz_fm.ui.tema",
]

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from kozgaz_fm import hatter, kghsz
from kozgaz_fm.naptar_import import KIHAGY, MUVELET_NEV, ImportHiba, Javaslat, esemeny_javaslatok, javaslatok, letoltes
from kozgaz_fm.ui.elemek import cimke, gomb, sor
from kozgaz_fm.ui.tema import SZIN

HONAPOK = ["jan.", "febr.", "márc.", "ápr.", "máj.", "jún.", "júl.", "aug.", "szept.", "okt.", "nov.", "dec."]


def _datum(d) -> str:
    return f"{d.year}. {HONAPOK[d.month - 1]} {d.day}."


def idoszak_szoveg(j: Javaslat) -> str:
    e = j.esemeny
    return _datum(e.tol) if e.tol == e.ig else f"{_datum(e.tol)} – {_datum(e.ig)}"


class NaptarImportAblak(QDialog):
    def __init__(self, parent, beallitasok) -> None:
        super().__init__(parent)
        self.b = beallitasok
        self.javaslatok: list[Javaslat] = []
        self.iskolai: kghsz.IskolaiAdatok | None = None
        self.setWindowTitle("Tanév rendje importálása")
        self.resize(720, 560)
        elr = QVBoxLayout(self)
        elr.setSpacing(12)
        elr.addWidget(cimke("Az iskola honlapjáról (kghsz.hu), .ics fájlból vagy naptárlinkről (Google Naptár „titkos "
                            "cím iCal formátumban”, Kréta naptár-export). A szüneteket szünnapként, a rövidített "
                            "napokat és az áthelyezett munkanapokat kivételnapként veszem fel; a többi rendezvény nem "
                            "érinti a csengetést.", "halvany", sortores=True))
        self.honlap_gomb = gomb("Az iskola honlapjáról", "le")
        self.honlap_gomb.clicked.connect(self._honlaprol)
        elr.addLayout(sor(self.honlap_gomb, None))
        fajl = gomb("Fájl megnyitása…", "mappa")
        fajl.clicked.connect(self._fajl)
        self.cim = QLineEdit()
        self.cim.setPlaceholderText("https://… vagy webcal://… naptárlink")
        self.cim.returnPressed.connect(self._letolt)
        self.letolt_gomb = gomb("Letöltés", "le")
        self.letolt_gomb.clicked.connect(self._letolt)
        elr.addLayout(sor(fajl, self.cim, self.letolt_gomb))
        self.allapot = cimke("", "halvany", sortores=True)
        elr.addWidget(self.allapot)
        self.rend_pipa = QCheckBox()
        self.rend_pipa.setVisible(False)
        self.rend_pipa.toggled.connect(lambda _: self._gomb_frissit())
        elr.addWidget(self.rend_pipa)
        self.lista = QListWidget()
        self.lista.itemChanged.connect(lambda _: self._gomb_frissit())
        elr.addWidget(self.lista, 1)
        self.gombok = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.import_gomb = self.gombok.addButton("Importálás", QDialogButtonBox.ButtonRole.AcceptRole)
        self.import_gomb.setEnabled(False)
        self.gombok.accepted.connect(self.accept)
        self.gombok.rejected.connect(self.reject)
        elr.addWidget(self.gombok)

    def kivalasztott(self) -> list[Javaslat]:
        return [self.javaslatok[i] for i in range(self.lista.count())
                if self.lista.item(i).checkState() == Qt.CheckState.Checked]

    def rend_is_kell(self) -> bool:
        return self.iskolai is not None and self.rend_pipa.isChecked()

    def _honlaprol(self) -> None:
        self.honlap_gomb.setEnabled(False)
        self.allapot.setText("Az iskola honlapjának letöltése…")
        b = self.b

        def kesz(eredmeny) -> None:
            adatok, lista = eredmeny
            self.honlap_gomb.setEnabled(True)
            self.iskolai = adatok
            self._rend_mutat(adatok)
            self._megjelenit(lista, "az iskola honlapján")

        def hiba(e: Exception) -> None:
            self.honlap_gomb.setEnabled(True)
            self.allapot.setText(str(e) if isinstance(e, ImportHiba) else f"A letöltés nem sikerült: {e}")

        def munka():
            adatok = kghsz.letoltes(b)
            return adatok, esemeny_javaslatok(adatok.esemenyek, b)

        hatter.futtat(munka, kesz, hiba)

    def _rend_mutat(self, adatok: kghsz.IskolaiAdatok) -> None:
        valtozott = kghsz.rend_atvetel(self.b, adatok)
        if not valtozott:
            self.rend_pipa.setVisible(False)
            self.rend_pipa.setChecked(False)
            return
        jelenlegi = self.b.rend("Normál")
        self.rend_pipa.setText(
            f"Csengetési rend átvétele ({', '.join(valtozott)}): a honlapon {kghsz.orak_szoveg(adatok.normal)}, "
            f"most {kghsz.orak_szoveg(jelenlegi.orak if jelenlegi else [])}")
        self.rend_pipa.setChecked(True)
        self.rend_pipa.setVisible(True)

    def _fajl(self) -> None:
        ut, _ = QFileDialog.getOpenFileName(self, "Naptár megnyitása", "", "iCalendar (*.ics);;Minden fájl (*)")
        if not ut:
            return
        try:
            szoveg = Path(ut).read_bytes()[:2_000_001].decode("utf-8", "replace")
        except OSError as e:
            self.allapot.setText(f"A fájl nem olvasható: {e}")
            return
        self._betolt(szoveg, Path(ut).name)

    def _letolt(self) -> None:
        cim = self.cim.text().strip()
        if not cim:
            return
        self.letolt_gomb.setEnabled(False)
        self.allapot.setText("Letöltés…")

        def kesz(szoveg: str) -> None:
            self.letolt_gomb.setEnabled(True)
            self._betolt(szoveg, "a naptárlinkről")

        def hiba(e: Exception) -> None:
            self.letolt_gomb.setEnabled(True)
            self.allapot.setText(str(e) if isinstance(e, ImportHiba) else f"A letöltés nem sikerült: {e}")

        hatter.futtat(lambda: letoltes(cim), kesz, hiba)

    def _betolt(self, szoveg: str, honnan: str) -> None:
        self.iskolai = None
        self.rend_pipa.setVisible(False)
        self.allapot.setText("A naptár feldolgozása…")
        b = self.b

        def hiba(e: Exception) -> None:
            self.allapot.setText(str(e) if isinstance(e, ImportHiba) else f"A naptár nem értelmezhető: {e}")

        hatter.futtat(lambda: javaslatok(szoveg, b), lambda lista: self._megjelenit(lista, honnan), hiba)

    def _megjelenit(self, lista: list[Javaslat], honnan: str) -> None:
        self.javaslatok = lista
        self.lista.blockSignals(True)
        self.lista.clear()
        for j in self.javaslatok:
            muvelet = MUVELET_NEV[j.muvelet] + (f" ({j.megjegyzes})" if j.megjegyzes else "")
            elem = QListWidgetItem(f"{idoszak_szoveg(j)}   {j.esemeny.nev}\n→ {muvelet}")
            elem.setFlags(elem.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            elem.setCheckState(Qt.CheckState.Unchecked if j.muvelet == KIHAGY else Qt.CheckState.Checked)
            if j.muvelet == KIHAGY:
                elem.setFlags(elem.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                elem.setForeground(QColor(SZIN["halvany"]))
            self.lista.addItem(elem)
        self.lista.blockSignals(False)
        erinti = sum(1 for j in self.javaslatok if j.muvelet != KIHAGY)
        self.allapot.setText(f"{len(self.javaslatok)} közelgő esemény {honnan}; ebből {erinti} érinti a "
                             "csengetést. A pipát kiveheted, ami nem kell." if self.javaslatok
                             else f"Nincs közelgő esemény {honnan}.")
        self._gomb_frissit()

    def _gomb_frissit(self) -> None:
        self.import_gomb.setEnabled(bool(self.kivalasztott()) or self.rend_is_kell())
