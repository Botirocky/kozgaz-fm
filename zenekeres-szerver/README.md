# Közgáz FM – zenekérő szerver (PHP)

A diákok ezen az oldalon kérnek zenét a QR-kóddal. Az iskolai Közgáz FM program néhány
másodpercenként lekéri innen az új kéréseket (`POST /api/gep`, `X-Kozgaz-FM-Kulcs` fejléc),
ellenőrzi őket (YouTube-keresés, dalszöveg- és korhatár-szűrő, tiltólista), és visszaküldi az
állapotukat, amit a diák a telefonján lát.

## Telepítés Debianra (.deb, Docker nélkül)

Debian 12/13-on, Ubuntu 22.04-en vagy újabbon és Raspberry Pi OS-en (bookworm, trixie) a kiadások mellett
van egy `kozgaz-fm-szerver_VERZIO_all.deb` csomag is. PHP beépített szerverrel, systemd-szolgáltatásként fut,
és minden architektúrán megy (amd64, arm64).

```
wget https://github.com/Botirocky/kozgaz-fm/releases/latest/download/SHA256SUMS.txt
wget https://github.com/Botirocky/kozgaz-fm/releases/download/vVERZIO/kozgaz-fm-szerver_VERZIO_all.deb
sha256sum --ignore-missing -c SHA256SUMS.txt
sudo apt install ./kozgaz-fm-szerver_*_all.deb
```

A telepítő:

- létrehozza a `kozgaz-fm-szerver` rendszerfelhasználót,
- legenerálja a program kulcsát az `/etc/kozgaz-fm-szerver/szerver.env` fájlba (csak az első telepítéskor),
- elindítja és bekapcsolja a `kozgaz-fm-szerver` szolgáltatást: `http://127.0.0.1:8100`.

Az adatbázis a `/var/lib/kozgaz-fm-szerver` mappában van, a zenék alapból a `/var/lib/kozgaz-fm-szerver/zene`
mappába kerülnek. Frissítésnél (`sudo apt install ./új.deb`) a beállítások, a kulcs és az adatok megmaradnak.

## Webes Közgáz FM ugyanebben a csomagban

A csomag a teljes, böngészőből kezelhető Közgáz FM-et is tartalmazza (csengetés, szünetzene, kért zenék,
bemondás, napló). Ez nem indul el magától, mert tudnia kell, melyik felhasználó hangrendszerén szóljon:

```
sudo kozgaz-fm-szerver fm-be <felhasználó>
```

- bekapcsolja a `kozgaz-fm-web@<felhasználó>` (webes felület, `0.0.0.0:8080`) és a
  `kozgaz-fm-demon@<felhasználó>` (lejátszó) szolgáltatást,
- bekapcsolja a felhasználó „lingering” módját, így a PipeWire bejelentkezés nélkül, a gép indulásakor is fut,
- telepíti a friss yt-dlp-t a `/var/lib/kozgaz-fm-ytdlp` mappába (frissítés: `sudo kozgaz-fm-szerver ytdlp-frissites`),
- ha még nincs webes jelszó, beállít egy véletlen kezdő jelszót, és kiírja (belépés után átírható).

Az adatok a felhasználó `~/.local/share/kozgaz-fm-web` mappájában vannak, a zenék alapból a `~/Zenék`
mappából jönnek; ezek a csomag eltávolítása után is megmaradnak. Port, cím, mappák:
`sudo kozgaz-fm-szerver fm-beallitas` (`/etc/kozgaz-fm-szerver/fm.env`: `KFM_WEB_CIM`, `KFM_WEB_PORT`,
`KOZGAZ_FM_ADAT`, `KOZGAZ_FM_ZENE`).

**Távoli elérés:** a felület a helyi hálózaton a gép címén érhető el (`http://GÉP:8080`). Iskolán kívülről a
legegyszerűbb a [Tailscale](https://tailscale.com): telepítsd a gépre (`curl -fsSL https://tailscale.com/install.sh | sh`,
`sudo tailscale up`), és a saját eszközeidről a gép Tailscale-címén (`http://100.x.y.z:8080`) éred el. Az
`fm-be` és az `allapot` parancs ki is írja ezt a címet. Nyilvános internetre (port-továbbítás, Funnel) ne tedd ki.

### Kezelés

```
kozgaz-fm-szerver allapot         a szolgáltatás és a /egeszseg válasza
sudo kozgaz-fm-szerver kulcs      a program kulcsa (Zene → Zenekérés → Szerver kulcsa)
sudo kozgaz-fm-szerver uj-kulcs   új kulcs, újraindítással (a programban is át kell írni)
sudo kozgaz-fm-szerver beallitas  a szerver.env szerkesztése, utána újraindít
kozgaz-fm-szerver naplo [sorok]   a szolgáltatás naplója
sudo kozgaz-fm-szerver ujraindit

sudo kozgaz-fm-szerver fm-be [felhasználó]   webes Közgáz FM be (első jelszóval)
sudo kozgaz-fm-szerver fm-ki                 webes Közgáz FM ki (az adatok maradnak)
kozgaz-fm-szerver fm-naplo [sorok]           a webes felület és a lejátszó naplója
sudo kozgaz-fm-szerver fm-beallitas          az fm.env szerkesztése, utána újraindít
sudo kozgaz-fm-szerver pin-torles            elfelejtett PIN törlése
sudo kozgaz-fm-szerver jelszo-torles         elfelejtett webes jelszó törlése (megnyitáskor újat kér)
sudo kozgaz-fm-szerver ytdlp-frissites       a yt-dlp frissítése
```

