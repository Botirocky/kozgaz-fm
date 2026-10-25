__lazy_modules__ = ["csv", "logging", "sqlite3", "threading", "datetime", "pathlib", "kozgaz_fm.utvonalak"]

import csv
import logging
import sqlite3
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

from kozgaz_fm.utvonalak import adat_mappa

naplo = logging.getLogger(__name__)

IDO = "%Y-%m-%d %H:%M:%S"
KESES_HATAR_MS = 2000
MEGORZES_NAP = 400

SEMA = """
CREATE TABLE IF NOT EXISTS lejatszas (
    id INTEGER PRIMARY KEY,
    kezdet TEXT NOT NULL,
    cim TEXT NOT NULL,
    forras TEXT NOT NULL DEFAULT '',
    kert INTEGER NOT NULL DEFAULT 0,
    hossz_mp REAL
);
CREATE INDEX IF NOT EXISTS lejatszas_kezdet ON lejatszas (kezdet);
CREATE TABLE IF NOT EXISTS csengetes (
    id INTEGER PRIMARY KEY,
    ido TEXT NOT NULL,
    tipus TEXT NOT NULL,
    leiras TEXT NOT NULL DEFAULT '',
    keses_ms INTEGER
);
CREATE INDEX IF NOT EXISTS csengetes_ido ON csengetes (ido);
CREATE TABLE IF NOT EXISTS keres (
    id INTEGER PRIMARY KEY,
    ido TEXT NOT NULL,
    eredmeny TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS keres_ido ON keres (ido);
"""


def _ido(t: datetime) -> str:
    return t.strftime(IDO)


def _hatarok(tol: date, ig: date) -> tuple[str, str]:
    return f"{tol:%Y-%m-%d} 00:00:00", f"{ig + timedelta(days=1):%Y-%m-%d} 00:00:00"


