from datetime import datetime

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from kozgaz_fm import APP_NEV, __version__, rendszer
from kozgaz_fm.orarend import allapot
from kozgaz_fm.ui.beallitas_oldal import BeallitasOldal
from kozgaz_fm.ui.bemondas_oldal import BemondasOldal
from kozgaz_fm.ui.csengetes_oldal import CsengetesOldal
from kozgaz_fm.ui.elemek import Ertesites, cimke, gomb
from kozgaz_fm.ui.kijelzo import Kijelzo
from kozgaz_fm.ui.naplo_oldal import NaploOldal
from kozgaz_fm.ui.naptar_oldal import NaptarOldal
from kozgaz_fm.ui.sugo_oldal import SugoOldal
from kozgaz_fm.ui.tema import SZIN, ikon, logo_ikon, logo_pixmap
from kozgaz_fm.ui.vezerlopult import Vezerlopult, idotartam
from kozgaz_fm.ui.zene_oldal import ZeneOldal
from kozgaz_fm.vezerlo import Vezerlo

OLDALAK = [
    ("Vezérlőpult", "pult", Vezerlopult),
    ("Csengetési rend", "csengo", CsengetesOldal),
    ("Zene", "zene", ZeneOldal),
    ("Naptár", "naptar", NaptarOldal),
    ("Bemondások", "bemondas", BemondasOldal),
    ("Napló", "naplo", NaploOldal),
    ("Beállítások", "beallitas", BeallitasOldal),
    ("Súgó", "nevjegy", SugoOldal),
]


