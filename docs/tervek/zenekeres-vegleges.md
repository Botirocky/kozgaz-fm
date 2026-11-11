# Közgáz FM zenekérés: végleges, tartósan működő terv

Állapot: terv, kód nincs. Alap: a main 1ee312b (1.18.2) állapota, a `zenekeres-worker/`, a `docs/`, a `php/` és a `zenekeres-szerver/debian/` kódja alapján.

---

## 1. Jelenlegi felépítés

```
 diák telefonja (mobilnet)
   |  QR -> GitHub Pages: docs/index.html + zenekeres.js
   |  fetch, 4 mp (kérés folyamatban) / 30 mp (üresjárat)
   v
 Cloudflare Worker (zenekeres-worker/src/index.js, workers.dev)
   |  D1: keresek, ertekek, szavazatok
   |  /api/zenekeres   diák: állapot, kérés, szavazás
   |  /api/gep         iskolai gép: kulcs, szinkron
   |  /egeszseg        radio: true/false (90 mp-es friss küszöb)
   ^
   |  kimenő HTTPS, 4 mp-enként (KOR_MP = 4), a gép kezdeményez
   |
 iskolai Linux gép
   kozgaz-fm-szerver .deb -> kozgaz-fm-web@ + kozgaz-fm-demon@ (systemd, Restart=always, linger)
   php/src/ZenekeresSzerver.php  (az asztali változat: src/kozgaz_fm/zenekeres_szerver.py)
   szűrő (Szuro) + tiltott telefonok + napi limit: a gépen dől el, elfogadja-e
   beállítás: sudo kozgaz-fm-szerver zenekeres-be <kulcsfájl> [cím]  (pendrive-ról)
```

Fontos tulajdonságok a kódból:

- A diák mobilneten van, nincs diák-wifi. Az iskolai szűrő így csak az iskolai gép kimenő forgalmát érinti, a diákokét nem.
- A Worker nem szűri a tartalmat. Trágárságot és tiltott telefont a gép dönt el, a diák az elutasítást 4 mp-en belül látja.
- A Workerben van: napi limit eszközönként (alap 3), óránként 20 kérés IP-nként, legfeljebb 40 várakozó, napi 5 szavazat, a kérések 2 napig maradnak.
- A `gep` bejegyzés írása legfeljebb 30 mp-enként történik. Ez a 90 mp-es „elérhető” küszöbbel együtt jó.
- Az `zenekeres-be` előbb ellenőrzi az elérhetőséget, majd 45 mp-ig vár a `radio: true`-ra.
- Az `zenekeres-szerver/` mappa PHP-közvetítő része leállított és elavult. A `zenekeres-szerver/debian/` viszont a ma is használt `kozgaz-fm-szerver` csomagot építi, ezért a mappa nem törölhető.
- A `php/` az asztali app tükre: minden asztali változtatást oda is át kell vinni, és fordítva.

## 2. Gyenge pontok, súlyosság szerint

| # | Gyenge pont | Súly | Miért |
|---|---|---|---|
| 1 | Az iskola szűrheti a `workers.dev`-et | Kritikus | Ha tilt, a funkció nem működik. A gépről kimenő kérés az egyetlen út, és otthonról nem tesztelhető. A hiba csak a helyszínen derül ki. |
| 2 | Nincs távoli láthatóság, a kiesés csendes | Magas | Ha a gép leáll vagy elveszti a hálózatot, senki nem tudja. A diák „nem elérhető” üzenetet kap, a fejlesztő semmit. Ez a többi hibát is láthatatlanná teszi. (Nem szerepelt a megadott listán, a kódból következik.) |
| 3 | Kézi telepítés az iskolai gépen | Magas | Egy pendrive-os alkalom, helyszíni terminállal, kulcs begépelésével. Hibás lépésnél nincs otthoni hozzáférés. Frissítésnél újra helyszín kell. |
| 4 | D1 kvóta, becslés szerint a határon | Magas | Lásd lent. A 4 mp-es éjszakai polling a reggeli keretet is felélheti. |
| 5 | Áramszünet utáni visszaállás | Közepes | A systemd-oldal jó (`Restart=always`, linger, `network-online.target`). Nem ismert: BIOS „AC power loss” beállítás, óra (RTC) és NTP az újraindulás után, a hálózat késői felállása. |
| 6 | Nincs tartalék útvonal | Közepes | Egyetlen cím, egyetlen szolgáltató, egyetlen Cloudflare-fiók. |
| 7 | Visszaélés: spam és trágár kérések | Közepes | A gépen szűrő van. A Worker 40 várakozónál lezár, így egy támadó a sort ki tudja tölteni (DoS). A 20/óra IP-korlát mobilszolgáltatói közös IP-nél (CGNAT) jogos diákokat is kizárhat. |
| 8 | Hosszú távú gazdaváltás | Közepes | A Cloudflare-fiók egy személyé, a gép csomagja kézzel frissül. A Worker-protokoll változása elronthatja a régi gépet. |
| 9 | Kulcs a pendrive-on | Alacsony | A használat után törlendő. A kulcscsere (`uj-kulcs`) kézi. |

