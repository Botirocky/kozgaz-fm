import json, sys, pathlib
from dataclasses import asdict
from datetime import date
from kozgaz_fm import kghsz, naptar_import
from kozgaz_fm.beallitasok import alapertelmezett
cel = pathlib.Path(sys.argv[1])
oldalak = {}
for nev, ut in (("csengetes", kghsz.OLDAL_CSENGETES), ("hazirend", kghsz.OLDAL_HAZIREND), ("tanev", kghsz.OLDAL_TANEV), ("esemenyek", kghsz.OLDAL_ESEMENYEK)):
    oldalak[nev] = kghsz._letolt(ut)
    (cel / f"kghsz_{nev}.html").write_text(oldalak[nev], encoding="utf-8")
b = alapertelmezett()
normal, rovid = kghsz.csengetesi_rend(oldalak["csengetes"], oldalak["hazirend"])
tanev = kghsz.tanev_esemenyek(oldalak["tanev"])
honlapi = kghsz.honlapi_esemenyek(oldalak["esemenyek"], date(2026, 11, 4))
ossz = kghsz.osszevon(tanev, honlapi, b)
ics = open(sys.argv[2], encoding="utf-8").read()
e = lambda x: {"nev": x.nev, "tol": x.tol.isoformat(), "ig": x.ig.isoformat()}
javaslatok = naptar_import.javaslatok(ics, b, date(2026, 1, 1)) + naptar_import.esemeny_javaslatok(ossz, b, date(2026, 1, 1))
kimenet = {"normal": [asdict(o) for o in normal], "rovid": [asdict(o) for o in rovid] if rovid else None,
           "tanev": [e(x) for x in tanev], "honlapi": [e(x) for x in honlapi], "ossz": [e(x) for x in ossz],
           "sorok_tanev": kghsz.sorok((kghsz.oldal_adat(oldalak["tanev"]).get("data") or {}).get("currentInfo") or ""),
           "javaslatok": [{"esemeny": e(j.esemeny), "muvelet": j.muvelet, "megjegyzes": j.megjegyzes} for j in javaslatok]}
json.dump(kimenet, sys.stdout, ensure_ascii=False)
