# Közgáz FM – használati útmutató

A Közgáz FM az iskola csengetőrendszere és szünetzene-lejátszója. A program a beállított csengetési rend szerint
magától csenget, a szünetekben zenét játszik (saját MP3-ak, YouTube vagy Spotify), és be tud mondani
üzeneteket is.

> **A legfontosabb:** a csengetés csak akkor működik, ha a program fut. Bezáráskor a tálcán (az óra mellett)
> fut tovább. A gép ne menjen alvó állapotba.

## Első beállítás (5 perc)

1. **Beállítások → Hangkimenet:** válaszd ki azt a kimenetet, amelyik az erősítőre / hangosításra van kötve,
   és nyomd meg a *Próbahang* gombot.
2. **Beállítások → Automatikus indítás:** kapcsold be, így a gép indulása után a program magától elindul.
3. **Csengetési rend:** ellenőrizd az órák kezdetét és végét. A *Generálás…* gombbal pár másodperc alatt
   elkészíthető egy teljes rend (óra hossza, szünetek, nagyszünet).
4. **Heti beosztás:** állítsd be, melyik napon melyik rend legyen (hétvégén: *Nincs csengetés*).
5. **Naptár:** az *Ünnepnapok betöltése* gomb felveszi a munkaszüneti napokat. A tanítási szüneteket
   (őszi, téli, tavaszi, nyári) a *Hozzáadás* gombbal add meg.
6. **Zene:** adj hozzá legalább egy zeneforrást, és nyomd meg az *Ez szóljon* gombot.

## Vezérlőpult

Az oldalak között a *Ctrl+1* … *Ctrl+9* billentyűkkel is lehet váltani.

- **Most:** pontos idő, hányadik óra vagy szünet van, és mennyi van hátra a következő csengetésig.
- **Szünetzene:** forrásválasztó, lejátszás / szünet, előző / következő szám, leállítás, hangerő.
  A *Ma legyen szünetzene* kapcsolóval csak a mai napra kapcsolható ki az automatikus zene.
- **Gyors műveletek:**
  - *Csengetés most* – azonnali csengetés (a *Más hang…* menüben jelzőcsengő, kicsengő, gong és a saját
    hangok is).
  - *Bemondás* – beírt szöveg felolvasása gonggal.
  - *Ma legyen csengetés* – kikapcsolva ma egyáltalán nincs csengetés (kirándulás, rendezvény).
  - *Mai csengetési rend* – például *Rövidített* órák csak mára; éjfélkor visszaáll.
- **Mai menetrend:** a mai csengetések és szünetzenék listája, a következő ki van emelve.

## Riasztás

Külön oldal az oldalsávban (*Ctrl+2*), szándékosan nem a Vezérlőpulton, hogy véletlenül ne lehessen elindítani.
Ha van rendszergazda-PIN, a Riasztás oldal is csak a PIN megadása után nyílik meg.

- *Riasztás indítása* – megerősítés után folyamatos riasztó hang minden hangszóróban (minden zónában, teljes
  hangerővel) a leállításig. A szünetzene azonnal elhallgat, közben nincs csengetés és bemondás.
- Riasztáskor a program előjön, és magától erre az oldalra ugrik; itt a *Riasztás leállítása* gombbal állítható le.
- A riasztó hangja a *Csengetési rend* oldalon cserélhető, előre beállított gyakorlathoz lásd a
  *Rendkívüli események* részt. A webpanelről is indítható és leállítható.

## Csengetési rend

- Több rend is lehet (pl. *Normál*, *Rövidített*, *Vizsganap*). Új rendet az *Új* vagy a *Másolat* gombbal
  hozhatsz létre.
- Az időpontok közvetlenül a táblázatban szerkeszthetők. A program jelzi, ha egy óra vége a kezdete előtt van,
  vagy ha két óra átfedi egymást.
- **Jelzőcsengő:** a becsengetés előtt néhány perccel szól egy rövid figyelmeztető csengő. A kapcsolóval
  kikapcsolható; ilyenkor csak becsengő (és kicsengő) van.
- **Kicsengetés:** kikapcsolható, ha az iskolában csak becsengetés van.
- **Hangok:** minden csengőnek választható beépített vagy saját hang. A ▶ gombbal meghallgatható.
- **Saját hangok:** a *Hozzáadás…* gombbal (vagy a hanglisták *Saját hang hozzáadása…* sorával) saját
  csengőhang, dallam vagy jingle tehető be (MP3, WAV, M4A, OGG, FLAC…, legfeljebb 30 MB). A program bemásolja a
  saját adatmappájába (`hangok`), így az eredeti fájl áthelyezhető vagy törölhető. A betett hangok átnevezhetők
  és törölhetők; ha egy használatban lévő hangot törölsz, helyette a beépített alaphang szól.
