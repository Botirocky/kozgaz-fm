__lazy_modules__ = ["pathlib", "PySide6.QtCore", "PySide6.QtGui", "kozgaz_fm.ui.qr", "kozgaz_fm.utvonalak"]

from pathlib import Path

from PySide6.QtCore import QMarginsF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPageLayout, QPageSize, QPainter, QPdfWriter, QPen

from kozgaz_fm.ui.qr import qr_png
from kozgaz_fm.utvonalak import csomag_mappa

KEK = QColor("#4085C0")
SARGA = QColor("#DCBD31")
TINTA = QColor("#1B2430")
DPI = 300


def _mm(ertek: float) -> float:
    return ertek * DPI / 25.4


def _betu(meret: float, vastag: bool = False) -> QFont:
    f = QFont("Segoe UI")
    f.setStyleHint(QFont.StyleHint.SansSerif)
    f.setPointSizeF(meret)
    f.setWeight(QFont.Weight.Bold if vastag else QFont.Weight.Normal)
    return f


def lepesek() -> list[str]:
    return [
        "Olvasd be a QR-kódot a telefonod kamerájával.",
        "Írd be az előadót és a szám címét, vagy másold be a YouTube-linkjét.",
        "Ha a szám rendben van, a következő szünetek egyikében szól.",
    ]


def zenekeres_plakat(ut: str | Path, cim: str, nev: str = "Közgáz FM") -> None:
    iro = QPdfWriter(str(ut))
    iro.setResolution(DPI)
    iro.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait,
                                  QMarginsF(0, 0, 0, 0)))
    iro.setTitle(f"{nev} – zenekérés")
    iro.setCreator("Közgáz FM")
    p = QPainter(iro)
    try:
        _rajzol(p, iro.width(), iro.height(), cim, nev)
    finally:
        p.end()


def _rajzol(p: QPainter, szel: float, mag: float, cim: str, nev: str) -> None:
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.fillRect(QRectF(0, 0, szel, mag), Qt.GlobalColor.white)
    margo = _mm(18)
    fejlec = _mm(46)
    p.fillRect(QRectF(0, 0, szel, fejlec), KEK)
    p.fillRect(QRectF(0, fejlec, szel, _mm(3.2)), SARGA)
    logo = QImage(str(csomag_mappa() / "kepek" / "logo.png"))
    logo_meret = _mm(28)
    if not logo.isNull():
        p.setBrush(Qt.GlobalColor.white)
        p.setPen(Qt.PenStyle.NoPen)
        keret = QRectF(margo, (fejlec - logo_meret) / 2, logo_meret, logo_meret)
        p.drawRoundedRect(keret, _mm(4), _mm(4))
        p.drawImage(keret.adjusted(_mm(1.5), _mm(1.5), -_mm(1.5), -_mm(1.5)), logo)
    szoveg_x = margo + logo_meret + _mm(8)
    p.setPen(Qt.GlobalColor.white)
    p.setFont(_betu(13, True))
    p.drawText(QRectF(szoveg_x, _mm(10), szel - szoveg_x - margo, _mm(9)),
               Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, nev.upper())
    p.setFont(_betu(30, True))
    p.drawText(QRectF(szoveg_x, _mm(19), szel - szoveg_x - margo, _mm(18)),
               Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "Kérj zenét a szünetre!")

    y = fejlec + _mm(16)
    p.setPen(TINTA)
    p.setFont(_betu(15))
    bevezeto = QRectF(margo, y, szel - 2 * margo, _mm(16))
    p.drawText(bevezeto, Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap,
               "Olvasd be a kódot, és a kedvenc számod szólhat a szünetben.")
    y += _mm(22)

    qr_meret = _mm(98)
    qr = QImage.fromData(qr_png(cim, 20))
    qr_x = (szel - qr_meret) / 2
    p.setPen(QPen(SARGA, _mm(1.6)))
    p.setBrush(Qt.GlobalColor.white)
    p.drawRoundedRect(QRectF(qr_x - _mm(5), y - _mm(5), qr_meret + _mm(10), qr_meret + _mm(10)), _mm(5), _mm(5))
    p.drawImage(QRectF(qr_x, y, qr_meret, qr_meret), qr)
    y += qr_meret + _mm(10)
    p.setPen(KEK)
    p.setFont(_betu(12, True))
    p.drawText(QRectF(margo, y, szel - 2 * margo, _mm(8)), Qt.AlignmentFlag.AlignHCenter, cim.rstrip("/"))
    y += _mm(17)

    p.setFont(_betu(13))
    sor_szel = szel - 2 * margo - _mm(14)
    for i, szoveg in enumerate(lepesek(), start=1):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(KEK)
        p.drawEllipse(QRectF(margo, y, _mm(9), _mm(9)))
        p.setPen(Qt.GlobalColor.white)
        p.setFont(_betu(12, True))
        p.drawText(QRectF(margo, y, _mm(9), _mm(9)), Qt.AlignmentFlag.AlignCenter, str(i))
        p.setPen(TINTA)
        p.setFont(_betu(13))
        doboz = p.boundingRect(QRectF(margo + _mm(14), y, sor_szel, _mm(40)),
                               Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, szoveg)
        p.drawText(QRectF(margo + _mm(14), y + max(0.0, (_mm(9) - doboz.height()) / 2), sor_szel, doboz.height()),
                   Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, szoveg)
        y += max(_mm(9), doboz.height()) + _mm(6)

    p.fillRect(QRectF(0, mag - _mm(12), szel, _mm(12)), KEK)
    p.setPen(Qt.GlobalColor.white)
    p.setFont(_betu(10))
    p.drawText(QRectF(margo, mag - _mm(12), szel - 2 * margo, _mm(12)),
               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"{nev} · iskolarádió")
    p.drawText(QRectF(margo, mag - _mm(12), szel - 2 * margo, _mm(12)),
               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, "Jó zenélést!")
