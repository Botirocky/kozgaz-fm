__lazy_modules__ = [
    "json",
    "logging",
    "re",
    "smtplib",
    "socket",
    "ssl",
    "threading",
    "time",
    "urllib.error",
    "urllib.parse",
    "urllib.request",
    "collections.abc",
    "typing",
    "datetime",
    "email.message",
    "email.utils",
    "kozgaz_fm",
]

import json
import logging
import re
import smtplib
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from typing import Any

from kozgaz_fm import hatter

naplo = logging.getLogger(__name__)

ESEMENYEK = {
    "kimaradt": "Kimaradt csengetés (pl. alvás vagy óraugrás után)",
    "hiba": "Hibák: hiányzó hangfájl, zenehiba, nincs felolvasó hang",
    "hangkimenet": "Eltűnt vagy nem elérhető hangkimenet",
    "riasztas": "Riasztás indult",
    "tartalek": "A tartalékgép átvette vagy visszaadta a csengetést",
    "indulas": "A program elindult (pl. összeomlás vagy áramszünet után)",
    "reggel": "Reggeli önteszt tanítási napokon",
}
SMTP_MODOK = {"starttls": "STARTTLS (587)", "ssl": "SSL/TLS (465)", "nincs": "Titkosítás nélkül (csak belső hálón)"}
ISMETLES_MP = 30 * 60
IDOKORLAT_MP = 15
_TOPIC = re.compile(r"^[-_A-Za-z0-9]{1,64}$")
_PRIORITAS = {"info": 3, "figy": 4, "hiba": 5}
_CIMKE = {"info": "white_check_mark", "figy": "warning", "hiba": "rotating_light"}


class ErtesitesHiba(Exception):
    pass


def ntfy_cel(url: str) -> tuple[str, str]:
    reszek = urllib.parse.urlsplit(url.strip())
    if reszek.scheme not in ("http", "https") or not reszek.netloc:
        raise ErtesitesHiba("Az ntfy-cím http:// vagy https:// kezdetű legyen, pl. https://ntfy.sh/kozgaz-fm-xyz")
    utvonal = [r for r in reszek.path.split("/") if r]
    if not utvonal or not _TOPIC.fullmatch(utvonal[-1]):
        raise ErtesitesHiba("Az ntfy-cím végén a téma (topic) neve legyen: betű, szám, - vagy _.")
    alap = urllib.parse.urlunsplit((reszek.scheme, reszek.netloc, "/" + "/".join(utvonal[:-1]), "", ""))
    return alap, utvonal[-1]


def ntfy_kuld(url: str, token: str, cim: str, uzenet: str, szint: str = "figy") -> None:
    alap, tema = ntfy_cel(url)
    torzs = json.dumps({"topic": tema, "title": cim[:250], "message": uzenet[:3500],
                        "priority": _PRIORITAS.get(szint, 3), "tags": [_CIMKE.get(szint, "bell")]},
                       ensure_ascii=False).encode()
    fejlec = {"Content-Type": "application/json", "User-Agent": "KozgazFM"}
    if token.strip():
        fejlec["Authorization"] = f"Bearer {token.strip()}"
    keres = urllib.request.Request(alap, data=torzs, headers=fejlec, method="POST")
    try:
        with urllib.request.urlopen(keres, timeout=IDOKORLAT_MP) as valasz:
            valasz.read(10_000)
    except urllib.error.HTTPError as e:
        raise ErtesitesHiba(f"Az ntfy-szerver {e.code}-as hibát adott"
                            + (" (hibás vagy hiányzó token?)" if e.code in (401, 403) else "") + ".") from None
    except OSError as e:
        raise ErtesitesHiba(f"Az ntfy-szerver nem érhető el: {e}") from None


def cimzettek(szoveg: str) -> list[str]:
    return [c.strip() for c in re.split(r"[,;\s]+", szoveg) if "@" in c]


def email_kuld(b, cim: str, uzenet: str) -> None:
    lista = cimzettek(b.ertesites_email)
    if not lista or not b.smtp_szerver.strip():
        raise ErtesitesHiba("Add meg a címzettet és az SMTP-szervert.")
    level = EmailMessage()
    level["Subject"] = f"Közgáz FM: {cim}"
    level["From"] = b.smtp_felado.strip() or b.smtp_felhasznalo.strip() or lista[0]
    level["To"] = ", ".join(lista)
    level["Date"] = formatdate(localtime=True)
    level["Message-ID"] = make_msgid(domain="kozgaz-fm")
    level.set_content(uzenet)
    kornyezet = ssl.create_default_context()
    try:
        if b.smtp_mod == "ssl":
            kapcsolat = smtplib.SMTP_SSL(b.smtp_szerver.strip(), b.smtp_port, timeout=IDOKORLAT_MP,
                                         context=kornyezet)
        else:
            kapcsolat = smtplib.SMTP(b.smtp_szerver.strip(), b.smtp_port, timeout=IDOKORLAT_MP)
        with kapcsolat:
            if b.smtp_mod == "starttls":
                kapcsolat.starttls(context=kornyezet)
            if b.smtp_felhasznalo.strip():
                kapcsolat.login(b.smtp_felhasznalo.strip(), b.smtp_jelszo)
            kapcsolat.send_message(level)
    except smtplib.SMTPAuthenticationError:
        raise ErtesitesHiba("Az SMTP-szerver nem fogadta el a felhasználónevet vagy a jelszót.") from None
    except (smtplib.SMTPException, OSError) as e:
        raise ErtesitesHiba(f"Az e-mail nem ment el: {e}") from None


def csatornak(b) -> list[str]:
    lista = []
    if b.ertesites_ntfy.strip():
        lista.append("ntfy")
    if b.ertesites_email.strip() and b.smtp_szerver.strip():
        lista.append("e-mail")
    return lista


