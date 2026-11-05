import json, sys
from kozgaz_fm.szuro import Szuro, ertekel, szavak_kibontva
from kozgaz_fm.dalszoveg import cim_bontas, DalszovegTar
szovegek = [
    "Ez egy teljesen tiszta szöveg a napsütésről", "What the f*ck is this sh!t", "k*rva jó buli volt",
    "fasza gyerek vagy", "faszination", "Basszus, ez fasz", "f u c k", "fuuuuuck you", "sh1t happens",
    "a seggem fáj", "Shitake gomba recept", "b@sszátok meg", "KURVA ANYÁD", "ribanc köcsög buzi",
    "Damn, damn, damn", "asshole bastard crap", "Szaros nap", "picsába", "pöcsfej", "lófasz se",
    "#### szöveg", "Explicit Version", "geciiii", "Nigga please", "mothafucka", "ez a kurvá-ja",
    "szopd le", "5h1t", "f@sz", "Bazdmeg", "ki b*szott", "elbaszott meccs", "Árvíztűrő tükörfúrógép",
]
dalok = ["Tankcsapda - Ez az a ház (Official Video)", "01. Avicii - Levels [HD] ft. Someone", "Valami | lyrics",
         "Daft Punk – Around the World (Radio Edit)", "Csak egy cím", "Ákos: Ilyenek voltunk – Hivatalos videoklip"]
sz = Szuro(["saját*", "tiltott szó"], True)
kimenet = {"ertekeles": [[s, list(vars(ertekel(s)).values()), szavak_kibontva(s), sz.talalat(s), Szuro().talalat(s)] for s in szovegek],
           "dal": [[d, list(cim_bontas(d)), DalszovegTar.kulcs(d)] for d in dalok]}
json.dump(kimenet, sys.stdout, ensure_ascii=False)
