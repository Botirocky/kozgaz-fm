__lazy_modules__ = [
    "os",
    "sys",
    "tempfile",
    "time",
    "pathlib",
    "PySide6.QtWidgets",
    "kozgaz_fm",
    "kozgaz_fm.beallitasok",
    "kozgaz_fm.ui.fo_ablak",
    "kozgaz_fm.ui.tema",
    "kozgaz_fm.utvonalak",
    "kozgaz_fm.vezerlo",
]

import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["KOZGAZ_FM_ADAT"] = tempfile.mkdtemp()

from PySide6.QtWidgets import QApplication

from kozgaz_fm import sajat_hangok
from kozgaz_fm.beallitasok import Bemondas, Szunnap, ZeneForras, alapertelmezett
from kozgaz_fm.ui.fo_ablak import FoAblak
from kozgaz_fm.ui.tema import betutipus, stilus
from kozgaz_fm.utvonalak import beepitett_hang
from kozgaz_fm.vezerlo import Vezerlo


def main() -> None:
    cel = Path(sys.argv[1] if len(sys.argv) > 1 else "kepek")
    cel.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(betutipus())
    app.setStyleSheet(stilus())
    b = alapertelmezett()
    b.forrasok = [ZeneForras("mappa", "Iskolarádió válogatás", "D:/Zene/Iskolarádió"),
                  ZeneForras("youtube", "Slágerlista", "https://www.youtube.com/playlist?list=PL4fGSI1pDJn6puJdseH2Rt9sMvt9E2M4i"),
                  ZeneForras("spotify", "Today's Top Hits", "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M")]
    b.szunnapok = [Szunnap("2026-10-23", "2026-11-01", "Őszi szünet"),
                   Szunnap("2026-12-21", "2027-01-01", "Téli szünet")]
    b.bemondasok = [Bemondas("Hétfő reggeli Himnusz", "07:55", [0], tipus="fajl", tartalom="/zene/himnusz.mp3")]
    sajat_hangok.hozzaad(beepitett_hang("dallam"), "Közgáz FM szignál")
    b.hang_becsengo = sajat_hangok.hozzaad(beepitett_hang("csengo"), "Iskolai csengő (régi)").ertek
    v = Vezerlo(b)
    ablak = FoAblak(v)
    ablak.resize(1360, 900)
    ablak.show()
    for i in range(len(ablak.oldalak)):
        ablak._lapozas(i)
        for _ in range(20):
            app.processEvents()
            time.sleep(0.02)
        ablak.ertesites.hide()
        ablak.grab().save(str(cel / f"{i}.png"))
    v.leallit()


if __name__ == "__main__":
    main()
