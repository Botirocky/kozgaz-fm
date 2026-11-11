__lazy_modules__ = [
    "json",
    "logging",
    "math",
    "re",
    "subprocess",
    "threading",
    "pathlib",
    "kozgaz_fm.hangossag",
    "kozgaz_fm.utvonalak",
]

import json
import logging
import math
import re
import subprocess
import threading
from pathlib import Path

from kozgaz_fm import hangossag
from kozgaz_fm.utvonalak import gyorsitotar_mappa

naplo = logging.getLogger(__name__)

CSEND_KUSZOB_DB = -50
CSEND_MIN_MP = 0.3
CSEND_MAX_MP = 20.0
CSEND_MERES_IDOKORLAT_MP = 300
MIN_LEVAGAS_MS = 150
MAX_ATUSZTATAS_MP = 12.0
KEZI_ATUSZTATAS_MP = 2.0
CSENGO_ELHALKITAS_MP = 0.25

_CSEND_MINTA = re.compile(r"silence_(start|end):\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)")
_HOSSZ_MINTA = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


def gorbe_be(t: float) -> float:
    return math.sin(max(0.0, min(1.0, t)) * math.pi / 2)


def gorbe_ki(t: float) -> float:
    return math.cos(max(0.0, min(1.0, t)) * math.pi / 2)


def atuszas_hossz_ms(be: bool, mp: float) -> int:
    return int(max(0.0, min(MAX_ATUSZTATAS_MP, mp)) * 1000) if be else 0


def atuszas_kezdet_ms(hossz_ms: int, vege_csend_ms: int, atuszas_ms: int) -> int:
    return max(0, hossz_ms - vege_csend_ms - atuszas_ms)


def csend_ertelmez(kimenet: str) -> tuple[float, float]:
    hossz = None
    if m := _HOSSZ_MINTA.search(kimenet):
        hossz = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
    szakaszok: list[list[float | None]] = []
    for jel, ertek in _CSEND_MINTA.findall(kimenet):
        if jel == "start":
            szakaszok.append([float(ertek), None])
        elif szakaszok and szakaszok[-1][1] is None:
            szakaszok[-1][1] = float(ertek)
    eleje = vege = 0.0
    if szakaszok and szakaszok[0][0] is not None and szakaszok[0][0] <= 0.05 and szakaszok[0][1] is not None:
        eleje = szakaszok[0][1] or 0.0
    if hossz is not None and szakaszok:
        kezdet, veg = szakaszok[-1]
        if kezdet is not None and (veg is None or veg >= hossz - 0.1) and kezdet > eleje:
            vege = hossz - kezdet
    if hossz is not None and eleje + vege > hossz / 2:
        return 0.0, 0.0
    return min(eleje, CSEND_MAX_MP), min(max(vege, 0.0), CSEND_MAX_MP)


def csend_meres(ut: Path, ffmpeg: str | None = None) -> tuple[float, float]:
    program = ffmpeg or hangossag.ffmpeg_ut()
    if program is None:
        raise hangossag.HangossagHiba("nincs ffmpeg")
    szuro = f"silencedetect=n={CSEND_KUSZOB_DB}dB:d={CSEND_MIN_MP}"
    parancs, opciok = hangossag._parancs(program, ut, szuro)
    try:
        folyamat = subprocess.run(parancs, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.PIPE, text=True, errors="replace",
                                  timeout=CSEND_MERES_IDOKORLAT_MP, **opciok)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise hangossag.HangossagHiba(f"a csend-mérés nem sikerült: {e}") from None
    if folyamat.returncode != 0:
        raise hangossag.HangossagHiba((folyamat.stderr.strip().splitlines() or ["ismeretlen hiba"])[-1][:200])
    return csend_ertelmez(folyamat.stderr)


class CsendTar:
    def __init__(self, fajl: Path | None = None) -> None:
        self.fajl = fajl or gyorsitotar_mappa() / "csend.json"
        self._zar = threading.Lock()
        self._adat: dict[str, dict] = {}
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
            return float(e["e"]), float(e["v"])
        except (KeyError, TypeError, ValueError):
            return None

    def beir(self, ut: Path, eleje: float, vege: float) -> None:
        jel = self._jel(ut)
        if jel is None:
            return
        with self._zar:
            self._adat[str(ut)] = {"m": jel[0], "s": jel[1], "e": eleje, "v": vege}
            adat = dict(self._adat)
        try:
            self.fajl.parent.mkdir(parents=True, exist_ok=True)
            ideig = self.fajl.with_suffix(".tmp")
            ideig.write_text(json.dumps(adat, ensure_ascii=False), encoding="utf-8")
            ideig.replace(self.fajl)
        except OSError as e:
            naplo.warning("A csend-tár nem menthető: %s", e)
