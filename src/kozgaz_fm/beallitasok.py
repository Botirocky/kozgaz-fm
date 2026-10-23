__lazy_modules__ = ["json", "logging", "os", "types", "typing", "dataclasses", "pathlib", "kozgaz_fm.utvonalak"]

import json
import logging
import os
import types
import typing
from dataclasses import MISSING, asdict, dataclass, field, fields
from pathlib import Path

from kozgaz_fm.utvonalak import beallitas_fajl

naplo = logging.getLogger(__name__)

BEEPITETT_HANGOK = {
    "csengo": "Klasszikus csengő",
    "rovid": "Rövid csengő",
    "dallam": "Dallamos csengő",
    "gong": "Gong",
    "riasztas": "Riasztás",
}

NAPOK = ["Hétfő", "Kedd", "Szerda", "Csütörtök", "Péntek", "Szombat", "Vasárnap"]


@dataclass
class Ora:
    kezdet: str
    vege: str


@dataclass
class Csengetesirend:
    nev: str
    orak: list[Ora] = field(default_factory=list)


@dataclass
class Szunnap:
    tol: str
    ig: str
    nev: str = ""


@dataclass
class Bemondas:
    nev: str
    ido: str
    napok: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    datum: str = ""
    tipus: str = "szoveg"
    tartalom: str = ""
    gong: bool = True
    aktiv: bool = True


@dataclass
class ZeneForras:
    tipus: str
    nev: str
    cim: str
    aktiv: bool = True


@dataclass
class Beallitasok:
    rendek: list[Csengetesirend] = field(default_factory=list)
    het: list[str] = field(default_factory=lambda: ["Normál"] * 5 + ["", ""])
    kivetelek: dict[str, str] = field(default_factory=dict)
    szunnapok: list[Szunnap] = field(default_factory=list)
    jelzo: bool = True
    jelzo_perc: int = 2
    kicsengo: bool = True
    hang_becsengo: str = "beepitett:csengo"
    hang_kicsengo: str = "beepitett:csengo"
    hang_jelzo: str = "beepitett:rovid"
    hang_gong: str = "beepitett:gong"
    hang_riasztas: str = "beepitett:riasztas"
    csengo_hangero: int = 90
    zene_hangero: int = 60
    zene_szunetben: bool = True
    zene_min_szunet: int = 5
    zene_kesleltetes: int = 10
    zene_leall_elotte: int = 20
    elhalkitas: float = 3.0
    atusztatas: float = 4.0
    reggeli_zene: bool = False
    reggeli_zene_tol: str = "07:30"
    forrasok: list[ZeneForras] = field(default_factory=list)
    aktiv_forras: int = 0
    keveres: bool = True
    youtube_gyorsitotar: bool = True
    bemondasok: list[Bemondas] = field(default_factory=list)
    spotify_client_id: str = ""
    spotify_eszkoz: str = ""
    tts_hang: str = ""
    kimenet: str = ""
    talcara_zar: bool = True
    automatikus_inditas: bool = False
    admin_pin: str = ""
    tema: str = "vilagos"
    admin_zar_perc: int = 5
    web_panel: bool = False
    web_port: int = 8080
    web_jelszo: str = ""
    kijelzo_cim: str = "Közgáz FM"
    frissites_kereses: bool = True
    frissites_auto: bool = True
    ma_nincs_csengetes: str = ""
    ma_nincs_zene: str = ""

    def rend(self, nev: str) -> Csengetesirend | None:
        return next((r for r in self.rendek if r.nev == nev), None)

    def mentes(self, ut: Path | None = None) -> None:
        ut = ut or beallitas_fajl()
        ideiglenes = ut.with_suffix(".tmp")
        with ideiglenes.open("w", encoding="utf-8") as f:
            f.write(json.dumps(asdict(self), ensure_ascii=False, indent=2))
            f.flush()
            os.fsync(f.fileno())
        if ut.exists():
            ut.replace(ut.with_suffix(".bak"))
        ideiglenes.replace(ut)

    @classmethod
    def betoltes(cls, ut: Path | None = None) -> "Beallitasok":
        ut = ut or beallitas_fajl()
        for jelolt in (ut, ut.with_suffix(".bak")):
            try:
                return _ebbol(cls, json.loads(jelolt.read_text(encoding="utf-8")))
            except FileNotFoundError:
                continue
            except (json.JSONDecodeError, TypeError, ValueError) as hiba:
                naplo.warning("Hibás beállításfájl (%s): %s", jelolt, hiba)
        return alapertelmezett()


def _ertek(tipus, adat):
    eredeti = typing.get_origin(tipus)
    if eredeti in (typing.Union, types.UnionType):
        valodi = [t for t in typing.get_args(tipus) if t is not type(None)]
        return None if adat is None else _ertek(valodi[0], adat)
    if eredeti is list:
        (elem,) = typing.get_args(tipus)
        return [_ertek(elem, e) for e in adat]
    if eredeti is dict:
        _, ertek_tipus = typing.get_args(tipus)
        return {str(k): _ertek(ertek_tipus, v) for k, v in adat.items()}
    if isinstance(tipus, type) and hasattr(tipus, "__dataclass_fields__"):
        return _ebbol(tipus, adat)
    if tipus is float and isinstance(adat, int):
        return float(adat)
    if isinstance(tipus, type) and not isinstance(adat, tipus):
        raise TypeError(f"{tipus.__name__} kellene, ez jött: {adat!r}")
    return adat


def _ebbol(cls, adat: dict):
    if not isinstance(adat, dict):
        raise TypeError(f"{cls.__name__}: objektum kellene")
    tipusok = typing.get_type_hints(cls)
    kwargs = {}
    for mezo in fields(cls):
        if mezo.name in adat:
            kwargs[mezo.name] = _ertek(tipusok[mezo.name], adat[mezo.name])
        elif mezo.default is MISSING and mezo.default_factory is MISSING:
            raise ValueError(f"{cls.__name__}: hiányzik a(z) {mezo.name} mező")
    return cls(**kwargs)


def ora_lista(*parok: tuple[str, str]) -> list[Ora]:
    return [Ora(k, v) for k, v in parok]


def alapertelmezett() -> Beallitasok:
    normal = Csengetesirend("Normál", ora_lista(
        ("08:00", "08:45"), ("08:55", "09:40"), ("09:50", "10:35"), ("10:50", "11:35"),
        ("11:45", "12:30"), ("12:40", "13:25"), ("13:35", "14:20"), ("14:25", "15:10"),
    ))
    rovid = Csengetesirend("Rövidített", ora_lista(
        ("08:00", "08:30"), ("08:40", "09:10"), ("09:20", "09:50"), ("10:00", "10:30"),
        ("10:40", "11:10"), ("11:20", "11:50"), ("12:00", "12:30"), ("12:35", "13:05"),
    ))
    return Beallitasok(rendek=[normal, rovid])
