<p align="center"><img src="src/kozgaz_fm/kepek/logo.png" width="180" alt="Közgáz FM"></p>

# Közgáz FM

Iskolai csengetőrendszer és szünetzene-lejátszó. A csengetési rend szerint magától csenget, a szünetekben
zenét játszik helyi MP3-ból, YouTube-ról vagy Spotifyról, és hangosbemondásra is képes.

![Vezérlőpult](docs/vezerlopult.png)

## Funkciók

- **Automatikus csengetés:** becsengő, kicsengő, jelzőcsengő (X perccel előtte), több csengetési rend
  (Normál, Rövidített…), heti beosztás, rend-generátor.
- **Szünetzene:** mappa, MP3-fájlok / .m3u, YouTube (link, lista vagy keresés), Spotify (Premium, Web API).
  Csak a megadott hossznál hosszabb szünetekben, elhalkítással leáll a csengő előtt, reggeli zene.
- **YouTube előletöltés:** a következő számok gyorsítótárba kerülnek – akadásmentes, rövid netkiesésnél is szól.
- **Naptár:** szünnapok, tanítási szünetek, magyar ünnepnapok egy gombbal, kivételnapok.
- **Bemondás:** azonnali vagy ütemezett, felolvasott szöveg (TTS) vagy hangfájl, gonggal; a zene közben
  lehalkul.
- **Riasztás:** folyamatos riasztó hang egy gombbal, megerősítéssel, külön oldalon (nem a Vezérlőpulton).
- **Mai kapcsolók:** ma nincs csengetés / ma nincs zene / mai rend (pl. rövidített órák).
- **Folyosói kijelző:** teljes képernyős óra, visszaszámláló, épp szóló szám, a zenekérés QR-kódja (F11).
- **Működés:** tálcán fut, automatikus indítás, egyetlen példány, hangkimenet-választás, napló,
  beállítás-export/import, beépített súgó, óraszinkron-figyelés.
- **Saját hangok:** saját csengőhang, dallam, jingle bemásolva a program mappájába; hiányzó hang helyett a
  beépített szól.
- **Átúsztatás:** a szünetzene számai egymásba úsznak (állítható, csengőnél azonnal elhallgat).
- **PIN-kód:** a beállító oldalak rendszergazda-PIN-nel zárhatók, a Vezérlőpult szabadon használható marad.
- **Rendkívüli események:** előre beállított tűzriadó-gyakorlat (magától indul és leáll), rendkívüli
  csengetés (pl. ünnepség kezdete) és csendes időszak (érettségi, mérés: nincs zene és bemondás, a csengő
  néma vagy halk).
- **Webes vezérlés telefonról:** csengetés, zene (a következő számok listájával, ugrással), bemondás
  szerkeszthető sablonokkal, mai kapcsolók, csendes időszak egy gombbal és riasztás böngészőből az iskolai
  hálózaton, jelszóval; a telefon kezdőképernyőjére is kitehető. Minden webes művelet naplózva.
- **Zenekérés QR-kóddal, automatikusan:** a diák beolvassa a QR-kódot, beírja a számot (vagy egy szám saját
  QR-kódját olvassa be), és ha a szám átmegy az ellenőrzésen, magától a szünetzene következő helyére kerül.
  Amit nem sikerül ellenőrizni, az a rendszergazdához kerül jóváhagyásra. Napi korlát telefononként,
  hosszkorlát, tiltólista, duplikátum-szűrés; a jóváhagyás kérése egy kapcsolóval visszaállítható.
  Külön zenekérő szerverrel a kérő oldal mobilnetről is elérhető (a program lekéri onnan a kéréseket), és
  nyomtatható A4-es plakát (PDF) is menthető a QR-kóddal. A szerver PHP-forrása a `zenekeres-szerver/` mappában van (Docker).
- **Tartalékgép:** két gép (pl. a hangosító Windows-gép és egy Pi) figyeli egymást; ha a fő gép kiesik, a
  tartalék kb. 15 másodpercen belül átveszi a csengetést, és visszaadja, amint a fő gép újra működik. A
  csengetési rendet és a naptárt a tartalék magától átveszi.
- **Hangerő-kiegyenlítés:** minden szám ugyanolyan hangosan szól (EBU R128 mérés ffmpeg-gel, egyszer, a
  háttérben); a csengő- és riasztóhangok hangereje nem változik.
