import json
import sys
from dataclasses import asdict
from datetime import date, datetime, timedelta

from kozgaz_fm.beallitasok import Bemondas, Rendkivuli, Szunnap, alapertelmezett
from kozgaz_fm.orarend import allapot, kovetkezo_esemeny, napi_esemenyek, zene_szunet


def valtozatok():
    b = alapertelmezett()
    yield "alap", b
    b = alapertelmezett()
    b.reggeli_zene = True
    b.jelzo_perc = 5
    b.zene_min_szunet = 10
    b.kivetelek["2026-11-05"] = "Rövidített"
    b.szunnapok.append(Szunnap("2026-11-06", "2026-11-06", "Teszt szünnap"))
    b.ma_nincs_zene = "2026-11-09"
    b.zene_kihagyott_szunetek = [3, 0]
    b.rendkivuli += [
        Rendkivuli("Tűzriadó", "2026-11-10", "10:30", tipus="riado", riado_perc=4),
        Rendkivuli("Ünnepség", "2026-11-10", "12:10"),
        Rendkivuli("Érettségi", "2026-11-11", "08:00", tipus="csend", ig="10:15", csengo_hangero=25),
        Rendkivuli("Mérés", "2026-11-12", "09:00", tipus="csend", ig="09:30"),
    ]
    b.bemondasok += [
        Bemondas("Reggeli", "07:40", napok=[0, 2, 4]),
        Bemondas("Egyszeri", "11:10", datum="2026-11-12", tipus="fajl", tartalom="/x.mp3", gong=False),
        Bemondas("Csendben", "09:10", napok=[3]),
    ]
    yield "valtozat", b
    b = alapertelmezett()
    b.jelzo = False
    b.kicsengo = False
    b.zene_szunetben = False
    b.het = ["Normál", "Rövidített", "", "Normál", "Rövidített", "Normál", ""]
    yield "het", b


def esemeny(e):
    return [e.ido.isoformat(), e.tipus.value, e.ora, e.leiras, e.hangero]


kimenet = {}
for nev, b in valtozatok():
    napok = {}
    nap = date(2026, 11, 2)
    for _ in range(14):
        napok[nap.isoformat()] = [esemeny(e) for e in napi_esemenyek(b, nap)]
        nap += timedelta(days=1)
    allapotok = []
    most = datetime(2026, 11, 2, 6, 50)
    while most < datetime(2026, 11, 13, 17, 0):
        a = allapot(b, most)
        kov = kovetkezo_esemeny(b, most)
        allapotok.append([most.isoformat(), a.szakasz.value, a.ora, a.cim, a.vege.isoformat() if a.vege else None,
                          a.csend, esemeny(kov) if kov else None, zene_szunet(b, most)])
        most += timedelta(minutes=7)
    kimenet[nev] = {"beallitasok": asdict(b), "napok": napok, "allapotok": allapotok}
json.dump(kimenet, sys.stdout, ensure_ascii=False)
