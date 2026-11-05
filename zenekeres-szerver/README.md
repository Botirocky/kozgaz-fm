# Közgáz FM – zenekérő szerver (PHP)

A diákok ezen az oldalon kérnek zenét a QR-kóddal. Az iskolai Közgáz FM program néhány
másodpercenként lekéri innen az új kéréseket (`POST /api/gep`, `X-Kozgaz-FM-Kulcs` fejléc),
ellenőrzi őket (YouTube-keresés, dalszöveg- és korhatár-szűrő, tiltólista), és visszaküldi az
állapotukat, amit a diák a telefonján lát.

## Gyors telepítés: `telepites.sh`

A szervergépen (Debian/Ubuntu), ebben a mappában:

```
./telepites.sh                                       # telepítés vagy frissítés
./telepites.sh /srv/tarolok/PARKADAT/zenek           # zenemappa megadásával
./telepites.sh --funnel /srv/tarolok/PARKADAT/zenek  # + Tailscale Funnel, kívülről is elérhető
```

Ha kell, telepíti a Dockert, létrehozza a `.env`-et új kulccsal, beállítja az `adat/` mappa jogait,
elindítja és ellenőrzi a konténert, a végén kiírja a programba beírandó címet és kulcsot. Többször is
futtatható, a meglévő `.env`-et és adatokat megtartja. Az alábbi lépések ugyanezt írják le kézzel.

## Telepítés szervergépre (lépésről lépésre)

Debian/Ubuntu szerverre. A konténer csak a gépen belül, a `127.0.0.1:8100`-on figyel; kívülről a
Tailscale Funnel teszi elérhetővé.

### 1. Docker és git

```
sudo apt update && sudo apt install -y git curl
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER      # utána jelentkezz ki és be
```

### 2. A fájlok a szerverre

```
git clone https://github.com/botirocky/kozgaz-fm.git
cd kozgaz-fm/zenekeres-szerver
```

Git nélkül elég csak ezt a mappát átmásolni: `scp -r zenekeres-szerver felhasznalo@szerver:~/`

### 3. Beállítások (`.env`)

```
cp .env.minta .env
openssl rand -hex 24               # ez legyen a KFM_GEP_KULCS
nano .env
```

- `KFM_GEP_KULCS` – kötelező, a programban ugyanezt kell megadni.
- `ZENEKERES_ZENE` – a zenemappa (pl. a pendrive) útvonala; alapból `./zene`.
- `KFM_ENGEDETT_ORIGIN` – csak akkor kell, ha a kérőoldal nem a `https://botirocky.github.io` címről jön.

### 4. Az adatmappa jogai

A kérések adatbázisa (`zenekeres.sqlite`) az `adat/` mappába kerül. Ha ezt a Docker hozza létre, a
tulajdonosa root lesz, és a konténerben futó PHP (www-data, uid 33) nem tud bele írni. Ezért indítás előtt:

```
mkdir -p adat && sudo chown 33:33 adat
```

### 5. Indítás és ellenőrzés

```
docker compose up -d --build
curl http://127.0.0.1:8100/egeszseg
docker compose logs -f             # hibakereséshez
```

A `restart: unless-stopped` miatt a szerver újraindítása után magától elindul.

### 6. Elérhetővé tétel kívülről (Tailscale Funnel)

```
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
sudo tailscale funnel --bg --https=443 http://127.0.0.1:8100
tailscale funnel status            # itt látszik a https://<gép>.<tailnet>.ts.net cím
```

A Funnelt a Tailscale admin felületén is engedélyezni kell. Saját nyilvános IP-vel és domainnel Funnel
helyett Caddy vagy nginx is továbbíthat a `127.0.0.1:8100`-ra.

### 7. Összekötés a programmal

A programban: *Zene → Zenekérés diákoktól → Zenekérő szerver* = a Funnel-cím, *Szerver kulcsa* = a
`KFM_GEP_KULCS`.

### Frissítés, mentés

- Frissítés: `git pull && ./telepites.sh` (vagy `docker compose up -d --build`) (másolásnál a `.env`-et és az `adat/`-ot hagyd meg).
- Mentés: az `adat/` mappa és a `.env`.

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
