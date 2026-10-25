__lazy_modules__ = [
    "contextlib",
    "logging",
    "shutil",
    "subprocess",
    "sys",
    "time",
    "pathlib",
    "PySide6.QtCore",
    "kozgaz_fm",
    "kozgaz_fm.utvonalak",
]

import contextlib
import logging
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PySide6.QtCore import QLocale, QObject, Signal

from kozgaz_fm import hatter
from kozgaz_fm.utvonalak import gyorsitotar_mappa

naplo = logging.getLogger(__name__)


WINDOWS_ESPEAK = [Path(r"C:\Program Files\eSpeak NG\espeak-ng.exe"),
                  Path(r"C:\Program Files (x86)\eSpeak NG\espeak-ng.exe")]


def espeak_ut() -> str | None:
    talalt = shutil.which("espeak-ng") or shutil.which("espeak")
    if talalt is None and sys.platform == "win32":
        talalt = next((str(ut) for ut in WINDOWS_ESPEAK if ut.is_file()), None)
    return talalt


def espeak_wav(szoveg: str, ut: Path, program: str | None = None) -> Path:
    program = program or espeak_ut()
    if program is None:
        raise OSError("nincs espeak-ng")
    opciok = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if sys.platform == "win32" else {}
    p = subprocess.run([program, "-v", "hu", "-s", "150", "-w", str(ut), "--", szoveg], capture_output=True,
                       timeout=60, **opciok)
    if p.returncode != 0 or not ut.exists() or ut.stat().st_size < 100:
        raise OSError(p.stderr.decode(errors="replace").strip()[:200] or "az espeak-ng nem készített hangot")
    return ut


class Bemondo(QObject):
    kesz = Signal()
    hangfajl_kesz = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tts = None
        self._beszel = False
        self._espeak_fut = False
        self._utolso_szoveg = ""
        self._generacio = 0
        self.hang_nev = ""
        self.hangero = 90
        self.zona_mod = False

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
        return self._motor() is not None or (self.zona_mod and espeak_ut() is not None)

    @staticmethod
    def zonazhato() -> bool:
        return espeak_ut() is not None

    def beallit(self, hang_nev: str, hangero: int) -> None:
        self.hang_nev = hang_nev
        self.hangero = hangero
        self._hang_valasztas()

    def mond(self, szoveg: str) -> bool:
        if not szoveg.strip():
            return False
        if self.zona_mod and self._hangfajlba(szoveg):
            return True
        return self._kimond(szoveg)

    def _kimond(self, szoveg: str) -> bool:
        motor = self._motor()
        if motor is None:
            return False
        motor.setVolume(max(0.0, min(1.0, self.hangero / 100)))
        motor.setRate(-0.05)
        self._beszel = True
        motor.say(szoveg)
        return True

    def _uj_fajl(self) -> Path:
        mappa = gyorsitotar_mappa() / "bemondas"
        mappa.mkdir(parents=True, exist_ok=True)
        for regi in sorted(mappa.glob("*.wav"))[:-4]:
            with contextlib.suppress(OSError):
                regi.unlink()
        return mappa / f"bemondas-{time.time_ns()}.wav"

    def _hangfajlba(self, szoveg: str) -> bool:
        self._generacio += 1
        generacio = self._generacio
        if espeak_ut() is None:
            return False
        ut = self._uj_fajl()
        self._beszel = True
        self._espeak_fut = True
        self._utolso_szoveg = szoveg
        hatter.futtat(lambda: espeak_wav(szoveg, ut), lambda kesz_ut: self._fajl_kesz(generacio, kesz_ut),
                      lambda e: self._fajl_hiba(generacio, e))
        return True

    def _fajl_kesz(self, generacio: int, ut: Path) -> None:
        if generacio != self._generacio or not self._beszel:
            return
        self._espeak_fut = False
        self._beszel = False
        self.hangfajl_kesz.emit(str(ut))

    def _fajl_hiba(self, generacio: int, e: Exception) -> None:
        if generacio != self._generacio:
            return
        naplo.warning("A bemondás hangfájlja nem készült el, a rendszer felolvasója szól: %s", e)
        self._espeak_fut = False
        self._beszel = False
        if not self._kimond(self._utolso_szoveg):
            self.kesz.emit()

    def megallit(self) -> None:
        self._generacio += 1
        if not self._beszel:
            return
        if not self._espeak_fut and self._tts is not None:
            self._tts.stop()
            if self._tts.state().name not in ("Ready", "Error"):
                return
        self._espeak_fut = False
        self._beszel = False
        self.kesz.emit()

    def _allapot(self, allapot) -> None:
        from PySide6.QtTextToSpeech import QTextToSpeech

        if allapot in (QTextToSpeech.State.Ready, QTextToSpeech.State.Error) and self._beszel:
            self._beszel = False
            self.kesz.emit()
