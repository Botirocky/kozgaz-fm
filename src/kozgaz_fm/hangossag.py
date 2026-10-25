__lazy_modules__ = [
    "collections",
    "concurrent.futures",
    "json",
    "logging",
    "os",
    "re",
    "shutil",
    "subprocess",
    "sys",
    "threading",
    "pathlib",
    "PySide6.QtCore",
    "kozgaz_fm.utvonalak",
]

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, Signal

from kozgaz_fm.utvonalak import gyorsitotar_mappa

naplo = logging.getLogger(__name__)

CEL_LUFS = -16.0
MAX_EMELES_DB = 6.0
MAX_CSOKKENTES_DB = -20.0
CSUCS_HATAR_DBTP = -1.0
CSEND_LUFS = -60.0
MERES_IDOKORLAT_MP = 300

_I_MINTA = re.compile(r"^\s*I:\s*(-?\d+(?:\.\d+)?|-inf)\s*LUFS", re.M)
_CSUCS_MINTA = re.compile(r"^\s*Peak:\s*(-?\d+(?:\.\d+)?|-inf)\s*dBFS", re.M)


class HangossagHiba(Exception):
    pass


_ffmpeg: str | None = None
_ffmpeg_keresve = False


def ffmpeg_ut() -> str | None:
    global _ffmpeg, _ffmpeg_keresve
    if _ffmpeg_keresve:
        return _ffmpeg
    _ffmpeg_keresve = True
    _ffmpeg = shutil.which("ffmpeg")
    if _ffmpeg is None:
        try:
            import imageio_ffmpeg
            _ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            if sys.platform != "win32" and not os.access(_ffmpeg, os.X_OK):
                os.chmod(_ffmpeg, os.stat(_ffmpeg).st_mode | 0o111)
        except Exception as e:
            naplo.info("Nincs ffmpeg, a hangerő-kiegyenlítés nem működik: %s", e)
    return _ffmpeg


def _szam(szoveg: str) -> float:
    return float("-inf") if szoveg == "-inf" else float(szoveg)


def kimenet_ertelmez(kimenet: str) -> tuple[float, float]:
    osszegzes = kimenet[kimenet.rfind("Summary:"):] if "Summary:" in kimenet else kimenet
    i = _I_MINTA.findall(osszegzes)
    csucs = _CSUCS_MINTA.findall(osszegzes)
    if not i:
        raise HangossagHiba("az ffmpeg nem adott hangosságot")
    return _szam(i[-1]), _szam(csucs[-1]) if csucs else 0.0


def _parancs(program: str, ut: Path) -> tuple[list[str], dict]:
    parancs = [program, "-nostdin", "-hide_banner", "-nostats", "-i", str(ut), "-vn", "-sn",
               "-af", "ebur128=peak=true", "-f", "null", "-"]
    if sys.platform == "win32":
        return parancs, {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)
                         | getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)}
    nice = shutil.which("nice")
    return ([nice, "-n", "15", *parancs] if nice else parancs), {}


def meres(ut: Path, ffmpeg: str | None = None, inditva=None) -> tuple[float, float]:
    program = ffmpeg or ffmpeg_ut()
    if program is None:
        raise HangossagHiba("nincs ffmpeg")
    parancs, opciok = _parancs(program, ut)
    try:
        folyamat = subprocess.Popen(parancs, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE, text=True, errors="replace", **opciok)
    except OSError as e:
        raise HangossagHiba(f"az ffmpeg nem indult: {e}") from None
    if inditva:
        inditva(folyamat)
    try:
        _, hibakimenet = folyamat.communicate(timeout=MERES_IDOKORLAT_MP)
    except subprocess.TimeoutExpired:
        folyamat.kill()
        folyamat.communicate()
        raise HangossagHiba("a mérés túl sokáig tartott") from None
    finally:
        if inditva:
            inditva(None)
    if folyamat.returncode != 0:
        raise HangossagHiba((hibakimenet.strip().splitlines() or ["ismeretlen hiba"])[-1][:200])
    return kimenet_ertelmez(hibakimenet)


def erosites_db(lufs: float, csucs: float, cel: float = CEL_LUFS) -> float:
    if lufs == float("-inf") or lufs < CSEND_LUFS:
        return 0.0
    db = cel - lufs
    if db > 0 and csucs != float("-inf"):
        db = min(db, CSUCS_HATAR_DBTP - csucs)
    return max(MAX_CSOKKENTES_DB, min(MAX_EMELES_DB, db))


def szorzo(db: float) -> float:
    return 10 ** (db / 20)


