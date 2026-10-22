__lazy_modules__ = [
    "hashlib",
    "json",
    "os",
    "re",
    "shutil",
    "subprocess",
    "sys",
    "tarfile",
    "tempfile",
    "urllib.error",
    "urllib.request",
    "dataclasses",
    "datetime",
    "pathlib",
    "kozgaz_fm",
    "kozgaz_fm.utvonalak",
]

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from kozgaz_fm import FRISSITES_REPO, __version__
from kozgaz_fm.utvonalak import gyorsitotar_mappa

API = "https://api.github.com/repos/{repo}/releases/latest"
FEJLEC = {"Accept": "application/vnd.github+json", "User-Agent": f"KozgazFM/{__version__}"}
WINDOWS = sys.platform.startswith("win")


class FrissitesHiba(Exception):
    pass


@dataclass(frozen=True)
class Kiadas:
    verzio: str
    cim: str
    leiras: str
    oldal: str
    eszkozok: dict[str, str] = field(default_factory=dict)
    datum: str = ""

    @property
    def uj(self) -> bool:
        return verzio_kulcs(self.verzio) > verzio_kulcs(__version__)


def verzio_kulcs(verzio: str) -> tuple[int, ...]:
    szamok = re.findall(r"\d+", verzio.split("-")[0].split("+")[0])
    return tuple(int(s) for s in szamok[:4]) or (0,)


def telepitesi_mod() -> str:
    if getattr(sys, "frozen", False):
        return "windows" if WINDOWS else "linux-csomag"
    csomag = Path(__file__).resolve()
    if sys.prefix != sys.base_prefix and "site-packages" in csomag.parts:
        return "venv"
    return "fejlesztoi"


def _get(url: str, idokorlat: float = 20) -> bytes:
    keres = urllib.request.Request(url, headers=FEJLEC)
    try:
        with urllib.request.urlopen(keres, timeout=idokorlat) as v:
            return v.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise FrissitesHiba("Még nincs kiadott verzió a GitHubon.") from e
        if e.code == 403:
            raise FrissitesHiba("A GitHub átmenetileg korlátozza a lekérdezést, később újrapróbálom.") from e
        raise FrissitesHiba(f"GitHub-hiba ({e.code})") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise FrissitesHiba("Nem érhető el a GitHub (nincs internet?).") from e


def legujabb(repo: str = FRISSITES_REPO) -> Kiadas:
    adat = json.loads(_get(API.format(repo=repo)))
    eszkozok = {e["name"]: e["browser_download_url"] for e in adat.get("assets", [])}
    return Kiadas(
        verzio=str(adat.get("tag_name", "")).lstrip("vV"),
        cim=adat.get("name") or adat.get("tag_name", ""),
        leiras=adat.get("body") or "",
        oldal=adat.get("html_url", ""),
        eszkozok=eszkozok,
        datum=str(adat.get("published_at") or "")[:10],
    )


def _arm() -> bool:
    import platform

    return platform.machine().lower() in ("aarch64", "arm64")


def csomag_neve(kiadas: Kiadas, mod: str | None = None) -> str | None:
    mod = mod or telepitesi_mod()
    nevek = list(kiadas.eszkozok)
    if mod == "windows":
        minta = r"^KozgazFM-.*-telepito\.exe$"
    elif mod == "linux-csomag":
        minta = r"^KozgazFM-.*-linux-aarch64\.tar\.gz$" if _arm() else r"^KozgazFM-.*-linux-x86_64\.tar\.gz$"
    elif mod == "venv":
        minta = r"^kozgaz_fm-.*-py3-none-any\.whl$"
    else:
        return None
    return next((n for n in nevek if re.match(minta, n)), None)


def ellenorzo_osszegek(kiadas: Kiadas) -> dict[str, str]:
    url = kiadas.eszkozok.get("SHA256SUMS.txt")
    if not url:
        raise FrissitesHiba("A kiadásból hiányzik az ellenőrzőösszeg-fájl, nem telepítem.")
    osszegek = {}
    for sor in _get(url).decode("utf-8", errors="replace").splitlines():
        reszek = sor.split()
        if len(reszek) == 2:
            osszegek[reszek[1].lstrip("*")] = reszek[0].lower()
    return osszegek