- **Biztonság:** ha a beállított hangfájl valamiért hiányzik, a csengő nem marad néma – a beépített hang szól.

## Zene

### Forrástípusok

| Forrás | Mire jó | Mi kell hozzá |
| --- | --- | --- |
| **Mappa** | Egy mappa összes zenéje (almappákkal együtt) | Zenefájlok a gépen vagy hálózati meghajtón |
| **MP3-fájlok** | Kiválasztott fájlok vagy .m3u lejátszási lista | Zenefájlok |
| **YouTube** | Videó, lejátszási lista vagy keresőszó | Internet |
| **Spotify** | Lejátszási lista, album vagy szám | Spotify Premium + a gépen futó Spotify app |

### Szünetzene beállításai

- **Zene nélküli szünetek:** pipáld be, melyik szünetekben ne induljon szünetzene (*Reggel* = tanítás előtt,
  *1.* = az 1. óra utáni szünet). A csengetést nem érinti.
- **Csak ennél hosszabb szünetben:** a rövid szünetekben nem indul zene.
- **Kicsengetés után ennyivel indul:** hogy a csengő ne keveredjen a zenével.
- **Átúsztatás a számok között:** a szám vége előtt ennyi másodperccel már indul a következő, és a kettő
  egymásba úszik (mint a rádióban). 0 = a számok szünet nélkül, egymás után szólnak. Csengetésnél és bemondásnál
  a kifutó szám azonnal elhallgat. YouTube-számoknál csak akkor úszik át, ha a következő már le van töltve.
- **A következő csengő előtt ennyivel áll le:** a zene halkan elhallgat a jelző- vagy becsengő előtt.
- **Elhalkítás hossza:** milyen lassan halkuljon el a zene.
- **Reggeli zene:** az első óra előtt a megadott időponttól is szól zene.
- **YouTube-számok előre letöltése:** a következő számokat a program előre letölti, így nem akad és rövid
  internetkimaradásnál is szól. A letöltött fájlok a *Gyorsítótár ürítése* gombbal törölhetők.
- **Hangerő-kiegyenlítés:** a program minden számnak megméri a hangosságát (egyszer, a háttérben), és úgy
  szabályozza, hogy mind ugyanolyan hangosan szóljon – nincs túl halk vagy fülsértően hangos dal. A csengő-,
  riasztó- és bemondáshangok hangereje nem változik. A Spotify a saját kiegyenlítését használja. Az új számok mérése pár
  másodperc; ha egy szám még nincs megmérve, az első másodpercekben áll be a helyes hangerő.

### Műsorblokkok

Szünetenként és naponként más zeneforrás szólhat. Példák: reggel (*Tanítás előtt*) a nyugodt lista, a
nagyszünetben (pl. *3. szünet*) a slágerek, pénteken egész nap a buli-lista. *Zene → Műsorblokkok → Új blokk*:
név, forrás, napok, és hogy minden szünetben vagy csak a kijelöltekben szóljon.

- A szünet **sorszáma** számít (az „1. szünet” az 1. óra utáni), így rövidített napokon is ugyanaz a lista szól.
- Ha több blokk illik, a listában **feljebb álló** nyer (a nyilakkal rendezhető).
- Ha egyik sem illik, a kiválasztott (*Ez szóljon*) forrás szól.
- Ha egy szünetben kézzel másik forrást választasz, az a szünet végéig érvényes, utána újra a blokkok döntenek.
- A program forrásonként megjegyzi, hol tartott (4 órán át), így a visszatérő lista nem az elejéről kezdi.

### Szűrő

A szűrőn fennakadó szám nem kerül a lejátszási sorba, és diák sem kérheti.

- **Beépített lista:** gyakori magyar és angol trágár szavak, valamint az „Explicit” jelölésű címek; a Spotifyon
  az explicit jelölésű számokat átugorja.
- **Korhatáros YouTube-videók kihagyása:** a 18+ besorolású videót nem tölti le, hanem a következő számra lép.
- **Saját tiltólista:** soronként egy szó, előadó vagy cím. Alapból egész szóra illeszkedik („szar” nem szűri ki a
  „szarvas”-t); csillaggal a végén szókezdetre („bunkó*” → „bunkók”). Kis- és nagybetű, ékezet mindegy.
- A cím mellett a fájl mappájának neve (pl. előadó szerinti mappák) és Spotifynál az előadó is számít.
- A *Próba* mezőbe írt címről azonnal látszik, átengedné-e a szűrő.
- **Nagyon trágár dalszövegek kiszűrése:** a program a szám címe alapján letölti a dalszöveget az LRCLIB
  szolgáltatásról, és pontozza a trágár szavakat. A trágárnak ítélt szám kikerül a sorból, Spotifyon átugorja. Csak a
  szám címe és a beírt keresőszó megy ki az internetre, és csak a pontszámot tárolja, a szöveget nem. A címet „előadó - cím” formában
  érdemes megadni, különben nem biztos, hogy megtalálja.