class Tar:
    def __init__(self, fajl: Path | None = None) -> None:
        self.fajl = fajl or gyorsitotar_mappa() / "hangossag.json"
        self._zar = threading.Lock()
        self._adat: dict[str, dict] = {}
        self._valtozott = False
        try:
            betoltott = json.loads(self.fajl.read_text(encoding="utf-8"))
            if isinstance(betoltott, dict):
                self._adat = {k: v for k, v in betoltott.items() if isinstance(v, dict)}
        except (OSError, ValueError):
            pass

    @staticmethod
    def _jel(ut: Path) -> tuple[float, int] | None:
        try:
            st = ut.stat()
        except OSError:
            return None
        return st.st_mtime, st.st_size

    def keres(self, ut: Path) -> tuple[float, float] | None:
        jel = self._jel(ut)
        with self._zar:
            e = self._adat.get(str(ut))
        if not e or jel is None or e.get("m") != jel[0] or e.get("s") != jel[1]:
            return None
        try:
            return _szam(str(e["i"])), _szam(str(e["p"]))
        except (KeyError, ValueError):
            return None

    def beir(self, ut: Path, lufs: float, csucs: float) -> None:
        jel = self._jel(ut)
        if jel is None:
            return
        with self._zar:
            self._adat[str(ut)] = {"m": jel[0], "s": jel[1], "i": str(lufs), "p": str(csucs)}
            self._valtozott = True

    def darab(self) -> int:
        with self._zar:
            return len(self._adat)

    def mentes(self) -> None:
        with self._zar:
            if not self._valtozott:
                return
            adat = dict(self._adat)
            self._valtozott = False
        try:
            self.fajl.parent.mkdir(parents=True, exist_ok=True)
            ideig = self.fajl.with_suffix(".tmp")
            ideig.write_text(json.dumps(adat, ensure_ascii=False), encoding="utf-8")
            ideig.replace(self.fajl)
        except OSError as e:
            naplo.warning("A hangosság-tár nem menthető: %s", e)


class Kiegyenlito(QObject):
    mert = Signal(str)
    allapot_valtozott = Signal()

    def __init__(self, parent: QObject | None = None, tar: Tar | None = None) -> None:
        super().__init__(parent)
        self.tar = tar or Tar()
        self.bekapcsolva = True
        self.cel = CEL_LUFS
        self._sor: deque[Path] = deque()
        self._sorban: set[str] = set()
        self._hibas: set[str] = set()
        self._fut: str | None = None
        self._folyamat: subprocess.Popen | None = None
        self._leallitva = False
        self._zar = threading.Lock()
        self._vegrehajto = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kozgaz-fm-hangossag")
        self._mento = QTimer(self)
        self._mento.setSingleShot(True)
        self._mento.setInterval(5000)
        self._mento.timeout.connect(self.tar.mentes)
        self.mert.connect(self._ment_kesobb, Qt.ConnectionType.QueuedConnection)

    def _ment_kesobb(self, _ut: str) -> None:
        self._mento.start()

    def _folyamat_jelol(self, folyamat: subprocess.Popen | None) -> None:
        with self._zar:
            self._folyamat = folyamat

    @property
    def elerheto(self) -> bool:
        return ffmpeg_ut() is not None

    def varakozik(self) -> int:
        with self._zar:
            return len(self._sor) + (1 if self._fut else 0)

    def szorzo(self, ut: Path | None) -> float:
        if not self.bekapcsolva or ut is None:
            return 1.0
        mert = self.tar.keres(ut)
        if mert is None:
            return 1.0
        return szorzo(erosites_db(*mert, cel=self.cel))

    def kell(self, ut: Path | None, elore: bool = False) -> None:
        if self._leallitva or not self.bekapcsolva or ut is None or not self.elerheto:
            return
        kulcs = str(ut)
        if kulcs in self._hibas or self.tar.keres(ut) is not None:
            return
        with self._zar:
            if kulcs == self._fut:
                return
            if kulcs in self._sorban:
                if not elore:
                    return
                self._sor.remove(ut)
            self._sorban.add(kulcs)
            self._sor.appendleft(ut) if elore else self._sor.append(ut)
            indul = self._fut is None
        if indul:
            self._kovetkezo()

    def _kovetkezo(self) -> None:
        with self._zar:
            if self._leallitva or self._fut is not None or not self._sor:
                return
            ut = self._sor.popleft()
            self._sorban.discard(str(ut))
            self._fut = str(ut)
        self._vegrehajto.submit(self._mer, ut)

    def _mer(self, ut: Path) -> None:
        try:
            lufs, csucs = meres(ut, inditva=self._folyamat_jelol)
            self.tar.beir(ut, lufs, csucs)
        except HangossagHiba as e:
            naplo.info("Hangosság nem mérhető (%s): %s", ut.name, e)
            self._hibas.add(str(ut))
        except Exception:
            naplo.exception("Váratlan hiba a hangosság mérésekor")
            self._hibas.add(str(ut))
        finally:
            with self._zar:
                self._fut = None
                leallitva = self._leallitva
        if leallitva:
            return
        try:
            self.mert.emit(str(ut))
            self.allapot_valtozott.emit()
        except RuntimeError:
            return
        self._kovetkezo()

    def leallit(self) -> None:
        with self._zar:
            self._leallitva = True
            self._sor.clear()
            self._sorban.clear()
            folyamat = self._folyamat
        if folyamat is not None:
            folyamat.kill()
        self._vegrehajto.shutdown(wait=False, cancel_futures=True)
        self.tar.mentes()
