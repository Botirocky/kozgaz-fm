# Közgáz FM – zenekérő szerver (PHP)

A diákok ezen az oldalon kérnek zenét a QR-kóddal. Az iskolai Közgáz FM program néhány
másodpercenként lekéri innen az új kéréseket (`POST /api/gep`, `X-Kozgaz-FM-Kulcs` fejléc),
ellenőrzi őket (YouTube-keresés, dalszöveg- és korhatár-szűrő, tiltólista), és visszaküldi az
állapotukat, amit a diák a telefonján lát.

## Futtatás

```
cp .env.minta .env    # KFM_GEP_KULCS = hosszú véletlen kulcs (openssl rand -hex 24)
docker compose up -d --build
```

A konténer a `127.0.0.1:8100`-on figyel; kívülről a Tailscale Funnel teszi elérhetővé:
`sudo tailscale funnel --bg --https=443 http://127.0.0.1:8100`.

A programban: *Zene → Zenekérés diákoktól → Zenekérő szerver* = a Funnel-cím, *Szerver kulcsa* = a
`KFM_GEP_KULCS`.

## Végpontok

- `GET /` – a diákoldal
- `GET|POST /api/zenekeres` – a diák kérései (süti: `kfm_eszkoz`)
- `POST /api/gep` – az iskolai gép egyeztetése (kulccsal)
- `GET /egeszseg` – állapot (`radio`: él-e az iskolai gép kapcsolata)
