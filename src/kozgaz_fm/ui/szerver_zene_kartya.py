__lazy_modules__ = [
    "PySide6.QtCore",
    "PySide6.QtWidgets",
    "kozgaz_fm.ui.elemek",
    "kozgaz_fm.ui.tema",
    "kozgaz_fm.vezerlo",
]

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFileDialog, QGridLayout, QLineEdit, QSpinBox

from kozgaz_fm.ui.elemek import Kartya, cimke, gomb, kapcsolo, sor
from kozgaz_fm.ui.tema import SZIN
from kozgaz_fm.vezerlo import Vezerlo


class SzerverZeneKartya(Kartya):
    def __init__(self, v: Vezerlo) -> None:
        super().__init__("Zenék a szerverről")
        self.v = v
        b = v.b
        self.add(cimke("A szerver zenemappáját a program letölti erre a gépre, és innen játssza le, így szünetben "
                       "nem streamel a hálózaton. Csak az új vagy megváltozott fájlokat tölti le, félbeszakadt "
                       "letöltésnél onnan folytatja, ahol abbamaradt, és amit a szerveren törölsz, itt is törli. "
                       "A zenekérő szerver címét és kulcsát használja; félóránként néz rá.",
                       "halvany", sortores=True))
        self.be = kapcsolo("Zenék letöltése a szerverről", b.zene_szinkron)
        self.be.toggled.connect(self._bekapcsol)
        self.mappa = QLineEdit(str(v.zene_szinkron.mappa()))
        self.mappa.editingFinished.connect(lambda: self._allit("zene_szinkron_mappa", self.mappa.text().strip()))
        valaszt = gomb("Mappa…", tipp="Hova kerüljenek a letöltött zenék ezen a gépen")
        valaszt.clicked.connect(self._mappa_valaszt)
        self.kbps = QSpinBox(minimum=0, maximum=100_000, singleStep=256, suffix=" KB/s")
        self.kbps.setSpecialValueText("korlátlan")
        self.kbps.setValue(b.zene_szinkron_kbps)
        self.kbps.valueChanged.connect(lambda e: self._allit("zene_szinkron_kbps", e))
        self.most = gomb("Letöltés most", "le", tipp="Azonnal megnézi a szervert, és letölti az új zenéket")
        self.most.clicked.connect(self.v.zene_szinkron.indit)
        self.allapot = cimke("", "halvany", sortores=True)
        racs = QGridLayout()
        racs.setVerticalSpacing(10)
        racs.addWidget(self.be, 0, 0, 1, 2)
        racs.addWidget(cimke("Letöltési mappa ezen a gépen:"), 1, 0, 1, 2)
        racs.addLayout(sor(self.mappa, valaszt), 2, 0, 1, 2)
        racs.addWidget(cimke("Sebességkorlát (hogy ne fogja meg a hálózatot):"), 3, 0)
        racs.addWidget(self.kbps, 3, 1)
        racs.setColumnStretch(0, 1)
        self.add(racs)
        self.add(sor(self.allapot, None, self.most))
        v.zene_szinkron.valtozott.connect(self.frissit)
        v.keres_szerver.valtozott.connect(self.frissit)
        self.frissit()

    def _allit(self, mezo: str, ertek) -> None:
        setattr(self.v.b, mezo, ertek)
        self.v.mentes_kesobb()

    def _bekapcsol(self, be: bool) -> None:
        self.v.b.zene_szinkron = be
        self.v.log(f"Zenék letöltése a szerverről {'bekapcsolva' if be else 'kikapcsolva'}")
        self.v.mentes()
        if be:
            QTimer.singleShot(0, self.v.zene_szinkron.indit)
        else:
            self.v.zene_szinkron.leallit()
        self.frissit()

    def _mappa_valaszt(self) -> None:
        mappa = QFileDialog.getExistingDirectory(self, "Letöltött zenék mappája", self.mappa.text())
        if mappa:
            self.mappa.setText(mappa)
            self._allit("zene_szinkron_mappa", mappa)

    def frissit(self) -> None:
        sz = self.v.zene_szinkron
        b = self.v.b
        self.most.setEnabled(sz.beallitva() and not sz.fut)
        if not b.zenekeres_szerver.strip() or not b.zenekeres_szerver_kulcs.strip():
            szoveg = "Előbb add meg lent a zenekérő szerver címét és kulcsát."
        elif not b.zene_szinkron:
            szoveg = "Kikapcsolva."
        elif sz.fut:
            szoveg = sz.allapot or "Letöltés…"
        elif sz.hiba:
            szoveg = f"<span style='color:{SZIN['hiba']}'>{sz.hiba}</span>"
        elif sz.utolso and sz.eredmeny:
            e = sz.eredmeny
            szoveg = (f"<span style='color:{SZIN['szol']}'>Naprakész</span> · {e.osszes} szám · utoljára "
                      f"{sz.utolso:%H:%M}" + (f" · {e.uj} új" if e.uj else "")
                      + (f" · {e.torolt} törölve" if e.torolt else "")
                      + (f" · {e.hibas} hibás, újrapróbálja" if e.hibas else ""))
        else:
            szoveg = "Hamarosan ellenőrzi a szervert…"
        self.allapot.setText(szoveg)