### Beállítások (`/etc/kozgaz-fm-szerver/szerver.env`)

| Kulcs | Alap | Mire jó |
| --- | --- | --- |
| `KFM_GEP_KULCS` | (generált, 48 hex) | az iskolai program ezzel azonosítja magát, legalább 24 karakter |
| `KFM_CIM` | `127.0.0.1` | ezen a címen figyel; `0.0.0.0` = a helyi hálózatról is elérhető |
| `KFM_PORT` | `8100` | port |
| `KFM_ZENE_MAPPA` | `/var/lib/kozgaz-fm-szerver/zene` | a letölthető zenék mappája (pl. egy felcsatolt pendrive) |
| `KFM_ENGEDETT_ORIGIN` | `https://botirocky.github.io` | a GitHubos kérő oldal címe (CORS), vesszővel több is megadható |
| `PHP_CLI_SERVER_WORKERS` | `4` | párhuzamos kiszolgáló folyamatok |

A zenemappát a `kozgaz-fm-szerver` felhasználónak olvasnia kell. A `/home` alatti mappa is megadható, de
csak olvasásra éri el (a szolgáltatás `ProtectHome=read-only`). Pendrive esetén csatold fel olvashatóan, pl.
vfat-nál `uid=kozgaz-fm-szerver` vagy `umask=022` opcióval.

### Kívülről elérhetővé tétel

A szerver alapból csak a gépen belül figyel. A diákok mobilnetről a Tailscale Funnelen át érik el:

```
sudo tailscale funnel --bg --https=443 http://127.0.0.1:8100
```

Másik lehetőség egy fordított proxy (Caddy, nginx) HTTPS-sel a `127.0.0.1:8100` elé; a szerver a proxy
`X-Forwarded-For` fejlécének utolsó elemét veszi a diák IP-címének.

### Eltávolítás

```
sudo apt remove kozgaz-fm-szerver   # a beállítások és az adatok maradnak
sudo apt purge kozgaz-fm-szerver    # mindent töröl (kulcs, adatbázis, a /var/lib alatti zenék)
```

### Hibakeresés

- `kozgaz-fm-szerver allapot` szerint nem fut → `kozgaz-fm-szerver naplo`; gyakori ok, hogy a port foglalt
  (`sudo ss -ltnp | grep 8100`), vagy hiányzik a `KFM_GEP_KULCS`.
- A program „Hibás kulcs” hibát ír → a programban megadott kulcs nem egyezik a `sudo kozgaz-fm-szerver kulcs`
  kimenetével.
- `/api/zenek` 503-at ad → a zenemappa nem létezik, üres, vagy a pendrive nincs felcsatolva.

A csomag építése a repó gyökeréből: `zenekeres-szerver/debian/epit-deb.sh [kimeneti mappa]` (`dpkg-deb` kell).

## Futtatás Dockerrel

```
cp .env.minta .env    # KFM_GEP_KULCS = hosszú véletlen kulcs (openssl rand -hex 24)
docker compose up -d --build
```

A konténer a `127.0.0.1:8100`-on figyel; kívülről a Tailscale Funnel teszi elérhetővé:
`sudo tailscale funnel --bg --https=443 http://127.0.0.1:8100`.

A programban: *Zene → Zenekérés diákoktól → Zenekérő szerver* = a Funnel-cím, *Szerver kulcsa* = a
`KFM_GEP_KULCS`.

## Zenék a szerverről

A `ZENEKERES_ZENE` mappa (alapból `./zene`, a picloudon a Kingston pendrive: `/srv/tarolok/PARKADAT/zenek`)
csak olvashatóan a konténer `/zene` mappájába kerül. Az iskolai program innen tölti le a zenéket a saját
gépére (*Zene → Zenék a szerverről*), és onnan játssza, így nem streamel a hálózaton.

## Végpontok

- `GET /` – a diákoldal
- `GET|POST /api/zenekeres` – a diák kérései (süti: `kfm_eszkoz`)
- `POST /api/gep` – az iskolai gép egyeztetése (kulccsal)
- `GET /api/zenek` – a szerver zenemappájának listája (kulccsal; útvonal, méret, módosítás ideje)
- `GET /api/zenek/fajl?ut=…` – egy zenefájl letöltése (kulccsal)
- `GET /egeszseg` – állapot (`radio`: él-e az iskolai gép kapcsolata)
