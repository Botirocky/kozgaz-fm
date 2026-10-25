__lazy_modules__ = [
    "datetime",
    "pathlib",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "kozgaz_fm.ui.elemek",
    "kozgaz_fm.ui.tema",
    "kozgaz_fm.vezerlo",
]

from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QComboBox, QFileDialog, QGridLayout, QListWidget, QToolTip, QVBoxLayout, QWidget

from kozgaz_fm.ui.elemek import Kartya, Oldal, cimke, gomb, sor
from kozgaz_fm.ui.tema import SZIN
from kozgaz_fm.vezerlo import Vezerlo

IDOSZAKOK = [("Ma", 0), ("Az elmúlt 7 nap", 6), ("Az elmúlt 30 nap", 29), ("Ebben a tanévben", -1)]
HONAPOK = ["jan.", "febr.", "márc.", "ápr.", "máj.", "jún.", "júl.", "aug.", "szept.", "okt.", "nov.", "dec."]


def tanev_kezdete(ma: date) -> date:
    return date(ma.year if ma.month >= 9 else ma.year - 1, 9, 1)


def idotartam_szoveg(perc: int) -> str:
    if perc < 60:
        return f"{perc} perc"
    return f"{perc // 60} óra {perc % 60} perc" if perc % 60 else f"{perc // 60} óra"


def nap_felirat(nap: str) -> str:
    d = date.fromisoformat(nap)
    return f"{HONAPOK[d.month - 1]} {d.day}."


