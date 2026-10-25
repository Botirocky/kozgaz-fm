__lazy_modules__ = ["json", "datetime", "kozgaz_fm.beallitasok", "kozgaz_fm.ertesites", "kozgaz_fm.orarend"]

import json
from datetime import date, datetime, timedelta

import pytest

from kozgaz_fm import ertesites
from kozgaz_fm.beallitasok import alapertelmezett
from kozgaz_fm.ertesites import (
    ErtesitesHiba,
    Ertesito,
    email_kuld,
    kimaradt_csengetesek,
    ntfy_cel,
    ntfy_kuld,
    reggeli_jelentes,
)
from kozgaz_fm.orarend import CSENGOK, Esemeny, Tipus


@pytest.mark.parametrize(("url", "vart"), [
    ("https://ntfy.sh/kozgaz-fm-xyz", ("https://ntfy.sh/", "kozgaz-fm-xyz")),
    ("http://192.168.1.5:8080/sajat/riaszt_1/", ("http://192.168.1.5:8080/sajat", "riaszt_1")),
])
def test_ntfy_cel(url, vart):
    assert ntfy_cel(url) == vart


@pytest.mark.parametrize("url", ["ntfy.sh/tema", "file:///etc/x", "https://ntfy.sh/", "https://ntfy.sh/rossz téma"])
def test_ntfy_cel_hibas(url):
    with pytest.raises(ErtesitesHiba):
        ntfy_cel(url)


class _Valasz:
    def read(self, *_):
        return b"{}"

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_ntfy_kuld_json_es_token(monkeypatch):
    kuldott = []
    monkeypatch.setattr(ertesites.urllib.request, "urlopen", lambda k, timeout: kuldott.append(k) or _Valasz())
    ntfy_kuld("https://ntfy.sh/kozgaz-fm-xyz", " titok ", "Kimaradt csengetés", "8:00 Becsengő", "hiba")
    k = kuldott[0]
    adat = json.loads(k.data)
    assert k.full_url == "https://ntfy.sh/" and k.get_method() == "POST"
    assert adat == {"topic": "kozgaz-fm-xyz", "title": "Kimaradt csengetés", "message": "8:00 Becsengő",
                    "priority": 5, "tags": ["rotating_light"]}
    assert k.headers["Authorization"] == "Bearer titok"


def test_ntfy_kuld_hibauzenet(monkeypatch):
    def tilt(k, timeout):
        raise ertesites.urllib.error.HTTPError(k.full_url, 403, "tiltva", {}, None)
    monkeypatch.setattr(ertesites.urllib.request, "urlopen", tilt)
    with pytest.raises(ErtesitesHiba, match="token"):
        ntfy_kuld("https://ntfy.sh/tema", "", "a", "b")


class _Smtp:
    peldanyok: list = []

    def __init__(self, szerver, port, timeout=0, context=None):
        self.szerver, self.port, self.ssl = szerver, port, context is not None
        self.lepesek = []
        _Smtp.peldanyok.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def starttls(self, context=None):
        self.lepesek.append("starttls")

    def login(self, felh, jelszo):
        self.lepesek.append(("login", felh, jelszo))

    def send_message(self, level):
        self.lepesek.append(("kuld", level["Subject"], level["To"], level.get_content().strip()))


def smtp_beallitas(**kw):
    b = alapertelmezett()
    b.ertesites_email = "rg@iskola.hu; tanar@iskola.hu"
    b.smtp_szerver, b.smtp_felhasznalo, b.smtp_jelszo = "smtp.iskola.hu", "rg@iskola.hu", "alkalmazasjelszo"
    for k, v in kw.items():
        setattr(b, k, v)
    return b


def test_email_starttls(monkeypatch):
    _Smtp.peldanyok = []
    monkeypatch.setattr(ertesites.smtplib, "SMTP", _Smtp)
    email_kuld(smtp_beallitas(), "Hiba", "Ékezetes üzenet")
    s = _Smtp.peldanyok[0]
    assert (s.szerver, s.port) == ("smtp.iskola.hu", 587)
    assert s.lepesek == ["starttls", ("login", "rg@iskola.hu", "alkalmazasjelszo"),
                         ("kuld", "Közgáz FM: Hiba", "rg@iskola.hu, tanar@iskola.hu", "Ékezetes üzenet")]


def test_email_ssl_es_hianyzo_beallitas(monkeypatch):
    _Smtp.peldanyok = []
    monkeypatch.setattr(ertesites.smtplib, "SMTP_SSL", _Smtp)
    email_kuld(smtp_beallitas(smtp_mod="ssl", smtp_port=465), "a", "b")
    assert _Smtp.peldanyok[0].ssl and "starttls" not in _Smtp.peldanyok[0].lepesek
    with pytest.raises(ErtesitesHiba, match="címzett"):
        email_kuld(smtp_beallitas(ertesites_email="nem-email"), "a", "b")


