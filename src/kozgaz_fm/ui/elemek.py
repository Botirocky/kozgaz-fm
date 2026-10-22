from PySide6.QtCore import QSize, Qt, QTime, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListView,
    QPushButton,
    QScrollArea,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from kozgaz_fm.ui.tema import SZIN, ikon


def cimke(szoveg: str = "", szerep: str = "", sortores: bool = False) -> QLabel:
    c = QLabel(szoveg)
    if szerep:
        c.setProperty("szerep", szerep)
    c.setWordWrap(sortores)
    return c


def gomb(szoveg: str, ikon_nev: str = "", szerep: str = "", tipp: str = "", szin: str | None = None) -> QPushButton:
    g = QPushButton(szoveg)
    if ikon_nev:
        g.setIcon(ikon(ikon_nev, szin or (SZIN["kiemelt_szoveg"] if szerep == "fo" else SZIN["szoveg"])))
        g.setIconSize(QSize(18, 18))
    if szerep:
        g.setProperty("szerep", szerep)
    if tipp:
        g.setToolTip(tipp)
    g.setCursor(Qt.CursorShape.PointingHandCursor)
    return g


def ikon_gomb(ikon_nev: str, tipp: str, szerep: str = "kerek", meret: int = 20, szin: str | None = None
              ) -> QPushButton:
    g = QPushButton()
    g.setIcon(ikon(ikon_nev, szin or SZIN["szoveg"]))
    g.setIconSize(QSize(meret, meret))
    g.setProperty("szerep", szerep)
    g.setToolTip(tipp)
    g.setAccessibleName(tipp)
    g.setCursor(Qt.CursorShape.PointingHandCursor)
    return g


class Kartya(QFrame):
    def __init__(self, cim: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("szerep", "kartya")
        self.elrendezes = QVBoxLayout(self)
        self.elrendezes.setContentsMargins(20, 18, 20, 18)
        self.elrendezes.setSpacing(12)
        if cim:
            self.elrendezes.addWidget(cimke(cim.upper(), "szekcio"))

    def add(self, elem) -> None:
        if isinstance(elem, QWidget):
            self.elrendezes.addWidget(elem)
        else:
            self.elrendezes.addLayout(elem)


def sor(*elemek, terkoz: int = 10, nyujt: bool = False) -> QHBoxLayout:
    s = QHBoxLayout()
    s.setSpacing(terkoz)
    for e in elemek:
        if e is None:
            s.addStretch(1)
        elif isinstance(e, QWidget):
            s.addWidget(e)
        else:
            s.addLayout(e)
    if nyujt:
        s.addStretch(1)
    return s


def kapcsolo(szoveg: str, ertek: bool, tipp: str = "") -> QCheckBox:
    k = QCheckBox(szoveg)
    k.setChecked(ertek)
    k.setCursor(Qt.CursorShape.PointingHandCursor)
    if tipp:
        k.setToolTip(tipp)
    return k


def ido_mezo(szoveg: str) -> QTimeEdit:
    m = QTimeEdit()
    m.setDisplayFormat("HH:mm")
    ora, perc = (int(x) for x in szoveg.split(":")[:2])
    m.setTime(QTime(ora, perc))
    m.setMinimumWidth(92)
    return m


def gorgeto(belso: QWidget) -> QScrollArea:
    g = QScrollArea()
    g.setWidgetResizable(True)
    g.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    g.setFrameShape(QFrame.Shape.NoFrame)
    g.setWidget(belso)
    return g


def keskeny(lista: QComboBox, karakter: int = 14) -> QComboBox:
    lista.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    lista.setMinimumContentsLength(karakter)
    return lista


class Oldal(QWidget):
    def __init__(self, cim: str, leiras: str = "") -> None:
        super().__init__()
        kulso = QVBoxLayout(self)
        kulso.setContentsMargins(0, 0, 0, 0)
        belso = QWidget()
        self.elrendezes = QVBoxLayout(belso)
        self.elrendezes.setContentsMargins(32, 28, 32, 28)
        self.elrendezes.setSpacing(16)
        self.elrendezes.addWidget(cimke(cim, "cim"))
        if leiras:
            self.elrendezes.addWidget(cimke(leiras, "halvany", sortores=True))
        kulso.addWidget(gorgeto(belso))

    def add(self, elem, nyujt: int = 0) -> None:
        if isinstance(elem, QWidget):
            self.elrendezes.addWidget(elem, nyujt)
        else:
            self.elrendezes.addLayout(elem, nyujt)

    def showEvent(self, esemeny) -> None:
        super().showEvent(esemeny)
        for kombo in self.findChildren(QComboBox):
            keskeny(kombo)
        for lista in self.findChildren(QListView):
            lista.doItemsLayout()

    def frissit(self) -> None:
        pass


class Ertesites(QFrame):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("ertesites")
        e = QHBoxLayout(self)
        e.setContentsMargins(18, 12, 16, 12)
        self.szoveg = cimke(sortores=True)
        e.addWidget(self.szoveg)
        self._idozito = QTimer(self)
        self._idozito.setSingleShot(True)
        self._idozito.timeout.connect(self.hide)
        self.hide()

    def mutat(self, szoveg: str, szint: str = "info") -> None:
        szin = {"hiba": SZIN["hiba"], "siker": SZIN["szol"]}.get(szint, SZIN["info"])
        self.setStyleSheet(f"QFrame#ertesites {{ background: {SZIN['felulet2']}; border-radius: 10px;"
                           f" border: 1px solid {SZIN['keret_eros']}; border-left: 4px solid {szin}; }}")
        self.szoveg.setText(szoveg)
        szulo = self.parentWidget()
        szel = min(460, szulo.width() - 40)
        self.setFixedWidth(szel)
        self.adjustSize()
        self.move(szulo.width() - szel - 20, szulo.height() - self.height() - 20)
        self.raise_()
        self.show()
        self._idozito.start(6000 if szint == "hiba" else 3500)


class Valtozas(QWidget):
    valtozott = Signal()