- **Érzékenység:** *Szigorú* (már két erős szó is elég), *Normál* (öt erős szó, vagy sok közepes), *Laza* (csak a
  végig káromkodó számok). A *Dalszöveg ellenőrzése* gomb megmutatja, mit szólna egy számhoz.
- Ha egy szám szövege nincs meg, vagy a szolgáltatás nem érhető el, a saját listák száma lejátszható (a cím- és
  korhatár-szűrés ettől még él). A szűrő nem tévedhetetlen: a sok magyar számnak nincs meg a szövege, és egy
  félrecímkézett videót nem ismer fel.

### Zenék a szerverről

Ha a zenék egy szerveren vannak (például a zenekérő szerver gépére dugott pendrive-on), a program letölti őket
erre a gépre, és innen játssza le. Így szünetben nem a hálózaton streamel, és akkor is szól, ha éppen nincs net.

1. Előbb állítsd be a **Zenekérés diákoktól** kártyán a zenekérő szerver címét és kulcsát (ugyanezt használja).
2. A **Zenék a szerverről** kártyán kapcsold be a *Zenék letöltése a szerverről* kapcsolót.
3. Az első letöltés után megjelenik egy új zeneforrás, *Zenék a szerverről* néven. Válaszd ki, vagy tedd be egy
   műsorblokkba.

- Félóránként megnézi a szervert, és csak az új vagy megváltozott fájlokat tölti le, egyszerre egyet. A *Letöltés
  most* gomb azonnal megnézi.
- Ha félbeszakad a letöltés, onnan folytatja, ahol abbamaradt. Amit a szerverről törölsz, azt itt is törli, de a
  mappába saját kezűleg tett fájlokhoz nem nyúl.
- A **Sebességkorlát** megadja, legfeljebb milyen gyorsan töltsön, hogy ne lassítsa le az iskolai netet (0 =
  korlátlan).
- A letöltési mappa gépenként külön állítható, a biztonsági mentés nem viszi át másik gépre.

### Zenekérés diákoktól

A diákok telefonról kérhetnek számot a szünetekre. Az ellenőrzésen átment szám magától a sorba kerül, ha az
*Automatikus hozzáadás* be van kapcsolva (alapból igen); kikapcsolva minden kérés jóváhagyásra vár.

1. *Zene → Zenekérés diákoktól → Zenekérés bekapcsolása.*
2. **Zenekérő szerverrel (ajánlott):** add meg a *Zenekérő szerver* címét és a *Szerver kulcsát*. A diákok ekkor
   az interneten, mobilnetről is elérik a kérő oldalt; a program néhány másodpercenként lekéri onnan az új
   kéréseket, és visszaküldi az állapotukat. A kártya alján látszik, hogy él-e a kapcsolat. Ha a program nem fut
   (pl. éjjel), az oldal kiírja, hogy az iskolarádió most nem elérhető.
   **Szerver nélkül:** kapcsold be a webes vezérlést (*Beállítások → Webes vezérlés*); ekkor csak az iskolai
   hálózatra csatlakozott telefonok érik el a gépet (pl. `http://192.168.1.50:8080/keres`).
3. Megjelenik a kérés-oldal címe és QR-kódja. A QR-kód a folyosói kijelzőn is látszik; a *Plakát (PDF)* gomb
   nyomtatható A4-es plakátot ment a QR-kóddal és a tudnivalókkal, a *QR-kód mentése* csak a kódot.
4. A diák beírja az előadót és a címet (vagy bemásolja a YouTube-linket), a program megkeresi a YouTube-on.
5. A program ellenőrzi a címet, a korhatárt, a hosszt és a dalszöveget. Ha minden rendben, a szám a szünetzene
   következő helyére kerül; a diák a telefonján látja, hogy elfogadták, majd hogy szól.

**A kért zenék sorrendje:** a kért zenék külön sorba kerülnek, és mindig ezek szólnak először, a kérés sorrendjében
(aki elsőként kért, azé szól elsőnek, a második kérés másodiknak). A most szóló szám még végigmegy, utána jönnek a
kérések. Ha elfogytak, az alap lejátszási lista onnan folytatódik, ahol abbamaradt. A lejátszott kérés kikerül a
sorból, nem jön elő újra. A *Zene → Lejátszási sor* kártyán külön látszik a *Kért zenék* és az *Alap lejátszási
lista*, kiemelve, hol tart az alap lista (pl. 4/12). Ugyanez látszik a Vezérlőpulton és a webpanelen is.
6. A *Jóváhagyásra váró kérések* listájába (a programban és a webpanelen is) az kerül, amit nem sikerült
   ellenőrizni: nincs meg a dalszövege, nem érhető el a szolgáltatás, vagy már 10 elfogadott szám vár a sorra. A sorban
   látszik az ok; *Elfogadás* után ugyanúgy a sorba kerül.

