__lazy_modules__ = ["time", "collections.abc", "PySide6.QtCore", "kozgaz_fm.dalszoveg", "kozgaz_fm.hang"]

import time
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer

from kozgaz_fm import dalszoveg, hatter
from kozgaz_fm.dalszoveg import DalszovegTar, Eredmeny

TICK_MS = 2000
HIBA_SZUNET_MP = 120.0


class DalszovegOr(QObject):
    def __init__(self, zene, tar: DalszovegTar, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.zene = zene
        self.tar = tar
        self.be = True
        self.erzekenyseg = "normal"
        self._fut = False
        self._szunet_ig = 0.0
        self._nezett: set[str] = set()
        self._ora = QTimer(self)
        self._ora.setInterval(TICK_MS)
        self._ora.timeout.connect(self.tick)
        self._ora.start()

    def beallit(self, be: bool, erzekenyseg: str) -> None:
        if (be, erzekenyseg) == (self.be, self.erzekenyseg):
            return
        self.be, self.erzekenyseg = be, erzekenyseg
        self._nezett.clear()
        self.zene.tragarak_torlese()

    def tragar(self, eredmeny: Eredmeny | None) -> bool:
        return bool(eredmeny and eredmeny.talalt and eredmeny.ertekeles.tragar(self.erzekenyseg))

    def tick(self) -> None:
        if not self.be or self._fut or time.monotonic() < self._szunet_ig:
            return
        for szam in self.zene.vizsgalando():
            if szam.cim in self._nezett:
                continue
            ismert = self.tar.keres(szam.cim)
            if ismert is None:
                mappa = szam.helyi.parent.name if szam.helyi and not szam.yt else ""
                self._lekerdez(szam.cim, 0, mappa, lambda e, sz=szam: self._itel(sz, e))
                return
            self._itel(szam, ismert)

    def _itel(self, szam, eredmeny: Eredmeny) -> None:
        self._nezett.add(szam.cim)
        if self.tragar(eredmeny):
            self.zene.tragarat_kivesz(szam, eredmeny.ertekeles.szoveg())

    def spotify_vizsgal(self, felirat: str, kesz: Callable[[Eredmeny], None]) -> None:
        if not self.be or self._fut or time.monotonic() < self._szunet_ig:
            return
        ismert = self.tar.keres(felirat)
        if ismert is not None:
            kesz(ismert)
        else:
            self._lekerdez(felirat, 0, "", kesz)

    def _lekerdez(self, cim: str, hossz: int, tobblet: str, kesz: Callable[[Eredmeny], None]) -> None:
        self._fut = True

        def siker(eredmeny: Eredmeny) -> None:
            self._fut = False
            self.tar.beir(cim, eredmeny)
            kesz(eredmeny)

        def hiba(_e: Exception) -> None:
            self._fut = False
            self._szunet_ig = time.monotonic() + HIBA_SZUNET_MP

        hatter.futtat(lambda: dalszoveg.vizsgal(cim, hossz, tobblet), siker, hiba)