### A D1 kvóta részletesen (becslés, mérni kell)

Az ingyenes keret nagyságrendje: 100 ezer Worker-kérés/nap, D1-ből 5 millió sor-olvasás és 100 ezer sor-írás naponta. A pontos számokat a bevezetés előtt a Cloudflare dokumentációjában újra kell ellenőrizni.

- A gép napi 21 600 szinkront küld, ha éjjel-nappal fut. Ez a kérés-keret ötöde.
- Minden szinkron lefuttatja a `lejartTakaritas`-t. Ebben a `DELETE FROM keresek WHERE ido < ?` nem használ indexet (nincs index az `ido` oszlopon), tehát végigolvassa a táblát.
- Ha a tábla 300–500 sort tart (2 napnyi megőrzés), akkor 21 600 szinkron × 300–500 sor = 6–11 millió sor-olvasás naponta. Ez az ingyenes keret fölött lehet.
- A napi keret UTC éjfélkor (itt kb. 01:00–02:00) nullázódik. Az éjszakai polling így még a reggeli órák előtt elfogyaszthatja az új nap keretét.
- Túllépés után a D1-hívások hibára futnak, és minden leáll a következő nullázásig.

Teendő: mérni (Cloudflare irányítópult vagy `wrangler d1 insights`), és a pollingot iskolai időn kívül lelassítani, a takarítást ritkítani, az `ido` oszlopra indexet tenni.

## 3. Megoldás-változatok

### A. Rétegzett, szakaszolt megoldás (ajánlott), kb. 28 óra

Tartalma: diagnosztika, őrszem, kvóta-kímélés, önbeállító pendrive, áramszünet-edzés, majd saját domain és tartalék cím, végül visszaélés-védelem.

- Előny: minden gyenge pontot kezel, és szakaszolható. Az F0–F3 szakasz (kb. 13 óra) önmagában is használható, a domain csak akkor készül el, ha szükséges.
- Előny: a domain eltávolítja a „workers.dev-et tiltják” kockázatot, és az iskolai informatikusnak is egyetlen, ismert címet lehet kérni engedélyezésre.
- Hátrány: évi néhány ezer Ft domainköltség, és a Python és a PHP kliens kétcímes támogatása párhuzamos munka.
- Hátrány: a tartalék cím ugyanarra a Workerre és D1-re mutat, ezért csak a szűrés ellen véd, a Cloudflare-kiesés ellen nem.

### B. Csak reaktív, kb. 13 óra

Tartalma: diagnosztika, őrszem, kvóta-kímélés, önbeállító pendrive, áramszünet-edzés. Domain nincs, tartalék cím nincs. Ha a próba szerint a `workers.dev` tilos, utólag jön az A változat F4 szakasza.

- Előny: gyors, olcsó, és az első valós próba mutatja meg, kell-e a domain.
- Hátrány: ha a szűrő tilt, a legrosszabb pillanatban derül ki, és újabb helyszíni látogatás kell.
- Hátrány: a visszaélés elleni védelem is kimarad (a gyors kikapcsolás gombján kívül).

### C. Független másodlagos közvetítő, kb. 35 óra

