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
- **Riasztás:** folyamatos riasztó hang egy gombbal, megerősítéssel.
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
- **Zenekérés diákoktól:** QR-kód a folyosói kijelzőn → a diák telefonról kér számot (cím vagy
  YouTube-link), a rendszergazda jóváhagyja, és a szám a szünetzene következő helyére kerül. Napi korlát
  telefononként, hosszkorlát, tiltólista, duplikátum-szűrés.
- **Tartalékgép:** két gép (pl. a hangosító Windows-gép és egy Pi) figyeli egymást; ha a fő gép kiesik, a
  tartalék kb. 15 másodpercen belül átveszi a csengetést, és visszaadja, amint a fő gép újra működik. A
  csengetési rendet és a naptárt a tartalék magától átveszi.
- **Hangerő-kiegyenlítés:** minden szám ugyanolyan hangosan szól (EBU R128 mérés ffmpeg-gel, egyszer, a
  háttérben); a csengő- és riasztóhangok hangereje nem változik.
- **Statisztika:** mi szólt, hányszor, mennyi kért szám, mennyire pontosak a csengetések; napi zeneidő,
  toplista, CSV-export (pl. jogdíj-elszámoláshoz), heti összefoglaló a webpanelen.
- **Tanév rendje importálása:** az iskola naptára (.ics fájl vagy Google Naptár/webcal link) egy kattintással:
  szünetek szünnapként, rövidített és szombati munkanapok kivételnapként, előnézettel.
- **Hangzónák:** több hangkimenet (pl. folyosó, udvar, tanári), zónánként kapcsolható csengő, zene és
  bemondás, külön hangerővel; a riasztás mindig mindenhol szól.
- **Értesítés a rendszergazdának:** ntfy (telefon) vagy e-mail, ha kimaradt egy csengetés, hiba van, eltűnt
  a hangkimenet, riasztás indult vagy a tartalékgép átvette a csengetést; reggeli önteszt tanítási napokon.
- **Világos és sötét téma**, a mai nap idővonala a Vezérlőpulton.
- **Automatikus frissítés a GitHubról:** saját frissítő ablak változáslistával; csak tanítási időn kívül
  települ magától, SHA-256-tal ellenőrzött csomagból (Windows-telepítő, Linux-csomag és a Pi is).
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
- Tanév rendje importálása .ics fájlból vagy naptárlinkről, előnézettel.
- A párbeszédablakok gombjai magyarul jelennek meg (Mégse, Igen, Nem).

## Újdonságok a 0.6.0-ban

- Rendkívüli események a Naptárban: tűzriadó-gyakorlat, rendkívüli csengetés, csendes időszak.
- Zenekérés diákoktól QR-kóddal, jóváhagyással.
- Tartalékgép: automatikus átvétel és visszaadás, beállítás-szinkron.
- Webpanel: zenesor és ugrás, bemondás-sablonok (a programmal közösek), csendes időszak telefonról, telepíthető ikon.
- A dalcímek mindenhol sima szövegként jelennek meg; a kért számok keresése csak a YouTube-on fut.

## Telepítés

- **Windows:** `KozgazFM-<verzió>-telepito.exe` a Releases oldalról (rendszergazdai jog nem kell).
- **Linux:** `tar xzf KozgazFM-<verzió>-linux-x86_64.tar.gz && ./KozgazFM-*/telepites.sh`
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
Linux-csomag, wheel és Pi-lemezkép). A Pi-kép helyben: `pi-os/epit.sh`.

Használati útmutató: [src/kozgaz_fm/sugo.md](src/kozgaz_fm/sugo.md) (a programban a *Súgó* oldalon is).
