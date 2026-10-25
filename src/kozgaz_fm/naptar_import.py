__lazy_modules__ = ["re", "urllib.parse", "urllib.request", "dataclasses", "datetime", "kozgaz_fm.beallitasok"]

import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from kozgaz_fm.beallitasok import Beallitasok, Szunnap

MAX_MERET = 2_000_000
MAX_ESEMENY = 3000
MAX_HOSSZ_NAP = 120
LETOLTES_IDOKORLAT = 15

SZUNNAP = "szunnap"
ROVIDITETT = "rovidített"
TANITASI_NAP = "tanitasi_nap"
KIHAGY = "kihagy"
MUVELET_NEV = {
    SZUNNAP: "szünnap (nincs csengetés)",
    ROVIDITETT: "rövidített órák",
    TANITASI_NAP: "tanítási nap (van csengetés)",
    KIHAGY: "nem érinti a csengetést",
}

_BETU = "a-záéíóöőúüű"
_SZUNNAP_MINTA = re.compile(
    rf"tanítás\s*nélküli|tanitas\s*nelkuli|szünet|szunet|szünidő|munkaszüneti|pihenőnap|ünnepnap"
    rf"|ünnep(?![{_BETU}])|igazgatói\s*nap", re.I)
_ROVID_MINTA = re.compile(r"rövidített|rovidített|rovidítet|rövid\s+órá", re.I)
_MUNKANAP_MINTA = re.compile(r"munkanap|tanítási\s*nap|tanitasi\s*nap", re.I)
_TANITASI_JELZO = re.compile(r"(utolsó|első|utolso|elso)\s+tanítási|szünet\s+(előtti|utáni)|szunet\s+(elotti|utani)",
                             re.I)
_NELKULI = re.compile(r"nélküli|nelkuli", re.I)


class ImportHiba(Exception):
    pass


@dataclass
class IcsEsemeny:
    nev: str
    tol: date
    ig: date


@dataclass
class Javaslat:
    esemeny: IcsEsemeny
    muvelet: str
    megjegyzes: str = ""


def _kibont(szoveg: str) -> list[str]:
    darabok: list[list[str]] = []
    for sor in szoveg.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if sor[:1] in (" ", "\t") and darabok:
            darabok[-1].append(sor[1:])
        else:
            darabok.append([sor])
    return ["".join(d) for d in darabok]


def _szoveg(ertek: str) -> str:
    return re.sub(r"\\([\\;,nN])", lambda m: "\n" if m.group(1) in "nN" else m.group(1), ertek).strip()


def _datum(parameterek: str, ertek: str) -> tuple[date, bool]:
    ertek = ertek.strip()
    tipus = parameterek.upper()
    if ("VALUE=DATE" in tipus and "VALUE=DATE-TIME" not in tipus) or len(ertek) == 8:
        return datetime.strptime(ertek[:8], "%Y%m%d").date(), True
    alap = datetime.strptime(ertek[:15], "%Y%m%dT%H%M%S")
    if ertek.endswith("Z"):
        alap = alap.replace(tzinfo=UTC).astimezone()
    return alap.date(), alap.hour == 0 and alap.minute == 0


def ics_beolvas(szoveg: str) -> list[IcsEsemeny]:
    if "BEGIN:VCALENDAR" not in szoveg.upper():
        raise ImportHiba("Ez nem iCalendar (.ics) naptár.")
    esemenyek: list[IcsEsemeny] = []
    akt: dict[str, tuple[str, str]] | None = None
    for sor in _kibont(szoveg):
        felso = sor.upper()
        if felso == "BEGIN:VEVENT":
            akt = {}
            continue
        if felso == "END:VEVENT":
            if akt is not None:
                e = _esemeny(akt)
                if e is not None:
                    esemenyek.append(e)
                    if len(esemenyek) > MAX_ESEMENY:
                        raise ImportHiba("Túl sok esemény van a naptárban.")
            akt = None
            continue
        if akt is None or ":" not in sor:
            continue
        fej, ertek = sor.split(":", 1)
        nev, _, parameterek = fej.partition(";")
        akt.setdefault(nev.upper(), (parameterek, ertek))
    return sorted(esemenyek, key=lambda e: (e.tol, e.ig, e.nev))


