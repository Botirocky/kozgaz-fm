__lazy_modules__ = ["datetime", "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets", "kozgaz_fm.ui.tema"]

from datetime import datetime, timedelta

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from kozgaz_fm.ui.tema import SZIN, szam_betu

PEREM = timedelta(minutes=10)


class Idovonal(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.orak: list[tuple[datetime, datetime]] = []
        self.most = datetime.now()
        self.zene_szol = False
        self.ures_szoveg = "Ma nincs tanítás"
        self.setMinimumHeight(78)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    def beallit(self, orak: list[tuple[datetime, datetime]], most: datetime, zene_szol: bool,
                ures_szoveg: str = "Ma nincs tanítás") -> None:
        valtozott = (orak != self.orak or zene_szol != self.zene_szol or ures_szoveg != self.ures_szoveg
                     or int(most.timestamp()) // 5 != int(self.most.timestamp()) // 5)
        self.orak, self.most, self.zene_szol, self.ures_szoveg = orak, most, zene_szol, ures_szoveg
        if valtozott:
            self.update()

    def sizeHint(self):
        meret = super().sizeHint()
        meret.setHeight(78)
        return meret

    def paintEvent(self, _esemeny) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        szel, mag = self.width(), self.height()
        if not self.orak:
            p.setPen(QColor(SZIN["halvany"]))
            p.setFont(szam_betu(10.5))
            p.drawText(QRectF(0, 0, szel, mag), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       self.ures_szoveg)
            return
        eleje = self.orak[0][0] - PEREM
        vege = self.orak[-1][1] + PEREM
        teljes = (vege - eleje).total_seconds()

        def x(ido: datetime) -> float:
            return max(0.0, min(1.0, (ido - eleje).total_seconds() / teljes)) * szel

        sav_y, sav_m = 18.0, 28.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(SZIN["felulet2"]))
        p.drawRoundedRect(QRectF(0, sav_y + sav_m / 2 - 1, szel, 2), 1, 1)
        if self.zene_szol:
            for (_k, v1), (k2, _v) in zip(self.orak, self.orak[1:], strict=False):
                if v1 <= self.most < k2:
                    p.setBrush(QColor(SZIN["kiemelt"]))
                    p.drawRoundedRect(QRectF(x(v1) + 2, sav_y + sav_m / 2 - 2, x(k2) - x(v1) - 4, 4), 2, 2)
        szam_font = szam_betu(9)
        ido_font = szam_betu(8.5, szam_font.weight())
        utolso_cimke = -1e9
        for i, (kezdet, veg) in enumerate(self.orak, start=1):
            bal, jobb = x(kezdet), x(veg)
            teglalap = QRectF(bal, sav_y, max(2.0, jobb - bal), sav_m)
            ut = QPainterPath()
            ut.addRoundedRect(teglalap, 3, 3)
            if veg <= self.most:
                p.fillPath(ut, QColor("#232A33"))
                szoveg_szin = QColor("#5F6773")
            elif kezdet <= self.most < veg:
                p.fillPath(ut, QColor(SZIN["kek_halvany"]))
                arany = (self.most - kezdet) / (veg - kezdet)
                p.save()
                p.setClipPath(ut)
                p.fillRect(QRectF(bal, sav_y, (jobb - bal) * arany, sav_m), QColor(SZIN["kek_sotet"]))
                p.restore()
                p.setPen(QPen(QColor(SZIN["kek"]), 1.2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(ut)
                p.setPen(Qt.PenStyle.NoPen)
                szoveg_szin = QColor("#FFFFFF")
            else:
                p.fillPath(ut, QColor(SZIN["felulet2"]))
                p.setPen(QPen(QColor(SZIN["keret_eros"]), 1))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(ut)
                p.setPen(Qt.PenStyle.NoPen)
                szoveg_szin = QColor(SZIN["szoveg"])
            if jobb - bal > 22:
                p.setFont(szam_font)
                p.setPen(szoveg_szin)
                p.drawText(teglalap, Qt.AlignmentFlag.AlignCenter, f"{i}.")
                p.setPen(Qt.PenStyle.NoPen)
            if bal - utolso_cimke > 44:
                p.setFont(ido_font)
                p.setPen(QColor(SZIN["halvany"]))
                p.drawText(QRectF(bal - 2, sav_y + sav_m + 6, 60, 16), Qt.AlignmentFlag.AlignLeft, f"{kezdet:%H:%M}")
                p.setPen(Qt.PenStyle.NoPen)
                utolso_cimke = bal
        utolso = self.orak[-1][1]
        if x(utolso) - utolso_cimke > 44:
            p.setFont(ido_font)
            p.setPen(QColor(SZIN["halvany"]))
            p.drawText(QRectF(x(utolso) - 60, sav_y + sav_m + 6, 60, 16), Qt.AlignmentFlag.AlignRight,
                       f"{utolso:%H:%M}")
        if eleje <= self.most <= vege:
            mx = x(self.most)
            p.setPen(QPen(QColor(SZIN["kiemelt"]), 2))
            p.drawLine(int(mx), int(sav_y - 6), int(mx), int(sav_y + sav_m + 2))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(SZIN["kiemelt"]))
            haromszog = QPainterPath()
            haromszog.moveTo(mx - 5, sav_y - 12)
            haromszog.lineTo(mx + 5, sav_y - 12)
            haromszog.lineTo(mx, sav_y - 5)
            haromszog.closeSubpath()
            p.drawPath(haromszog)
