__lazy_modules__ = ["pathlib", "PySide6.QtCore", "PySide6.QtGui", "segno", "kozgaz_fm.utvonalak"]

from pathlib import Path

from PySide6.QtCore import QMarginsF, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QLinearGradient,
    QPageLayout,
    QPageSize,
    QPainter,
    QPainterPath,
    QPdfWriter,
    QPen,
)

from kozgaz_fm.utvonalak import csomag_mappa

KEK = QColor("#4085C0")
MELYKEK = QColor("#173F68")
SARGA = QColor("#DCBD31")
TINTA = QColor("#14273D")
HALVANY = QColor("#5B6B7D")
DPI = 300


def _mm(ertek: float) -> float:
    return ertek * DPI / 25.4


def _betu(meret: float, suly: QFont.Weight = QFont.Weight.Normal) -> QFont:
    f = QFont("Segoe UI")
    f.setFamilies(["Segoe UI", "Noto Sans", "DejaVu Sans"])
    f.setStyleHint(QFont.StyleHint.SansSerif)
    f.setPointSizeF(meret)
    f.setWeight(suly)
    return f


def lepesek() -> list[tuple[str, str]]:
    return [
        ("Olvasd be", "a QR-kódot a telefonod kamerájával."),
        ("Írd be", "az előadót és a szám címét, vagy egy YouTube-linket."),
        ("Hallgasd", "a következő szünetek egyikében szól."),
    ]


def rovid_cim(cim: str) -> str:
    return cim.split("://", 1)[-1].rstrip("/")


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


def _qr(p: QPainter, cim: str, keret: QRectF) -> None:
    import segno

    matrix = [list(sor) for sor in segno.make(cim, error="h").matrix]
    n = len(matrix)
    modul = keret.width() / n
    utvonal = QPainterPath()
    for y, sor in enumerate(matrix):
        for x, ertek in enumerate(sor):
            if ertek and not _kereso(x, y, n):
                utvonal.addRect(QRectF(keret.x() + x * modul, keret.y() + y * modul, modul + 0.6, modul + 0.6))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(TINTA)
    p.drawPath(utvonal)
    for kx, ky in ((0, 0), (n - 7, 0), (0, n - 7)):
        kulso = QRectF(keret.x() + kx * modul, keret.y() + ky * modul, 7 * modul, 7 * modul)
        gyuru = QPainterPath()
        gyuru.addRoundedRect(kulso, 1.8 * modul, 1.8 * modul)
        gyuru.addRoundedRect(kulso.adjusted(modul, modul, -modul, -modul), 1.1 * modul, 1.1 * modul)
        p.setBrush(TINTA)
        p.drawPath(gyuru)
        p.setBrush(KEK)
        p.drawRoundedRect(kulso.adjusted(2 * modul, 2 * modul, -2 * modul, -2 * modul), 0.9 * modul, 0.9 * modul)


def _kereso(x: int, y: int, n: int) -> bool:
    return (x < 7 and y < 7) or (x >= n - 7 and y < 7) or (x < 7 and y >= n - 7)


def _hullamok(p: QPainter, kozep: QPointF, sugar: float, db: int) -> None:
    p.setBrush(Qt.BrushStyle.NoBrush)
    for i in range(db):
        szin = QColor(255, 255, 255, 34 - i * 4)
        p.setPen(QPen(szin, _mm(1.1)))
        r = sugar + i * _mm(13)
        p.drawEllipse(kozep, r, r)


def _arnyek(p: QPainter, doboz: QRectF, sugar: float) -> None:
    p.setPen(Qt.PenStyle.NoPen)
    for i in range(14, 0, -1):
        terulet = doboz.adjusted(-i * _mm(0.35), -i * _mm(0.2), i * _mm(0.35), i * _mm(0.55) + _mm(1.2))
        p.setBrush(QColor(10, 30, 55, 5))
        p.drawRoundedRect(terulet, sugar + i * _mm(0.35), sugar + i * _mm(0.35))