class FoAblak(QMainWindow):
    def __init__(self, v: Vezerlo, kioszk: bool = False) -> None:
        super().__init__()
        self.v = v
        self.kioszk = kioszk
        self._ido_ok: bool | None = None
        self._kilepes = False
        self.kijelzo: Kijelzo | None = None
        self.setWindowTitle(APP_NEV)
        self.setWindowIcon(logo_ikon())
        self.resize(1320, 860)
        self.setMinimumSize(1000, 680)
        kozep = QWidget()
        e = QHBoxLayout(kozep)
        e.setContentsMargins(0, 0, 0, 0)
        e.setSpacing(0)
        e.addWidget(self._oldalsav())
        self.lapok = QStackedWidget()
        e.addWidget(self.lapok, 1)
        self.setCentralWidget(kozep)
        self.ertesites = Ertesites(kozep)
        self._oldalak_epit()
        self._talca()
        v.uzenet.connect(self._uzenet)
        v.riasztas_valtozott.connect(self._riasztas)
        self._masodperc = QTimer(self)
        self._masodperc.setInterval(1000)
        self._masodperc.timeout.connect(self._tick)
        self._masodperc.start()
        QShortcut(QKeySequence("F11"), self, activated=self._kijelzo_nyit)
        self._tick()

    def _oldalsav(self) -> QFrame:
        sav = QFrame()
        sav.setObjectName("oldalsav")
        sav.setFixedWidth(240)
        e = QVBoxLayout(sav)
        e.setContentsMargins(16, 22, 16, 18)
        e.setSpacing(4)
        logo = cimke()
        logo.setPixmap(logo_pixmap(150))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        e.addWidget(logo)
        e.addSpacing(18)
        self.nav = QButtonGroup(self)
        self.nav.setExclusive(True)
        for i, (nev, ikon_nev, _osztaly) in enumerate(OLDALAK):
            g = gomb(nev, szerep="nav")
            g.setIcon(ikon(ikon_nev, SZIN["halvany"], SZIN["kiemelt"]))
            g.setIconSize(QSize(20, 20))
            g.setCheckable(True)
            g.setChecked(i == 0)
            self.nav.addButton(g, i)
            e.addWidget(g)
        self.nav.idClicked.connect(self._lapozas)
        e.addStretch(1)
        self.sav_allapot = cimke("", sortores=True)
        self.sav_allapot.setStyleSheet(f"color: {SZIN['halvany']}; font-size: 9pt;")
        e.addWidget(self.sav_allapot)
        kijelzo = gomb("Kijelző mód", "kijelzo", tipp="Teljes képernyős óra (F11)")
        kijelzo.clicked.connect(self._kijelzo_nyit)
        e.addWidget(kijelzo)
        verzio = cimke(f"v{__version__}", "halvany")
        verzio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        e.addWidget(verzio)
        return sav

    def _oldalak_epit(self) -> None:
        aktualis = max(0, self.lapok.currentIndex())
        while self.lapok.count():
            regi = self.lapok.widget(0)
            self.lapok.removeWidget(regi)
            regi.deleteLater()
        self.oldalak = [osztaly(self.v) for _n, _i, osztaly in OLDALAK]
        for oldal in self.oldalak:
            self.lapok.addWidget(oldal)
        beall = next(o for o in self.oldalak if isinstance(o, BeallitasOldal))
        beall.kijelzo_kerelem.connect(self._kijelzo_nyit)
        beall.importalva.connect(lambda: QTimer.singleShot(0, self._oldalak_epit))
        self.lapok.setCurrentIndex(aktualis)

    def _lapozas(self, index: int) -> None:
        self.lapok.setCurrentIndex(index)
        self.oldalak[index].frissit()

    def _talca(self) -> None:
        self.talca = QSystemTrayIcon(logo_ikon(), self)
        menu = QMenu()
        menu.addAction("Megnyitás", self.elohoz)
        menu.addSeparator()
        menu.addAction(ikon("csengo", SZIN["szoveg"]), "Csengetés most",
                       lambda: self.v.csengetes(self.v.b.hang_becsengo))
        self.zene_akcio = QAction(ikon("zene", SZIN["szoveg"]), "Zene indítása", self)
        self.zene_akcio.triggered.connect(self.v.zene_valt)
        menu.addAction(self.zene_akcio)
        menu.addSeparator()
        menu.addAction("Kilépés", self.kilepes)
        menu.aboutToShow.connect(lambda: self.zene_akcio.setText("Zene leállítása" if self.v.zene.szol
                                                                  else "Zene indítása"))
        self.talca.setContextMenu(menu)
        self.talca.activated.connect(self._talca_kattintas)
        self.talca.setToolTip(APP_NEV)
        if QSystemTrayIcon.isSystemTrayAvailable() and not self.kioszk:
            self.talca.show()

    def _talca_kattintas(self, ok: QSystemTrayIcon.ActivationReason) -> None:
        if ok in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            if self.isVisible() and not self.isMinimized():
                self.hide()
            else:
                self.elohoz()

    def elohoz(self) -> None:
        if self.kioszk:
            self.showFullScreen()
            return
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _tick(self) -> None:
        most = datetime.now()
        a = allapot(self.v.b, most)
        hatra = a.hatralevo(most)
        szoveg = a.cim + (f" · még {idotartam(hatra)}" if hatra is not None else "")
        zene = "\n♪ zene szól" if self.v.zene.szol else ""
        if most.second == 0 and most.minute % 5 == 0 or not hasattr(self, "_ido_nezve"):
            self._ido_nezve = True
            self._ido_ok = rendszer.ido_szinkronban()
        extra = "<br>♪ zene szól" if zene else ""
        if self._ido_ok is False:
            extra += f"<br><span style='color:{SZIN['figyelem']}'>⚠ Az óra nincs szinkronban</span>"
        if self.v.frissito.kiadas is not None:
            extra += f"<br><span style='color:{SZIN['kiemelt']}'>↑ Új verzió: {self.v.frissito.kiadas.verzio}</span>"
        self.sav_allapot.setText(f"<span style='color:{SZIN['szol']}'>●</span> Automatika fut<br>{szoveg}{extra}")
        self.talca.setToolTip(f"{APP_NEV}\n{szoveg}{zene}")
        aktualis = self.lapok.currentWidget()
        if isinstance(aktualis, Vezerlopult):
            aktualis.frissit()
        if self.kijelzo is not None:
            self.kijelzo.frissit()

    def _uzenet(self, szoveg: str, szint: str) -> None:
        self.ertesites.mutat(szoveg, szint)
        if szint == "hiba" and not self.isVisible() and self.talca.isVisible():
            self.talca.showMessage(APP_NEV, szoveg, QSystemTrayIcon.MessageIcon.Warning, 6000)

    def _riasztas(self, be: bool) -> None:
        if be:
            self.elohoz()
            self.ertesites.mutat("RIASZTÁS folyamatban – a Vezérlőpulton állítható le.", "hiba")

    def _kijelzo_nyit(self, kepernyo: int = -1) -> None:
        if self.kijelzo is None:
            self.kijelzo = Kijelzo(self.v)
        kepek = QGuiApplication.screens()
        if not isinstance(kepernyo, int) or not 0 <= kepernyo < len(kepek):
            kepernyo = len(kepek) - 1 if len(kepek) > 1 else 0
        self.kijelzo.setScreen(kepek[kepernyo])
        self.kijelzo.setGeometry(kepek[kepernyo].geometry())
        self.kijelzo.showFullScreen()

    def closeEvent(self, esemeny: QCloseEvent) -> None:
        if self.kioszk and not self._kilepes:
            esemeny.ignore()
            return
        if not self._kilepes and self.v.b.talcara_zar and self.talca.isVisible():
            esemeny.ignore()
            self.hide()
            if not getattr(self, "_talca_jelezve", False):
                self._talca_jelezve = True
                self.talca.showMessage(APP_NEV, "A program a tálcán fut tovább, a csengetés működik.",
                                       QSystemTrayIcon.MessageIcon.Information, 4000)
            return
        if not self._kilepes:
            valasz = QMessageBox.question(self, "Kilépés", "Ha kilépsz, nem lesz csengetés és szünetzene. "
                                          "Biztosan kilépsz?")
            if valasz != QMessageBox.StandardButton.Yes:
                esemeny.ignore()
                return
        self.v.leallit()
        if self.kijelzo is not None:
            self.kijelzo.close()
        self.talca.hide()
        esemeny.accept()
        QApplication.quit()

    def kilepes(self) -> None:
        valasz = QMessageBox.question(self, "Kilépés", "Ha kilépsz, nem lesz csengetés és szünetzene. "
                                      "Biztosan kilépsz?")
        if valasz == QMessageBox.StandardButton.Yes:
            self._kilepes = True
            self.close()
