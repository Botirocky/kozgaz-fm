import json
from dataclasses import asdict

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QTextBrowser,
)

from kozgaz_fm import APP_NEV, KESZITO, __version__, rendszer
from kozgaz_fm.beallitasok import Beallitasok, _ebbol
from kozgaz_fm.hang import eszkoz_azonosito
from kozgaz_fm.ui.elemek import Kartya, Oldal, cimke, gomb, kapcsolo, keskeny, sor
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
        racs.addWidget(self._frissites_kartya(), 2, 0)
        racs.addWidget(self._rendszer_kartya(), 2, 1)
        racs.addWidget(self._nevjegy_kartya(), 3, 0, 1, 2)
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
        self.kimenet = keskeny(QComboBox(), 18)
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
        self.kepernyo = keskeny(QComboBox(), 12)
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

    def _frissites_kartya(self) -> Kartya:
        f = self.v.frissito
        k = Kartya("Frissítések")
        modok = {"windows": "Windows-telepítő", "linux-csomag": "Linux-csomag", "venv": "Közgáz FM OS / Python",
                 "fejlesztoi": "fejlesztői futtatás (git)"}
        k.add(cimke(f"Telepített verzió: <b>{__version__}</b> · {modok.get(f.mod, f.mod)}", sortores=True))
        self.frissites_allapot = cimke(f.allapot or "Az új verziókat a GitHubról tölti le, ellenőrzött "
                                       "csomagból.", "halvany", sortores=True)
        self.frissites_halad = QProgressBar()
        self.frissites_halad.setRange(0, 1000)
        self.frissites_halad.setTextVisible(False)
        self.frissites_halad.hide()
        keres = gomb("Keresés most", "frissites")
        keres.clicked.connect(lambda: f.kereses(kezi=True))
        self.telepites_gomb = gomb("Telepítés most", "le", "fo")
        self.telepites_gomb.clicked.connect(self._telepites)
        self.telepites_gomb.setEnabled(f.kiadas is not None and f.tamogatott)
        auto_kereses = kapcsolo("Új verzió keresése automatikusan", self.v.b.frissites_kereses)
        auto_kereses.toggled.connect(lambda e: self._allit("frissites_kereses", e))
        auto = kapcsolo("Automatikus telepítés tanítási időn kívül", self.v.b.frissites_auto,
                        "Csak ha nincs óra, zene és riasztás, és a következő csengetésig van még 45 perc")
        auto.toggled.connect(lambda e: self._allit("frissites_auto", e))
        self.ujdonsagok = QTextBrowser()
        self.ujdonsagok.setOpenExternalLinks(True)
        self.ujdonsagok.setMaximumHeight(140)
        self.ujdonsagok.hide()
        k.add(self.frissites_allapot)
        k.add(self.frissites_halad)
        k.add(sor(keres, self.telepites_gomb, None))
        k.add(auto_kereses)
        k.add(auto)
        k.add(self.ujdonsagok)
        f.allapot_valtozott.connect(self.frissites_allapot.setText)
        f.halad.connect(self._halad)
        f.kiadas_valtozott.connect(self._kiadas)
        self._kiadas(f.kiadas)
        return k

    def _rendszer_kartya(self) -> Kartya:
        k = Kartya("Rendszer")
        self.ido_cimke = cimke("", "halvany", sortores=True)
        ujra = gomb("Gép újraindítása", "frissites")
        ujra.clicked.connect(lambda: self._gep("újraindítod", rendszer.gep_ujrainditas))
        le = gomb("Gép leállítása", "stop", "veszely", szin="#FFFFFF")
        le.clicked.connect(lambda: self._gep("leállítod", rendszer.gep_leallitas))
        k.add(cimke("A pontos csengetéshez a gép órájának pontosnak kell lennie (internetes időszinkron).",
                    "halvany", sortores=True))
        k.add(self.ido_cimke)
        k.add(sor(ujra, le, None))
        self._ido_frissit()
        return k

    def _ido_frissit(self) -> None:
        allapot = rendszer.ido_szinkronban()
        if allapot is None:
            self.ido_cimke.setText("Időszinkron: a Windows kezeli (Gépház → Idő és nyelv → Szinkronizálás most).")
        elif allapot:
            self.ido_cimke.setText("✓ Az óra szinkronban van az internetes időszerverrel.")
        else:
            self.ido_cimke.setText("⚠ Az óra NINCS szinkronizálva – ellenőrizd a hálózatot!")

    def _gep(self, mit: str, muvelet) -> None:
        if QMessageBox.question(self, "Rendszer", f"Biztosan {mit} a gépet? Addig nem lesz csengetés."
                                ) == QMessageBox.StandardButton.Yes:
            self.v.leallit()
            muvelet()

    def _halad(self, ertek: float) -> None:
        self.frissites_halad.show()
        self.frissites_halad.setValue(int(ertek * 1000))

    def _kiadas(self, kiadas) -> None:
        f = self.v.frissito
        self.telepites_gomb.setEnabled(kiadas is not None and f.tamogatott)
        if kiadas is None:
            self.ujdonsagok.hide()
            return
        self.telepites_gomb.setText(f"Telepítés: {kiadas.verzio}")
        self.ujdonsagok.setMarkdown(f"**{kiadas.cim}**\n\n{kiadas.leiras}\n\n[Megnyitás a GitHubon]({kiadas.oldal})")
        self.ujdonsagok.show()

    def _telepites(self) -> None:
        f = self.v.frissito
        if f.kiadas is None:
            return
        if QMessageBox.question(self, "Frissítés", f"Telepíted a(z) {f.kiadas.verzio} verziót? A program "
                                "a telepítés után újraindul (pár másodpercig nincs csengetés)."
                                ) == QMessageBox.StandardButton.Yes:
            f.telepites()

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
