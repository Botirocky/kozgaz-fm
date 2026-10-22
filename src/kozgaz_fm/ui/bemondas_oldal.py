__lazy_modules__ = [
    "pathlib",
    "PySide6.QtCore",
    "PySide6.QtWidgets",
    "kozgaz_fm.beallitasok",
    "kozgaz_fm.hang",
    "kozgaz_fm.ui.elemek",
    "kozgaz_fm.ui.tema",
    "kozgaz_fm.vezerlo",
]

from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QRadioButton,
)

from kozgaz_fm.beallitasok import NAPOK, Bemondas
from kozgaz_fm.hang import HANGFAJLOK
from kozgaz_fm.ui.elemek import Kartya, Oldal, cimke, gomb, ido_mezo, kapcsolo, sor
from kozgaz_fm.ui.tema import SZIN, ikon
from kozgaz_fm.vezerlo import Vezerlo

SABLONOK = [
    "Kedves Diákok! Felhívjuk figyelmeteket, hogy a mai napon rövidített órák lesznek.",
    "Figyelem! Az osztályfőnöki órák után rendkívüli diákközgyűlést tartunk az aulában.",
    "Kedves Diákok és Tanárok! A tanítás vége után a tornateremben kezdődik a ballagási próba.",
    "Kérjük az ügyeletes diákokat, hogy jelentkezzenek a titkárságon.",
]