def _probal(nev: str, fv: Callable[[], None], hibak: list[str]) -> None:
    try:
        fv()
    except ErtesitesHiba as e:
        hibak.append(f"{nev}: {e}")
    except UnicodeError:
        hibak.append(f"{nev}: a jelszó vagy a token csak ékezet nélküli karaktereket tartalmazhat.")
    except Exception as e:
        naplo.exception("Váratlan hiba az értesítés küldésekor")
        hibak.append(f"{nev}: váratlan hiba ({e.__class__.__name__}: {e})")


def kikuld(b, cim: str, uzenet: str, szint: str) -> list[str]:
    hibak: list[str] = []
    teljes = f"{uzenet}\n\n– {socket.gethostname()}, {datetime.now():%Y.%m.%d. %H:%M}"
    if b.ertesites_ntfy.strip():
        _probal("ntfy", lambda: ntfy_kuld(b.ertesites_ntfy, b.ertesites_ntfy_token, cim, teljes, szint), hibak)
    if b.ertesites_email.strip() and b.smtp_szerver.strip():
        _probal("e-mail", lambda: email_kuld(b, cim, teljes), hibak)
    return hibak


class Ertesito:
    def __init__(self, beallitasok: Callable[[], Any], naplo_fv: Callable[[str], None] | None = None,
                 futtato: Callable = hatter.futtat) -> None:
        self._b = beallitasok
        self._naplo = naplo_fv or (lambda _s: None)
        self._futtato = futtato
        self._legutobb: dict[tuple[str, str], float] = {}
        self._zar = threading.Lock()

    def bekapcsolt(self, esemeny: str) -> bool:
        b = self._b()
        return bool(csatornak(b)) and esemeny in b.ertesites_esemenyek

    def kuld(self, esemeny: str, cim: str, uzenet: str, szint: str = "figy", ismetles_mp: float = ISMETLES_MP,
             kulcs_szoveg: str | None = None) -> bool:
        if not self.bekapcsolt(esemeny):
            return False
        kulcs = (esemeny, kulcs_szoveg or f"{cim}\n{uzenet}")
        most = time.monotonic()
        with self._zar:
            if most - self._legutobb.get(kulcs, -1e9) < ismetles_mp:
                return False
            self._legutobb[kulcs] = most
            self._legutobb = {k: v for k, v in self._legutobb.items() if most - v < ISMETLES_MP * 4}
        b = self._b()
        self._futtato(lambda: kikuld(b, cim, uzenet, szint), self._eredmeny,
                      lambda e: self._eredmeny([f"váratlan hiba: {e}"]))
        return True

    def _eredmeny(self, hibak: list[str]) -> None:
        for hiba in hibak:
            self._naplo(f"Értesítés nem ment el – {hiba}")

    def proba(self, kesz: Callable[[list[str]], None]) -> None:
        b = self._b()
        if not csatornak(b):
            kesz(["Nincs beállítva sem ntfy-cím, sem e-mail."])
            return
        self._futtato(lambda: kikuld(b, "Próbaértesítés", "Ha ezt látod, a Közgáz FM értesítései működnek.",
                                     "info"), kesz, lambda e: kesz([f"Váratlan hiba: {e}"]))


def kimaradt_csengetesek(esemenyek, elozo: datetime, most: datetime, csengo_tipusok) -> list:
    if most <= elozo or most - elozo > timedelta(hours=36):
        return []
    return [e for e in esemenyek if elozo < e.ido <= most and e.tipus in csengo_tipusok]


def reggeli_jelentes(*, nap: date, rend: str | None, elso: datetime | None, csengetesek: int,
                     kimenet: str | None, forras: str | None, szamok: int, tegnap: dict | None,
                     hibak: int, uj_verzio: str | None, szabad_gb: float | None) -> tuple[str, str, str]:
    gondok = []
    sorok = []
    if rend is None:
        sorok.append("Ma nincs csengetés.")
    else:
        sorok.append(f"Mai rend: {rend}, {csengetesek} csengetés"
                     + (f", az első {elso:%H:%M}-kor." if elso else "."))
    if kimenet:
        sorok.append(f"Hangkimenet: {kimenet}.")
    else:
        sorok.append("Hangkimenet: NEM TALÁLHATÓ.")
        gondok.append("nincs hangkimenet")
    if forras:
        sorok.append(f"Szünetzene: {forras}" + (f" ({szamok} szám)." if szamok else "."))
    else:
        sorok.append("Szünetzene: nincs kiválasztott forrás.")
    if tegnap:
        c = tegnap["csengetes"]
        pontossag = (f", átlagos eltérés {c['atlag_keses_ms'] / 1000:.1f} mp".replace(".", ",")
                     if c.get("atlag_keses_ms") is not None else "")
        sorok.append(f"Tegnap: {tegnap['zene']['perc']} perc zene, {c['darab']} csengetés{pontossag}.")
        if c.get("kesett"):
            gondok.append(f"tegnap {c['kesett']} csengetés késett")
    if hibak:
        sorok.append(f"Az elmúlt 24 órában {hibak} hiba került a naplóba.")
        gondok.append(f"{hibak} hiba")
    if szabad_gb is not None and szabad_gb < 2:
        sorok.append(f"Kevés a szabad hely: {szabad_gb:.1f} GB.".replace(".", ",", 1))
        gondok.append("kevés hely")
    if uj_verzio:
        sorok.append(f"Új verzió érhető el: {uj_verzio}.")
    cim = f"Reggeli önteszt ({nap:%m.%d.})" + (": " + ", ".join(gondok) if gondok else ": minden rendben")
    return cim, "\n".join(sorok), "figy" if gondok else "info"