**Egy konkrét szám QR-kódja:** írd be a számot a QR-kód alatti mezőbe, és mentsd el *A szám QR-kódja* gombbal. Aki ezt
beolvassa, annak a telefonja rögtön elküldi a kérést; a kérésre ugyanazok a szabályok vonatkoznak.

Szabályok, amelyeket a program magától betart:

- **Napi korlát** telefononként (alapból 3 szám), és óránként legfeljebb 20 kérés egy hálózati címről.
- **Hosszkorlát** (alapból 7 perc); élő adás és lejátszási lista nem kérhető. Ha a kért szám hosszabb, a program
  megkeresi a YouTube-on a rádiós változatát (*radio edit*, *radio version*), és csak azt teszi a sorba – a
  kérések listájában ez megjegyzésként látszik. Ha nincs a korláton belüli rádiós változat, a kérés elutasul.
- **Kért számok MP3-ba:** az elfogadott kért számok MP3-ként a megadott mappába kerülnek (a cím lesz a
  fájlnév). Kikapcsolható, a mappa a Zenekérés kártyán választható.
- **Kérő oldal címe:** ha megadod (pl. a GitHubon futó https://botirocky.github.io/kozgaz-fm/ oldalt), a QR-kód,
  a plakát és a folyosói kijelző erre a címre mutat.
- **Tiltólista:** soronként egy szó vagy előadó; ha a kérésben vagy a talált címben szerepel, a kérés nem megy át.
- Ugyanazt a számot nem lehet kétszer kérni, amíg az előző vár vagy szólni fog, és a már lejátszottat is csak
  legalább 12 óra múlva.
- **Trágár szöveg:** a dalszöveg-szűrőn fennakadó szám nem kérhető, és nem fogy vele a napi keret.
- Csak YouTube-ról keres; más weboldal linkjét nem fogadja el. Spotify forrás mellett a kért szám nem
  játszható le (mappa, MP3 vagy YouTube forrás kell).
- A kérések a program újraindításáig maradnak meg.

### Moderálás

Ha valami mégsem való a folyosóra, a *Zene → Moderálás* kártyán és a webpanel *Zenekérések* részében beavatkozhatsz.
Minden művelet bekerül a naplóba, a tiltások pedig feloldhatók.

- **A most szóló szám tiltása:** azonnal a következő számra lép, és a szám többé nem szól. A webpanelen a *Szünetzene*
  résznél van a *Szám tiltása* gomb.
- **Levétel a sorból:** a kért szám kikerül a lejátszási sorból, ha éppen szól, akkor a következő jön. Ezt a számot utána
  kb. 12 óráig senki nem kérheti újra, és a diák napi kerete sem nő vissza.
- **Szám tiltása:** a szám minden forrásból kimarad, és nem kérhető, amíg fel nem oldod. A cím is számít, ezért
  ugyanannak a számnak egy másik feltöltése is kiesik, ha a címe az előadóval együtt ugyanaz.
- **Telefon tiltása:** az adott telefon egy hétig nem kérhet, a függő és sorban álló kérései törlődnek.

A telefon tiltása a böngészőben tárolt azonosítón alapul, ezért a sütik törlésével vagy privát ablakkal megkerülhető. A
hálózati címenkénti óránkénti korlát ettől még él. A tiltás feloldása után a már kivett szám a következő betöltéskor
kerül vissza a listába. A tartalékgép átveszi a letiltott számokat, a letiltott telefonokat nem.

### Spotify összekapcsolása (egyszer kell)

1. Nyisd meg a [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) oldalt, és lépj be
   az iskola Spotify Premium fiókjával.
2. *Create app* → adj neki nevet (pl. Közgáz FM), a **Redirect URI** legyen pontosan:
   `http://127.0.0.1:8898/callback`, az API-k közül jelöld be a *Web API*-t.
3. Másold ki a **Client ID**-t, és illeszd be a Zene oldal Spotify részébe.
4. Nyomd meg a *Bejelentkezés* gombot, és a böngészőben engedélyezd a hozzáférést.
5. Indítsd el a gépen a Spotify alkalmazást, és válaszd ki a *Lejátszó eszköz* listában.

A Spotify a saját alkalmazásában beállított hangkimenetet használja – azt is az erősítőre állítsd.

## Naptár

- **Szünnap:** nincs csengetés és szünetzene (ünnepek, tanítási szünetek, igazgatói napok).
- **Kivételnap:** egy adott napon más rend érvényes (pl. rövidített órák), vagy szünnapon / hétvégén is
  legyen csengetés (pl. szombati tanítási nap).
- A naptárban pirossal a szünnapok, sárgával a kivételnapok, kékkel aláhúzva a rendkívüli események látszanak;
  egy napra kattintva kiírja, milyen rend lesz aznap.

### Tanév rendje importálása

A **Szünnapok** kártyán a *Tanév rendje…* gombbal az iskola naptára egyszerre betölthető: *Az iskola honlapjáról*
(kghsz.hu), `.ics` fájlból vagy naptárlinkről (Google Naptárban: a naptár beállításai → *Titkos cím iCal
formátumban*; webcal:// link is jó). Az előnézetben látszik, mi mivé válik:

- a **szünetek**, tanítás nélküli munkanapok és ünnepek **szünnapok** lesznek;
- a **rövidített órás** napok kivételnapok a „Rövidített” renddel (ha van ilyen nevű rend);
- a **szombati munkanapok** kivételnapok a hétköznapi renddel;
- a többi esemény (ünnepség, szülői értekezlet) nem érinti a csengetést, csak a listában látszik.

Amit nem szeretnél, arról vedd le a pipát. A már meglévő szünnapokat nem veszi fel újra.

A honlapról a **csengetési rend** is átvehető: ha eltér a jelenlegitől, külön pipa jelenik meg az előnézet fölött,
rajta a két rend összevetésével. A *Normál* rend a házirend csengetési órarendjéből jön (9 óra), ha az nem olvasható,
a honlap csengetési rendjéből. A *Rövidített* rendet csak akkor írja felül, ha a honlapon valóban eltér a normáltól.
A nemzeti ünnepek nincsenek a honlapon, azokat az *Ünnepnapok betöltése* gomb veszi fel.

### Rendkívüli események

Egyszeri, előre beállított események a *Naptár → Rendkívüli események* részben (*Hozzáadás*). A pipával
ideiglenesen kikapcsolhatók, törlés nélkül.

- **Tűzriadó-gyakorlat:** a megadott időpontban magától elindul a riasztás, és a beállított idő (pl. 3 perc)
  után leáll; 0 perc = kézi leállításig. A folyosói kijelző előre nem mutatja, a gyakorlat meglepetés maradhat.
  Ha közben valaki kézzel indít riasztást, azt a gyakorlat vége nem állítja le.
- **Rendkívüli csengetés:** a megadott időpontban egyszer megszólal a kiválasztott hang (pl. ünnepség kezdete,
  fogadóóra vége). Szünnapon és „ma nincs csengetés” mellett is szól.
- **Csendes időszak:** kezdettől végig nincs szünetzene és ütemezett bemondás; a csengő néma, vagy ha kéred,
  halk (pl. 25%). Érettségire, mérésre, ünnepségre. A Vezérlőpulton kiírja, hogy épp csendes időszak van.
  A webpanelről egy gombbal is indítható „most, N percre”, és ott be is fejezhető.

## Bemondások

- **Azonnali bemondás:** írd be a szöveget (vagy válassz sablont), és nyomd meg a *Bemondás most* gombot.
  Előtte gong szól, a zene közben lehalkul.
- **Sablonok:** a sablonlista melletti **+** gomb a beírt szöveget sablonként elmenti, a kuka a kiválasztott
  sablont törli. A sablonok a webpanelen is megjelennek (egy koppintással beilleszthetők), és ott is menthetők.
- **Ütemezett bemondás:** adott időpontban, a hét kiválasztott napjain vagy egyetlen napon. Lehet
  felolvasott szöveg vagy hangfájl (pl. Himnusz hétfő reggel, előre felvett üzenet).
- A felolvasáshoz a gépen kell magyar beszédhang. Windows-on: *Gépház → Idő és nyelv → Beszéd → Hangok
  hozzáadása → Magyar*.

## Folyosói kijelző

A bal alsó *Kijelző mód* gomb (vagy F11) teljes képernyős órát nyit: aktuális óra/szünet, visszaszámlálás,
haladásjelző, épp szóló szám, és ha a zenekérés be van kapcsolva, a kérés-oldal QR-kódja. Több monitor esetén a *Beállítások → Folyosói kijelző* részben választható a
képernyő. Kilépés: **Esc** vagy dupla kattintás.

## Frissítések

A program magától keresi az új verziókat a GitHubon (indítás után és 6 óránként). Ha talál, a bal alsó
sarokban megjelenik: *↑ Új verzió*.

- **Automatikus telepítés tanítási időn kívül:** csak akkor frissít, ha nincs óra, nem szól zene, nincs
  riasztás, és a következő csengetésig legalább 45 perc van hátra (pl. délután vagy szünnapon).
- **Kézzel:** *Beállítások → Frissítések → Telepítés most*. A program pár másodpercre leáll, majd magától
  újraindul a beállítások megtartásával.
- A letöltött csomagot a program ellenőrzőösszeggel (SHA-256) ellenőrzi, sérült vagy hamis fájlt nem telepít.

## Hozzáférés (PIN-kód)

- *Beállítások → Hozzáférés → PIN beállítása…*: 4–8 számjegyű PIN. Ezután a **Csengetési rend**, **Zene**,
  **Naptár**, **Bemondások**, **Napló** és **Beállítások** oldal csak a PIN megadása után nyílik meg.
- A **Riasztás** oldal is a PIN-hez kötött (ugyanaz a PIN).
- A **Vezérlőpult** (csengetés most, bemondás, zene, mai kapcsolók), a **Statisztika** és a **Súgó** PIN
  nélkül is használható – a napi működéshez nem kell PIN.
- Feloldás után a beállítások a megadott ideig (alapból 5 perc) tétlenség után maguktól újra zárolódnak; a bal
  alsó *Beállítások zárolása* gombbal azonnal is zárolhatók. Ha a program a tálcára kerül, szintén zárol.
- 5 hibás próbálkozás után 60 másodpercig nem lehet újra próbálni.
- **Elfelejtett PIN:** futtasd egyszer a `KozgazFM.exe --pin-torles` parancsot (Linuxon / Pi-n:
  `kozgaz-fm --pin-torles`). Ha a program közben fut, azonnal megkapja; a többi beállítás megmarad.
- A PIN a véletlen vagy kéretlen átállítás ellen véd; aki a géphez rendszergazdaként hozzáfér, az a PIN-t
  törölni tudja. A PIN-t a program csak titkosítva (sózott kivonatként) tárolja, és exportáláskor nem kerül a
  fájlba (a webpanel jelszava és bekapcsolása sem).

## Webes vezérlés (telefonról)

A Vezérlőpult legfontosabb gombjai böngészőből is elérhetők, az iskolai hálózaton bármelyik telefonról vagy gépről:
csengetés most (más hanggal is), szünetzene indítása / leállítása / következő szám, zeneforrás és hangerő,
bemondás felolvasása, mai kapcsolók és mai csengetési rend, riasztás – és látszik a visszaszámláló meg a mai menetrend.

- **Bekapcsolás:** *Beállítások → Webes vezérlés → Webpanel bekapcsolása*. Első bekapcsoláskor jelszót kér
  (legalább 8 karakter). Alatta megjelenik a cím, például `http://192.168.1.50:8080` – ezt kell a telefon
  böngészőjébe beírni (a *Cím másolása* gombbal vágólapra tehető). Érdemes a telefonon kezdőképernyőre tenni.
- **Windows:** az első bekapcsoláskor a Windows tűzfal rákérdez – engedélyezd a **magánhálózaton**.
- **Biztonság:** csak jelszóval lehet belépni; 5 hibás próbálkozás után 60 másodpercig senki nem próbálkozhat.
  A belépés 12 óra tétlenség után lejár, jelszócserekor mindenki kilép. A beállító oldalak (csengetési rend, zene
  forrásai, naptár stb.) a weben **nem** módosíthatók. Minden webes művelet a gép IP-címével bekerül a **Napló**ba.
- A kapcsolat nem titkosított (HTTP), ezért csak az iskolai belső hálózaton használd, ne tedd ki az internetre.
- A port (alapból 8080) a beállításoknál módosítható, ha azt már más program használja.
- **Szünetzene:** a *Következik* lista a következő számokat mutatja; egy számra koppintva azonnal az szól.
- **Csendes időszak most:** a *Ma* részben választható hossz (15 perc – 3 óra), opcionálisan halk csengővel.
  Amíg tart, felül kék sáv jelzi, és a *Vége most* gombbal befejezhető.
- **A telefon kezdőképernyőjére** a böngésző menüjéből (*Hozzáadás a kezdőképernyőhöz*) tehető ki ikonként.

## Tartalékgép (két gép)

Ha két gép is be van kötve a hangosításba (például a hangosító Windows-gép és egy Közgáz FM OS-es Raspberry Pi,
keverőn át), a kettő figyelheti egymást: a **tartalék** csak akkor csenget, ha a **fő gép** kiesett.

1. A fő gépen: *Beállítások → Tartalékgép → Ennek a gépnek a szerepe: Ez a fő gép.* A program generál egy közös
   kulcsot; a másoló gombbal vágólapra teheted. A *Másik gép címe* mezőbe a tartalék gép címe kerül (pl.
   `192.168.1.60:8080`); ez nem kötelező, de így a fő gép állapotsora is mutatja, hogy a tartalék él-e.
2. A tartalék gépen: szerep *Ez a tartalék gép*, cím a fő gép címe (pl. `192.168.1.50:8080`), kulcsnak a fő gépről
   másolt kulcs.
3. Az állapot alul látszik: *A fő gép működik, ez a gép készenlétben vár.*

Működés:

- A tartalék 5 másodpercenként jelet kér a fő géptől. Ha háromszor egymás után nem kap választ (a gép leállt,
  lefagyott, elment az áram vagy a hálózat), kb. 15 másodpercen belül **átveszi a csengetést**, a zenét és a
  bemondásokat. Ha az átvétel előtti utolsó percben kimaradt egy csengetés, azt pótolja.
- Amint a fő gép újra válaszol, a tartalék **visszaáll készenlétbe**.
- A tartalék 5 percenként **átveszi a fő gépről** a csengetési rendet, a heti beosztást, a naptárt, a rendkívüli
  eseményeket, a bemondásokat, a sablonokat és a mai kapcsolókat (a *Szinkronizálás most* gombbal azonnal is).
  A zeneforrásokat, a hangkimenetet és a jelszavakat nem, ezeket gépenként kell beállítani.
- Készenlétben a tartalék gépen is lehet kézzel csengetni és bemondani.
- A két gép a webes vezérlés portján beszél (a webpanel jelszava nélkül is elindul, de csak a kulccsal válaszol).
  Windows-on a tűzfalban engedélyezd a magánhálózaton. A forgalom nem titkosított, ezért csak az iskolai belső
  hálózaton használd, és a kulcsot ne add ki.

## Statisztika

A **Statisztika** oldalon látszik, mennyi zene szólt, melyik számok mentek a legtöbbször, hány kért szám volt, és
hogy a csengetések mennyire pontosak (átlagos eltérés a beállított időtől). Időszak: ma, az elmúlt 7 vagy 30 nap,
vagy az egész tanév. A *Lejátszási lista mentése (CSV)* gomb Excelben megnyitható listát készít (dátum, idő,
cím, forrás, kért szám-e, hossz) – például jogdíj-elszámoláshoz. Az elmúlt hét összefoglalója a webpanelen is
látszik. Az adatok 400 napig maradnak meg.

## Hangzónák (több hangkimenet)

Ha az iskolában több külön hangosítás van (pl. folyosó, udvar, tanári), a **Beállítások → Hangzónák** kártyán
mindegyik kaphat saját hangkimenetet (hangkártyát, USB-s hangkártyát, HDMI-t). Zónánként beállítható:

- **Csengő** – szóljon-e itt a becsengő, kicsengő, jelzőcsengő;
- **Zene** – szóljon-e itt a szünetzene (pl. a tanáriban ne);
- **Bemondás** – hallják-e itt a bemondásokat (a gongot is);
- **Hangerő** – halkítás ebben a zónában (100% = teljes, 50% = halkabb); a riasztást nem halkítja.

A **riasztás mindig minden zónában szól**, ezt nem lehet kikapcsolni. A ▶ gombbal próbahangot játszhatsz csak az
adott zónában. Ha egy zóna eszköze nem érhető el (kihúzták), ott az alapértelmezett kimenet szól, és a program
figyelmeztet (értesítést is küld, ha be van kapcsolva). Üres zónalistánál minden a felső Hangkimenetre megy.

A **felolvasott bemondás** a zónákra a magyar *eSpeak NG* hanggal megy (a Közgáz FM OS-ben benne van; Windowson
az eSpeak NG telepítése után). Ha nincs eSpeak NG, a felolvasott szöveg a gép alapértelmezett kimenetén szól,
a gong és a hangfájlos bemondás viszont zónák szerint. A zónák gépenként külön állítandók (az export nem viszi át).

## Értesítések a rendszergazdának

**Beállítások → Értesítések a rendszergazdának.** A program szól a telefonodra vagy e-mailben, ha baj van:

- **kimaradt csengetés** – a gép aludt, lefagyott vagy ugrott az órája, és emiatt csengetés maradt ki (időponttal);
- **hiba** – hiányzik egy hangfájl, nem játszható a zene, nincs felolvasó hang;
- **hangkimenet** – kihúzták az erősítő kábelét, vagy nincs hangkártya;
- **riasztás indult**, illetve a **tartalékgép átvette** vagy visszaadta a csengetést;
- **a program elindult** – ha nem te indítottad, összeomlás vagy áramszünet lehetett;
- **reggeli önteszt** tanítási napokon a megadott időben: mai rend, első csengetés, hangkimenet, zeneforrás,
  tegnapi csengetések pontossága, elérhető frissítés.

Ugyanaz az üzenet fél órán belül nem ismétlődik.

**Telefonra (ntfy, ingyenes):** telepítsd az *ntfy* alkalmazást, iratkozz fel egy hosszú, nehezen kitalálható
témára (pl. `kozgaz-fm-7f3k9q2x`), és a beállításokba a teljes címet írd: `https://ntfy.sh/kozgaz-fm-7f3k9q2x`.
Aki ismeri a témanevet, olvashatja az értesítéseket, ezért ne használj egyszerű nevet. Saját ntfy-szervernél
tokent is megadhatsz.

**E-mailben:** a címzett(ek) mellé az iskola SMTP-szervere kell (Gmailnél `smtp.gmail.com`, 587-es port,
STARTTLS és alkalmazásjelszó). A *Próbaértesítés küldése* gombbal azonnal kipróbálhatod. Az értesítési
beállításokat (ntfy-cím, token, SMTP-adatok) a beállítás-exportálás nem viszi át másik gépre, minden gépen
külön kell megadni.

## Napló és biztonsági mentés

- A **Napló** oldalon minden csengetés, zene és bemondás visszakereshető.
- **Beállítások → Exportálás:** minden beállítás egy fájlba menthető, és másik gépre importálható.

## Közgáz FM OS (Raspberry Pi)

- A Pi-n a Közgáz FM bekapcsolás után magától, teljes képernyőn indul. Távolról VNC-vel kezelhető
  (például TigerVNC Viewer): a cím a *Beállítások → Rendszer* panelen látszik (`IP-cím:5900`), felhasználó `kozgaz`.
- **Alapértelmezett jelszavak:** rendszergazda `admin` / `kozgazfm`, VNC `kozgaz` / `kozgazfm`. Amíg ezek vannak
  beállítva, az állapotsor pirosan figyelmeztet. Megváltoztatás: az SD-kártya *bootfs* meghajtóján hozz létre egy
  `kozgazfm.txt` fájlt `ADMIN_JELSZO=…` és `VNC_JELSZO=…` sorokkal, és indítsd újra a Pi-t – a rendszer beállítja,
  majd törli a fájlt.
- Ha a program lefagy, 2 perc múlva magától újraindul; ha az egész gép megakad, a hardveres watchdog újraindítja.
- Indításkor a program legfeljebb 2 percig vár a pontos időre (internetes időszinkron). Kábeles hálózat ajánlott.

## Gyakori kérdések

**Nem szól a csengő.** Ellenőrizd a hangkimenetet (*Beállítások → Próbahang*), a csengők hangerejét
(*Csengetési rend → Csengők hangereje*), és hogy a mai napon van-e csengetés (Vezérlőpult, *Mai menetrend*).

**Nem indul a zene a szünetben.** A szünet hosszabb-e a beállított minimumnál? Be van-e kapcsolva a
*Ma legyen szünetzene*? Van-e kiválasztott forrás?

**A Spotify nem indul.** Fut-e a Spotify alkalmazás a gépen? Premium-e a fiók? A Zene oldalon frissítsd az
eszközlistát.

**A YouTube nem játszik le.** Van-e internet? Ha előre letöltött számok vannak, azok net nélkül is szólnak.
A YouTube időnként változtat a rendszerén – ilyenkor a program frissítése segít.

**Raspberry Pi-n (Közgáz FM OS) fut a program.** A Pi-t a hangosító Windows-gépről is kezelheted
távoli asztallal (VNC): `kozgaz-fm.local:5900`. Részletek: a Pi-hez mellékelt *Közgáz FM OS* leírásban.

**A telefon nem éri el a webpanelt.** Ugyanazon a hálózaton van-e a telefon, mint a hangosító gép (nem mobilneten)?
A *Beállítások → Webes vezérlés* alatt zöld-e az állapot? Windows-on a tűzfalban engedélyezve van-e a Közgáz FM
a magánhálózaton? Egyes vendég-wifik elszigetelik a készülékeket egymástól – ilyenkor a tanári hálózatot használd.

**A diákok nem érik el a kérés-oldalt.** Ugyanazon a wifin vannak-e, mint a hangosító gép? A diák-wifi gyakran
el van választva a tanári hálózattól; ilyenkor a rendszergazdának kell átjárást nyitnia a gép webes portjára,
vagy a zenekérést a tanári hálózatról lehet használni.

**A tartalék gép „nem fogadta el a kulcsot” hibát ír.** A két gépen eltér a kulcs: másold át újra a fő gépről.

**Bezártam az ablakot, és nem találom.** A program a tálcán fut tovább (az óra melletti ikonok között).
A Start menüből újraindítva is előjön az ablak.
