__lazy_modules__ = [
    "datetime",
    "PySide6.QtCore",
    "PySide6.QtWidgets",
    "kozgaz_fm.beallitasok",
    "kozgaz_fm.orarend",
    "kozgaz_fm.ui.elemek",
    "kozgaz_fm.ui.hangvalaszto",
    "kozgaz_fm.ui.tema",
    "kozgaz_fm.vezerlo",
]

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QHeaderView,
    QInputDialog,
    QListWidget,
    QMessageBox,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
)

from kozgaz_fm.beallitasok import NAPOK, Csengetesirend, Ora
from kozgaz_fm.orarend import rend_generalas
from kozgaz_fm.ui.elemek import Kartya, Oldal, cimke, gomb, ido_mezo, kapcsolo, sor
from kozgaz_fm.ui.hangvalaszto import HangValaszto, SajatHangokKartya
from kozgaz_fm.ui.tema import SZIN
from kozgaz_fm.vezerlo import Vezerlo


class GeneraloAblak(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle("Csengetési rend generálása")
        f = QFormLayout(self)
        f.setSpacing(12)
        self.elso = ido_mezo("08:00")
        self.darab = QSpinBox(minimum=1, maximum=14, value=8)
        self.hossz = QSpinBox(minimum=10, maximum=120, value=45, suffix=" perc")
        self.szunet = QSpinBox(minimum=0, maximum=60, value=10, suffix=" perc")
        self.nagy_utan = QSpinBox(minimum=0, maximum=14, value=3, specialValueText="nincs")
        self.nagy = QSpinBox(minimum=0, maximum=90, value=15, suffix=" perc")
        f.addRow("Első óra kezdete:", self.elso)
        f.addRow("Órák száma:", self.darab)
        f.addRow("Óra hossza:", self.hossz)
        f.addRow("Szünetek hossza:", self.szunet)
        f.addRow("Nagyszünet ennyi óra után:", self.nagy_utan)
        f.addRow("Nagyszünet hossza:", self.nagy)
        gombok = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        gombok.accepted.connect(self.accept)
        gombok.rejected.connect(self.reject)
        f.addRow(gombok)

    def orak(self) -> list[Ora]:
        parok = rend_generalas(self.elso.time().toString("HH:mm"), self.darab.value(), self.hossz.value(),
                               self.szunet.value(), self.nagy_utan.value(), self.nagy.value())
        return [Ora(k, v) for k, v in parok]


class CsengetesOldal(Oldal):
    def __init__(self, v: Vezerlo) -> None:
        super().__init__("Csengetési rend", "Itt állíthatod be, mikor csengessen a rendszer. A változások "
                         "azonnal mentődnek és életbe lépnek.")
        self.v = v
        self.add(self._rend_kartya())
        alsor = QGridLayout()
        alsor.setSpacing(16)
        alsor.addWidget(self._het_kartya(), 0, 0)
        alsor.addWidget(self._hang_kartya(), 0, 1)
        alsor.setColumnStretch(0, 1)
        alsor.setColumnStretch(1, 1)
        self.add(alsor)
        self.add(SajatHangokKartya(v))
        self.elrendezes.addStretch(1)
        self._rendek_frissit()

    def _rend_kartya(self) -> Kartya:
        k = Kartya("Csengetési rendek")
        self.rendek = QListWidget()
        self.rendek.setMaximumWidth(240)
        self.rendek.currentRowChanged.connect(self._rend_valasztva)
        uj = gomb("Új", "plusz")
        uj.clicked.connect(self._uj)
        masol = gomb("Másolat", "masol")
        masol.clicked.connect(self._masolat)
        atnevez = gomb("Átnevezés")
        atnevez.clicked.connect(self._atnevez)
        torol = gomb("", "kuka", tipp="Rend törlése")
        torol.clicked.connect(self._torol)
        self.tabla = QTableWidget(0, 4)
        self.tabla.setHorizontalHeaderLabels(["Óra", "Kezdet", "Vége", "Hossz / szünet utána"])
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setMinimumHeight(380)
        hozzaad = gomb("Óra hozzáadása", "plusz")
        hozzaad.clicked.connect(self._ora_hozzaad)
        torles = gomb("Kijelölt óra törlése", "kuka")
        torles.clicked.connect(self._ora_torol)
        general = gomb("Generálás…", "frissites", "fo", "Teljes rend gyors létrehozása óra- és szünethosszból")
        general.clicked.connect(self._general)
        bal = QGridLayout()
        bal.addWidget(self.rendek, 0, 0, 1, 2)
        bal.addWidget(uj, 1, 0)
        bal.addWidget(masol, 1, 1)
        bal.addWidget(atnevez, 2, 0)
        bal.addWidget(torol, 2, 1)
        jobb = QGridLayout()
        jobb.addWidget(self.tabla, 0, 0)
        jobb.addLayout(sor(hozzaad, torles, None, general), 1, 0)
        k.add(sor(bal, jobb, terkoz=18))
        return k

    def _het_kartya(self) -> Kartya:
        k = Kartya("Heti beosztás")
        k.add(cimke("Melyik napon melyik rend szerint csengessen. Szünnapokat és kivételeket a Naptár "
                    "oldalon adhatsz meg.", "halvany", sortores=True))
        racs = QGridLayout()
        racs.setVerticalSpacing(8)
        self.nap_valasztok: list[QComboBox] = []
        for i, nap in enumerate(NAPOK):
            valaszto = QComboBox()
            valaszto.activated.connect(lambda _s, i=i: self._nap_valtozott(i))
            racs.addWidget(cimke(nap), i, 0)
            racs.addWidget(valaszto, i, 1)
            self.nap_valasztok.append(valaszto)
        racs.setColumnStretch(1, 1)
        k.add(racs)
        return k

    def _hang_kartya(self) -> Kartya:
        b = self.v.b
        k = Kartya("Csengők")
        jelzo_be = b.jelzo and b.jelzo_perc > 0
        self.jelzo = QSpinBox(minimum=1, maximum=15, suffix=" perccel a becsengő előtt")
        self.jelzo.setValue(b.jelzo_perc if b.jelzo_perc > 0 else 2)
        self.jelzo.setEnabled(jelzo_be)
        self.jelzo.valueChanged.connect(lambda e: self._allit("jelzo_perc", e))
        jelzo = kapcsolo("Jelzőcsengő az óra előtt", jelzo_be,
                         "Rövid figyelmeztető csengetés néhány perccel a becsengő előtt")
        jelzo.toggled.connect(self._jelzo_kapcsolo)
        kicsengo = kapcsolo("Kicsengetés az óra végén", b.kicsengo)
        kicsengo.toggled.connect(lambda e: self._allit("kicsengo", e))
        racs = QGridLayout()
        racs.setVerticalSpacing(10)
        racs.addWidget(cimke("Jelzőcsengő ideje:"), 0, 0)
        racs.addWidget(self.jelzo, 0, 1)
        sorok = [("Becsengő hangja:", "hang_becsengo"), ("Kicsengő hangja:", "hang_kicsengo"),
                 ("Jelzőcsengő hangja:", "hang_jelzo"), ("Bemondás előtti gong:", "hang_gong"),
                 ("Riasztás hangja:", "hang_riasztas")]
        for i, (felirat, mezo) in enumerate(sorok, start=1):
            valaszto = HangValaszto(self.v, getattr(b, mezo), mezo)
            valaszto.valtozott.connect(lambda e, m=mezo: self._allit(m, e))
            if mezo == "hang_jelzo":
                self.jelzo_hang = valaszto
                valaszto.setEnabled(jelzo_be)
            racs.addWidget(cimke(felirat), i, 0)
            racs.addWidget(valaszto, i, 1)
        racs.setColumnStretch(1, 1)
        k.add(jelzo)
        k.add(kicsengo)
        k.add(racs)
        self.hangero = QSlider(Qt.Orientation.Horizontal)
        self.hangero.setRange(0, 100)
        self.hangero.setValue(b.csengo_hangero)
        hangero_cimke = cimke(f"{b.csengo_hangero}%", "halvany")
        self.hangero.valueChanged.connect(lambda e: (hangero_cimke.setText(f"{e}%"), self._allit("csengo_hangero", e)))
        k.add(sor(cimke("Csengők hangereje:"), self.hangero, hangero_cimke))
        return k

    def _jelzo_kapcsolo(self, be: bool) -> None:
        self.jelzo.setEnabled(be)
        self.jelzo_hang.setEnabled(be)
        self.v.b.jelzo = be
        self.v.b.jelzo_perc = self.jelzo.value()
        self.v.mentes_kesobb()

    def _allit(self, mezo: str, ertek) -> None:
        setattr(self.v.b, mezo, ertek)
        self.v.mentes_kesobb()

    def _aktualis(self) -> Csengetesirend | None:
        sor_ = self.rendek.currentRow()
        return self.v.b.rendek[sor_] if 0 <= sor_ < len(self.v.b.rendek) else None

    def _rendek_frissit(self, valasztott: str | None = None) -> None:
        b = self.v.b
        elozo = valasztott or (self._aktualis().nev if self._aktualis() else None)
        self.rendek.blockSignals(True)
        self.rendek.clear()
        for r in b.rendek:
            self.rendek.addItem(r.nev)
        nevek = [r.nev for r in b.rendek]
        self.rendek.setCurrentRow(nevek.index(elozo) if elozo in nevek else (0 if nevek else -1))
        self.rendek.blockSignals(False)
        for i, valaszto in enumerate(self.nap_valasztok if hasattr(self, "nap_valasztok") else []):
            valaszto.clear()
            valaszto.addItem("Nincs csengetés", "")
            for nev in nevek:
                valaszto.addItem(nev, nev)
            valaszto.setCurrentIndex(max(0, valaszto.findData(b.het[i] if b.het[i] in nevek else "")))
        self._tabla_frissit()

    def _rend_valasztva(self, _sor: int) -> None:
        self._tabla_frissit()

    def _tabla_frissit(self) -> None:
        rend = self._aktualis()
        self.tabla.setRowCount(0)
        if rend is None:
            return
        self.tabla.setRowCount(len(rend.orak))
        for i, ora in enumerate(rend.orak):
            szam = QTableWidgetItem(f"{i + 1}.")
            szam.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(i, 0, szam)
            for oszlop, mezo in ((1, "kezdet"), (2, "vege")):
                szerk = ido_mezo(getattr(ora, mezo))
                szerk.setFrame(False)
                szerk.timeChanged.connect(lambda _t, i=i, m=mezo, s=szerk: self._ido_valtozott(i, m, s))
                self.tabla.setCellWidget(i, oszlop, szerk)
            self.tabla.setRowHeight(i, 40)
        self._hosszak()

    def _hosszak(self) -> None:
        rend = self._aktualis()
        if rend is None:
            return
        for i, ora in enumerate(rend.orak):
            hossz = _perc(ora.vege) - _perc(ora.kezdet)
            szoveg = f"{hossz} perc"
            szin = SZIN["szoveg"]
            if hossz <= 0:
                szoveg, szin = "Hibás: a vége a kezdet előtt van!", SZIN["hiba"]
            elif i + 1 < len(rend.orak):
                szunet = _perc(rend.orak[i + 1].kezdet) - _perc(ora.vege)
                if szunet < 0:
                    szoveg, szin = "Hibás: átfedés a következő órával!", SZIN["hiba"]
                else:
                    szoveg += f",  utána {szunet} perc szünet"
            elem = QTableWidgetItem(szoveg)
            elem.setForeground(Qt.GlobalColor.red if szin == SZIN["hiba"] else Qt.GlobalColor.white)
            self.tabla.setItem(i, 3, elem)

    def _ido_valtozott(self, index: int, mezo: str, szerk: QTimeEdit) -> None:
        rend = self._aktualis()
        if rend is None or index >= len(rend.orak):
            return
        setattr(rend.orak[index], mezo, szerk.time().toString("HH:mm"))
        self._hosszak()
        self.v.mentes_kesobb()

    def _ora_hozzaad(self) -> None:
        rend = self._aktualis()
        if rend is None:
            return
        if rend.orak:
            utolso = _perc(rend.orak[-1].vege) + 10
            hossz = _perc(rend.orak[-1].vege) - _perc(rend.orak[-1].kezdet)
        else:
            utolso, hossz = 8 * 60, 45
        rend.orak.append(Ora(_szoveg(utolso), _szoveg(utolso + max(hossz, 10))))
        self._tabla_frissit()
        self.v.mentes_kesobb()

    def _ora_torol(self) -> None:
        rend = self._aktualis()
        sor_ = self.tabla.currentRow()
        if rend is None or not rend.orak:
            return
        rend.orak.pop(sor_ if 0 <= sor_ < len(rend.orak) else -1)
        self._tabla_frissit()
        self.v.mentes_kesobb()

    def _general(self) -> None:
        rend = self._aktualis()
        if rend is None:
            return
        ablak = GeneraloAblak(self)
        if ablak.exec() != QDialog.DialogCode.Accepted:
            return
        if rend.orak and QMessageBox.question(self, "Felülírás", f"Felülírod a(z) „{rend.nev}” rend óráit?"
                                              ) != QMessageBox.StandardButton.Yes:
            return
        rend.orak = ablak.orak()
        self._tabla_frissit()
        self.v.mentes_kesobb()

    def _nev_ker(self, cim: str, alap: str = "") -> str | None:
        nev, ok = QInputDialog.getText(self, cim, "A rend neve:", text=alap)
        nev = nev.strip()
        if not ok or not nev:
            return None
        if any(r.nev == nev for r in self.v.b.rendek):
            QMessageBox.warning(self, cim, "Már van ilyen nevű csengetési rend.")
            return None
        return nev

    def _uj(self) -> None:
        nev = self._nev_ker("Új csengetési rend")
        if nev:
            self.v.b.rendek.append(Csengetesirend(nev))
            self._rendek_frissit(nev)
            self.v.mentes_kesobb()

    def _masolat(self) -> None:
        rend = self._aktualis()
        if rend is None:
            return
        nev = self._nev_ker("Másolat", f"{rend.nev} (másolat)")
        if nev:
            self.v.b.rendek.append(Csengetesirend(nev, [Ora(o.kezdet, o.vege) for o in rend.orak]))
            self._rendek_frissit(nev)
            self.v.mentes_kesobb()

    def _atnevez(self) -> None:
        rend = self._aktualis()
        if rend is None:
            return
        nev = self._nev_ker("Átnevezés", rend.nev)
        if not nev:
            return
        b = self.v.b
        b.het = [nev if n == rend.nev else n for n in b.het]
        b.kivetelek = {d: (nev if n == rend.nev else n) for d, n in b.kivetelek.items()}
        rend.nev = nev
        self._rendek_frissit(nev)
        self.v.mentes_kesobb()

    def _torol(self) -> None:
        rend = self._aktualis()
        if rend is None:
            return
        if QMessageBox.question(self, "Törlés", f"Biztosan törlöd a(z) „{rend.nev}” csengetési rendet?"
                                ) != QMessageBox.StandardButton.Yes:
            return
        b = self.v.b
        b.rendek.remove(rend)
        b.het = ["" if n == rend.nev else n for n in b.het]
        b.kivetelek = {d: n for d, n in b.kivetelek.items() if n != rend.nev}
        self._rendek_frissit()
        self.v.mentes_kesobb()

    def _nap_valtozott(self, index: int) -> None:
        self.v.b.het[index] = self.nap_valasztok[index].currentData() or ""
        self.v.mentes_kesobb()


def _perc(szoveg: str) -> int:
    ido = datetime.strptime(szoveg, "%H:%M")
    return ido.hour * 60 + ido.minute


def _szoveg(perc: int) -> str:
    perc = max(0, min(perc, 23 * 60 + 59))
    return f"{perc // 60:02d}:{perc % 60:02d}"
