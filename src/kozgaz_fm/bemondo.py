__lazy_modules__ = ["logging", "PySide6.QtCore"]

import logging

from PySide6.QtCore import QLocale, QObject, Signal

naplo = logging.getLogger(__name__)


class Bemondo(QObject):
    kesz = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tts = None
        self._beszel = False
        self.hang_nev = ""
        self.hangero = 90

    def _motor(self):
        if self._tts is None:
            try:
                from PySide6.QtTextToSpeech import QTextToSpeech
            except ImportError:
                return None
            if not QTextToSpeech.availableEngines():
                return None
            self._tts = QTextToSpeech(self)
            self._tts.stateChanged.connect(self._allapot)
            self._hang_valasztas()
        return self._tts

    @property
    def beszel(self) -> bool:
        return self._beszel

    def _hang_valasztas(self) -> None:
        if self._tts is None:
            return
        magyar = QLocale(QLocale.Language.Hungarian, QLocale.Country.Hungary)
        if magyar in self._tts.availableLocales():
            self._tts.setLocale(magyar)
        hangok = self._tts.availableVoices()
        valasztott = next((h for h in hangok if h.name() == self.hang_nev), None)
        if valasztott is None:
            valasztott = next((h for h in hangok if h.locale().language() == QLocale.Language.Hungarian), None)
        if valasztott is not None:
            self._tts.setVoice(valasztott)

    def hangok(self) -> list[str]:
        motor = self._motor()
        return [h.name() for h in motor.availableVoices()] if motor else []

    def elerheto(self) -> bool:
        return self._motor() is not None

    def beallit(self, hang_nev: str, hangero: int) -> None:
        self.hang_nev = hang_nev
        self.hangero = hangero
        self._hang_valasztas()

    def mond(self, szoveg: str) -> bool:
        motor = self._motor()
        if motor is None or not szoveg.strip():
            return False
        motor.setVolume(max(0.0, min(1.0, self.hangero / 100)))
        motor.setRate(-0.05)
        self._beszel = True
        motor.say(szoveg)
        return True

    def megallit(self) -> None:
        if self._tts is not None and self._beszel:
            self._tts.stop()

    def _allapot(self, allapot) -> None:
        from PySide6.QtTextToSpeech import QTextToSpeech

        if allapot in (QTextToSpeech.State.Ready, QTextToSpeech.State.Error) and self._beszel:
            self._beszel = False
            self.kesz.emit()