class BemondasAblak(QDialog):
    def __init__(self, parent, b: Bemondas | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ütemezett bemondás")
        self.setMinimumWidth(520)
        b = b or Bemondas("", "07:55")
        f = QFormLayout(self)
        f.setSpacing(12)
        self.nev = QLineEdit(b.nev)
        self.nev.setPlaceholderText("pl. Hétfő reggeli Himnusz")
        self.ido = ido_mezo(b.ido)
        self.ismetlodo = QRadioButton("A hét kiválasztott napjain")
        self.egyszeri = QRadioButton("Egyszer, ezen a napon:")
        csoport = QButtonGroup(self)
        csoport.addButton(self.ismetlodo)
        csoport.addButton(self.egyszeri)
        self.napok = [QCheckBox(n[:3]) for n in NAPOK]
        for i, k in enumerate(self.napok):
            k.setChecked(i in b.napok)
        self.datum = QDateEdit(QDate.fromString(b.datum, "yyyy-MM-dd") if b.datum else QDate.currentDate())
        self.datum.setCalendarPopup(True)
        self.datum.setDisplayFormat("yyyy. MM. dd.")
        (self.egyszeri if b.datum else self.ismetlodo).setChecked(True)
        self.szoveg_mod = QRadioButton("Felolvasott szöveg")
        self.fajl_mod = QRadioButton("Hangfájl (pl. Himnusz, előre felvett üzenet)")
        csoport2 = QButtonGroup(self)
        csoport2.addButton(self.szoveg_mod)
        csoport2.addButton(self.fajl_mod)
        (self.fajl_mod if b.tipus == "fajl" else self.szoveg_mod).setChecked(True)
        self.szoveg = QPlainTextEdit(b.tartalom if b.tipus == "szoveg" else "")
        self.szoveg.setPlaceholderText("A felolvasandó szöveg…")
        self.szoveg.setMaximumHeight(110)
        self.fajl = QLineEdit(b.tartalom if b.tipus == "fajl" else "")
        tallozas = gomb("Tallózás…", "mappa")
        tallozas.clicked.connect(self._tallozas)
        self.gong = kapcsolo("Gong előtte", b.gong)
        f.addRow("Megnevezés:", self.nev)
        f.addRow("Időpont:", self.ido)
        f.addRow(self.ismetlodo)
        f.addRow(sor(*self.napok, nyujt=True, terkoz=6))
        f.addRow(sor(self.egyszeri, self.datum, nyujt=True))
        f.addRow(self.szoveg_mod)
        f.addRow(self.szoveg)
        f.addRow(self.fajl_mod)
        f.addRow(sor(self.fajl, tallozas))
        f.addRow(self.gong)
        gombok = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        gombok.accepted.connect(self._ok)
        gombok.rejected.connect(self.reject)
        f.addRow(gombok)
        self.aktiv = b.aktiv

    def _tallozas(self) -> None:
        szuro = "Hangfájlok (" + " ".join(f"*{k}" for k in HANGFAJLOK) + ")"
        ut, _ = QFileDialog.getOpenFileName(self, "Hangfájl", "", szuro)
        if ut:
            self.fajl.setText(ut)
            self.fajl_mod.setChecked(True)

    def _ok(self) -> None:
        if self.szoveg_mod.isChecked() and not self.szoveg.toPlainText().strip():
            QMessageBox.warning(self, "Bemondás", "Írd be a felolvasandó szöveget.")
            return
        if self.fajl_mod.isChecked() and not Path(self.fajl.text().strip()).is_file():
            QMessageBox.warning(self, "Bemondás", "A hangfájl nem található.")
            return
        if self.ismetlodo.isChecked() and not any(k.isChecked() for k in self.napok):
            QMessageBox.warning(self, "Bemondás", "Jelölj ki legalább egy napot.")
            return
        self.accept()

    def bemondas(self) -> Bemondas:
        szoveges = self.szoveg_mod.isChecked()
        return Bemondas(
            nev=self.nev.text().strip() or "Bemondás",
            ido=self.ido.time().toString("HH:mm"),
            napok=[i for i, k in enumerate(self.napok) if k.isChecked()],
            datum=self.datum.date().toString("yyyy-MM-dd") if self.egyszeri.isChecked() else "",
            tipus="szoveg" if szoveges else "fajl",
            tartalom=self.szoveg.toPlainText().strip() if szoveges else self.fajl.text().strip(),
            gong=self.gong.isChecked(),
            aktiv=self.aktiv,
        )


class BemondasOldal(Oldal):
    def __init__(self, v: Vezerlo) -> None:
        super().__init__("Bemondások", "Azonnali vagy ütemezett hangosbemondás: felolvasott szöveg vagy "
                         "hangfájl. Bemondás alatt a zene automatikusan lehalkul.")
        self.v = v
        racs = QGridLayout()
        racs.setSpacing(16)
        racs.addWidget(self._azonnali_kartya(), 0, 0)
        racs.addWidget(self._utemezett_kartya(), 0, 1)
        racs.setColumnStretch(0, 1)
        racs.setColumnStretch(1, 1)
        self.add(racs)
        self.elrendezes.addStretch(1)
        self._lista_frissit()

    def _azonnali_kartya(self) -> Kartya:
        k = Kartya("Azonnali bemondás")
        self.szoveg = QPlainTextEdit()
        self.szoveg.setPlaceholderText("Írd ide, amit a rendszer felolvasson…")
        self.szoveg.setMinimumHeight(140)
        self.sablon = QComboBox()
        self.sablon.addItem("Sablon beillesztése…")
        for s in SABLONOK:
            self.sablon.addItem(s[:70] + ("…" if len(s) > 70 else ""), s)
        self.sablon.activated.connect(self._sablon)
        self.gong = kapcsolo("Gong előtte", True)
        mond = gomb("Bemondás most", "bemondas", "fo")
        mond.clicked.connect(self._mond)
        stop = gomb("Leállítás", "stop")
        stop.clicked.connect(self._stop)
        self.hang = QComboBox()
        self.hang.setToolTip("Felolvasó hang (a Windows magyar hangja: Microsoft Szabolcs)")
        self.hang.activated.connect(self._hang_valasztva)
        k.add(self.sablon)
        k.add(self.szoveg)
        k.add(sor(self.gong, None, stop, mond))
        k.add(sor(cimke("Felolvasó hang:"), self.hang))
        self.tts_info = cimke("", "halvany", sortores=True)
        k.add(self.tts_info)
        self._hangok()
        return k

    def _utemezett_kartya(self) -> Kartya:
        k = Kartya("Ütemezett bemondások")
        self.lista = QListWidget()
        self.lista.setMinimumHeight(280)
        self.lista.itemDoubleClicked.connect(lambda _: self._szerkeszt())
        self.lista.itemChanged.connect(self._aktiv_valtozott)
        uj = gomb("Új", "plusz", "fo")
        uj.clicked.connect(self._uj)
        szerk = gomb("Szerkesztés")
        szerk.clicked.connect(self._szerkeszt)
        proba = gomb("Próba", "lejatszas", tipp="Lejátszás most")
        proba.clicked.connect(self._proba)
        torol = gomb("", "kuka", tipp="Törlés")
        torol.clicked.connect(self._torol)
        k.add(self.lista)
        k.add(sor(uj, szerk, proba, None, torol))
        return k

    def _hangok(self) -> None:
        hangok = self.v.bemondo.hangok()
        self.hang.clear()
        self.hang.addItem("Automatikus (magyar, ha van)", "")
        for h in hangok:
            self.hang.addItem(h, h)
        self.hang.setCurrentIndex(max(0, self.hang.findData(self.v.b.tts_hang)))
        if not self.v.bemondo.elerheto():
            self.tts_info.setText("Ezen a gépen nem érhető el szövegfelolvasó. Windows-on: Gépházban "
                                  "Idő és nyelv → Beszéd → Hangok hozzáadása → Magyar.")
        else:
            self.tts_info.setText("Ha a felolvasás nem magyar kiejtésű, telepítsd a magyar hangot: Gépház → Idő és "
                                  "nyelv → Beszéd → Hangok hozzáadása.")

    def _hang_valasztva(self, _i: int) -> None:
        self.v.b.tts_hang = self.hang.currentData() or ""
        self.v.mentes()

    def _sablon(self, i: int) -> None:
        if i > 0:
            self.szoveg.setPlainText(self.sablon.itemData(i))
        self.sablon.setCurrentIndex(0)

    def _mond(self) -> None:
        szoveg = self.szoveg.toPlainText().strip()
        if szoveg:
            self.v.gyors_bemondas(szoveg, self.gong.isChecked())

    def _stop(self) -> None:
        self.v.bemondo.megallit()
        self.v.csengo.megallit()

    def _lista_frissit(self) -> None:
        self.lista.blockSignals(True)
        self.lista.clear()
        for b in self.v.b.bemondasok:
            mikor = b.datum if b.datum else ", ".join(NAPOK[i][:3] for i in b.napok)
            mit = "hangfájl" if b.tipus == "fajl" else f"„{b.tartalom[:50]}{'…' if len(b.tartalom) > 50 else ''}”"
            elem = QListWidgetItem(ikon("bemondas", SZIN["szoveg"]), f"{b.ido}  {b.nev}\n{mikor}, {mit}")
            elem.setFlags(elem.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            elem.setCheckState(Qt.CheckState.Checked if b.aktiv else Qt.CheckState.Unchecked)
            self.lista.addItem(elem)
        if not self.v.b.bemondasok:
            self.lista.addItem("Még nincs ütemezett bemondás.")
        self.lista.blockSignals(False)

    def _kijelolt(self) -> int:
        i = self.lista.currentRow()
        return i if 0 <= i < len(self.v.b.bemondasok) else -1

    def _aktiv_valtozott(self, elem: QListWidgetItem) -> None:
        i = self.lista.row(elem)
        if 0 <= i < len(self.v.b.bemondasok):
            self.v.b.bemondasok[i].aktiv = elem.checkState() == Qt.CheckState.Checked
            self.v.mentes()

    def _uj(self) -> None:
        ablak = BemondasAblak(self)
        if ablak.exec() == QDialog.DialogCode.Accepted:
            self.v.b.bemondasok.append(ablak.bemondas())
            self.v.b.bemondasok.sort(key=lambda b: (b.datum or "", b.ido))
            self.v.mentes()
            self._lista_frissit()

    def _szerkeszt(self) -> None:
        i = self._kijelolt()
        if i < 0:
            return
        ablak = BemondasAblak(self, self.v.b.bemondasok[i])
        if ablak.exec() == QDialog.DialogCode.Accepted:
            self.v.b.bemondasok[i] = ablak.bemondas()
            self.v.mentes()
            self._lista_frissit()

    def _proba(self) -> None:
        i = self._kijelolt()
        if i >= 0:
            self.v.bemondas(self.v.b.bemondasok[i])

    def _torol(self) -> None:
        i = self._kijelolt()
        if i < 0:
            return
        if QMessageBox.question(self, "Törlés", f"Törlöd: {self.v.b.bemondasok[i].nev}?") == \
                QMessageBox.StandardButton.Yes:
            self.v.b.bemondasok.pop(i)
            self.v.mentes()
            self._lista_frissit()