class Statisztika:
    def __init__(self, ut: Path | None = None) -> None:
        self.ut = ut or adat_mappa() / "statisztika.sqlite"
        self.ut.parent.mkdir(parents=True, exist_ok=True)
        self._zar = threading.Lock()
        self._db = sqlite3.connect(self.ut, check_same_thread=False, isolation_level=None)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA busy_timeout=3000")
        self._db.executescript(SEMA)
        self._nyitott: tuple[int, datetime] | None = None

    def bezar(self) -> None:
        self.szam_vege()
        with self._zar:
            self._db.close()

    def _ir(self, sql: str, parameterek: tuple) -> int:
        with self._zar:
            try:
                return self._db.execute(sql, parameterek).lastrowid or 0
            except sqlite3.Error as e:
                naplo.warning("A statisztika nem írható: %s", e)
                return 0

    def szam_kezd(self, cim: str, forras: str = "", kert: bool = False, most: datetime | None = None) -> None:
        most = most or datetime.now()
        self.szam_vege(most)
        azon = self._ir("INSERT INTO lejatszas (kezdet, cim, forras, kert) VALUES (?, ?, ?, ?)",
                        (_ido(most), cim[:300], forras[:120], int(kert)))
        self._nyitott = (azon, most) if azon else None

    @property
    def nyitott(self) -> bool:
        return self._nyitott is not None

    def szam_vege(self, most: datetime | None = None) -> None:
        if self._nyitott is None:
            return
        azon, kezdet = self._nyitott
        self._nyitott = None
        hossz = max(0.0, ((most or datetime.now()) - kezdet).total_seconds())
        self._ir("UPDATE lejatszas SET hossz_mp = ? WHERE id = ?", (round(hossz, 1), azon))

    def csengetes(self, tipus: str, leiras: str = "", tervezett: datetime | None = None,
                  most: datetime | None = None) -> None:
        most = most or datetime.now()
        keses = int((most - tervezett).total_seconds() * 1000) if tervezett else None
        self._ir("INSERT INTO csengetes (ido, tipus, leiras, keses_ms) VALUES (?, ?, ?, ?)",
                 (_ido(most), tipus, leiras[:200], keses))

    def keres(self, eredmeny: str, most: datetime | None = None) -> None:
        self._ir("INSERT INTO keres (ido, eredmeny) VALUES (?, ?)", (_ido(most or datetime.now()), eredmeny))

    def _lekerdez(self, sql: str, parameterek: tuple) -> list[tuple]:
        with self._zar:
            try:
                return self._db.execute(sql, parameterek).fetchall()
            except sqlite3.Error as e:
                naplo.warning("A statisztika nem olvasható: %s", e)
                return []

    def osszegzes(self, tol: date, ig: date, top: int = 10) -> dict:
        a, b = _hatarok(tol, ig)
        zene = self._lekerdez("SELECT COUNT(*), COALESCE(SUM(hossz_mp), 0), COALESCE(SUM(kert), 0) "
                              "FROM lejatszas WHERE kezdet >= ? AND kezdet < ?", (a, b))[0]
        legtobb = self._lekerdez("SELECT cim, COUNT(*) AS db, MAX(kert) FROM lejatszas "
                                 "WHERE kezdet >= ? AND kezdet < ? "
                                 "GROUP BY cim ORDER BY db DESC, MAX(kezdet) DESC LIMIT ?", (a, b, top))
        csengo = self._lekerdez("SELECT COUNT(*), AVG(ABS(keses_ms)), MAX(keses_ms), "
                                "SUM(CASE WHEN keses_ms > ? THEN 1 ELSE 0 END), "
                                "SUM(CASE WHEN tipus = 'kezi' THEN 1 ELSE 0 END) "
                                "FROM csengetes WHERE ido >= ? AND ido < ?", (KESES_HATAR_MS, a, b))[0]
        keresek = dict(self._lekerdez("SELECT eredmeny, COUNT(*) FROM keres WHERE ido >= ? AND ido < ? "
                                      "GROUP BY eredmeny", (a, b)))
        napi_zene = dict(self._lekerdez("SELECT substr(kezdet, 1, 10), COALESCE(SUM(hossz_mp), 0) FROM lejatszas "
                                        "WHERE kezdet >= ? AND kezdet < ? GROUP BY 1", (a, b)))
        napi_csengo = dict(self._lekerdez("SELECT substr(ido, 1, 10), COUNT(*) FROM csengetes "
                                          "WHERE ido >= ? AND ido < ? GROUP BY 1", (a, b)))
        napok = []
        nap = tol
        while nap <= ig:
            kulcs = nap.isoformat()
            napok.append({"nap": kulcs, "zene_perc": round(napi_zene.get(kulcs, 0) / 60),
                          "csengetes": napi_csengo.get(kulcs, 0)})
            nap += timedelta(days=1)
        return {
            "tol": tol.isoformat(), "ig": ig.isoformat(),
            "zene": {"szamok": zene[0], "perc": round(zene[1] / 60), "kert": zene[2]},
            "legtobbet": [{"cim": c, "darab": d, "kert": bool(k)} for c, d, k in legtobb],
            "csengetes": {"darab": csengo[0], "kezi": csengo[4] or 0,
                          "atlag_keses_ms": round(csengo[1]) if csengo[1] is not None else None,
                          "max_keses_ms": csengo[2], "kesett": csengo[3] or 0},
            "keresek": {"erkezett": keresek.get("erkezett", 0), "elfogadva": keresek.get("elfogadva", 0),
                        "elutasitva": keresek.get("elutasitva", 0)},
            "napok": napok,
        }

    def csv_export(self, tol: date, ig: date, fajl: Path) -> int:
        a, b = _hatarok(tol, ig)
        sorok = self._lekerdez("SELECT kezdet, cim, forras, kert, hossz_mp FROM lejatszas "
                               "WHERE kezdet >= ? AND kezdet < ? ORDER BY kezdet", (a, b))
        with open(fajl, "w", encoding="utf-8-sig", newline="") as f:
            iro = csv.writer(f, delimiter=";")
            iro.writerow(["Dátum", "Idő", "Cím", "Forrás", "Kért szám", "Hossz (mp)"])
            for kezdet, cim, forras, kert, hossz in sorok:
                biztos = "'" + cim if cim[:1] in "=+-@\t\r" else cim
                iro.writerow([kezdet[:10], kezdet[11:], biztos, forras, "igen" if kert else "",
                              "" if hossz is None else f"{hossz:.0f}"])
        return len(sorok)

    def takarit(self, nap: int = MEGORZES_NAP, most: datetime | None = None) -> None:
        hatar = _ido((most or datetime.now()) - timedelta(days=nap))
        for tabla, oszlop in (("lejatszas", "kezdet"), ("csengetes", "ido"), ("keres", "ido")):
            self._ir(f"DELETE FROM {tabla} WHERE {oszlop} < ?", (hatar,))
