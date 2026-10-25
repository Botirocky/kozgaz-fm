__lazy_modules__ = [
    "datetime",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "kozgaz_fm.beallitasok",
    "kozgaz_fm.naptar_import",
    "kozgaz_fm.orarend",
    "kozgaz_fm.ui.elemek",
    "kozgaz_fm.ui.hangvalaszto",
    "kozgaz_fm.ui.naptar_import_ablak",
    "kozgaz_fm.ui.tema",
    "kozgaz_fm.unnepek",
    "kozgaz_fm.vezerlo",
]

from datetime import date, timedelta

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QTextCharFormat
from PySide6.QtWidgets import (
    QCalendarWidget,
    QCheckBox,
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
    QSpinBox,
)

from kozgaz_fm.beallitasok import RENDKIVULI_TIPUSOK, Rendkivuli, Szunnap
from kozgaz_fm.naptar_import import alkalmaz
from kozgaz_fm.orarend import napi_rend, szunnap_nev
from kozgaz_fm.ui.elemek import Kartya, Oldal, cimke, gomb, ido_mezo, sor
from kozgaz_fm.ui.hangvalaszto import HangValaszto
from kozgaz_fm.ui.naptar_import_ablak import NaptarImportAblak
from kozgaz_fm.ui.tema import SZIN, ikon
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


RENDKIVULI_IKON = {"csengetes": "csengo", "riado": "riasztas", "csend": "hold"}
RENDKIVULI_SUGO = {
    "csengetes": "A megadott időpontban egyszer megszólal a kiválasztott hang (pl. ünnepség kezdete). "
                 "Szünnapon és „ma nincs csengetés” mellett is szól.",
    "riado": "A megadott időpontban magától elindul a riasztás, és a beállított idő után leáll "
             "(0 perc = kézi leállításig). A folyosói kijelző előre nem mutatja.",
    "csend": "Az időszak alatt nincs szünetzene és ütemezett bemondás; a csengő néma vagy halk "
             "(pl. érettségi, ünnepség, mérés).",
}


def rendkivuli_leiras(r: Rendkivuli) -> str:
    if r.tipus == "csend":
        csengo = f"halk csengő ({r.csengo_hangero}%)" if r.csengo_hangero else "néma csengő"
        return f"{r.tol}–{r.ig}, {csengo}"
    if r.tipus == "riado":
        return f"{r.tol}, " + (f"{r.riado_perc} percig" if r.riado_perc else "kézi leállításig")
    return r.tol