def _esemeny(akt: dict[str, tuple[str, str]]) -> IcsEsemeny | None:
    if "DTSTART" not in akt or akt.get("STATUS", ("", ""))[1].strip().upper() == "CANCELLED":
        return None
    try:
        tol, egesz_napos = _datum(*akt["DTSTART"])
        if "DTEND" in akt:
            ig, ejfel = _datum(*akt["DTEND"])
            if (egesz_napos or ejfel) and ig > tol:
                ig -= timedelta(days=1)
        else:
            ig = tol
    except ValueError:
        return None
    if ig < tol:
        ig = tol
    if (ig - tol).days > MAX_HOSSZ_NAP:
        return None
    nev = _szoveg(akt.get("SUMMARY", ("", ""))[1])[:120] or "Névtelen esemény"
    return IcsEsemeny(nev, tol, ig)


def rovid_rend(b: Beallitasok) -> str | None:
    return next((r.nev for r in b.rendek if "rövid" in r.nev.casefold() or "rovid" in r.nev.casefold()), None)


def alap_rend(b: Beallitasok) -> str | None:
    return next((n for n in b.het[:5] if n and b.rend(n)), b.rendek[0].nev if b.rendek else None)


def besorol(e: IcsEsemeny, b: Beallitasok) -> Javaslat:
    if _TANITASI_JELZO.search(e.nev) and not _NELKULI.search(e.nev):
        return Javaslat(e, KIHAGY, "tanítási nap")
    if _SZUNNAP_MINTA.search(e.nev):
        return Javaslat(e, SZUNNAP)
    if _ROVID_MINTA.search(e.nev):
        rend = rovid_rend(b)
        return Javaslat(e, ROVIDITETT, rend or "") if rend else Javaslat(
            e, KIHAGY, "nincs „Rövidített” nevű csengetési rend")
    if _MUNKANAP_MINTA.search(e.nev) and any(n.weekday() >= 5 for n in napok(e)):
        rend = alap_rend(b)
        return Javaslat(e, TANITASI_NAP, rend or "") if rend else Javaslat(e, KIHAGY, "nincs csengetési rend")
    return Javaslat(e, KIHAGY, "rendezvény")


def napok(e: IcsEsemeny) -> list[date]:
    return [e.tol + timedelta(days=i) for i in range((e.ig - e.tol).days + 1)]


def javaslatok(szoveg: str, b: Beallitasok, tol: date | None = None) -> list[Javaslat]:
    tol = tol or date.today() - timedelta(days=1)
    return [besorol(e, b) for e in ics_beolvas(szoveg) if e.ig >= tol]


def alkalmaz(b: Beallitasok, kivalasztott: list[Javaslat]) -> tuple[int, int, int]:
    meglevo = {(s.tol, s.ig) for s in b.szunnapok}
    uj_szunnap = uj_kivetel = megtartott = 0
    for j in kivalasztott:
        e = j.esemeny
        if j.muvelet == SZUNNAP:
            kulcs = (e.tol.isoformat(), e.ig.isoformat())
            if kulcs not in meglevo:
                b.szunnapok.append(Szunnap(*kulcs, e.nev))
                meglevo.add(kulcs)
                uj_szunnap += 1
        elif j.muvelet in (ROVIDITETT, TANITASI_NAP) and j.megjegyzes and b.rend(j.megjegyzes):
            for nap in napok(e):
                kulcs = nap.isoformat()
                if j.muvelet == ROVIDITETT and nap.weekday() >= 5:
                    continue
                if kulcs in b.kivetelek:
                    megtartott += b.kivetelek[kulcs] != j.megjegyzes
                    continue
                b.kivetelek[kulcs] = j.megjegyzes
                uj_kivetel += 1
    b.szunnapok.sort(key=lambda s: s.tol)
    return uj_szunnap, uj_kivetel, megtartott


def letoltes(cim: str) -> str:
    cim = cim.strip()
    if cim.lower().startswith("webcal://"):
        cim = "https://" + cim[9:]
    reszek = urllib.parse.urlsplit(cim)
    if reszek.scheme not in ("http", "https") or not reszek.netloc:
        raise ImportHiba("Csak http(s):// vagy webcal:// naptárlink adható meg.")
    keres = urllib.request.Request(cim, headers={"User-Agent": "KozgazFM", "Accept": "text/calendar, */*"})
    try:
        with urllib.request.urlopen(keres, timeout=LETOLTES_IDOKORLAT) as valasz:
            adat = valasz.read(MAX_MERET + 1)
    except OSError as e:
        raise ImportHiba(f"A naptár nem tölthető le: {e}") from None
    if len(adat) > MAX_MERET:
        raise ImportHiba("A naptár túl nagy (2 MB fölött).")
    return adat.decode("utf-8", "replace")