- **Statisztika:** mi szólt, hányszor, mennyi kért szám, mennyire pontosak a csengetések; napi zeneidő,
  toplista, CSV-export (pl. jogdíj-elszámoláshoz), heti összefoglaló a webpanelen.
- **Tanév rendje importálása:** az iskola honlapjáról (kghsz.hu, a csengetési renddel együtt), .ics fájlból vagy
  Google Naptár/webcal linkről egy kattintással: szünetek szünnapként, rövidített és szombati munkanapok kivételnapként, előnézettel.
- **Hangzónák:** több hangkimenet (pl. folyosó, udvar, tanári), zónánként kapcsolható csengő, zene és
  bemondás, külön hangerővel; a riasztás mindig mindenhol szól.
- **Értesítés a rendszergazdának:** ntfy (telefon) vagy e-mail, ha kimaradt egy csengetés, hiba van, eltűnt
  a hangkimenet, riasztás indult vagy a tartalékgép átvette a csengetést; reggeli önteszt tanítási napokon.
- **Műsorblokkok:** szünetenként és naponként más zeneforrás, a szünet sorszáma szerint (rövidített napon is).
- **Szűrő:** trágár szavak (a csillagozott és számokkal írt alakok is), „Explicit” jelölés, saját tiltólista,
  korhatáros YouTube-videók kihagyása.
- **Moderálás:** a most szóló szám egy gombbal letiltható, a kért szám levehető a sorból, a visszaélő telefon egy
  hétre kizárható, a programból és a webpanelről is.
- **Dalszöveg-szűrő:** letölti a szám szövegét, pontozza a trágár szavakat, és a nagyon trágár számot kiveszi a
  sorból; három érzékenységi fokozat, MP3-ra, YouTube-ra, Spotifyra és a kért számokra is érvényes.
- **Világos és sötét téma**, a mai nap idővonala a Vezérlőpulton.
- **Automatikus frissítés a GitHubról:** saját frissítő ablak változáslistával; csak tanítási időn kívül
  települ magától, SHA-256-tal ellenőrzött csomagból (Windows-telepítő, Linux- és Debian-csomag, a Pi is).
- **Közgáz FM OS:** saját Raspberry Pi rendszer – bekapcsolás után kioszk módban indul, VNC-n távolról
  kezelhető, Spotify Connect hangszóró, hardveres watchdog és lefagyás-figyelő. Leírás: [pi-os/OLVASS-EL.md](pi-os/OLVASS-EL.md).

### Webes vezérlés és zenekérés

<p>
  <img src="docs/webpanel.png" width="560" alt="Webes vezérlés: csengetés, szünetzene a következő számokkal, zenekérések jóváhagyása, mai kapcsolók és menetrend">
  <img src="docs/zenekeres.png" width="220" alt="A diákok kérés-oldala telefonon">
</p>

### Tartalékgép

![Tartalékgép beállítása](docs/tartalek.png)

### Frissítés

![Frissítés](docs/frissites.png)

## Hogyan működik a dalszöveg-szűrő

1. A cím megtisztítása: a program leveszi a „(Official Video)”, „ft. …” és hasonló toldalékokat, és szétválasztja az
   előadót és a számot.