class Oszlopdiagram(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.napok: list[dict] = []
        self.setMinimumHeight(170)
        self.setMouseTracking(True)
        self.setAccessibleName("Napi zeneidő oszlopdiagramja")

    def adat(self, napok: list[dict]) -> None:
        self.napok = napok
        osszes = sum(n["zene_perc"] for n in napok)
        self.setAccessibleDescription(f"{len(napok)} nap, összesen {idotartam_szoveg(osszes)} zene")
        self.update()

    def _sav(self, i: int) -> QRectF:
        terulet = self.rect().adjusted(4, 8, -4, -22)
        szel = terulet.width() / max(1, len(self.napok))
        return QRectF(terulet.left() + i * szel, terulet.top(), szel, terulet.height())

    def paintEvent(self, _esemeny) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.napok:
            return
        maximum = max(1, max(n["zene_perc"] for n in self.napok))
        also = self.rect().bottom() - 22
        p.setPen(QColor(SZIN["keret"]))
        p.drawLine(QPointF(4, also + 0.5), QPointF(self.width() - 4, also + 0.5))
        lepes = max(1, len(self.napok) // 8)
        for i, n in enumerate(self.napok):
            r = self._sav(i)
            szel = min(28.0, max(2.0, r.width() - 2))
            mag = (r.height()) * n["zene_perc"] / maximum
            if mag >= 1:
                x = r.center().x() - szel / 2
                ut = QPainterPath()
                sugar = min(4.0, szel / 2, mag)
                ut.addRoundedRect(QRectF(x, also - mag, szel, mag + sugar), sugar, sugar)
                p.save()
                p.setClipRect(QRectF(x, also - mag - 1, szel, mag + 1))
                p.fillPath(ut, QColor(SZIN["kek"]))
                p.restore()
            if i % lepes == 0 or len(self.napok) <= 8:
                p.setPen(QColor(SZIN["halvany"]))
                p.drawText(QRectF(r.left() - 20, also + 4, r.width() + 40, 16), Qt.AlignmentFlag.AlignCenter,
                           nap_felirat(n["nap"]))

    def mouseMoveEvent(self, esemeny) -> None:
        for i, n in enumerate(self.napok):
            if self._sav(i).adjusted(0, -8, 0, 22).contains(esemeny.position()):
                QToolTip.showText(esemeny.globalPosition().toPoint(),
                                  f"{nap_felirat(n['nap'])}: {idotartam_szoveg(n['zene_perc'])} zene, "
                                  f"{n['csengetes']} csengetés", self)
                return
        QToolTip.hideText()


def _szamkartya(cim: str) -> tuple[QWidget, object, object]:
    doboz = QWidget()
    elr = QVBoxLayout(doboz)
    elr.setContentsMargins(0, 0, 0, 0)
    elr.setSpacing(2)
    fo = cimke("–", "szam")
    al = cimke("", "halvany", sortores=True)
    al.setMinimumHeight(al.fontMetrics().lineSpacing() * 2 + 4)
    al.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
    elr.addWidget(cimke(cim, "halvany"))
    elr.addWidget(fo)
    elr.addWidget(al)
    return doboz, fo, al


class StatisztikaOldal(Oldal):
    def __init__(self, v: Vezerlo) -> None:
        super().__init__("Statisztika", "Mi szólt, mikor és hányszor, és mennyire pontosak a csengetések.")
        self.v = v
        self.idoszak = QComboBox()
        for nev, _ in IDOSZAKOK:
            self.idoszak.addItem(nev)
        self.idoszak.setCurrentIndex(1)
        self.idoszak.currentIndexChanged.connect(lambda _: self.frissit())
        export = gomb("Lejátszási lista mentése (CSV)…", "le")
        export.clicked.connect(self._export)
        self.add(sor(cimke("Időszak:"), self.idoszak, None, export))

        osszegzo = Kartya()
        racs = QGridLayout()
        racs.setHorizontalSpacing(28)
        self.szamok = {}
        for i, (kulcs, cim) in enumerate((("zene", "Zene"), ("kert", "Kért számok"), ("csengetes", "Csengetések"),
                                          ("pontossag", "Csengetések pontossága"))):
            doboz, fo, al = _szamkartya(cim)
            self.szamok[kulcs] = (fo, al)
            racs.addWidget(doboz, 0, i)
        osszegzo.add(racs)
        self.add(osszegzo)

        napi = Kartya("Napi zeneidő")
        self.diagram = Oszlopdiagram()
        napi.add(self.diagram)
        self.add(napi)

        top = Kartya("Legtöbbet játszott számok")
        self.lista = QListWidget()
        self.lista.setMinimumHeight(220)
        top.add(self.lista)
        self.add(top, 1)

    def _tartomany(self) -> tuple[date, date]:
        ma = date.today()
        hossz = IDOSZAKOK[self.idoszak.currentIndex()][1]
        return (tanev_kezdete(ma) if hossz < 0 else ma - timedelta(days=hossz)), ma

    def frissit(self) -> None:
        if self.v.stat is None:
            self.szamok["zene"][0].setText("–")
            self.szamok["zene"][1].setText("A statisztika-adatbázis nem nyitható meg.")
            return
        tol, ig = self._tartomany()
        o = self.v.stat.osszegzes(tol, ig)
        z, c, k = o["zene"], o["csengetes"], o["keresek"]
        self._kiir("zene", idotartam_szoveg(z["perc"]), f"{z['szamok']} szám szólt")
        self._kiir("kert", str(z["kert"]),
                   f"{k['erkezett']} kérés érkezett, {k['elfogadva']} elfogadva, {k['elutasitva']} elutasítva")
        self._kiir("csengetes", str(c["darab"]), f"ebből {c['kezi']} kézi" if c["kezi"] else "mind időzített")
        if c["atlag_keses_ms"] is None:
            self._kiir("pontossag", "–", "Még nincs időzített csengetés ebben az időszakban.")
        else:
            self._kiir("pontossag", f"{c['atlag_keses_ms'] / 1000:.1f} mp".replace(".", ","),
                       "átlagos eltérés; " + (f"{c['kesett']} késett 2 mp-nél többet" if c["kesett"]
                                              else "egyik sem késett 2 mp-nél többet"))
        self.diagram.adat(o["napok"])
        self.lista.clear()
        for i, t in enumerate(o["legtobbet"], 1):
            self.lista.addItem(f"{i}.  {t['cim']}  –  {t['darab']}×" + ("  (kért)" if t["kert"] else ""))
        if not o["legtobbet"]:
            self.lista.addItem("Ebben az időszakban még nem szólt zene.")

    def _kiir(self, kulcs: str, fo: str, al: str) -> None:
        self.szamok[kulcs][0].setText(fo)
        self.szamok[kulcs][1].setText(al)

    def _export(self) -> None:
        if self.v.stat is None:
            return
        tol, ig = self._tartomany()
        ut, _ = QFileDialog.getSaveFileName(self, "Lejátszási lista mentése", f"kozgaz-fm-zene-{tol}_{ig}.csv",
                                            "CSV (*.csv)")
        if not ut:
            return
        try:
            darab = self.v.stat.csv_export(tol, ig, Path(ut))
        except OSError as e:
            self.v.uzenet.emit(f"A fájl nem menthető: {e}", "hiba")
            return
        self.v.uzenet.emit(f"{darab} lejátszás mentve: {Path(ut).name}", "info")
