from datetime import datetime, timedelta

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
from kozgaz_fm.hang import kimeneti_eszkoz
from kozgaz_fm.orarend import Szakasz, allapot
from kozgaz_fm.ui.beallitas_oldal import BeallitasOldal
from kozgaz_fm.ui.bemondas_oldal import BemondasOldal
from kozgaz_fm.ui.csengetes_oldal import CsengetesOldal
from kozgaz_fm.ui.elemek import Ertesites, cimke, gomb
from kozgaz_fm.ui.kijelzo import Kijelzo
from kozgaz_fm.ui.naplo_oldal import NaploOldal
from kozgaz_fm.ui.naptar_oldal import NaptarOldal
from kozgaz_fm.ui.sugo_oldal import SugoOldal
from kozgaz_fm.ui.tema import SZIN, ikon, logo_ikon, logo_pixmap, szam_betu
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
        jobb = QVBoxLayout()
        jobb.setContentsMargins(0, 0, 0, 0)
        jobb.setSpacing(0)
        jobb.addWidget(self._fejlec())
        self.lapok = QStackedWidget()
        jobb.addWidget(self.lapok, 1)
        jobb.addWidget(self._allapotsor())
        e.addLayout(jobb, 1)
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
        sav.setFixedWidth(220)
        e = QVBoxLayout(sav)
        e.setContentsMargins(0, 22, 0, 16)
        e.setSpacing(2)
        logo = cimke()
        logo.setPixmap(logo_pixmap(116))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        e.addWidget(logo)
        e.addSpacing(22)
        self.nav = QButtonGroup(self)
        self.nav.setExclusive(True)
        for i, (nev, ikon_nev, _osztaly) in enumerate(OLDALAK):
            g = gomb(nev, szerep="nav")
            g.setIcon(ikon(ikon_nev, SZIN["halvany"], SZIN["kek"]))
            g.setIconSize(QSize(18, 18))
            g.setCheckable(True)
            g.setChecked(i == 0)
            self.nav.addButton(g, i)
            e.addWidget(g)
        self.nav.idClicked.connect(self._lapozas)
        e.addStretch(1)
        kijelzo = gomb("Folyosói kijelző", "kijelzo", "sav", "Teljes képernyős óra kivetítőre vagy TV-re (F11)")
        alja = QHBoxLayout()
        alja.setContentsMargins(16, 0, 16, 0)
        alja.addWidget(kijelzo)
        e.addLayout(alja)
        return sav

    def _fejlec(self) -> QFrame:
        fejlec = QFrame()
        fejlec.setObjectName("fejlec")
        fejlec.setFixedHeight(68)
        e = QHBoxLayout(fejlec)
        e.setContentsMargins(28, 0, 28, 0)
        e.setSpacing(18)
        self.fej_cim = cimke("", "cim")
        e.addWidget(self.fej_cim)
        e.addStretch(1)
        self.elo = QFrame()
        self.elo.setObjectName("elo")
        elo_e = QHBoxLayout(self.elo)
        elo_e.setContentsMargins(10, 5, 12, 5)
        elo_e.setSpacing(8)
        self.elo_ikon = cimke()
        self.elo_szoveg = cimke()
        self.elo_szoveg.setMaximumWidth(360)
        elo_e.addWidget(self.elo_ikon)
        elo_e.addWidget(self.elo_szoveg)
        e.addWidget(self.elo)
        jobb = QVBoxLayout()
        jobb.setSpacing(1)
        self.fej_szakasz = cimke()
        self.fej_szakasz.setFont(szam_betu(11))
        self.fej_szakasz.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.fej_hatra = cimke("", "halvany")
        self.fej_hatra.setFont(szam_betu(9, self.fej_hatra.font().weight()))
        self.fej_hatra.setAlignment(Qt.AlignmentFlag.AlignRight)
        jobb.addStretch(1)
        jobb.addWidget(self.fej_szakasz)
        jobb.addWidget(self.fej_hatra)
        jobb.addStretch(1)
        e.addLayout(jobb)
        self.fej_ora = cimke()
        self.fej_ora.setFont(szam_betu(22, szam_betu(1).weight()))
        e.addWidget(self.fej_ora)
        return fejlec

    def _allapotsor(self) -> QFrame:
        sor_ = QFrame()
        sor_.setObjectName("allapotsor")
        sor_.setFixedHeight(30)
        e = QHBoxLayout(sor_)
        e.setContentsMargins(16, 0, 16, 0)
        e.setSpacing(22)
        self.as_automatika = cimke()
        self.as_kimenet = cimke()
        self.as_ido = cimke()
        self.as_frissites = cimke()
        for c in (self.as_automatika, self.as_kimenet, self.as_ido, self.as_frissites):
            e.addWidget(c)
        e.addStretch(1)
        e.addWidget(cimke(f"{APP_NEV} {__version__}"))
        return sor_

    def _oldalak_epit(self) -> None:
        aktualis = max(0, self.lapok.currentIndex())
        while self.lapok.count():
            regi = self.lapok.widget(0)
            self.lapok.removeWidget(regi)
            regi.deleteLater()
        self.oldalak = [osztaly(self.v) for _n, _i, osztaly in OLDALAK]
        for oldal in self.oldalak:
            if hasattr(oldal, "cim_cimke"):
                oldal.cim_cimke.hide()
            self.lapok.addWidget(oldal)
        beall = next(o for o in self.oldalak if isinstance(o, BeallitasOldal))
        beall.kijelzo_kerelem.connect(self._kijelzo_nyit)
        beall.importalva.connect(lambda: QTimer.singleShot(0, self._oldalak_epit))
        self.lapok.setCurrentIndex(aktualis)
        self.fej_cim.setText(OLDALAK[aktualis][0])

    def _lapozas(self, index: int) -> None:
        self.lapok.setCurrentIndex(index)
        self.fej_cim.setText(OLDALAK[index][0])
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
        szoveg = a.cim + (f", még {idotartam(hatra)}" if hatra is not None else "")
        zene = f"\nZene: {self.v.zene.most_cim}" if self.v.zene.szol and self.v.zene.most_cim else ""
        if most.second == 0 and most.minute % 5 == 0 or not hasattr(self, "_ido_nezve"):
            self._ido_nezve = True
            self._ido_ok = rendszer.ido_szinkronban()
        self._fejlec_frissit(most, a, hatra)
        self._allapotsor_frissit()
        self.talca.setToolTip(f"{APP_NEV}\n{szoveg}{zene}")
        aktualis = self.lapok.currentWidget()
        if isinstance(aktualis, Vezerlopult):
            aktualis.frissit()
        if self.kijelzo is not None:
            self.kijelzo.frissit()

    def _fejlec_frissit(self, most: datetime, a, hatra) -> None:
        self.fej_ora.setText(f"{most:%H:%M:%S}")
        pulton = isinstance(self.lapok.currentWidget(), Vezerlopult)
        self.fej_szakasz.setVisible(not pulton)
        self.fej_hatra.setVisible(not pulton)
        self.fej_szakasz.setText(a.cim)
        if a.szakasz is Szakasz.ORA:
            self.fej_hatra.setText(f"Kicsengetésig {idotartam(hatra)}")
        elif a.szakasz in (Szakasz.SZUNET, Szakasz.REGGEL):
            self.fej_hatra.setText(f"Becsengetésig {idotartam(hatra)}")
        elif a.kovetkezo is not None:
            nap = "holnap" if a.kovetkezo.ido.date() == most.date() + timedelta(days=1) else f"{a.kovetkezo.ido:%m.%d.}"
            self.fej_hatra.setText(f"Következő csengetés {nap} {a.kovetkezo.ido:%H:%M}")
        else:
            self.fej_hatra.setText("A következő két hétben nincs csengetés")
        riaszt = self.v.riasztas
        szol = self.v.zene.szol
        self.elo.setVisible(riaszt or szol)
        allapot_ = "szol" if szol and not riaszt else ""
        if self.elo.property("allapot") != allapot_:
            self.elo.setProperty("allapot", allapot_)
            self.elo.style().unpolish(self.elo)
            self.elo.style().polish(self.elo)
        if riaszt:
            self.elo_ikon.setPixmap(ikon("riasztas", SZIN["hiba"]).pixmap(16, 16))
            self.elo_szoveg.setText("Riasztás szól")
        elif szol:
            self.elo_ikon.setPixmap(ikon("zene", SZIN["kiemelt"]).pixmap(16, 16))
            cim = self.v.zene.most_cim or "Szünetzene"
            metrika = self.elo_szoveg.fontMetrics()
            self.elo_szoveg.setText(metrika.elidedText(cim, Qt.TextElideMode.ElideRight, 340))

    def _allapotsor_frissit(self) -> None:
        if self.v.riasztas:
            self.as_automatika.setText(f"<span style='color:{SZIN['hiba']}'>&#9679;</span>&nbsp; Riasztás")
        else:
            self.as_automatika.setText(f"<span style='color:{SZIN['szol']}'>&#9679;</span>&nbsp; Automatika fut")
        nev = getattr(self, "_kimenet_nev", None)
        if nev is None or getattr(self, "_kimenet_kulcs", None) != self.v.b.kimenet:
            self._kimenet_kulcs = self.v.b.kimenet
            self._kimenet_nev = nev = kimeneti_eszkoz(self.v.b.kimenet).description() or "alapértelmezett"
        self.as_kimenet.setText(f"Hangkimenet: {nev}")
        if self._ido_ok is False:
            self.as_ido.setText(f"<span style='color:{SZIN['figyelem']}'>Az óra nincs szinkronban "
                                "az internetes időszerverrel</span>")
        else:
            self.as_ido.setText("Pontos idő: szinkronban" if self._ido_ok else "")
        kiadas = self.v.frissito.kiadas
        self.as_frissites.setText(f"<span style='color:{SZIN['kek']}'>Új verzió érhető el: {kiadas.verzio}</span>"
                                  if kiadas is not None else "")

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
