__lazy_modules__ = [
    "PySide6.QtCore",
    "PySide6.QtMultimedia",
    "PySide6.QtWidgets",
    "kozgaz_fm.beallitasok",
    "kozgaz_fm.bemondo",
    "kozgaz_fm.kimenetek",
    "kozgaz_fm.ui.elemek",
    "kozgaz_fm.vezerlo",
]

from PySide6.QtCore import Qt, Signal
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import QCheckBox, QComboBox, QGridLayout, QLineEdit, QSpinBox, QWidget

from kozgaz_fm.beallitasok import Zona
from kozgaz_fm.bemondo import espeak_ut
from kozgaz_fm.kimenetek import eszkoz_azonosito
from kozgaz_fm.ui.elemek import Kartya, cimke, gomb, keskeny, sor
from kozgaz_fm.vezerlo import Vezerlo

OSZLOPOK = ["Zóna neve", "Hangkimenet", "Csengő", "Zene", "Bemondás", "Hangerő", ""]


def _urit(elrendezes) -> None:
    while elrendezes.count():
        elem = elrendezes.takeAt(0)
        if elem is None:
            break
        if elem.widget() is not None:
            elem.widget().deleteLater()
        elif elem.layout() is not None:
            _urit(elem.layout())


class ZonakKartya(Kartya):
    valtozott = Signal()

    def __init__(self, v: Vezerlo) -> None:
        super().__init__("Hangzónák")
        self.v = v
        self.add(cimke("Ha több hangkimenet van (pl. folyosó, udvar, tanári), itt zónánként állíthatod, mi szóljon "
                       "ott. A riasztás mindig minden zónában szól. Üres lista esetén minden a fenti Hangkimenetre "
                       "megy, mint eddig.", "halvany", sortores=True))
        self.racs_doboz = QWidget()
        self.racs = QGridLayout(self.racs_doboz)
        self.racs.setContentsMargins(0, 0, 0, 0)
        self.racs.setHorizontalSpacing(10)
        self.racs.setVerticalSpacing(6)
        self.add(self.racs_doboz)
        uj = gomb("Zóna hozzáadása", "plusz")
        uj.clicked.connect(self._uj)
        self.megjegyzes = cimke("", "halvany", sortores=True)
        self.add(sor(uj, None))
        self.add(self.megjegyzes)
        self._media = QMediaDevices(self)
        self._media.audioOutputsChanged.connect(self.frissit)
        self.frissit()

    def _eszkozok(self) -> list[tuple[str, str]]:
        alap = QMediaDevices.defaultAudioOutput()
        return [(f"Alapértelmezett ({alap.description()})", "")] + [
            (e.description(), eszkoz_azonosito(e)) for e in QMediaDevices.audioOutputs()]

    def frissit(self) -> None:
        _urit(self.racs)
        zonak = self.v.b.zonak
        self.racs_doboz.setVisible(bool(zonak))
        if zonak:
            for oszlop, felirat in enumerate(OSZLOPOK):
                self.racs.addWidget(cimke(felirat, "halvany"), 0, oszlop)
        eszkozok = self._eszkozok()
        for i, z in enumerate(zonak, 1):
            nev = QLineEdit(z.nev)
            nev.setPlaceholderText(f"{i}. zóna")
            nev.editingFinished.connect(lambda n=nev, z=z: self._allit(z, "nev", n.text().strip()))
            kimenet = keskeny(QComboBox(), 22)
            for felirat, azon in eszkozok:
                kimenet.addItem(felirat, azon)
            if z.kimenet and kimenet.findData(z.kimenet) < 0:
                kimenet.addItem("Nem elérhető eszköz (kihúzták?)", z.kimenet)
            kimenet.setCurrentIndex(max(0, kimenet.findData(z.kimenet)))
            kimenet.activated.connect(lambda _x, k=kimenet, z=z: self._allit(z, "kimenet", k.currentData() or ""))
            self.racs.addWidget(nev, i, 0)
            self.racs.addWidget(kimenet, i, 1)
            for oszlop, mezo in enumerate(("csengo", "zene", "bemondas"), 2):
                pipa = QCheckBox()
                pipa.setChecked(getattr(z, mezo))
                pipa.setToolTip(f"{OSZLOPOK[oszlop]} szóljon ebben a zónában")
                pipa.toggled.connect(lambda e, z=z, m=mezo: self._allit(z, m, e))
                self.racs.addWidget(pipa, i, oszlop, alignment=Qt.AlignmentFlag.AlignCenter)
            hangero = QSpinBox(minimum=0, maximum=100, suffix=" %")
            hangero.setValue(min(100, z.hangero))
            hangero.setToolTip("Halkítás ebben a zónában (100% = teljes). A riasztást nem halkítja.")
            hangero.editingFinished.connect(lambda h=hangero, z=z: self._allit(z, "hangero", h.value()))
            self.racs.addWidget(hangero, i, 5)
            proba = gomb("", "lejatszas", tipp="Próbahang csak ebben a zónában")
            proba.clicked.connect(lambda _x=False, idx=i - 1: self.v.zona_proba(idx))
            torol = gomb("", "kuka", tipp="Zóna törlése")
            torol.clicked.connect(lambda _x=False, z=z: self._torol(z))
            self.racs.addLayout(sor(proba, torol, terkoz=4), i, 6)
        self.racs.setColumnStretch(1, 1)
        self._megjegyzes()

    def _megjegyzes(self) -> None:
        zonak = self.v.b.zonak
        sorok = []
        if zonak and not any(z.zene for z in zonak):
            sorok.append("Egyik zónában sincs bekapcsolva a zene, így a szünetzene sehol sem szól.")
        if zonak and not any(z.csengo for z in zonak):
            sorok.append("Figyelem: egyik zónában sincs csengő!")
        eszkozok = [z.kimenet for z in zonak]
        if len(eszkozok) != len(set(eszkozok)):
            sorok.append("Két zóna ugyanarra a hangkimenetre szól – ott minden kétszer szólna. Válassz másik "
                         "kimenetet, vagy töröld az egyiket.")
        if zonak and espeak_ut() is None:
            sorok.append("A felolvasott bemondás ezen a gépen az alapértelmezett kimeneten szól (a zónákra "
                         "irányításához az eSpeak NG kell); a gong és a hangfájlos bemondás zónák szerint megy.")
        elif zonak:
            sorok.append("A zónás felolvasás az eSpeak NG magyar hangját használja (a Bemondások oldalon "
                         "választott hang helyett).")
        hianyzo = self.v.hianyzo_zonak()
        if hianyzo:
            sorok.append(f"Nem érhető el: {', '.join(hianyzo)} – ott az alapértelmezett kimenet szól.")
        self.megjegyzes.setText(" ".join(sorok))
        self.megjegyzes.setVisible(bool(sorok))

    def _uj(self) -> None:
        zonak = self.v.b.zonak
        if not zonak:
            zonak.append(Zona("Folyosó", self.v.b.kimenet))
        foglalt = {z.kimenet or eszkoz_azonosito(QMediaDevices.defaultAudioOutput()) for z in zonak}
        szabad = next((azon for _f, azon in self._eszkozok()[1:] if azon not in foglalt), None)
        if szabad is not None or len(zonak) > 1:
            zonak.append(Zona(f"{len(zonak) + 1}. zóna", szabad or "", csengo=True, zene=False, bemondas=True))
        self.v.mentes()
        self.frissit()
        self.valtozott.emit()

    def _allit(self, z: Zona, mezo: str, ertek) -> None:
        if getattr(z, mezo) == ertek:
            return
        setattr(z, mezo, ertek)
        self.v.mentes()
        self._megjegyzes()

    def _torol(self, z: Zona) -> None:
        if z in self.v.b.zonak:
            self.v.b.zonak.remove(z)
            self.v.mentes()
            self.frissit()
            self.valtozott.emit()
