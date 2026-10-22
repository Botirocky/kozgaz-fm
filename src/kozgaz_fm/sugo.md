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

- **Most:** pontos idő, hányadik óra vagy szünet van, és mennyi van hátra a következő csengetésig.
- **Szünetzene:** forrásválasztó, lejátszás / szünet, előző / következő szám, leállítás, hangerő.
  A *Ma legyen szünetzene* kapcsolóval csak a mai napra kapcsolható ki az automatikus zene.
- **Gyors műveletek:**
  - *Csengetés most* – azonnali csengetés (a *Más hang…* menüben jelzőcsengő, kicsengő, gong is).
  - *Bemondás* – beírt szöveg felolvasása gonggal.
  - *RIASZTÁS* – folyamatos riasztó hang a leállításig, a zene azonnal elhallgat. Megerősítést kér.
  - *Ma legyen csengetés* – kikapcsolva ma egyáltalán nincs csengetés (kirándulás, rendezvény).
  - *Mai csengetési rend* – például *Rövidített* órák csak mára; éjfélkor visszaáll.
- **Mai menetrend:** a mai csengetések és szünetzenék listája, a következő ki van emelve.

## Csengetési rend

- Több rend is lehet (pl. *Normál*, *Rövidített*, *Vizsganap*). Új rendet az *Új* vagy a *Másolat* gombbal
  hozhatsz létre.
- Az időpontok közvetlenül a táblázatban szerkeszthetők. A program jelzi, ha egy óra vége a kezdete előtt van,
  vagy ha két óra átfedi egymást.
- **Jelzőcsengő:** a becsengetés előtt ennyi perccel szól egy rövid figyelmeztető csengő (0 = nincs).
- **Kicsengetés:** kikapcsolható, ha az iskolában csak becsengetés van.
- **Hangok:** minden csengőnek választható beépített hang vagy saját hangfájl (MP3, WAV stb.). A ▶ gombbal
  meghallgatható.

## Zene

### Forrástípusok

| Forrás | Mire jó | Mi kell hozzá |
| --- | --- | --- |
| **Mappa** | Egy mappa összes zenéje (almappákkal együtt) | Zenefájlok a gépen vagy hálózati meghajtón |
| **MP3-fájlok** | Kiválasztott fájlok vagy .m3u lejátszási lista | Zenefájlok |
| **YouTube** | Videó, lejátszási lista vagy keresőszó | Internet |
| **Spotify** | Lejátszási lista, album vagy szám | Spotify Premium + a gépen futó Spotify app |

### Szünetzene beállításai

- **Csak ennél hosszabb szünetben:** a rövid szünetekben nem indul zene.
- **Kicsengetés után ennyivel indul:** hogy a csengő ne keveredjen a zenével.
- **A következő csengő előtt ennyivel áll le:** a zene halkan elhallgat a jelző- vagy becsengő előtt.
- **Elhalkítás hossza:** milyen lassan halkuljon el a zene.
- **Reggeli zene:** az első óra előtt a megadott időponttól is szól zene.
- **YouTube-számok előre letöltése:** a következő számokat a program előre letölti, így nem akad és rövid
  internetkimaradásnál is szól. A letöltött fájlok a *Gyorsítótár ürítése* gombbal törölhetők.

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
- A naptárban pirossal a szünnapok, sárgával a kivételnapok látszanak; egy napra kattintva kiírja, milyen
  rend lesz aznap.

## Bemondások

- **Azonnali bemondás:** írd be a szöveget (vagy válassz sablont), és nyomd meg a *Bemondás most* gombot.
  Előtte gong szól, a zene közben lehalkul.
- **Ütemezett bemondás:** adott időpontban, a hét kiválasztott napjain vagy egyetlen napon. Lehet
  felolvasott szöveg vagy hangfájl (pl. Himnusz hétfő reggel, előre felvett üzenet).
- A felolvasáshoz a gépen kell magyar beszédhang. Windows-on: *Gépház → Idő és nyelv → Beszéd → Hangok
  hozzáadása → Magyar*.

## Folyosói kijelző

A bal alsó *Kijelző mód* gomb (vagy F11) teljes képernyős órát nyit: aktuális óra/szünet, visszaszámlálás,
haladásjelző, épp szóló szám. Több monitor esetén a *Beállítások → Folyosói kijelző* részben választható a
képernyő. Kilépés: **Esc** vagy dupla kattintás.

## Frissítések

A program magától keresi az új verziókat a GitHubon (indítás után és 6 óránként). Ha talál, a bal alsó
sarokban megjelenik: *↑ Új verzió*.

- **Automatikus telepítés tanítási időn kívül:** csak akkor frissít, ha nincs óra, nem szól zene, nincs
  riasztás, és a következő csengetésig legalább 45 perc van hátra (pl. délután vagy szünnapon).
- **Kézzel:** *Beállítások → Frissítések → Telepítés most*. A program pár másodpercre leáll, majd magától
  újraindul a beállítások megtartásával.
- A letöltött csomagot a program ellenőrzőösszeggel (SHA-256) ellenőrzi, sérült vagy hamis fájlt nem telepít.

## Napló és biztonsági mentés

- A **Napló** oldalon minden csengetés, zene és bemondás visszakereshető.
- **Beállítások → Exportálás:** minden beállítás egy fájlba menthető, és másik gépre importálható.

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

**Bezártam az ablakot, és nem találom.** A program a tálcán fut tovább (az óra melletti ikonok között).
A Start menüből újraindítva is előjön az ablak.
