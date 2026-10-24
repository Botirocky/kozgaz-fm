__lazy_modules__ = [
    "PySide6.QtCore",
    "PySide6.QtWidgets",
    "kozgaz_fm.ui.elemek",
    "kozgaz_fm.ui.qr",
    "kozgaz_fm.ui.tema",
    "kozgaz_fm.vezerlo",
    "kozgaz_fm.zenekeres",
]

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QSpinBox,
)

from kozgaz_fm.ui.elemek import Kartya, cimke, gomb, kapcsolo, sor
from kozgaz_fm.ui.qr import qr_pixmap, qr_png
from kozgaz_fm.ui.tema import SZIN, ikon
from kozgaz_fm.vezerlo import Vezerlo
from kozgaz_fm.zenekeres import KeresHiba

QR_MERET = 180


class ZenekeresKartya(Kartya):
    def __init__(self, v: Vezerlo) -> None:
        super().__init__("Zenekérés diákoktól")
        self.v = v
        b = v.b
        self.add(cimke("A diákok telefonról kérhetnek számot a QR-kóddal (a folyosói kijelzőn is megjelenik). "
                       "A kérés csak jóváhagyás után szól: itt vagy a webpanelen fogadhatod el. A webes vezérlésnek "
                       "bekapcsolva kell lennie, és a telefonoknak el kell érniük ezt a gépet a hálózaton.",
                       "halvany", sortores=True))
        self.be = kapcsolo("Zenekérés bekapcsolása", b.zenekeres)
        self.be.toggled.connect(self._bekapcsol)
        self.napi = QSpinBox(minimum=1, maximum=20, suffix=" szám")
        self.napi.setValue(b.zenekeres_napi)
        self.napi.valueChanged.connect(lambda e: self._allit("zenekeres_napi", e))
        self.max_perc = QSpinBox(minimum=2, maximum=15, suffix=" perc")
        self.max_perc.setValue(b.zenekeres_max_perc)
        self.max_perc.valueChanged.connect(lambda e: self._allit("zenekeres_max_perc", e))
        self.tiltott = QPlainTextEdit("\n".join(b.zenekeres_tiltott))
        self.tiltott.setPlaceholderText("Soronként egy tiltott szó vagy előadó")
        self.tiltott.setMaximumHeight(90)
        self._tiltott_mento = QTimer(self)
        self._tiltott_mento.setSingleShot(True)
        self._tiltott_mento.setInterval(800)
        self._tiltott_mento.timeout.connect(self._tiltott_mentes)
        self.tiltott.textChanged.connect(self._tiltott_mento.start)
        racs = QGridLayout()
        racs.setVerticalSpacing(10)
        racs.addWidget(cimke("Naponta ennyit kérhet egy telefon:"), 0, 0)
        racs.addWidget(self.napi, 0, 1)
        racs.addWidget(cimke("A kért szám legfeljebb:"), 1, 0)
        racs.addWidget(self.max_perc, 1, 1)
        racs.addWidget(cimke("Tiltólista (cím, előadó, szó):"), 2, 0, 1, 2)
        racs.addWidget(self.tiltott, 3, 0, 1, 2)
        racs.setColumnStretch(0, 1)
        self.qr = cimke()
        self.qr.setFixedSize(QR_MERET, QR_MERET)
        self.qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cim = cimke("", "halvany")
        self.cim.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.qr_mentes = gomb("QR-kód mentése", "le", tipp="Nagy felbontású PNG plakáthoz")
        self.qr_mentes.clicked.connect(self._qr_mentes)
        bal = QGridLayout()
        bal.addWidget(self.be, 0, 0)
        bal.addLayout(racs, 1, 0)
        bal.addWidget(self.qr, 0, 1, 2, 1, Qt.AlignmentFlag.AlignTop)
        bal.setColumnStretch(0, 1)
        bal.setHorizontalSpacing(24)
        self.add(bal)
        self.add(sor(self.cim, None, self.qr_mentes))
        self.lista = QListWidget()
        self.lista.setMinimumHeight(150)
        self.lista.itemDoubleClicked.connect(lambda _: self._dont(True))
        elfogad = gomb("Elfogadás", "pipa", "fo", "A szám a szünetzene következő helyére kerül")
        elfogad.clicked.connect(lambda: self._dont(True))
        elutasit = gomb("Elutasítás", "kuka")
        elutasit.clicked.connect(lambda: self._dont(False))
        self.add(cimke("Jóváhagyásra váró kérések", "alcim"))
        self.add(self.lista)
        self.add(sor(elfogad, elutasit, None))
        v.keresek_valtoztak.connect(self.frissit)
        v.frissult.connect(self._cim_frissit)
        self._utolso_cim: str | None = None
        self.frissit()

    def _allit(self, mezo: str, ertek) -> None:
        setattr(self.v.b, mezo, ertek)
        self.v.mentes_kesobb()

    def _bekapcsol(self, be: bool) -> None:
        self.v.b.zenekeres = be
        self.v.log(f"Zenekérés {'bekapcsolva' if be else 'kikapcsolva'}")
        self.v.mentes()
        if be and not self.v.web.fut:
            QMessageBox.information(self, "Zenekérés", "A zenekéréshez kapcsold be a webes vezérlést is "
                                    "(Beállítások → Webes vezérlés), különben a telefonok nem érik el a gépet.")
        self.frissit()

    def _tiltott_mentes(self) -> None:
        self.v.b.zenekeres_tiltott = [s.strip() for s in self.tiltott.toPlainText().splitlines() if s.strip()]
        self.v.mentes_kesobb()

    def _cim_frissit(self) -> None:
        cim = self.v.web.keres_cim() if self.v.b.zenekeres else ""
        if cim == self._utolso_cim:
            return
        self._utolso_cim = cim
        self.qr_mentes.setEnabled(bool(cim))
        if cim:
            self.qr.setPixmap(qr_pixmap(cim, QR_MERET))
            self.cim.setText(f"Kérés oldala: <b>{cim}</b>")
        else:
            self.qr.clear()
            self.qr.setText("")
            self.cim.setText("A QR-kód a zenekérés és a webes vezérlés bekapcsolása után jelenik meg."
                             if not self.v.b.zenekeres or not self.v.web.fut else "")

    def frissit(self) -> None:
        self._cim_frissit()
        kijelolt = self._kijelolt()
        self.lista.clear()
        for k in self.v.keresek.fuggo():
            hossz = f"{k.hossz // 60}:{k.hossz % 60:02d}" if k.hossz else ""
            reszletek = " · ".join(x for x in (k.ido.strftime("%H:%M"), k.nev, hossz, f"kérés: „{k.szoveg}”") if x)
            szoveg = "Keresés a YouTube-on…" if k.allapot == "kereses" else k.cim
            elem = QListWidgetItem(ikon("youtube", SZIN["szoveg"]), f"{szoveg}\n{reszletek}")
            elem.setData(Qt.ItemDataRole.UserRole, k.azon)
            if k.allapot == "kereses":
                elem.setForeground(Qt.GlobalColor.gray)
            self.lista.addItem(elem)
            if k.azon == kijelolt:
                self.lista.setCurrentItem(elem)
        if not self.lista.count():
            self.lista.addItem("Nincs jóváhagyásra váró kérés.")

    def _kijelolt(self) -> str | None:
        elem = self.lista.currentItem()
        return elem.data(Qt.ItemDataRole.UserRole) if elem else None

    def _dont(self, elfogad: bool) -> None:
        azon = self._kijelolt()
        if not azon:
            return
        try:
            self.v.zenekeres_dontes(azon, elfogad, "a programból")
        except KeresHiba as e:
            QMessageBox.warning(self, "Zenekérés", str(e))

    def _qr_mentes(self) -> None:
        cim = self.v.web.keres_cim()
        if not cim:
            return
        ut, _ = QFileDialog.getSaveFileName(self, "QR-kód mentése", "zenekeres-qr.png", "PNG-kép (*.png)")
        if ut:
            with open(ut, "wb") as f:
                f.write(qr_png(cim, 24))
