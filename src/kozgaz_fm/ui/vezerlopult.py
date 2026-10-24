__lazy_modules__ = [
    "datetime",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "kozgaz_fm",
    "kozgaz_fm.hang",
    "kozgaz_fm.orarend",
    "kozgaz_fm.ui.elemek",
    "kozgaz_fm.ui.idovonal",
    "kozgaz_fm.ui.tema",
    "kozgaz_fm.vezerlo",
]

from datetime import datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QProgressBar,
    QSlider,
)

from kozgaz_fm import sajat_hangok
from kozgaz_fm.hang import FORRAS_TIPUSOK
from kozgaz_fm.orarend import CSENGOK, KULONLEGES, Szakasz, Tipus, allapot, napi_orak
from kozgaz_fm.ui.elemek import Kartya, Oldal, cimke, gomb, ikon_gomb, kapcsolo, sor
from kozgaz_fm.ui.idovonal import Idovonal
from kozgaz_fm.ui.tema import SZIN, ikon, szam_betu
from kozgaz_fm.vezerlo import Vezerlo

HONAPOK = ["január", "február", "március", "április", "május", "június", "július", "augusztus", "szeptember",
           "október", "november", "december"]
NAPOK = ["hétfő", "kedd", "szerda", "csütörtök", "péntek", "szombat", "vasárnap"]


def idotartam(td: timedelta | None) -> str:
    if td is None:
        return "–"
    mp = int(td.total_seconds())
    ora, mp = divmod(mp, 3600)
    perc, mp = divmod(mp, 60)
    return f"{ora}:{perc:02d}:{mp:02d}" if ora else f"{perc:02d}:{mp:02d}"


