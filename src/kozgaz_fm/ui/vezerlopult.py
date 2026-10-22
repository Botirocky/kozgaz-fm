from datetime import datetime, timedelta

from PySide6.QtCore import Qt
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

from kozgaz_fm.hang import FORRAS_TIPUSOK
from kozgaz_fm.orarend import CSENGOK, Szakasz, Tipus, allapot
from kozgaz_fm.ui.elemek import Kartya, Oldal, cimke, gomb, ikon_gomb, kapcsolo, sor
from kozgaz_fm.ui.tema import SZIN, ikon
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
        racs = QGridLayout()
        racs.setSpacing(16)
        racs.addWidget(self._allapot_kartya(), 0, 0)
        racs.addWidget(self._zene_kartya(), 0, 1)
        racs.addWidget(self._gyors_kartya(), 1, 0)
        racs.addWidget(self._mai_kartya(), 1, 1)
        racs.setColumnStretch(0, 1)
        racs.setColumnStretch(1, 1)
        self.add(racs)
        self.elrendezes.addStretch(1)
        v.frissult.connect(self.frissit)
        v.zene.szam_valtozott.connect(self._szam)
        v.zene.allapot_valtozott.connect(lambda _: self._zene_gombok())
        v.zene.lista_valtozott.connect(self._zene_gombok)
        v.riasztas_valtozott.connect(self._riasztas_valtozott)
        self.frissit()

    def _allapot_kartya(self) -> Kartya:
        k = Kartya("Most")
        self.ora_cimke = cimke("", "cim")
        self.ora_cimke.setStyleSheet("font-size: 40pt; font-weight: 800; letter-spacing: 1px;")
        self.datum_cimke = cimke("", "halvany")
        self.szakasz_cimke = cimke("", "alcim")
        self.szakasz_cimke.setStyleSheet(f"font-size: 17pt; font-weight: 750; color: {SZIN['kiemelt']};")
        self.hatra_cimke = cimke("", "halvany")
        self.halad = QProgressBar()
        self.halad.setTextVisible(False)
        self.halad.setRange(0, 1000)
        self.kovetkezo_cimke = cimke("", "halvany", sortores=True)
        for e in (self.ora_cimke, self.datum_cimke, self.szakasz_cimke, self.hatra_cimke, self.halad,
                  self.kovetkezo_cimke):
            k.add(e)
        return k

    def _zene_kartya(self) -> Kartya:
        k = Kartya("Szünetzene")
        self.forras_valaszto = QComboBox()
        self.forras_valaszto.setMinimumHeight(38)
        self.forras_valaszto.activated.connect(self._forras_valasztva)
        self.szam_cimke = cimke("Nem szól zene", "alcim", sortores=True)
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
        csengetes = gomb("Csengetés most", "csengo", "fo", "Azonnali csengetés a becsengő hangjával")
        csengetes.setProperty("szerep", "fo")
        csengetes.setMinimumHeight(52)
        csengetes.clicked.connect(lambda: self.v.csengetes(self.v.b.hang_becsengo))
        menu = QMenu(self)
        menu.addAction("Jelzőcsengő", lambda: self.v.csengetes(self.v.b.hang_jelzo, "Kézi jelzőcsengő"))
        menu.addAction("Kicsengő", lambda: self.v.csengetes(self.v.b.hang_kicsengo, "Kézi kicsengő"))
        menu.addAction("Gong", lambda: self.v.csengetes(self.v.b.hang_gong, "Kézi gong"))
        tobb = gomb("Más hang…", "csengo")
        tobb.setMinimumHeight(52)
        tobb.setMenu(menu)
        bemondas = gomb("Bemondás", "bemondas", tipp="Szöveg felolvasása a hangosbemondón (gonggal)")
        bemondas.setMinimumHeight(52)
        bemondas.clicked.connect(self._gyors_bemondas)
        self.riasztas_gomb = gomb("RIASZTÁS", "riasztas", "veszely", "Riasztó hang folyamatosan, a zene leáll",
                                  szin="#FFFFFF")
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
        k.add(sor(cimke("Mai csengetési rend:", "halvany"), self.ma_rend, nyujt=False))
        return k

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
        self.ora_cimke.setText(f"{most:%H:%M:%S}")
        self.datum_cimke.setText(f"{most.year}. {HONAPOK[most.month - 1]} {most.day}., {NAPOK[most.weekday()]}")
        self.szakasz_cimke.setText(a.cim)
        hatra = a.hatralevo(most)
        if a.szakasz is Szakasz.ORA:
            self.hatra_cimke.setText(f"Kicsengetésig: {idotartam(hatra)}")
        elif a.szakasz in (Szakasz.SZUNET, Szakasz.REGGEL):
            self.hatra_cimke.setText(f"Becsengetésig: {idotartam(hatra)}")
        else:
            self.hatra_cimke.setText("")
        self.halad.setVisible(a.szakasz in (Szakasz.ORA, Szakasz.SZUNET))
        self.halad.setValue(int(a.haladas(most) * 1000))
        if a.kovetkezo:
            nap = "ma" if a.kovetkezo.ido.date() == most.date() else f"{a.kovetkezo.ido:%m.%d.}"
            self.kovetkezo_cimke.setText(f"Következő csengetés: {nap} {a.kovetkezo.ido:%H:%M} – "
                                         f"{a.kovetkezo.leiras}")
        else:
            self.kovetkezo_cimke.setText("A következő két hétben nincs csengetés.")
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
        self._zene_gombok()

    def _forrasok(self) -> None:
        b = self.v.b
        aktiv = self.v.aktiv_forras()
        self.forras_valaszto.blockSignals(True)
        self.forras_valaszto.clear()
        for i, f in enumerate(b.forrasok):
            if f.aktiv:
                self.forras_valaszto.addItem(ikon(_forras_ikon(f.tipus), SZIN["szoveg"]),
                                             f"{f.nev}  ·  {FORRAS_TIPUSOK.get(f.tipus, f.tipus)}", i)
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
        esemenyek = [e for e in self.v.mai_esemenyek() if e.tipus in CSENGOK or e.tipus is Tipus.BEMONDAS
                     or e.tipus is Tipus.ZENE_INDUL]
        kulcs = tuple((e.ido, e.tipus) for e in esemenyek)
        if getattr(self, "_lista_kulcs", None) != kulcs:
            self._lista_kulcs = kulcs
            self.lista.clear()
            if not esemenyek:
                self.lista.addItem("Ma nincs csengetés.")
            for e in esemenyek:
                szoveg = f"{e.ido:%H:%M}    {e.leiras if e.tipus is not Tipus.ZENE_INDUL else '♪ Szünetzene'}"
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
            elem.setForeground(Qt.GlobalColor.gray if mult else Qt.GlobalColor.white)
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

    def _zene_gombok(self) -> None:
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
        self.riasztas_gomb.setText("RIASZTÁS LEÁLLÍTÁSA" if be else "RIASZTÁS")


def _ma() -> str:
    return datetime.now().date().isoformat()


def _forras_ikon(tipus: str) -> str:
    return {"mappa": "mappa", "fajlok": "fajl", "youtube": "youtube", "spotify": "spotify"}.get(tipus, "zene")


def _esemeny_ikon(tipus: Tipus) -> str:
    return {Tipus.BEMONDAS: "bemondas", Tipus.ZENE_INDUL: "zene"}.get(tipus, "csengo")
