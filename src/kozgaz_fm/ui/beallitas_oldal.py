import json
from dataclasses import asdict

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import QComboBox, QFileDialog, QGridLayout, QLineEdit, QMessageBox

from kozgaz_fm import APP_NEV, KESZITO, __version__, rendszer
from kozgaz_fm.beallitasok import Beallitasok, _ebbol
from kozgaz_fm.hang import eszkoz_azonosito
from kozgaz_fm.ui.elemek import Kartya, Oldal, cimke, gomb, kapcsolo, sor
from kozgaz_fm.ui.tema import logo_pixmap
from kozgaz_fm.utvonalak import adat_mappa
from kozgaz_fm.vezerlo import Vezerlo


class BeallitasOldal(Oldal):
    kijelzo_kerelem = Signal(int)
    importalva = Signal()

    def __init__(self, v: Vezerlo) -> None:
        super().__init__("Beállítások")
        self.v = v
        racs = QGridLayout()
        racs.setSpacing(16)
        racs.addWidget(self._hang_kartya(), 0, 0)
        racs.addWidget(self._inditas_kartya(), 0, 1)
        racs.addWidget(self._kijelzo_kartya(), 1, 0)
        racs.addWidget(self._mentes_kartya(), 1, 1)
        racs.addWidget(self._nevjegy_kartya(), 2, 0, 1, 2)
        racs.setColumnStretch(0, 1)
        racs.setColumnStretch(1, 1)
        self.add(racs)
        self.elrendezes.addStretch(1)
        self._media = QMediaDevices(self)
        self._media.audioOutputsChanged.connect(self._kimenetek)
        self._kimenetek()

    def _hang_kartya(self) -> Kartya:
        k = Kartya("Hangkimenet")
        k.add(cimke("Válaszd ki azt a hangkártyát / kimenetet, amelyik az iskolai hangosításra (erősítőre) "
                    "van kötve. A csengő, a zene és a bemondás is ide szól. (A Spotify a saját alkalmazásában "
                    "beállított kimenetet használja.)", "halvany", sortores=True))
        self.kimenet = QComboBox()
        self.kimenet.activated.connect(self._kimenet_valasztva)
        proba = gomb("Próbahang", "lejatszas")
        proba.clicked.connect(lambda: self.v.csengo.lejatszas(self.v.b.hang_gong, self.v.b.csengo_hangero))
        k.add(sor(self.kimenet, proba))
        return k

    def _inditas_kartya(self) -> Kartya:
        k = Kartya("Indítás és működés")
        try:
            auto_be = rendszer.automatikus_inditas()
        except OSError:
            auto_be = False
        auto = kapcsolo("Automatikus indítás bejelentkezéskor", auto_be,
                        "Bejelentkezés után a tálcán indul, és azonnal csenget a rend szerint")
        auto.toggled.connect(self._auto)
        talca = kapcsolo("Bezáráskor fusson tovább a tálcán", self.v.b.talcara_zar,
                         "Kikapcsolva az ablak bezárása leállítja a csengetést is")
        talca.toggled.connect(lambda e: self._allit("talcara_zar", e))
        k.add(auto)
        k.add(talca)
        k.add(cimke("Fontos: a csengetés csak akkor működik, ha a program fut. Az energiagazdálkodásban "
                    "kapcsold ki a gép alvó állapotát.", "halvany", sortores=True))
        return k

    def _kijelzo_kartya(self) -> Kartya:
        k = Kartya("Folyosói kijelző")
        k.add(cimke("Teljes képernyős óra és visszaszámláló kivetítőre vagy folyosói TV-re. Kilépés: Esc "
                    "vagy dupla kattintás.", "halvany", sortores=True))
        self.kijelzo_cim = QLineEdit(self.v.b.kijelzo_cim)
        self.kijelzo_cim.editingFinished.connect(lambda: self._allit("kijelzo_cim", self.kijelzo_cim.text().strip()))
        self.kepernyo = QComboBox()
        for i, kep in enumerate(QGuiApplication.screens()):
            meret = kep.size()
            self.kepernyo.addItem(f"{i + 1}. képernyő – {kep.name()} ({meret.width()}×{meret.height()})", i)
        nyit = gomb("Kijelző indítása", "kijelzo", "fo")
        nyit.clicked.connect(lambda: self.kijelzo_kerelem.emit(self.kepernyo.currentData() or 0))
        k.add(sor(cimke("Felirat:"), self.kijelzo_cim))
        k.add(sor(self.kepernyo, nyit))
        return k

    def _mentes_kartya(self) -> Kartya:
        k = Kartya("Beállítások mentése")
        k.add(cimke("Minden beállítás (csengetési rendek, naptár, zeneforrások) egy fájlba menthető, és másik "
                    "gépre vihető.", "halvany", sortores=True))
        export = gomb("Exportálás…", "le")
        export.clicked.connect(self._export)
        imp = gomb("Importálás…", "fel")
        imp.clicked.connect(self._import)
        k.add(sor(export, imp, None))
        k.add(cimke(f"Adatmappa: {adat_mappa()}", "halvany", sortores=True))
        return k

    def _nevjegy_kartya(self) -> Kartya:
        k = Kartya("Névjegy")
        logo = cimke()
        logo.setPixmap(logo_pixmap(96))
        szoveg = cimke(f"<b>{APP_NEV}</b> {__version__}<br>Iskolai csengetőrendszer és szünetzene-lejátszó."
                       f"<br>Készítette: {KESZITO}", sortores=True)
        szoveg.setTextFormat(Qt.TextFormat.RichText)
        k.add(sor(logo, szoveg, nyujt=True, terkoz=18))
        return k

    def _allit(self, mezo: str, ertek) -> None:
        setattr(self.v.b, mezo, ertek)
        self.v.mentes_kesobb()

    def _kimenetek(self) -> None:
        self.kimenet.clear()
        alap = QMediaDevices.defaultAudioOutput()
        self.kimenet.addItem(f"Rendszer alapértelmezett ({alap.description()})", "")
        for e in QMediaDevices.audioOutputs():
            self.kimenet.addItem(e.description(), eszkoz_azonosito(e))
        self.kimenet.setCurrentIndex(max(0, self.kimenet.findData(self.v.b.kimenet)))

    def _kimenet_valasztva(self, _i: int) -> None:
        self.v.b.kimenet = self.kimenet.currentData() or ""
        self.v.mentes()

    def _auto(self, be: bool) -> None:
        try:
            rendszer.automatikus_inditas_beallit(be)
            self.v.b.automatikus_inditas = be
            self.v.mentes()
        except OSError as e:
            QMessageBox.warning(self, "Automatikus indítás", f"Nem sikerült beállítani: {e}")

    def _export(self) -> None:
        ut, _ = QFileDialog.getSaveFileName(self, "Beállítások exportálása", "kozgaz-fm-beallitasok.json",
                                            "JSON (*.json)")
        if ut:
            with open(ut, "w", encoding="utf-8") as f:
                json.dump(asdict(self.v.b), f, ensure_ascii=False, indent=2)

    def _import(self) -> None:
        ut, _ = QFileDialog.getOpenFileName(self, "Beállítások importálása", "", "JSON (*.json)")
        if not ut:
            return
        try:
            with open(ut, encoding="utf-8") as f:
                uj = _ebbol(Beallitasok, json.load(f))
        except (OSError, ValueError, TypeError) as e:
            QMessageBox.warning(self, "Importálás", f"A fájl nem olvasható be: {e}")
            return
        if QMessageBox.question(self, "Importálás", "Felülírod a jelenlegi beállításokat?"
                                ) != QMessageBox.StandardButton.Yes:
            return
        self.v.b.__dict__.update(uj.__dict__)
        self.v.mentes()
        self.importalva.emit()