def test_ertesito_szures_es_ismetles(monkeypatch):
    b = alapertelmezett()
    naplo, kuldesek = [], []
    monkeypatch.setattr(ertesites, "kikuld", lambda bb, cim, uzenet, szint: kuldesek.append(cim) or ["ntfy: rossz"])
    e = Ertesito(lambda: b, naplo.append, futtato=lambda fv, kesz=None, hiba=None: kesz(fv()))
    assert e.kuld("hiba", "A", "x") is False
    b.ertesites_ntfy = "https://ntfy.sh/tema"
    assert e.kuld("hiba", "A", "x") is True
    assert e.kuld("hiba", "A", "x") is False
    assert e.kuld("hiba", "A", "y") is True
    b.ertesites_esemenyek = ["riasztas"]
    assert e.kuld("hiba", "B", "z") is False
    assert e.kuld("riasztas", "R", "z", ismetles_mp=0) and e.kuld("riasztas", "R", "z", ismetles_mp=0)
    assert kuldesek == ["A", "A", "R", "R"] and naplo[0] == "Értesítés nem ment el – ntfy: rossz"


def test_proba_nincs_csatorna():
    eredmeny = []
    Ertesito(alapertelmezett).proba(eredmeny.append)
    assert "Nincs beállítva" in eredmeny[0][0]


def test_kimaradt_csengetesek():
    t = datetime(2026, 10, 26, 8, 0)
    esemenyek = [Esemeny(t, Tipus.BECSENGO, 1), Esemeny(t + timedelta(minutes=45), Tipus.KICSENGO, 1),
                 Esemeny(t + timedelta(minutes=10), Tipus.ZENE_INDUL, 1)]
    lista = kimaradt_csengetesek(esemenyek, t - timedelta(minutes=5), t + timedelta(hours=1), CSENGOK)
    assert [e.tipus for e in lista] == [Tipus.BECSENGO, Tipus.KICSENGO]
    assert kimaradt_csengetesek(esemenyek, t - timedelta(days=2), t + timedelta(hours=1), CSENGOK) == []
    assert len(kimaradt_csengetesek(esemenyek, t - timedelta(hours=13), t + timedelta(hours=1), CSENGOK)) == 2
    assert kimaradt_csengetesek(esemenyek, t + timedelta(hours=2), t, CSENGOK) == []


def test_reggeli_jelentes():
    cim, szoveg, szint = reggeli_jelentes(
        nap=date(2026, 10, 26), rend="Normál", elso=datetime(2026, 10, 26, 8, 0), csengetesek=16,
        kimenet="Erősítő (USB)", forras="Szünetzene", szamok=120,
        tegnap={"zene": {"perc": 95}, "csengetes": {"darab": 16, "atlag_keses_ms": 300, "kesett": 0}},
        hibak=0, uj_verzio=None, szabad_gb=40.0)
    assert szint == "info" and cim.endswith("minden rendben")
    assert "Normál, 16 csengetés, az első 08:00-kor" in szoveg and "átlagos eltérés 0,3 mp" in szoveg
    cim, szoveg, szint = reggeli_jelentes(
        nap=date(2026, 10, 26), rend="Normál", elso=None, csengetesek=0, kimenet=None, forras=None, szamok=0,
        tegnap=None, hibak=3, uj_verzio="0.8.1", szabad_gb=1.2)
    assert szint == "figy" and "nincs hangkimenet" in cim and "3 hiba" in cim and "kevés hely" in cim
    assert "NEM TALÁLHATÓ" in szoveg and "0.8.1" in szoveg and "1,2 GB" in szoveg


def test_kikuld_varatlan_hibat_uzenette_alakit(monkeypatch):
    b = alapertelmezett()
    b.ertesites_ntfy = "https://ntfy.sh/tema"
    b.ertesites_email, b.smtp_szerver = "rg@iskola.hu", "smtp.iskola.hu"

    def ekezet(*_a, **_k):
        raise UnicodeEncodeError("ascii", "jelszó", 5, 6, "nem ascii")

    def furcsa(*_a, **_k):
        raise RuntimeError("valami")
    monkeypatch.setattr(ertesites, "ntfy_kuld", furcsa)
    monkeypatch.setattr(ertesites, "email_kuld", ekezet)
    hibak = ertesites.kikuld(b, "a", "b", "info")
    assert hibak[0].startswith("ntfy: váratlan hiba (RuntimeError") and "ékezet nélküli" in hibak[1]


def test_kategoria_szerinti_ismetles(monkeypatch):
    b = alapertelmezett()
    b.ertesites_ntfy = "https://ntfy.sh/tema"
    kuldesek = []
    monkeypatch.setattr(ertesites, "kikuld", lambda bb, cim, uzenet, szint: kuldesek.append(uzenet) or [])
    e = Ertesito(lambda: b, futtato=lambda fv, kesz=None, hiba=None: kesz(fv()))
    for cim in ("1. dal", "2. dal", "3. dal"):
        e.kuld("hiba", "Zenehiba", f"Nem játszható: {cim}", kulcs_szoveg="zenehiba")
    assert kuldesek == ["Nem játszható: 1. dal"]