2. Dalszöveg-keresés az [LRCLIB](https://lrclib.net) nyilvános API-ján. Csak a szám címe és a diák által beírt keresőszó
   megy ki, a diák neve és a telefonja nem. Egy találat csak akkor számít, ha a cím, az előadó és a hossz is illik. Több
   változat (pl. rádiós és eredeti) közül a legtrágárabb dönt.
3. Pontozás: az erős szavak 5, a közepesek 3, az enyhék 1 pontot érnek. A program felismeri a toldalékos, ékezet
   nélküli, csillagozott és számokkal írt alakokat (`f*ck`, `sh1t`, `kurvára`), a hasonló ártatlan szavakat viszont nem
   bántja (`szarvas`, `baszk`, `pocsolya`).
4. Döntés: a szám trágár, ha elér egy adott számú erős szót, vagy túllép egy pontsűrűséget (pont / 100 szó).

| Érzékenység | Erős szó legfeljebb | Pontsűrűség legfeljebb |
| --- | --- | --- |
| Szigorú | 1 | 3 alatt |
| Normál (alap) | 4 | 5 alatt |
| Laza | 14 | 20 alatt |

Az eredményeket a program a gépen tárolja (csak a pontokat, a dalszöveget nem), ezért egy számot csak egyszer kérdez le.

**Korlátok.** Ez nem tökéletes szűrő. A szolgáltatás sok magyar számot nem ismer, és néha túlterhelt. Ha nincs meg a
szöveg, a saját listákban lévő szám a cím- és a korhatár-szűrés után lejátszható, a kért szám viszont nem kerül be
magától, hanem jóváhagyásra vár. A program azt vizsgálja, amit a videó címe állít: egy félrecímkézett videót nem
ismer fel. Az enyhén káromkodó szám normál fokozaton átmehet.

## Zenekérés API

A QR-kód a `http://<gép>:8080/keres` oldalra visz. Egy adott számot így lehet egyből kérni (ezt tartalmazza *A szám
QR-kódja* gombbal készült kód is), a telefon megnyitáskor rögtön elküldi a kérést:

```
http://<gép>:8080/keres?szam=Queen%20Don't%20Stop%20Me%20Now
```

Saját felületből az API is hívható, bejelentkezés nélkül, az iskolai hálózaton. A készüléket a `kfm_eszkoz` süti
azonosítja, ezt az első válasz állítja be:

```
GET  /api/v1/zenekeres    a kérés-oldal állapota és a saját mai kérések
POST /api/v1/zenekeres    {"szoveg": "Előadó – cím vagy YouTube-link", "nev": "10.B"}
```

A `POST` kéréshez `X-Kozgaz-FM: 1` fejléc kell. A kérés állapota a válaszban és a `GET` hívással követhető: `kereses`,
`varakozik`, `elfogadva`, `szol`, `elutasitva` (az `ok` mezőben az indokkal).

## Újdonságok az 1.19.2-ben

- Csiszoltabb felület: jobb kontraszt, egységesebb betűsúlyok, lekerekítések és térközök az asztali appban, a webes panelen és a PHP-felületen.

## Újdonságok az 1.19.1-ben

- DJ-szerű keverés: a számok egyenlő teljesítményű görbével úsznak át egymásba, a szám eleji és végi csend levágva.
  Kézi váltásnál (következő, ugrás, kért szám) rövid átúszás; csengőnél a zene 0,25 mp alatt halkul el, a csengő nem késik.
  Beállítás a Zene oldalon és a webes felületen: be/ki (alapból be), hossz 0–12 mp (alapból 5 mp).
- Megújult a diákok zenekérő oldala: telefonra szabott, világos és sötét mód, külön nézet a betöltésre, hibára és sikerre.
- Terv a zenekérés végleges megoldásáról: `docs/tervek/zenekeres-vegleges.md`.

## Újdonságok az 1.18.2-ben

- Saját riasztóhang: emelkedő szirénás söprés, ami másodpercenként ismétlődik, így jól elkülönül a csengőktől.
  Életszerű hangzás: hangszórós szirénahangszín, folyosói visszhang, és a söprések között apró eltérések vannak.
  Ez lett a riasztás alapértelmezett hangja; aki korábban mást állított be, annál a beállítás megmarad.
  A Csengetési rend oldalon „Riasztó” néven bármelyik hanghoz kiválasztható.

## Újdonságok az 1.18.1-ben

- Az asztali program webpaneljén is látszik a kért zenék szavazatszáma.

## Újdonságok az 1.18.0-ban

- **Szavazás a kérésekre:** a kérőoldalon látszanak a sorban lévő (elfogadott) kérések, és a diákok naponta 5
  szavazatot adhatnak rájuk (a sajátjukra nem). A több szavazatot kapott kérés előbb szól, egyenlőségnél a
  kérés sorrendje dönt; a most szóló számot ez nem mozdítja. A Kért zenék listában látszik a szavazatszám.

## Újdonságok az 1.17.0-ban

- **Hely a sorban:** a kérőoldalon az elfogadott kérésnél látszik, hányadik a kért zenék sorában
  („3. a sorban”, „Következő szám”). Az asztali és a webes Közgáz FM is elküldi a közvetítőnek.

## Újdonságok az 1.16.1-ben

- **Zenekérés bekapcsolása egy paranccsal:** `sudo kozgaz-fm-szerver zenekeres-be <kulcsfájl>` beállítja a webes
  Közgáz FM-ben a közvetítő címét, a kulcsot és a kérőoldalt, majd megvárja, hogy a rádió kapcsolódjon. Ha a gép
  nem éri el a közvetítőt, vagy rossz a kulcs, megmondja. Kikapcsolás: `zenekeres-ki`.

## Újdonságok az 1.16.0-ban

- **Zenekérés iskolai wifi nélkül:** új, ingyenes Cloudflare Worker közvetítő ([zenekeres-worker/](zenekeres-worker/README.md)).
  A diák mobilnetről a kérőoldalon küldi a kérést, az iskolai gép csak kifelé kérdezi le, így az iskola hálózatán
  semmit nem kell megnyitni. A kérőoldal (botirocky.github.io/kozgaz-fm) már ezt használja, a plakát és a QR-kód
  változatlan. Az iskolai gépen a Zenekérés beállításainál a szerver címét és kulcsát kell megadni.

## Újdonságok az 1.15.0-ban

- **Webes Közgáz FM a szervercsomagban:** a `kozgaz-fm-szerver` Debian-csomag a teljes, böngészőből kezelhető
  Közgáz FM-et is felrakja (PHP, Docker nélkül, forrás: [php/](php/README.md)). Bekapcsolás:
  `sudo kozgaz-fm-szerver fm-be <felhasználó>`; a hang a gép hangkimenetén szól, a felület jelszóval védett,
  távolról Tailscale-en érhető el. Az asztali program minden mostani funkciója megvan benne (kért zenék külön
  sorban, keverés, zenék a szerverről, új plakát, Napló PIN).

## Újdonságok az 1.14.1-ben

- A Napló oldal is PIN-kódot kér (ha van beállítva PIN).

## Újdonságok az 1.14.0-ban

- **Kért zenék külön sorban:** a kért zenék mindig elsőként szólnak, a kérés sorrendjében; ha elfogytak, az alap
  lista onnan folytatódik, ahol abbamaradt. A lejátszott kérés nem jön elő újra. A Zene oldalon, a Vezérlőpulton és a
  webpanelen is látszik, hol tart a lejátszás (pl. alap lista: 4/12).

## Újdonságok az 1.13.1-ben

- Új zenekérő plakát (Zene → Zenekérés → Plakát): nagy cím, kiemelt, vektoros QR-kód a kérő oldalra, három lépés.

## Újdonságok az 1.13.0-ban

- Keverés a webes vezérlőben is: *Véletlen sorrend (keverés)* kapcsoló és *Keverés most* gomb, ami a hátralévő
  számokat új sorrendbe rakja (a most szóló és a kért számok a helyükön maradnak). A Vezérlőpulton is van
  keverés gomb. API: `PATCH /api/v1/zene {"keveres": true|false}`, `POST /api/v1/zene/keveres`.

## Újdonságok az 1.12.0-ban

- Az iskola saját csengőhangjai lettek a beépített hangok: becsengő, kicsengő és jelzőcsengő. A korábbi
  generált hangok (klasszikus, rövid, dallamos, gong, riasztás) kikerültek; a régi beállítások maguktól átállnak
  (gong → jelzőcsengő, riasztás → kicsengő ismételve). Saját hang továbbra is választható.

## Újdonságok az 1.11.1-ben

- Javítva a Windows-os kiadás építése (az 1.10.0 és 1.11.0 újdonságai ezzel jelennek meg).

## Újdonságok az 1.11.0-ban

- A zenekérő szerver Debian-csomagot kapott (`kozgaz-fm-szerver_VERZIO_all.deb`): Docker nélkül, systemd-
  szolgáltatásként fut Debianon, Ubuntun és Raspberry Pi OS-en, a kulcsot telepítéskor generálja, és a
  `kozgaz-fm-szerver` paranccsal kezelhető. Leírás: [zenekeres-szerver/README.md](zenekeres-szerver/README.md).

## Újdonságok az 1.10.1-ben

- Ha a szerveren nincs bent a zenés pendrive (üres a zenemappa), a program nem törli a már letöltött zenéket,
  csak jelzi a hibát; a szerver ilyenkor 503-at ad.

## Újdonságok az 1.10.0-ban

- Zenék a szerverről: a program letölti a zenekérő szerver zenemappáját (például a szerverre dugott pendrive-ot)
  erre a gépre, és innen játssza le, így nem streamel a hálózaton. Csak az új vagy megváltozott fájlokat tölti
  le, a félbeszakadt letöltést folytatja, és a sebessége korlátozható (Zene → Zenék a szerverről).
- A zenekérő szerver új végpontjai: `GET /api/zenek` és `GET /api/zenek/fajl` (kulccsal, folytatható letöltéssel).

## Újdonságok az 1.9.0-ban

- A Riasztás oldal is a rendszergazda-PIN-hez kötött.
- Az elfogadott kért számok MP3-ként elmentődnek egy mappába (alapból „Közgáz FM kért számok” a saját mappádban).
- Kiválasztható, melyik szünetekben ne legyen szünetzene (Zene → Szünetzene beállításai).
- Zenekérő oldal a GitHubon (https://botirocky.github.io/kozgaz-fm/): a diákok mobilnetről is kérhetnek, a QR-kód
  és a plakát erre a címre mutathat (Zene → Zenekérés → Kérő oldal címe).

## Újdonságok az 1.8.0-ban

- Zenekérés: a hosszkorlátnál hosszabb számnak a program a rádiós változatát (radio edit) keresi meg, és csak
  azt játssza le; ha nincs ilyen, a kérést elutasítja.

## Újdonságok az 1.7.0-ban

- Visszakerült a riasztás (gomb, webpanel, tűzriadó-gyakorlat, riasztóhang, értesítés), de már saját oldalon
  (*Riasztás*, Ctrl+2), nem a Vezérlőpulton. Riasztáskor a program erre az oldalra ugrik.
- Görgetéskor a beállítások (legördülő listák, számmezők, időpontok, csúszkák) nem változnak meg véletlenül:
  a görgő mindig a lapot görgeti.

## Újdonságok az 1.6.0-ban

- Debian-csomag (`.deb`): Debian 12/13-ra és Ubuntu 22.04+-ra egy paranccsal telepíthető, menübejegyzéssel és ikonnal.
  Az önfrissítő a .deb-es telepítést is frissíti: a GitHubról letöltött, SHA-256-tal ellenőrzött csomagot egy kis
  rendszer-segéd telepíti (pkexec), amely csak a legújabb hivatalos kiadás csomagját fogadja el.

## Újdonságok az 1.4.0-ban

- Áttekinthetőbb Vezérlőpult: színes jelzés mutatja, hogy óra vagy szünet van, a következő csengetés szövegesen látszik
  (holnap, csütörtökön), szünnapon nem jelenik meg üres idővonal, a Mai menetrend kiemeli a következő eseményt.
- Csoportosított oldalsáv, *Ctrl+1* … *Ctrl+9* gyorsbillentyűk.
- Látható nyilak a lenyíló listákon és a számmezőkön, egységes jelölőnégyzetek, nagyobb térköz a gombok ikonja és szövege
  között, sötét módban is látható naptárnyilak.
- A Zene és a Naptár oldal kártyái alapméretű ablakban nem lógnak ki a képből.

## Újdonságok az 1.3.0-ban

- Az iskola adatai a kghsz.hu-ról: a *Tanév rendje…* ablak *Az iskola honlapjáról* gombja letölti a tanítási
  szüneteket, a tanításmentes munkanapokat és a csengetési rendet, előnézettel; a pipával választható, mi kerül át.
- Új telepítés már a valódi csengetési renddel indul (07:30–15:55, 9 óra) és a 2026/27-es szünetekkel; a meglévő
  beállításokat a frissítés nem írja át.

## Újdonságok az 1.2.0-ban

- Moderálás a programban és a webpanelen: a most szóló szám tiltása egy gombbal, kért szám levétele a sorból, telefon
  kizárása egy hétre, mindez feloldható és naplózva van.
- A letiltott szám minden forrásból kimarad (más feltöltésben is, ha a címe ugyanaz), és nem kérhető újra.

## Újdonságok az 1.1-ben

- Dalszöveg-szűrő: a nagyon trágár számok kiszűrése a szöveg pontozásával, három érzékenységgel, minden forrásra.
- Automatikus zenekérés: a QR-kóddal kért, ellenőrzött szám jóváhagyás nélkül a sorba kerül (kikapcsolható).
- Egy konkrét szám saját QR-kódja: beolvasásra rögtön elküldi a kérést.
- A cím-szűrő a csillagozott és számokkal írt trágár szavakat is felismeri.
- Ami nemrég szólt, azt egy ideig nem lehet újra kérni.

## Újdonságok az 1.0.0-ban

Az első stabil kiadás: a 0.x sorozat minden funkciója (csengetés, szünetzene, bemondás, naptár, webes
vezérlés, zenekérés, tartalékgép, hangzónák, értesítések, statisztika) kipróbálva, egy csomagban.

## Újdonságok a 0.10.0-ban

- Műsorblokkok: szünetenként és naponként más zeneforrás (pl. reggel nyugodt lista, nagyszünetben slágerek,
  pénteken buli-lista); a program forrásonként megjegyzi, hol tartott.
- Szűrő: beépített trágárszó-lista és „Explicit” jelölés, saját tiltólista (egész szó vagy szókezdet), korhatáros
  YouTube-videók kihagyása; a zenekérésre és a Spotifyra is érvényes.

## Újdonságok a 0.9.1-ben

- Hangzónák: több hangkimenet egyszerre, zónánként csengő / zene / bemondás és hangerő, próbahang zónánként.
- A felolvasott bemondás eSpeak NG-vel a kiválasztott zónákban szól.

## Újdonságok a 0.8.0-ban

- Értesítések a rendszergazdának telefonra (ntfy) vagy e-mailben: kimaradt csengetés, hibák, eltűnt
  hangkimenet, riasztás, tartalékgép-átvétel, a program újraindulása.
- Reggeli önteszt tanítási napokon: mai rend, hangkimenet, zeneforrás, tegnapi pontosság, frissítés.

## Újdonságok a 0.7.0-ban

- Hangerő-kiegyenlítés: nincs többé túl halk vagy túl hangos szám a folyosón.
- Statisztika oldal: zeneidő, toplista, kért számok, csengetési pontosság, CSV-export; heti összefoglaló a
  webpanelen.
- Tanév rendje importálása az iskola honlapjáról, .ics fájlból vagy naptárlinkről, előnézettel.
- A párbeszédablakok gombjai magyarul jelennek meg (Mégse, Igen, Nem).

## Újdonságok a 0.6.0-ban

- Rendkívüli események a Naptárban: tűzriadó-gyakorlat, rendkívüli csengetés, csendes időszak.
- Zenekérés diákoktól QR-kóddal, jóváhagyással.
- Tartalékgép: automatikus átvétel és visszaadás, beállítás-szinkron.
- Webpanel: zenesor és ugrás, bemondás-sablonok (a programmal közösek), csendes időszak telefonról, telepíthető ikon.
- A dalcímek mindenhol sima szövegként jelennek meg; a kért számok keresése csak a YouTube-on fut.

## Telepítés

- **Windows:** `KozgazFM-<verzió>-telepito.exe` a Releases oldalról (rendszergazdai jog nem kell).
- **Debian / Ubuntu:** `sudo apt install ./kozgaz-fm_<verzió>_amd64.deb` a Releases oldalról letöltött fájllal
  (eltávolítás: `sudo apt remove kozgaz-fm`, a beállítások a felhasználó mappájában megmaradnak).
- **Linux (más disztribúció):** `tar xzf KozgazFM-<verzió>-linux-x86_64.tar.gz && ./KozgazFM-*/telepites.sh`
- **Raspberry Pi:** `KozgazFM-OS-<verzió>-arm64.img.xz` Raspberry Pi Imagerrel SD-kártyára.

A már telepített példányok az önfrissítővel maguktól megkapják az új verziót (tanítási időn kívül).

## Fejlesztés

```bash
uv venv -p 3.14 && uv pip install -e ".[dev]"
.venv/bin/python -m kozgaz_fm
.venv/bin/pytest -q
.venv/bin/pyinstaller --noconfirm packaging/kozgaz-fm.spec
```

A beépített csengőhangokat az `eszkozok/hangok.py` generálja, a felület képernyőképeit az
`eszkozok/kepernyokep.py` készíti. A kiadást a `v*` tag indítja (GitHub Actions: Windows-telepítő,
Linux-csomag, Debian-csomag, wheel és Pi-lemezkép). A .deb helyben a PyInstaller-build után:
`packaging/debian/epit-deb.sh`. A Pi-kép helyben: `pi-os/epit.sh`.

Használati útmutató: [src/kozgaz_fm/sugo.md](src/kozgaz_fm/sugo.md) (a programban a *Súgó* oldalon is).
