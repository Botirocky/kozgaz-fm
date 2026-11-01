__lazy_modules__ = [
    "html.parser",
    "json",
    "re",
    "urllib.request",
    "dataclasses",
    "datetime",
    "kozgaz_fm.beallitasok",
    "kozgaz_fm.naptar_import",
]

import json
import re
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from html.parser import HTMLParser

from kozgaz_fm.beallitasok import Beallitasok, Csengetesirend, Ora
from kozgaz_fm.naptar_import import MAX_MERET, SZUNNAP, IcsEsemeny, ImportHiba, besorol, napok

ALAP_CIM = "https://kghsz.hu"
OLDAL_CSENGETES = "/rolunk/nyitvatartas"
OLDAL_HAZIREND = "/szakmai-dokumentumok/hazirend"
OLDAL_TANEV = "/tanuloinknak/tanev-rendje"
OLDAL_ESEMENYEK = "/tanuloinknak/esemenyek"
IDOKORLAT = 20

HONAPOK = {
    "január": 1, "február": 2, "március": 3, "április": 4, "május": 5, "június": 6,
    "július": 7, "augusztus": 8, "szeptember": 9, "október": 10, "november": 11, "december": 12,
}
_DATUM = r"(\d{4})\.\s*(" + "|".join(HONAPOK) + r")\s+(\d{1,2})\."
_ORA_SOR = re.compile(r"(\d{1,2})\.(?:\s*óra)?\s*\|\s*(\d{1,2}:\d{2})\s*(?:-|–|\|)\s*(\d{1,2}:\d{2})")
_NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


@dataclass
class IskolaiAdatok:
    normal: list[Ora]
    rovid: list[Ora] | None
    esemenyek: list[IcsEsemeny]


