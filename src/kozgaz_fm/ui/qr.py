__lazy_modules__ = ["io", "PySide6.QtGui", "segno"]

import io

from PySide6.QtGui import QPixmap


def qr_png(szoveg: str, meret: int = 10, sotet: str = "#000000", vilagos: str = "#FFFFFF") -> bytes:
    import segno

    puffer = io.BytesIO()
    segno.make(szoveg, error="m").save(puffer, kind="png", scale=meret, border=2, dark=sotet, light=vilagos)
    return puffer.getvalue()


def qr_pixmap(szoveg: str, kepmeret: int) -> QPixmap:
    import segno

    modulok = segno.make(szoveg, error="m").symbol_size(scale=1, border=2)[0]
    kep = QPixmap()
    kep.loadFromData(qr_png(szoveg, max(1, kepmeret // modulok)))
    return kep