Tartalma: B, plusz egy valódi, másik szolgáltatón futó közvetítő (a leállított PHP-közvetítő újraélesztése vagy másik fiók Workere), és a kliensek átkapcsolnak, ha az első nem elérhető.

- Előny: Cloudflare-kiesés ellen is véd.
- Hátrány: két külön tárolt állapot, két külön protokollkarbantartás, és a diákoldalnak mindkettőhöz tudnia kell kapcsolódni. A kérés-sor kettéhasad.
- Hátrány: a user a picloudot kifejezetten nem akarja erre használni, így a PHP-közvetítő külső tárhelyet igényelne.
- Nem ajánlott: a haszon (ritka Cloudflare-kiesés) kisebb a karbantartási költségnél.

## 4. Az ajánlott változat (A) lépésről lépésre

Elv: minden szakasz külön PR, külön kiadás. A Worker minden szakaszban visszafelé kompatibilis marad a régebbi gép-verziókkal.

### F0. Diagnosztika és mérés (kb. 2 óra)

1. Új alparancs: `kozgaz-fm-szerver zenekeres-proba [cím]`. Kiírja a DNS-feloldást, a TLS-kapcsolatot, a HTTP-választ a `/egeszseg`-re, az óra eltérését (a TLS idő nélkül nem megy) és az `NTP szinkronban` állapotot. Eredményt a képernyőre és egy fájlba ír (a pendrive-ra is, ha van).
2. A mérés beállítása: a D1 sor-olvasás és a Worker kéréseinek naponkénti figyelése 3–5 napig, az iskolai nyitás előtt és után. Ebből dől el, mennyire sürgős F1.
3. Az iskolai informatikushoz egy rövid, kész kérés: „kérem a (domain) engedélyezését a gépen”. Ez a legolcsóbb megoldás a szűrésre, és párhuzamosan mehet.

### F1. Worker: kvóta-kímélés és őrszem (kb. 5 óra)

1. Index az `ido` oszlopra a `keresek` táblán, új migrációs fájl (a `schema.sql` mellé).
2. `lejartTakaritas` ritkítása: a futás idejét az `ertekek` táblában tárolni, és legfeljebb 5 percenként lefuttatni.
3. A gép pollingjának lassítása iskolai időn kívül. A gép a Worker válaszában kapja az ajánlott időközt (`kovetkezo_mp`), így a kliens nem kell, hogy ismerje az órarendet. Iskolai időben 4 mp, azon kívül 30–60 mp, éjjel 120 mp. A Python és a PHP kliens a `kovetkezo_mp` mezőt kövesse, korlátok között (2–180 mp). Az iskolai időt a gép az órarendjéből küldi fel a `beallitasok`-ban (új, opcionális mező).
4. Őrszem: Worker Cron Trigger 5 percenként. Ha iskolai időben a `gep.utolso` 15 percnél régebbi, értesítést küld (ntfy vagy e-mail, lásd 5. szakasz). Visszaálláskor egy másodikat. Ismétlés legfeljebb óránként.
5. Tesztek a `zenekeres-worker/tests/`-be: takarítás-ritkítás, `kovetkezo_mp`, őrszem-logika (az idő beinjektálásával).
6. Ellenőrzés: a mérés F0-ból újra, a sor-olvasás napi értéke látható csökkenése.

### F2. Önbeállító pendrive (kb. 4 óra)

1. A pendrive tartalma: `telepit.sh`, az offline `kozgaz-fm-szerver_*.deb`, a `zenekeres-kulcs.txt` (a repóban nincs), és az `OLVASD.txt` három sorral.
2. `telepit.sh`: idempotens. Lépései: root-ellenőrzés, `apt install` a pendrive-ról, `fm-be`, ha még nincs, `zenekeres-proba`, `zenekeres-be`, végül a teljes kimenet a pendrive-ra `jelentes-ÉÉÉÉHHNN.txt` néven. A kulcsfájl törlését a végén megkérdezi.
3. Az `zenekeres-be` kapjon `--csendes` kapcsolót és érthető kilépési kódokat (nincs hálózat, szűrés, rossz kulcs, nincs kapcsolódás), a script ebből ad magyar magyarázatot.
4. Ellenőrzés: Debian 13 systemd-konténerben (ahogy a korábbi csomagpróbák), kétszeri futtatással (idempotencia), rossz kulccsal és kimenő hálózat nélkül is.
5. A `docs/tervek/` és az `ELESITES.txt` új változata: a lépések helyett „futtasd a `telepit.sh`-t”.