class Vezerlopult(Oldal):
    def __init__(self, v: Vezerlo) -> None:
        super().__init__("Vezérlőpult")
        self.v = v
        self.add(self._allapot_kartya())
        self.racs = QGridLayout()
        self.racs.setSpacing(14)
        self._kartyak = [self._gyors_kartya(), self._zene_kartya(), self._mai_kartya()]
        self._szeles: bool | None = None
        self._elrendez(True)
        self.add(self.racs)
        self.elrendezes.addStretch(1)
        v.frissult.connect(self.frissit)
        v.zene.szam_valtozott.connect(self._szam)
        v.zene.allapot_valtozott.connect(self._zene_gombok)
        v.zene.lista_valtozott.connect(self._zene_gombok)
        v.riasztas_valtozott.connect(self._riasztas_valtozott)
        self.frissit()

    def _elrendez(self, szeles: bool) -> None:
        if szeles == self._szeles:
            return
        self._szeles = szeles
        for k in self._kartyak:
            self.racs.removeWidget(k)
        gyors, zene, mai = self._kartyak
        if szeles:
            self.racs.addWidget(gyors, 0, 0)
            self.racs.addWidget(zene, 0, 1)
            self.racs.addWidget(mai, 0, 2)
        else:
            self.racs.addWidget(gyors, 0, 0)
            self.racs.addWidget(zene, 0, 1)
            self.racs.addWidget(mai, 1, 0, 1, 2)
        for oszlop in range(3):
            self.racs.setColumnStretch(oszlop, 1 if szeles or oszlop < 2 else 0)

    def resizeEvent(self, esemeny) -> None:
        super().resizeEvent(esemeny)
        self._elrendez(self.width() >= 1080)

    def _allapot_kartya(self) -> Kartya:
        k = Kartya("A mai nap")
        self.nap_kartya = k
        self.szakasz_cimke = cimke()
        self.szakasz_cimke.setFont(szam_betu(24))
        self.hatra_cimke = cimke()
        self.hatra_cimke.setFont(szam_betu(13, szam_betu(1).weight()))
        self.hatra_cimke.setStyleSheet(f"color: {SZIN['kek']};")
        self.kovetkezo_cimke = cimke("", "halvany")
        self.kovetkezo_cimke.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        bal = sor(self.szakasz_cimke, self.hatra_cimke, terkoz=18)
        bal.setAlignment(self.hatra_cimke, Qt.AlignmentFlag.AlignBaseline)
        k.add(sor(bal, None, self.kovetkezo_cimke))
        self.idovonal = Idovonal()
        k.add(self.idovonal)
        self.halad = QProgressBar()
        self.halad.hide()
        return k

    def _zene_kartya(self) -> Kartya:
        k = Kartya("Szünetzene")
        self.forras_valaszto = QComboBox()
        self.forras_valaszto.setMinimumHeight(38)
        self.forras_valaszto.activated.connect(self._forras_valasztva)
        self.szam_cimke = cimke("Nem szól zene", "alcim", sortores=True)
        self.szam_cimke.setTextFormat(Qt.TextFormat.PlainText)
        self.szam_cimke.setMinimumHeight(48)
        self.forras_cimke = cimke("", "halvany")
        self.elozo_gomb = ikon_gomb("elozo", "Előző szám")
        self.lejatszas_gomb = ikon_gomb("lejatszas", "Lejátszás / szünet", "kerek_fo", 26, SZIN["kiemelt_szoveg"])
        self.kovetkezo_gomb = ikon_gomb("kovetkezo", "Következő szám")
        self.stop_gomb = ikon_gomb("stop", "Zene leállítása")
        self.elozo_gomb.clicked.connect(self.v.zene.elozo)
        self.kovetkezo_gomb.clicked.connect(self.v.zene.kovetkezo)
        self.lejatszas_gomb.clicked.connect(self.v.zene_valt)
        self.stop_gomb.clicked.connect(self.v.zene_leallit)
        self.hangero = QSlider(Qt.Orientation.Horizontal)
        self.hangero.setRange(0, 100)
        self.hangero.setValue(self.v.b.zene_hangero)
        self.hangero.setToolTip("Zene hangereje")
        self.hangero.valueChanged.connect(self._hangero)
        self.hangero.sliderReleased.connect(self.v.b.mentes)
        self.hangero_cimke = cimke(f"{self.v.b.zene_hangero}%", "halvany")
        self.hangero_cimke.setMinimumWidth(40)
        hangero_ikon = cimke()
        hangero_ikon.setPixmap(ikon("hangero").pixmap(20, 20))
        k.add(self.forras_valaszto)
        k.add(self.szam_cimke)
        k.add(self.forras_cimke)
        k.add(sor(None, self.elozo_gomb, self.lejatszas_gomb, self.kovetkezo_gomb, self.stop_gomb, None, terkoz=14))
        k.add(sor(hangero_ikon, self.hangero, self.hangero_cimke))
        self.zene_kapcsolo = kapcsolo("Ma legyen szünetzene", self.v.b.ma_nincs_zene != _ma(),
                                      "Kikapcsolva ma nem indul automatikusan zene a szünetekben")
        self.zene_kapcsolo.toggled.connect(lambda be: self.v.ma_kapcsolo("ma_nincs_zene", not be))
        k.add(self.zene_kapcsolo)
        return k

    def _gyors_kartya(self) -> Kartya:
        k = Kartya("Gyors műveletek")
        csengetes = gomb("Csengetés most", "csengo", "adas", "Azonnali csengetés a becsengő hangjával")
        csengetes.setMinimumHeight(52)
        csengetes.clicked.connect(lambda: self.v.csengetes(self.v.b.hang_becsengo))
        menu = QMenu(self)
        menu.aboutToShow.connect(lambda: self._hang_menu(menu))
        tobb = gomb("Más hang…", "csengo")
        tobb.setMinimumHeight(52)
        tobb.setMenu(menu)
        bemondas = gomb("Bemondás", "bemondas", tipp="Szöveg felolvasása a hangosbemondón (gonggal)")
        bemondas.setMinimumHeight(52)
        bemondas.clicked.connect(self._gyors_bemondas)
        self.riasztas_gomb = gomb("Riasztás", "riasztas", "veszely", "Riasztó hang folyamatosan, a zene leáll")
        self.riasztas_gomb.setMinimumHeight(52)
        self.riasztas_gomb.clicked.connect(self._riasztas)
        k.add(sor(csengetes, tobb))
        k.add(sor(bemondas, self.riasztas_gomb))
        self.csengetes_kapcsolo = kapcsolo("Ma legyen csengetés", self.v.b.ma_nincs_csengetes != _ma(),
                                           "Kikapcsolva ma egyáltalán nem csenget (pl. kirándulás, rendezvény)")
        self.csengetes_kapcsolo.toggled.connect(lambda be: self.v.ma_kapcsolo("ma_nincs_csengetes", not be))
        k.add(self.csengetes_kapcsolo)
        self.ma_rend = QComboBox()
        self.ma_rend.setToolTip("Csak a mai napra vonatkozik, éjfélkor visszaáll")
        self.ma_rend.activated.connect(self._ma_rend_valasztva)
        k.add(cimke("Mai csengetési rend (éjfélkor visszaáll):", "halvany"))
        k.add(self.ma_rend)
        return k

    def _hang_menu(self, menu: QMenu) -> None:
        menu.clear()
        menu.addAction("Jelzőcsengő", lambda: self.v.csengetes(self.v.b.hang_jelzo, "Kézi jelzőcsengő"))
        menu.addAction("Kicsengő", lambda: self.v.csengetes(self.v.b.hang_kicsengo, "Kézi kicsengő"))
        menu.addAction("Gong", lambda: self.v.csengetes(self.v.b.hang_gong, "Kézi gong"))
        sajatok = sajat_hangok.lista()
        if sajatok:
            menu.addSection("Saját hangok")
            zene = ikon("zene")
            for h in sajatok:
                menu.addAction(zene, h.nev, lambda h=h: self.v.csengetes(h.ertek, f"Saját hang: {h.nev}"))

    def _mai_kartya(self) -> Kartya:
        k = Kartya("Mai menetrend")
        self.lista = QListWidget()
        self.lista.setMinimumHeight(260)
        self.lista.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        k.add(self.lista)
        return k

    def frissit(self) -> None:
        b = self.v.b
        most = datetime.now()
        a = allapot(b, most)
        self.nap_kartya.cim.setText(f"{most.year}. {HONAPOK[most.month - 1]} {most.day}., {NAPOK[most.weekday()]}")
        self.szakasz_cimke.setText(a.cim)
        hatra = a.hatralevo(most)
        if a.szakasz is Szakasz.ORA:
            self.hatra_cimke.setText(f"kicsengetésig {idotartam(hatra)}")
        elif a.szakasz in (Szakasz.SZUNET, Szakasz.REGGEL):
            self.hatra_cimke.setText(f"becsengetésig {idotartam(hatra)}")
        else:
            self.hatra_cimke.setText("")
        if a.kovetkezo:
            nap = "Ma" if a.kovetkezo.ido.date() == most.date() else f"{a.kovetkezo.ido:%m.%d.}"
            kovetkezo = f"Következő: {nap} {a.kovetkezo.ido:%H:%M}, {a.kovetkezo.leiras}"
        else:
            kovetkezo = "A következő két hétben nincs csengetés"
        self.kovetkezo_cimke.setText(f"Csendes időszak: {a.csend} · {kovetkezo}" if a.csend else kovetkezo)
        ures = a.szunnap_nev or ("Ma nincs csengetés" if a.szakasz is Szakasz.NINCS else "Ma nincs tanítás")
        self.idovonal.beallit(napi_orak(b, most.date()), most, self.v.zene.szol, ures)
        if not self.isVisible():
            return
        self._forrasok()
        self._mai_lista(most)
        self._ma_rendek()
        self.csengetes_kapcsolo.blockSignals(True)
        self.csengetes_kapcsolo.setChecked(b.ma_nincs_csengetes != _ma())
        self.csengetes_kapcsolo.blockSignals(False)
        self.zene_kapcsolo.blockSignals(True)
        self.zene_kapcsolo.setChecked(b.ma_nincs_zene != _ma())
        self.zene_kapcsolo.blockSignals(False)
        if not self.hangero.isSliderDown() and self.hangero.value() != b.zene_hangero:
            self.hangero.blockSignals(True)
            self.hangero.setValue(b.zene_hangero)
            self.hangero.blockSignals(False)
            self.hangero_cimke.setText(f"{b.zene_hangero}%")
        self._zene_gombok()

    def _forrasok(self) -> None:
        b = self.v.b
        aktiv = self.v.aktiv_forras()
        self.forras_valaszto.blockSignals(True)
        self.forras_valaszto.clear()
        for i, f in enumerate(b.forrasok):
            if f.aktiv:
                self.forras_valaszto.addItem(ikon(_forras_ikon(f.tipus), SZIN["szoveg"]),
                                             f"{f.nev} ({FORRAS_TIPUSOK.get(f.tipus, f.tipus).lower()})", i)
        if not b.forrasok:
            self.forras_valaszto.addItem("Nincs zeneforrás – add hozzá a Zene oldalon", -1)
        elif aktiv is not None:
            self.forras_valaszto.setCurrentIndex(max(0, self.forras_valaszto.findData(b.forrasok.index(aktiv))))
        self.forras_valaszto.blockSignals(False)

    def _forras_valasztva(self, _sor: int) -> None:
        index = self.forras_valaszto.currentData()
        if isinstance(index, int) and index >= 0:
            self.v.forras_valtas(index)

    def _mai_lista(self, most: datetime) -> None:
        esemenyek = [e for e in self.v.mai_esemenyek() if e.tipus in CSENGOK or e.tipus in KULONLEGES
                     or e.tipus is Tipus.BEMONDAS or e.tipus is Tipus.ZENE_INDUL]
        kulcs = tuple((e.ido, e.tipus) for e in esemenyek)
        if getattr(self, "_lista_kulcs", None) != kulcs:
            self._lista_kulcs = kulcs
            self.lista.clear()
            if not esemenyek:
                self.lista.addItem("Ma nincs csengetés.")
            for e in esemenyek:
                szoveg = f"{e.ido:%H:%M}    {e.leiras if e.tipus is not Tipus.ZENE_INDUL else 'Szünetzene'}"
                elem = QListWidgetItem(ikon(_esemeny_ikon(e.tipus), SZIN["halvany"]), szoveg)
                elem.setData(Qt.ItemDataRole.UserRole, e.ido)
                self.lista.addItem(elem)
        kovetkezo_sor = None
        for i in range(self.lista.count()):
            elem = self.lista.item(i)
            ido = elem.data(Qt.ItemDataRole.UserRole)
            if ido is None:
                continue
            mult = ido <= most
            elem.setForeground(QColor(SZIN["tiltott"]) if mult else QColor(SZIN["szoveg"]))
            if not mult and kovetkezo_sor is None:
                kovetkezo_sor = i
        if kovetkezo_sor is not None and getattr(self, "_kovetkezo_sor", None) != kovetkezo_sor:
            self._kovetkezo_sor = kovetkezo_sor
            self.lista.setCurrentRow(kovetkezo_sor)
            self.lista.scrollToItem(self.lista.item(kovetkezo_sor), QListWidget.ScrollHint.PositionAtCenter)

    def _ma_rendek(self) -> None:
        b = self.v.b
        kivetel = b.kivetelek.get(_ma())
        nevek = [r.nev for r in b.rendek]
        kulcs = (tuple(nevek), kivetel)
        if getattr(self, "_rend_kulcs", None) == kulcs:
            return
        self._rend_kulcs = kulcs
        self.ma_rend.blockSignals(True)
        self.ma_rend.clear()
        self.ma_rend.addItem("Szokásos (heti beosztás)", "")
        for nev in nevek:
            self.ma_rend.addItem(nev, nev)
        self.ma_rend.setCurrentIndex(max(0, self.ma_rend.findData(kivetel or "")))
        self.ma_rend.blockSignals(False)

    def _ma_rend_valasztva(self, _sor: int) -> None:
        self.v.ma_rend(self.ma_rend.currentData() or "")
        self._lista_kulcs = None
        self.frissit()

    def _zene_gombok(self, *_) -> None:
        szol = self.v.zene.szol
        self.lejatszas_gomb.setIcon(ikon("szunet" if szol else "lejatszas", SZIN["kiemelt_szoveg"]))
        if not szol:
            self.szam_cimke.setText("Nem szól zene")
            self.forras_cimke.setText("")

    def _szam(self, cim: str, forras: str) -> None:
        self.szam_cimke.setText(cim)
        self.forras_cimke.setText(f"Forrás: {forras}")

    def _hangero(self, ertek: int) -> None:
        self.v.b.zene_hangero = ertek
        self.hangero_cimke.setText(f"{ertek}%")
        self.v.zene.hangero(ertek)

    def _gyors_bemondas(self) -> None:
        szoveg, ok = QInputDialog.getMultiLineText(self, "Bemondás", "Mit olvasson fel a rendszer? "
                                                   "(Előtte gong szól.)")
        if ok and szoveg.strip():
            self.v.gyors_bemondas(szoveg.strip())

    def _riasztas(self) -> None:
        if self.v.riasztas:
            self.v.riasztas_leallit()
            return
        valasz = QMessageBox.warning(self, "Riasztás", "Biztosan elindítod a riasztó hangot?\n\n"
                                     "A zene leáll, a riasztás a leállításig szól.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                     QMessageBox.StandardButton.Cancel)
        if valasz == QMessageBox.StandardButton.Yes:
            self.v.riasztas_indit()

    def _riasztas_valtozott(self, be: bool) -> None:
        self.riasztas_gomb.setText("Riasztás leállítása" if be else "Riasztás")
        self.riasztas_gomb.setProperty("allapot", "aktiv" if be else "")
        self.riasztas_gomb.style().unpolish(self.riasztas_gomb)
        self.riasztas_gomb.style().polish(self.riasztas_gomb)


def _ma() -> str:
    return datetime.now().date().isoformat()


def _forras_ikon(tipus: str) -> str:
    return {"mappa": "mappa", "fajlok": "fajl", "youtube": "youtube", "spotify": "spotify"}.get(tipus, "zene")


def _esemeny_ikon(tipus: Tipus) -> str:
    return {Tipus.BEMONDAS: "bemondas", Tipus.ZENE_INDUL: "zene", Tipus.RIADO: "riasztas",
            Tipus.CSEND: "hold"}.get(tipus, "csengo")
