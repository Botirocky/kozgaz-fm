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

ALAP_SABLONOK = [
    "Kedves Diákok! Felhívjuk figyelmeteket, hogy a mai napon rövidített órák lesznek.",
    "Figyelem! Az osztályfőnöki órák után rendkívüli diákközgyűlést tartunk az aulában.",
    "Kedves Diákok és Tanárok! A tanítás vége után a tornateremben kezdődik a ballagási próba.",
    "Kérjük az ügyeletes diákokat, hogy jelentkezzenek a titkárságon.",
]

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
class Rendkivuli:
    nev: str
    datum: str
    tol: str
    tipus: str = "csengetes"
    ig: str = ""
    hang: str = "beepitett:csengo"
    riado_perc: int = 3
    csengo_hangero: int = 0
    aktiv: bool = True


RENDKIVULI_TIPUSOK = {
    "csengetes": "Rendkívüli csengetés",
    "riado": "Tűzriadó-gyakorlat",
    "csend": "Csendes időszak",
}


@dataclass
class TiltottSzam:
    azon: str
    cim: str
    yt: str = ""
    ido: str = ""


@dataclass
class TiltottTelefon:
    kulcs: str
    nev: str = ""
    ig: str = ""


@dataclass
class Zona:
    nev: str
    kimenet: str = ""
    csengo: bool = True
    zene: bool = True
    bemondas: bool = True
    hangero: int = 100


@dataclass
class ZeneForras:
    tipus: str
    nev: str
    cim: str
    aktiv: bool = True


@dataclass
class Musorblokk:
    nev: str
    forras: str
    napok: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    szunetek: list[int] = field(default_factory=list)
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
    zene_kihagyott_szunetek: list[int] = field(default_factory=list)
    forrasok: list[ZeneForras] = field(default_factory=list)
    aktiv_forras: int = 0
    keveres: bool = True
    youtube_gyorsitotar: bool = True
    hangero_kiegyenlites: bool = True
    musorblokkok: list[Musorblokk] = field(default_factory=list)
    szuro_alap: bool = True
    szuro_korhataros: bool = True
    szuro_szavak: list[str] = field(default_factory=list)
    szuro_dalszoveg: bool = True
    szuro_erzekenyseg: str = "normal"
    bemondasok: list[Bemondas] = field(default_factory=list)
    rendkivuli: list[Rendkivuli] = field(default_factory=list)
    bemondas_sablonok: list[str] = field(default_factory=lambda: list(ALAP_SABLONOK))
    spotify_client_id: str = ""
    spotify_eszkoz: str = ""
    tts_hang: str = ""
    kimenet: str = ""
    zonak: list[Zona] = field(default_factory=list)
    talcara_zar: bool = True
    automatikus_inditas: bool = False
    admin_pin: str = ""
    tema: str = "vilagos"
    admin_zar_perc: int = 5
    web_panel: bool = False
    web_port: int = 8080
    web_jelszo: str = ""
    zenekeres: bool = False
    zenekeres_auto: bool = True
    zenekeres_napi: int = 3
    zenekeres_max_perc: int = 7
    zenekeres_tiltott: list[str] = field(default_factory=list)
    zenekeres_szerver: str = ""
    zenekeres_szerver_kulcs: str = ""
    zenekeres_oldal: str = ""
    zenekeres_mp3: bool = True
    zenekeres_mp3_mappa: str = ""
    zene_szinkron: bool = False
    zene_szinkron_mappa: str = ""
    zene_szinkron_kbps: int = 0
    tiltott_szamok: list[TiltottSzam] = field(default_factory=list)
    tiltott_telefonok: list[TiltottTelefon] = field(default_factory=list)
    tartalek_mod: str = ""
    tartalek_cim: str = ""
    tartalek_kulcs: str = ""
    kijelzo_cim: str = "Közgáz FM"
    ertesites_ntfy: str = ""
    ertesites_ntfy_token: str = ""
    ertesites_email: str = ""
    smtp_szerver: str = ""
    smtp_port: int = 587
    smtp_mod: str = "starttls"
    smtp_felhasznalo: str = ""
    smtp_jelszo: str = ""
    smtp_felado: str = ""
    ertesites_esemenyek: list[str] = field(default_factory=lambda: [
        "kimaradt", "hiba", "hangkimenet", "riasztas", "tartalek", "indulas", "reggel"])
    ertesites_reggel_ido: str = "07:15"
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
                return _riado_vissza(_ebbol(cls, adat := json.loads(jelolt.read_text(encoding="utf-8"))), adat)
            except FileNotFoundError:
                continue
            except (json.JSONDecodeError, TypeError, ValueError) as hiba:
                naplo.warning("Hibás beállításfájl (%s): %s", jelolt, hiba)
        return alapertelmezett()


def _riado_vissza(b: "Beallitasok", adat: dict) -> "Beallitasok":
    if isinstance(adat, dict) and "hang_riasztas" not in adat and "riasztas" not in b.ertesites_esemenyek:
        b.ertesites_esemenyek.append("riasztas")
    return b


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
        ("07:30", "08:15"), ("08:25", "09:10"), ("09:25", "10:10"), ("10:20", "11:05"), ("11:20", "12:05"),
        ("12:15", "13:00"), ("13:20", "14:05"), ("14:15", "15:00"), ("15:10", "15:55"),
    ))
    rovid = Csengetesirend("Rövidített", ora_lista(
        ("07:30", "08:00"), ("08:10", "08:40"), ("08:50", "09:20"), ("09:30", "10:00"),
        ("10:10", "10:40"), ("10:50", "11:20"), ("11:30", "12:00"), ("12:05", "12:35"),
    ))
    szunnapok = [
        Szunnap("2026-11-30", "2026-11-30", "Tanításmentes munkanap: Pályaorientációs nap"),
        Szunnap("2026-12-12", "2026-12-12", "Tanításmentes munkanap: Nevelési értekezlet"),
        Szunnap("2026-12-19", "2027-01-03", "Téli szünet"),
        Szunnap("2027-03-24", "2027-03-24", "Tanításmentes munkanap: Diákönkormányzati nap"),
        Szunnap("2027-03-25", "2027-04-04", "Tavaszi szünet"),
        Szunnap("2027-04-30", "2027-04-30", "Tanításmentes munkanap: Ballagás"),
        Szunnap("2027-06-16", "2027-08-31", "Nyári szünet"),
    ]
    return Beallitasok(rendek=[normal, rovid], szunnapok=szunnapok)