### F3. Áramszünet-edzés (kb. 3 óra)

1. A `kozgaz-fm-*@.service` fájlokba `After=time-sync.target` és `Wants=time-sync.target`, hogy RTC-hiba után ne induljon TLS idő nélkül. A `network-online.target` marad.
2. `kozgaz-fm-szerver-ellenor.timer` + service (5 percenként): ha a helyi szolgáltatás él, de a Worker `radio:false`-t mond 10 percnél tovább, a szolgáltatások újraindítása; ha a hálózat hiányzik, naplóz és vár. Korlát: óránként legfeljebb 3 újraindítás.
3. Dokumentáció az iskolai gép gazdájának: a BIOS „Restore on AC Power Loss: Power On” beállítása, és hogy a gép napi ütemezett kikapcsolását (ha van) az órarendhez kell igazítani.
4. Ellenőrzés: systemd-konténerben szimulált újraindítás (`systemctl reboot` a konténerben), óraugrás szimuláció, kimenő hálózat megszakítása és visszaállítása. Elvárt: 2 percen belül `radio:true`.

### F4. Saját domain és tartalék cím (kb. 8 óra, feltételes: a 6. döntés után)

1. A domaint a Cloudflare DNS-be kell tenni (a Worker egyéni domainje ezt igényli). Worker-útvonal: `zenekeres.<domain>`. A `workers.dev` cím megmarad.
2. `wrangler.toml`: `routes` / egyéni domain. A `wrangler deploy` csak a `zenekeres-worker/` mappából futtatható (különben a wrangler új Workert csinál a `docs/`-ból, ez már egyszer megtörtént).
3. Kliens: a `zenekeres_szerver` mező elfogadjon szóközzel vagy vesszővel elválasztott címlistát. A kliens sorrendben próbálja, az utoljára működőre ragad, 5 hibás kör után vált. A Python (`szerver_cim`, `kuld`) és a PHP (`ZenekeresSzerver`) azonosan viselkedjen, mindkettőhöz teszt.
4. `kozgaz-fm-szerver`: az `ZK_CIM` két alapcímre bővül, az `zenekeres-be` mindkettőt próbálja és a működőket írja be.
5. Diákoldal: a `docs/zenekeres.js` `SZERVER` az új domainre, a `docs/index.html` CSP `connect-src` mindkét címmel az átállás idejére. A plakát és a QR változatlan, mert a Pages-címre mutat. A diákoldalon tartalék cím nem kell: a diák mobilneten van, nincs szűrés.
6. Ellenőrzés: a két cím egyidejű működése, az egyik elérhetetlenné tétele (hosts-fájlos blokk a konténerben), az átkapcsolás látszik a naplóban.

### F5. Visszaélés elleni védelem (kb. 4 óra, +4 óra, ha captcha kell)

1. Gyors kikapcsolás: a már meglévő gépoldali „Zenekérés ki” plusz egy Worker-változó (`KFM_BEZARVA`), amely a gépen kívül, a Cloudflare-felületről is lezárja a kéréseket.
2. Globális óránkénti plafon a kérésekre (az IP-korlát mellé), és kisebb várakozó-keret egy IP-re, hogy egyetlen forrás ne töltse meg a 40-es sort.
3. A gépen lévő szűrőlista felküldése a `beallitasok`-ban (a `tiltott_telefonok` mintájára, rövidítve és mérethatárral), hogy a Worker már a beküldéskor elutasítsa a trágár kérést. A gép szűrője marad a végső döntő, a Worker csak a korai elutasítás.
4. A CGNAT-kockázat: az IP-korlátot nem szigorítani, hanem mérni (a Worker számolja az elutasított `rate_limited` kéréseket, az őrszem jelez). Ha jogos diákot zár ki, a korlát emelhető.
5. Opcionális: Cloudflare Turnstile a kérés beküldésén. Kell hozzá: site key a `docs/`-ban, secret a Workerben, CSP bővítés (`challenges.cloudflare.com`). Csak akkor, ha tényleges visszaélés jelentkezik.
6. Ellenőrzés: Worker-tesztek a limitekre és az új plafonra, a szűrőlista-szinkron tesztje, és egy kézi próba a gép ki- és bekapcsolásával.

