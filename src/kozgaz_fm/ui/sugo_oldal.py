from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

from kozgaz_fm.ui.tema import SZIN
from kozgaz_fm.utvonalak import csomag_mappa
from kozgaz_fm.vezerlo import Vezerlo


class SugoOldal(QWidget):
    def __init__(self, v: Vezerlo) -> None:
        super().__init__()
        e = QVBoxLayout(self)
        e.setContentsMargins(28, 22, 28, 28)
        self.szoveg = QTextBrowser()
        self.szoveg.setOpenExternalLinks(True)
        self.szoveg.setStyleSheet(f"QTextBrowser {{ background: {SZIN['felulet']}; border: 1px solid {SZIN['keret']};"
                                  f" border-radius: 6px; padding: 18px 26px; font-size: 11pt; }}")
        self.szoveg.document().setDefaultStyleSheet(
            f"a {{ color: {SZIN['kek']}; }} h1 {{ color: {SZIN['szoveg']}; }} h2 {{ color: {SZIN['szoveg']}; }}"
            f" code {{ color: {SZIN['kek']}; }} th {{ text-align: left; }}")
        try:
            self.szoveg.setMarkdown((csomag_mappa() / "sugo.md").read_text(encoding="utf-8"))
        except OSError:
            self.szoveg.setPlainText("A súgó nem található.")
        e.addWidget(self.szoveg)

    def frissit(self) -> None:
        pass