def letoltes(kiadas: Kiadas, nev: str, halado=None) -> Path:
    vart = ellenorzo_osszegek(kiadas).get(nev)
    if not vart:
        raise FrissitesHiba(f"Nincs ellenőrzőösszeg ehhez: {nev}")
    mappa = gyorsitotar_mappa() / "frissites"
    mappa.mkdir(parents=True, exist_ok=True)
    cel = mappa / nev
    if cel.exists() and _sha256(cel) == vart:
        return cel
    ideiglenes = cel.with_suffix(cel.suffix + ".resz")
    keres = urllib.request.Request(kiadas.eszkozok[nev], headers=FEJLEC)
    try:
        with urllib.request.urlopen(keres, timeout=60) as v, ideiglenes.open("wb") as f:
            osszes = int(v.headers.get("Content-Length") or 0)
            kesz = 0
            while darab := v.read(256 * 1024):
                f.write(darab)
                kesz += len(darab)
                if halado and osszes:
                    halado(kesz / osszes)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        ideiglenes.unlink(missing_ok=True)
        raise FrissitesHiba(f"A letöltés megszakadt: {e}") from e
    if _sha256(ideiglenes) != vart:
        ideiglenes.unlink(missing_ok=True)
        raise FrissitesHiba("A letöltött fájl ellenőrzőösszege nem egyezik, nem telepítem.")
    ideiglenes.replace(cel)
    for regi in mappa.iterdir():
        if regi != cel and regi.is_file():
            regi.unlink(missing_ok=True)
    return cel


def _sha256(ut: Path) -> str:
    h = hashlib.sha256()
    with ut.open("rb") as f:
        while darab := f.read(1024 * 1024):
            h.update(darab)
    return h.hexdigest()


def inditasi_argumentumok() -> list[str]:
    return [a for a in sys.argv[1:] if a in ("--talcan", "--kioszk")]


def telepit(csomag: Path, mod: str | None = None) -> list[str] | None:
    mod = mod or telepitesi_mod()
    if mod == "windows":
        app_mappa = Path(sys.executable).resolve().parent
        programfajlok = [os.environ.get(v, "") for v in ("ProgramFiles", "ProgramFiles(x86)")]
        mindenkinek = any(p and str(app_mappa).lower().startswith(p.lower()) for p in programfajlok)
        parameterek = [str(csomag), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS",
                       "/ALLUSERS" if mindenkinek else "/CURRENTUSER"]
        jelzok = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        subprocess.Popen(parameterek, creationflags=jelzok, close_fds=True)
        return None
    if mod == "linux-csomag":
        with tempfile.TemporaryDirectory() as tmp:
            with tarfile.open(csomag) as tar:
                tar.extractall(tmp, filter="data")
            telepito = next(Path(tmp).glob("*/telepites.sh"), None)
            if telepito is None:
                raise FrissitesHiba("A csomagban nincs telepítő.")
            eredmeny = subprocess.run(["bash", str(telepito)], capture_output=True, text=True, timeout=300)
            if eredmeny.returncode != 0:
                raise FrissitesHiba(f"A telepítés nem sikerült: {eredmeny.stderr.strip()[-300:]}")
        uj = shutil.which("kozgaz-fm") or str(Path.home() / ".local" / "bin" / "kozgaz-fm")
        return [uj, *inditasi_argumentumok()]
    if mod == "venv":
        eredmeny = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "--no-input", str(csomag)],
                                  capture_output=True, text=True, timeout=900)
        if eredmeny.returncode != 0:
            raise FrissitesHiba(f"A pip-telepítés nem sikerült: {eredmeny.stderr.strip()[-300:]}")
        return [sys.executable, "-m", "kozgaz_fm", *inditasi_argumentumok()]
    raise FrissitesHiba("Fejlesztői futtatásnál nincs automatikus frissítés (git pull).")


def ujraindit(parancs: list[str]) -> None:
    os.execv(parancs[0], parancs)


def biztonsagos_ido(szakasz: str, kovetkezo: datetime | None, most: datetime, zene_szol: bool,
                    riasztas: bool) -> bool:
    if riasztas or zene_szol:
        return False
    if szakasz not in ("tanítás után", "szünnap", "nincs csengetés"):
        return False
    return kovetkezo is None or kovetkezo - most > timedelta(minutes=45)