### F6. Dokumentáció és átadás (kb. 2 óra)

1. `zenekeres-worker/README.md`: új változók, cron, domain, kvóta-mérés, kikapcsolás.
2. Új üzemeltetési oldal: „Mi a teendő, ha nem működik”, fokozatok szerint (gép, hálózat, Worker, Cloudflare).
3. Kulcscsere-útmutató és a Cloudflare-fiók átadási lista (lásd 5. szakasz 5. döntés).
4. A régi `zenekeres-szerver/` közvetítő-kód README-jába „leállított, csak a `debian/` aktív” megjegyzés.

### Sorrend és kiadás

F0 → F1 → F2 → F3 egy kiadási sorozatban (kb. 13 óra). Ezután döntés F4-ről az F0 mérése és az első valós iskolai próba alapján. F5 a visszaélés első jelére vagy kérésre. Verzióemelés és kiadás a szokásos szabály szerint, csak a megvalósításkor.

## 5. A user döntései

1. **Domain:** vásárolsz-e domaint a Workernek (évi néhány ezer Ft), vagy van-e meglévő domained, amit a Cloudflare DNS-be lehet tenni? Enélkül az F4 elmarad.
2. **Iskolai informatikus:** kéred-e tőle a domain engedélyezését, és tudod-e, ki az? (Ez az egyik legolcsóbb megoldás a szűrésre.)
3. **Értesítési csatorna az őrszemnek:** ntfy (nyilvános ntfy.sh, a picloud nélkül), e-mail vagy Discord webhook? A titkos címet a Worker secretjeként tartjuk, nem a repóban.
4. **Önfrissítés az iskolai gépen:** kérsz-e automatikus frissítést (időzítő, ami a GitHub-kiadásból telepít), vagy marad a kézi, pendrive-os frissítés? Az automatikus kényelmes, de a kiadási csatornába vetett bizalmat jelent.
5. **Cloudflare-fiók:** legyen-e második tulajdonos vagy átadási terv ballagás után, és be van-e kapcsolva a kétlépcsős belépés? (A hosszú távú működés feltétele.)
6. **F4 feltételessége:** akarod-e azonnal, vagy csak akkor, ha az F0 próba szerint kell?
7. **Visszaélés-védelem:** elég-e a szűrőlista-felküldés és a plafon, vagy kérsz Turnstile-t is?
8. **Az iskolai gép ütemezése:** be van-e kapcsolva éjjel? Ha ki van, az F1 lassítás és az őrszem iskolai ideje ahhoz igazodjon.
9. **Régi PHP-közvetítő:** maradjon az elavult README-jelöléssel, vagy távolítsuk el a közvetítő-kódot (a `debian/` marad)?
10. **Ingyenes keret:** ha a mérés szerint F1 után is szűk, vállalod-e a fizetős Workers csomagot (havi néhány dollár)?

### Meghozott döntések (2026-11-11)

- Saját domain: most nem; az iskolai próba dönt (ha a `workers.dev` szűrt, akkor F4).
- Őrszem-értesítés: ntfy.sh.
- Iskolai gép frissítése: automatikusan GitHubról.
- A még nyitott döntések (Cloudflare-fiók átadása, Turnstile) az F1–F3 után.

## Bizonytalanságok

- A `workers.dev` tiltása nem tesztelhető otthonról, csak az iskolai gépen.
- A D1-számok becslések a kódból: a tábla tényleges mérete és a pontos keretek mérésre és a Cloudflare dokumentációjára várnak.
- A `php/` változat (`kozgaz-fm-szerver` csomag) frissítési módja nem látszik a kódból: önfrissítése van-e, az F2/4. döntés előtt ellenőrizendő.
- Az iskolai gép BIOS-beállítása, NTP-je és éjszakai ütemezése nem ismert.
- A Cloudflare ingyenes csomagjának Cron-, egyéni domain- és D1-korlátait a megvalósítás előtt ellenőrizni kell.
