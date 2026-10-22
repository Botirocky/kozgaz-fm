__lazy_modules__ = [
    "logging",
    "datetime",
    "PySide6.QtCore",
    "PySide6.QtWidgets",
    "kozgaz_fm",
    "kozgaz_fm.frissites",
    "kozgaz_fm.orarend",
]

import logging
from datetime import datetime

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from kozgaz_fm import frissites, hatter
from kozgaz_fm.frissites import FrissitesHiba, Kiadas
from kozgaz_fm.orarend import allapot

naplo = logging.getLogger(__name__)

HAT_ORA = 6 * 3600 * 1000


class Frissito(QObject):
    allapot_valtozott = Signal(str)
    kiadas_valtozott = Signal(object)
    halad = Signal(float)

    def __init__(self, vezerlo, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.v = vezerlo
        self.kiadas: Kiadas | None = None
        self.mod = frissites.telepitesi_mod()
        self.allapot = ""
        self.fut = False
        self._kereso = QTimer(self)
        self._kereso.setInterval(HAT_ORA)
        self._kereso.timeout.connect(self.kereses)
        self._varo = QTimer(self)
        self._varo.setInterval(5 * 60 * 1000)
        self._varo.timeout.connect(self._auto_telepites)

    def indit(self) -> None:
        if self.v.b.frissites_kereses:
            QTimer.singleShot(90 * 1000, self.kereses)
        self._kereso.start()
        self._varo.start()

    @property
    def tamogatott(self) -> bool:
        return self.mod in ("windows", "linux-csomag", "venv")

    def _allit(self, szoveg: str) -> None:
        self.allapot = szoveg
        self.allapot_valtozott.emit(szoveg)

    def kereses(self, kezi: bool = False) -> None:
        if self.fut or (not kezi and not self.v.b.frissites_kereses):
            return
        self._allit("Frissítés keresése…")

        def kesz(kiadas: Kiadas) -> None:
            self.kiadas = kiadas if kiadas.uj else None
            self.kiadas_valtozott.emit(self.kiadas)
            if self.kiadas:
                self._allit(f"Új verzió érhető el: {kiadas.verzio}")
                self.v.log(f"Új verzió érhető el: {kiadas.verzio}")
                self._auto_telepites()
            else:
                self._allit(f"A program naprakész ({datetime.now():%H:%M}).")

        def hiba(e: Exception) -> None:
            self._allit(str(e) if isinstance(e, FrissitesHiba) else f"Hiba: {e}")

        hatter.futtat(frissites.legujabb, kesz, hiba)

    def _auto_telepites(self) -> None:
        if not (self.kiadas and self.v.b.frissites_auto and self.tamogatott) or self.fut:
            return
        most = datetime.now()
        a = allapot(self.v.b, most)
        kovetkezo = a.kovetkezo.ido if a.kovetkezo else None
        if frissites.biztonsagos_ido(a.szakasz.value, kovetkezo, most, self.v.zene.szol, self.v.riasztas):
            self.v.log(f"Automatikus frissítés: {self.kiadas.verzio}")
            self.telepites()

    def telepites(self) -> None:
        kiadas = self.kiadas
        if kiadas is None or self.fut:
            return
        if not self.tamogatott:
            self._allit("Ennél a futtatási módnál nincs automatikus frissítés.")
            return
        nev = frissites.csomag_neve(kiadas, self.mod)
        if nev is None:
            self._allit("A kiadásban nincs ehhez a géphez való csomag.")
            return
        self.fut = True
        self._allit(f"Letöltés: {nev}")

        def munka():
            csomag = frissites.letoltes(kiadas, nev, lambda x: self.halad.emit(x))
            if self.mod == "windows":
                return csomag
            return frissites.telepit(csomag, self.mod)

        def kesz(eredmeny) -> None:
            self.v.log(f"Frissítés telepítve: {kiadas.verzio}, újraindulás")
            self.v.leallit()
            if self.mod == "windows":
                frissites.telepit(eredmeny, self.mod)
                QApplication.quit()
                return
            hatter.leallit()
            frissites.ujraindit(eredmeny)

        def hiba(e: Exception) -> None:
            self.fut = False
            uzenet = str(e) if isinstance(e, FrissitesHiba) else f"Hiba: {e}"
            self._allit(uzenet)
            self.v.log(f"HIBA: frissítés – {uzenet}")

        hatter.futtat(munka, kesz, hiba)
