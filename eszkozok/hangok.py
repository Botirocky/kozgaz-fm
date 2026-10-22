__lazy_modules__ = ["math", "sys", "wave", "array", "pathlib"]

import math
import sys
import wave
from array import array
from pathlib import Path

MINTA = 22050


def ures(mp: float) -> list[float]:
    return [0.0] * int(mp * MINTA)


def harang(frek: float, mp: float, lecsenges: float, felhangok=((1, 1.0), (2.01, 0.5), (2.76, 0.35), (5.4, 0.12))):
    n = int(mp * MINTA)
    ki = []
    for i in range(n):
        t = i / MINTA
        tamadas = min(1.0, t / 0.004)
        jel = sum(a * math.exp(-t * lecsenges * (1 + 0.6 * k)) * math.sin(2 * math.pi * frek * f * t)
                  for k, (f, a) in enumerate(felhangok))
        ki.append(jel * tamadas)
    return ki


def keverd(alap: list[float], hang: list[float], kezdet: float, hangero: float = 1.0) -> None:
    eltolas = int(kezdet * MINTA)
    if len(alap) < eltolas + len(hang):
        alap.extend([0.0] * (eltolas + len(hang) - len(alap)))
    for i, v in enumerate(hang):
        alap[eltolas + i] += v * hangero


def elektromos(mp: float, frek: float = 1180.0, utes: float = 21.0) -> list[float]:
    ki = ures(mp)
    periodus = 1 / utes
    t = 0.0
    egy = harang(frek, 0.25, 9.0, ((1, 1.0), (2.32, 0.6), (3.9, 0.4), (5.1, 0.25), (7.3, 0.12)))
    while t < mp - 0.25:
        keverd(ki, egy, t, 0.5)
        t += periodus
    lecsengo = harang(frek, 0.6, 5.0, ((1, 1.0), (2.32, 0.6), (3.9, 0.4), (5.1, 0.25)))
    keverd(ki, lecsengo, mp - 0.25, 0.5)
    return ki


def csengo() -> list[float]:
    return elektromos(4.0)


def rovid() -> list[float]:
    ki = elektromos(0.9)
    keverd(ki, elektromos(0.9), 1.25)
    return ki


def hang_frek(nev: str) -> float:
    lepcso = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "H": 2}
    return 440.0 * 2 ** ((lepcso[nev[0]] + 12 * (int(nev[1:]) - 4)) / 12)


def dallam() -> list[float]:
    ki: list[float] = []
    sor = [("G4", 0.0), ("C5", 0.35), ("E5", 0.7), ("G5", 1.05), ("E5", 1.6), ("G5", 1.95), ("C6", 2.3)]
    for nev, t in sor:
        keverd(ki, harang(hang_frek(nev), 2.2, 2.2, ((1, 1.0), (2.0, 0.35), (3.0, 0.12), (4.2, 0.05))), t, 0.45)
    return ki


def gong() -> list[float]:
    ki: list[float] = []
    for nev, t in [("C5", 0.0), ("E5", 0.55), ("G5", 1.1)]:
        keverd(ki, harang(hang_frek(nev), 3.0, 1.4, ((1, 1.0), (2.0, 0.25), (3.0, 0.08))), t, 0.5)
    return ki


def riasztas() -> list[float]:
    ki = []
    for i in range(int(8.0 * MINTA)):
        t = i / MINTA
        frek = 960.0 if int(t / 0.5) % 2 == 0 else 640.0
        jel = math.sin(2 * math.pi * frek * t)
        jel = max(-0.6, min(0.6, jel * 1.6)) + 0.25 * math.sin(2 * math.pi * frek * 3 * t)
        ki.append(jel)
    return ki


def ment(ut: Path, minta: list[float]) -> None:
    csucs = max(abs(v) for v in minta) or 1.0
    szorzo = 0.89 / csucs
    halk = int(0.01 * MINTA)
    for i in range(min(halk, len(minta))):
        minta[-1 - i] *= i / halk
    adat = array("h", (int(max(-1.0, min(1.0, v * szorzo)) * 32767) for v in minta))
    if sys.byteorder == "big":
        adat.byteswap()
    with wave.open(str(ut), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(MINTA)
        f.writeframes(adat.tobytes())


def main() -> None:
    cel = Path(__file__).resolve().parent.parent / "src" / "kozgaz_fm" / "hangok"
    cel.mkdir(parents=True, exist_ok=True)
    for nev, gyarto in [("csengo", csengo), ("rovid", rovid), ("dallam", dallam), ("gong", gong),
                        ("riasztas", riasztas)]:
        ment(cel / f"{nev}.wav", gyarto())
        print(f"{nev}.wav kész")


if __name__ == "__main__":
    main()
