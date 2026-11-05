# Közgáz FM – webes változat (PHP)

Ugyanaz a csengetőrendszer és szünetzene, mint az asztali program, de böngészőből kezelve: csengetési rend,
naptár, zene és zeneforrások, kért zenék külön sorban, bemondás, riasztás, napló, statisztika, folyosói
kijelző, zenekérő oldal és plakát. A hang annak a gépnek a hangkimenetén szól, amelyiken fut.

Két részből áll:

- **webes felület** (`public/`, `src/Web/`): a PHP beépített szerverén fut, alapból a 8080-as porton,
  jelszóval védve; a beállító oldalak (és a Napló) PIN-kóddal is zárhatók;
- **lejátszó démon** (`bin/demon.php`): mpv-vel játssza a csengőt és a zenét a PipeWire/PulseAudio
  hangrendszeren, a lassú dolgokat (YouTube, dalszöveg, hangerőmérés, zenék letöltése) a `bin/munka.php`
  háttérfolyamatban végzi.

A beállításfájl (`beallitasok.json`) ugyanaz, mint az asztali programé, oda-vissza átvihető.

## Telepítés Debianra

A `kozgaz-fm-szerver` csomag tartalmazza (lásd [../zenekeres-szerver/README.md](../zenekeres-szerver/README.md)):

```
sudo apt install ./kozgaz-fm-szerver_*_all.deb
sudo kozgaz-fm-szerver fm-be <felhasználó>
```

A felhasználó az, akinek a gépére a hangosítás csatlakozik. A parancs kiírja a címet és az első jelszót.

## Docker (fejlesztéshez)

```
docker compose up -d --build
./teszt.sh
```

A `docker-compose.yml` a gép PipeWire-jét adja át a démonnak (`$XDG_RUNTIME_DIR/pulse/native`), a zenék a
`KFM_ZENE_MAPPA` (alapból `~/Zenék`) mappából jönnek.