class RendkivuliAblak(QDialog):
    def __init__(self, parent, v: Vezerlo, alap: date, r: Rendkivuli | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rendkívüli esemény")
        self.setMinimumWidth(480)
        r = r or Rendkivuli("", alap.isoformat(), "10:00", ig="11:00")
        self.aktiv = r.aktiv
        self.f = f = QFormLayout(self)
        f.setSpacing(12)
        self.tipus = QComboBox()
        for kulcs, nev in RENDKIVULI_TIPUSOK.items():
            self.tipus.addItem(ikon(RENDKIVULI_IKON[kulcs]), nev, kulcs)
        self.tipus.setCurrentIndex(max(0, self.tipus.findData(r.tipus)))
        self.sugo = cimke("", "halvany", sortores=True)
        self.nev = QLineEdit(r.nev)
        self.nev.setPlaceholderText("pl. Tűzriadó-gyakorlat, Érettségi, Március 15. ünnepség")
        self.datum = datum_mezo(date.fromisoformat(r.datum) if r.datum else alap)
        self.tol = ido_mezo(r.tol)
        self.ig = ido_mezo(r.ig or r.tol)
        self.hang = HangValaszto(v, r.hang)
        self.riado_perc = QSpinBox()
        self.riado_perc.setRange(0, 60)
        self.riado_perc.setSuffix(" perc")
        self.riado_perc.setSpecialValueText("kézi leállításig")
        self.riado_perc.setValue(r.riado_perc)
        self.halk = QCheckBox("Halk csengő:")
        self.halk.setChecked(r.csengo_hangero > 0)
        self.hangero = QSpinBox()
        self.hangero.setRange(5, 100)
        self.hangero.setSuffix("%")
        self.hangero.setValue(r.csengo_hangero or 30)
        self.hangero.setEnabled(self.halk.isChecked())
        self.halk.toggled.connect(self.hangero.setEnabled)
        f.addRow("Típus:", self.tipus)
        f.addRow(self.sugo)
        f.addRow("Megnevezés:", self.nev)
        f.addRow("Nap:", self.datum)
        f.addRow("Időpont:", self.tol)
        f.addRow("Vége:", self.ig)
        f.addRow("Hang:", self.hang)
        f.addRow("Riasztás hossza:", self.riado_perc)
        self.csengo_sor = sor(self.halk, self.hangero, None)
        f.addRow("Csengő:", self.csengo_sor)
        gombok = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        gombok.accepted.connect(self._ok)
        gombok.rejected.connect(self.reject)
        f.addRow(gombok)
        self.tipus.currentIndexChanged.connect(self._tipus_valtozott)
        self._tipus_valtozott()

    def _tipus_valtozott(self) -> None:
        tipus = self.tipus.currentData()
        self.sugo.setText(RENDKIVULI_SUGO[tipus])
        self.f.setRowVisible(self.ig, tipus == "csend")
        self.f.setRowVisible(self.hang, tipus == "csengetes")
        self.f.setRowVisible(self.riado_perc, tipus == "riado")
        self.f.setRowVisible(self.csengo_sor, tipus == "csend")
        self.f.labelForField(self.tol).setText("Kezdete:" if tipus == "csend" else "Időpont:")
        self.adjustSize()

    def _ok(self) -> None:
        if self.tipus.currentData() == "csend" and self.ig.time() <= self.tol.time():
            QMessageBox.warning(self, "Rendkívüli esemény", "A csendes időszak vége legyen később, mint a kezdete.")
            return
        self.accept()

    def rendkivuli(self) -> Rendkivuli:
        tipus = self.tipus.currentData()
        return Rendkivuli(
            nev=self.nev.text().strip() or RENDKIVULI_TIPUSOK[tipus],
            datum=_pydate(self.datum.date()).isoformat(),
            tol=self.tol.time().toString("HH:mm"),
            tipus=tipus,
            ig=self.ig.time().toString("HH:mm") if tipus == "csend" else "",
            hang=self.hang.ertek(),
            riado_perc=self.riado_perc.value(),
            csengo_hangero=self.hangero.value() if tipus == "csend" and self.halk.isChecked() else 0,
            aktiv=self.aktiv,
        )


class NaptarOldal(Oldal):
    def __init__(self, v: Vezerlo) -> None:
        super().__init__("Naptár", "Tanítási szünetek, ünnepnapok, kivételnapok és rendkívüli események. "
                         "Szünnapon nincs csengetés és szünetzene, kivételnapon a megadott rend érvényes.")
        self.v = v
        racs = QGridLayout()
        racs.setSpacing(16)
        racs.addWidget(self._naptar_kartya(), 0, 0, 2, 1)
        racs.addWidget(self._szunnap_kartya(), 0, 1)
        racs.addWidget(self._kivetel_kartya(), 1, 1)
        racs.addWidget(self._rendkivuli_kartya(), 2, 0, 1, 2)
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
                              f"<span style='color:{SZIN['elo_szin']}'>■</span> kivételnap   "
                              f"<span style='color:{SZIN['kek']}'>■</span> rendkívüli esemény   "
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
        tanev = gomb("Tanév rendje…", "le", tipp="Az iskola naptárának importálása (.ics fájl vagy naptárlink)")
        tanev.clicked.connect(self._tanev_import)
        k.add(self.szunnapok)
        k.add(sor(uj, unnep, tanev, None, torol))
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

    def _rendkivuli_kartya(self) -> Kartya:
        k = Kartya("Rendkívüli események")
        k.add(cimke("Egyszeri, előre beállított események: tűzriadó-gyakorlat, rendkívüli csengetés (pl. ünnepség "
                    "kezdete) vagy csendes időszak (érettségi, mérés), amikor nincs zene és bemondás.",
                    "halvany", sortores=True))
        self.rendkivuli = QListWidget()
        self.rendkivuli.setMinimumHeight(160)
        self.rendkivuli.itemDoubleClicked.connect(lambda _: self._rendkivuli_szerkeszt())
        self.rendkivuli.itemChanged.connect(self._rendkivuli_aktiv)
        uj = gomb("Hozzáadás", "plusz", "fo")
        uj.clicked.connect(self._uj_rendkivuli)
        szerk = gomb("Szerkesztés")
        szerk.clicked.connect(self._rendkivuli_szerkeszt)
        torol = gomb("", "kuka", tipp="Kijelölt törlése")
        torol.clicked.connect(self._rendkivuli_torol)
        k.add(self.rendkivuli)
        k.add(sor(uj, szerk, None, torol))
        return k

    def _rendkivuli_lista(self, ma: str) -> None:
        b = self.v.b
        b.rendkivuli.sort(key=lambda r: (r.datum, r.tol))
        self.rendkivuli.blockSignals(True)
        self.rendkivuli.clear()
        for r in b.rendkivuli:
            elem = QListWidgetItem(ikon(RENDKIVULI_IKON.get(r.tipus, "csengo")),
                                   f"{r.datum}   {r.nev}\n{RENDKIVULI_TIPUSOK.get(r.tipus, r.tipus)}: "
                                   f"{rendkivuli_leiras(r)}")
            elem.setFlags(elem.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            elem.setCheckState(Qt.CheckState.Checked if r.aktiv else Qt.CheckState.Unchecked)
            if r.datum < ma:
                elem.setForeground(QColor(SZIN["halvany"]))
            self.rendkivuli.addItem(elem)
        self.rendkivuli.blockSignals(False)

    def _kijelolt_rendkivuli(self) -> int:
        i = self.rendkivuli.currentRow()
        return i if 0 <= i < len(self.v.b.rendkivuli) else -1

    def _rendkivuli_aktiv(self, elem: QListWidgetItem) -> None:
        i = self.rendkivuli.row(elem)
        if 0 <= i < len(self.v.b.rendkivuli):
            self.v.b.rendkivuli[i].aktiv = elem.checkState() == Qt.CheckState.Checked
            self.v.mentes()
            self._szinez()
            self._nap_info()

    def _uj_rendkivuli(self) -> None:
        ablak = RendkivuliAblak(self, self.v, _pydate(self.naptar.selectedDate()))
        if ablak.exec() == QDialog.DialogCode.Accepted:
            r = ablak.rendkivuli()
            self.v.b.rendkivuli.append(r)
            self.v.log(f"Rendkívüli esemény hozzáadva: {r.nev} ({r.datum} {r.tol})")
            self.v.mentes()
            self.frissit()

    def _rendkivuli_szerkeszt(self) -> None:
        i = self._kijelolt_rendkivuli()
        if i < 0:
            return
        ablak = RendkivuliAblak(self, self.v, _pydate(self.naptar.selectedDate()), self.v.b.rendkivuli[i])
        if ablak.exec() == QDialog.DialogCode.Accepted:
            self.v.b.rendkivuli[i] = ablak.rendkivuli()
            self.v.mentes()
            self.frissit()

    def _rendkivuli_torol(self) -> None:
        i = self._kijelolt_rendkivuli()
        if i < 0:
            return
        if QMessageBox.question(self, "Törlés", f"Törlöd: {self.v.b.rendkivuli[i].nev}?") == \
                QMessageBox.StandardButton.Yes:
            self.v.b.rendkivuli.pop(i)
            self.v.mentes()
            self.frissit()

    def frissit(self) -> None:
        b = self.v.b
        ma = date.today().isoformat()
        self._rendkivuli_lista(ma)
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
        rendkivuli = {r.datum for r in b.rendkivuli if r.aktiv}
        for i in range(50):
            nap = elso + timedelta(days=i)
            f = QTextCharFormat()
            if nap.isoformat() in rendkivuli:
                f.setForeground(QColor(SZIN["kek"]))
                f.setFontWeight(700)
                f.setFontUnderline(True)
            elif nap.isoformat() in b.kivetelek:
                f.setForeground(QColor(SZIN["elo_szin"]))
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
        esemenyek = [f"{r.nev} ({rendkivuli_leiras(r)})" for r in b.rendkivuli
                     if r.aktiv and r.datum == nap.isoformat()]
        if esemenyek:
            szoveg += "<br>Rendkívüli: " + "; ".join(esemenyek)
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

    def _tanev_import(self) -> None:
        ablak = NaptarImportAblak(self, self.v.b)
        if ablak.exec() != QDialog.DialogCode.Accepted:
            return
        szunnap, kivetel, megtartott = alkalmaz(self.v.b, ablak.kivalasztott())
        self.v.log(f"Tanév rendje importálva: {szunnap} szünnap, {kivetel} kivételnap")
        self.v.mentes()
        self.frissit()
        QMessageBox.information(self, "Tanév rendje", f"{szunnap} új szünnap és {kivetel} kivételnap került "
                                "a naptárba. A már meglévő szünnapokat nem vettem fel újra."
                                + (f" {megtartott} napra már volt kézzel beállított kivétel, azokat "
                                   "nem írtam felül." if megtartott else ""))

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