class _Tablazat(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sorok: list[str] = []
        self._cellak: list[str] | None = None
        self._cella: list[str] | None = None
        self._kint: list[str] = []

    def _kint_lezar(self) -> None:
        szoveg = _tiszta("".join(self._kint))
        if szoveg:
            self.sorok.append(szoveg)
        self._kint = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "tr":
            self._kint_lezar()
            self._cellak = []
        elif tag in ("td", "th"):
            self._cella = []
        elif tag in ("p", "br", "div", "li") and self._cella is not None:
            self._cella.append(" ")
        elif tag in ("p", "br", "div", "li", "h1", "h2", "h3", "h4", "table"):
            self._kint_lezar()

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._cella is not None:
            if self._cellak is not None:
                self._cellak.append(_tiszta("".join(self._cella)))
            self._cella = None
        elif tag == "tr" and self._cellak is not None:
            sor = " | ".join(c for c in self._cellak if c)
            if sor:
                self.sorok.append(sor)
            self._cellak = None
        elif tag in ("p", "div", "li", "h1", "h2", "h3", "h4", "table") and self._cella is None:
            self._kint_lezar()

    def handle_data(self, data: str) -> None:
        if self._cella is not None:
            self._cella.append(data)
        else:
            self._kint.append(data)

    def close(self) -> None:
        super().close()
        self._kint_lezar()


def _tiszta(szoveg: str) -> str:
    return re.sub(r"\s+", " ", szoveg.replace("\xa0", " ")).strip()


def sorok(html: str) -> list[str]:
    elemzo = _Tablazat()
    elemzo.feed(html)
    elemzo.close()
    return elemzo.sorok


def oldal_adat(html: str) -> dict:
    talalat = _NEXT_DATA.search(html)
    if not talalat:
        raise ImportHiba("Az iskola honlapjának szerkezete megváltozott (nincs adatblokk).")
    try:
        adat = json.loads(talalat.group(1))["props"]["pageProps"]
    except (ValueError, KeyError, TypeError):
        raise ImportHiba("Az iskola honlapjának adatai nem értelmezhetők.") from None
    if not isinstance(adat, dict):
        raise ImportHiba("Az iskola honlapjának adatai nem értelmezhetők.")
    return adat


def _ido(szoveg: str) -> str:
    ora, perc = szoveg.split(":")
    return f"{int(ora):02d}:{perc}"


def _ervenyes_orak(orak: list[Ora]) -> bool:
    if not orak:
        return False
    idopontok = [i for o in orak for i in (o.kezdet, o.vege)]
    return all(re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", i) for i in idopontok) and idopontok == sorted(idopontok)


def orak_sorokbol(sorlista: list[str]) -> list[Ora]:
    talalatok = (_ORA_SOR.search(s) for s in sorlista)
    orak = [(int(t.group(1)), Ora(_ido(t.group(2)), _ido(t.group(3)))) for t in talalatok if t]
    return [o for _, o in sorted(orak, key=lambda p: p[0])]


def csengetesi_rend(csengetes_html: str, hazirend_html: str | None) -> tuple[list[Ora], list[Ora] | None]:
    adat = oldal_adat(csengetes_html).get("data") or {}
    normal = orak_sorokbol(sorok(adat.get("ringNormal") or ""))
    rovid = orak_sorokbol(sorok(adat.get("ringShort") or ""))
    valodi_rovid = rovid if _ervenyes_orak(rovid) and rovid != normal else None
    if hazirend_html:
        szoveg = (oldal_adat(hazirend_html).get("data") or {}).get("info") or ""
        reszlet = sorok(szoveg)
        kezdet = next((i for i, s in enumerate(reszlet) if "Csengetési órarend" in s and "|" not in s), None)
        if kezdet is not None:
            hazirendi = orak_sorokbol(_egymas_utan(reszlet[kezdet + 1:kezdet + 16]))
            if _ervenyes_orak(hazirendi):
                normal = hazirendi
    if not _ervenyes_orak(normal):
        raise ImportHiba("A csengetési rend nem olvasható ki az iskola honlapjáról.")
    return normal, valodi_rovid


def _egymas_utan(sorlista: list[str]) -> list[str]:
    return [s for s in sorlista if _ORA_SOR.search(s)]


def _datum(talalat: re.Match) -> date:
    return date(int(talalat.group(1)), HONAPOK[talalat.group(2)], int(talalat.group(3)))


def tanev_esemenyek(html: str) -> list[IcsEsemeny]:
    adat = oldal_adat(html).get("data") or {}
    sorlista = sorok(adat.get("currentInfo") or "")
    esemenyek: list[IcsEsemeny] = []
    szunet: str | None = None
    szakasz = ""
    for sor in sorlista:
        nev = re.match(r"(Őszi|Téli|Tavaszi) szünet\b", sor)
        if nev:
            szunet = nev.group(0)
            continue
        if sor.startswith("Tanításmentes munkanapok"):
            szakasz = "mentes"
            continue
        if sor.startswith("Érettségi vizsganapok"):
            szakasz = ""
            continue
        elozo = re.search(r"előtti utolsó tanítási nap\s+" + _DATUM, sor)
        utani = re.search(r"utáni első tanítási nap\s+" + _DATUM, sor)
        if szunet and elozo and utani:
            tol = _datum(elozo) + timedelta(days=1)
            ig = _datum(utani) - timedelta(days=1)
            if tol <= ig <= tol + timedelta(days=60):
                esemenyek.append(IcsEsemeny(szunet, tol, ig))
            szunet = None
            continue
        utolso = re.match(r"Utolsó tanítási nap\s*\|\s*" + _DATUM, sor)
        if utolso:
            nap = _datum(utolso)
            vege = date(nap.year, 8, 31)
            if nap < vege:
                esemenyek.append(IcsEsemeny("Nyári szünet", nap + timedelta(days=1), vege))
            continue
        if szakasz == "mentes":
            mentes = re.match(r"\d+\.\s*\|\s*" + _DATUM + r"\s*\|\s*(.+)", sor)
            if mentes:
                nap = _datum(mentes)
                esemenyek.append(IcsEsemeny(f"Tanításmentes munkanap: {mentes.group(4)}", nap, nap))
    if not any(e.nev.endswith("szünet") for e in esemenyek):
        raise ImportHiba("A tanév rendje nem olvasható ki az iskola honlapjáról.")
    return esemenyek


def _helyi_nap(ertek: str) -> date:
    return datetime.fromisoformat(ertek.replace("Z", "+00:00")).astimezone().date()


def honlapi_esemenyek(html: str, tol: date) -> list[IcsEsemeny]:
    lista = oldal_adat(html).get("events")
    if not isinstance(lista, list):
        raise ImportHiba("Az iskola eseménynaptára nem értelmezhető.")
    esemenyek: list[IcsEsemeny] = []
    for e in lista:
        try:
            kezdet = _helyi_nap(e["startDate"])
            veg = _helyi_nap(e["endDate"]) if e.get("endDate") else kezdet
            nev = _tiszta(str(e["title"]))[:120]
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if nev and kezdet <= veg <= kezdet + timedelta(days=120) and veg >= tol:
            esemenyek.append(IcsEsemeny(nev, kezdet, veg))
    return esemenyek


def osszevon(tanev: list[IcsEsemeny], honlapi: list[IcsEsemeny], b: Beallitasok) -> list[IcsEsemeny]:
    foglalt = {n for e in tanev for n in napok(e)}
    pluszok = [e for e in honlapi if not (besorol(e, b).muvelet == SZUNNAP and foglalt.intersection(napok(e)))]
    return sorted(tanev + pluszok, key=lambda e: (e.tol, e.ig, e.nev))


def _letolt(oldal: str) -> str:
    keres = urllib.request.Request(ALAP_CIM + oldal, headers={"User-Agent": "Mozilla/5.0 (KozgazFM)"})
    try:
        with urllib.request.urlopen(keres, timeout=IDOKORLAT) as valasz:
            adat = valasz.read(MAX_MERET + 1)
    except OSError as e:
        raise ImportHiba(f"Az iskola honlapja nem érhető el: {e}") from None
    if len(adat) > MAX_MERET:
        raise ImportHiba("Az iskola honlapjának oldala túl nagy.")
    return adat.decode("utf-8", "replace")


def letoltes(b: Beallitasok, ma: date | None = None) -> IskolaiAdatok:
    ma = ma or date.today()
    try:
        hazirend = _letolt(OLDAL_HAZIREND)
    except ImportHiba:
        hazirend = None
    normal, rovid = csengetesi_rend(_letolt(OLDAL_CSENGETES), hazirend)
    tanev = tanev_esemenyek(_letolt(OLDAL_TANEV))
    try:
        honlapi = honlapi_esemenyek(_letolt(OLDAL_ESEMENYEK), ma)
    except ImportHiba:
        honlapi = []
    return IskolaiAdatok(normal, rovid, osszevon(tanev, honlapi, b))


def orak_szoveg(orak: list[Ora]) -> str:
    return f"{len(orak)} óra, {orak[0].kezdet}–{orak[-1].vege}" if orak else "nincs megadva"


def rend_atvetel(b: Beallitasok, adatok: IskolaiAdatok) -> list[str]:
    valtozott: list[str] = []
    for nev, orak in (("Normál", adatok.normal), ("Rövidített", adatok.rovid)):
        if orak is None:
            continue
        rend = b.rend(nev)
        if rend is None or rend.orak != orak:
            valtozott.append(nev)
    return valtozott


def rend_alkalmaz(b: Beallitasok, adatok: IskolaiAdatok) -> list[str]:
    valtozott = rend_atvetel(b, adatok)
    for nev, orak in (("Normál", adatok.normal), ("Rövidített", adatok.rovid)):
        if orak is None or nev not in valtozott:
            continue
        rend = b.rend(nev)
        if rend is None:
            b.rendek.append(Csengetesirend(nev, list(orak)))
        else:
            rend.orak = list(orak)
    return valtozott