def _rajzol(p: QPainter, szel: float, mag: float, cim: str, nev: str) -> None:
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    p.fillRect(QRectF(0, 0, szel, mag), QColor("#F6F8FB"))
    margo = _mm(17)

    fej_mag = _mm(150)
    atmenet = QLinearGradient(0, 0, szel, fej_mag)
    atmenet.setColorAt(0, QColor("#4A8FCB"))
    atmenet.setColorAt(1, MELYKEK)
    fej = QPainterPath()
    fej.moveTo(0, 0)
    fej.lineTo(szel, 0)
    fej.lineTo(szel, fej_mag - _mm(14))
    fej.quadTo(szel / 2, fej_mag + _mm(10), 0, fej_mag - _mm(14))
    fej.closeSubpath()
    p.save()
    p.setClipPath(fej)
    p.fillRect(QRectF(0, 0, szel, fej_mag + _mm(10)), QBrush(atmenet))
    _hullamok(p, QPointF(szel + _mm(8), _mm(-6)), _mm(40), 7)
    p.restore()

    logo = QImage(str(csomag_mappa() / "kepek" / "logo.png"))
    logo_meret = _mm(24)
    keret = QRectF(margo, _mm(15), logo_meret, logo_meret)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(Qt.GlobalColor.white)
    p.drawRoundedRect(keret, _mm(5), _mm(5))
    if not logo.isNull():
        p.drawImage(keret.adjusted(_mm(2), _mm(2), -_mm(2), -_mm(2)), logo)
    szoveg_x = keret.right() + _mm(6)
    p.setPen(Qt.GlobalColor.white)
    p.setFont(_betu(17, QFont.Weight.Bold))
    p.drawText(QRectF(szoveg_x, _mm(16), szel - szoveg_x - margo, _mm(11)),
               Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, nev)
    p.setPen(QColor(255, 255, 255, 200))
    p.setFont(_betu(12))
    p.drawText(QRectF(szoveg_x, _mm(27), szel - szoveg_x - margo, _mm(9)),
               Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "iskolarádió · zenekérés")

    p.setPen(SARGA)
    cimke = _betu(13, QFont.Weight.Bold)
    cimke.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, _mm(0.9))
    p.setFont(cimke)
    p.drawText(QRectF(margo, _mm(52), szel - 2 * margo, _mm(9)), Qt.AlignmentFlag.AlignLeft, "SZÓLJON A TE SZÁMOD")
    p.setPen(Qt.GlobalColor.white)
    p.setFont(_betu(50, QFont.Weight.Black))
    p.drawText(QRectF(margo, _mm(60), szel - 2 * margo, _mm(24)),
               Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "Kérj zenét")
    p.setPen(SARGA)
    p.drawText(QRectF(margo, _mm(82), szel - 2 * margo, _mm(24)),
               Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "a szünetre!")
    p.setPen(QColor(255, 255, 255, 225))
    p.setFont(_betu(14))
    p.drawText(QRectF(margo, _mm(108), szel * 0.62, _mm(20)), Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
               "Olvasd be a kódot, írd be a kedvenc számod, és szólhat a következő szünetben.")

    kartya_szel = _mm(104)
    kartya = QRectF((szel - kartya_szel) / 2, _mm(128), kartya_szel, _mm(117))
    sugar = _mm(7)
    _arnyek(p, kartya, sugar)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(Qt.GlobalColor.white)
    p.drawRoundedRect(kartya, sugar, sugar)
    p.setBrush(SARGA)
    p.drawRoundedRect(QRectF(kartya.center().x() - _mm(14), kartya.top() - _mm(1.6), _mm(28), _mm(3.2)),
                      _mm(1.6), _mm(1.6))
    qr_meret = _mm(84)
    _qr(p, cim, QRectF(kartya.center().x() - qr_meret / 2, kartya.top() + _mm(9), qr_meret, qr_meret))
    p.setPen(QPen(QColor("#E3E8EF"), _mm(0.35)))
    elvalaszto = kartya.top() + _mm(98)
    p.drawLine(QPointF(kartya.left() + _mm(10), elvalaszto), QPointF(kartya.right() - _mm(10), elvalaszto))
    p.setPen(KEK)
    p.setFont(_betu(12, QFont.Weight.DemiBold))
    p.drawText(QRectF(kartya.left(), elvalaszto, kartya.width(), kartya.bottom() - elvalaszto),
               Qt.AlignmentFlag.AlignCenter, rovid_cim(cim))

    oszlop_szel = (szel - 2 * margo - 2 * _mm(8)) / 3
    y = _mm(254)
    for i, (cimsor, szoveg) in enumerate(lepesek()):
        x = margo + i * (oszlop_szel + _mm(8))
        kor = QRectF(x, y, _mm(10), _mm(10))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(SARGA)
        p.drawEllipse(kor)
        p.setPen(TINTA)
        p.setFont(_betu(13, QFont.Weight.Black))
        p.drawText(kor, Qt.AlignmentFlag.AlignCenter, str(i + 1))
        p.setFont(_betu(13, QFont.Weight.Bold))
        p.drawText(QRectF(x + _mm(13), y, oszlop_szel - _mm(13), _mm(10)),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, cimsor)
        p.setPen(HALVANY)
        p.setFont(_betu(10.5))
        p.drawText(QRectF(x, y + _mm(12), oszlop_szel, _mm(16)),
                   Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, szoveg)

    lab = QRectF(0, mag - _mm(11), szel, _mm(11))
    p.fillRect(lab, MELYKEK)
    p.fillRect(QRectF(0, lab.top(), szel, _mm(1.2)), SARGA)
    p.setPen(QColor(255, 255, 255, 215))
    p.setFont(_betu(9.5))
    belso = lab.adjusted(margo, _mm(1.2), -margo, 0)
    p.drawText(belso, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
               "Trágár vagy korhatáros szám nem kerül adásba.")
    p.setFont(_betu(9.5, QFont.Weight.Bold))
    p.drawText(belso, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, f"{nev} · jó zenélést!")
