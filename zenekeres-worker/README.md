# Közgáz FM zenekérő közvetítő (Cloudflare Worker)

Nyilvános, ingyenes közvetítő a diákok telefonja és az iskolai gép között. A diák a
[kérőoldalról](https://botirocky.github.io/kozgaz-fm/) ide küldi a kérést, az iskolai gép
(asztali vagy webes Közgáz FM) pedig 4 másodpercenként **kifelé** lekérdezi. Az iskola
hálózatán így semmit nem kell befelé megnyitni.

A protokoll ugyanaz, mint a `zenekeres-szerver/` PHP-s változaté (`/api/zenekeres`,
`/api/gep`, `/egeszseg`), csak D1 (SQLite) adatbázissal. Zenefájlokat nem tárol, ezért az
`/api/zenek` 503-at ad.

## Telepítés

```sh
cd zenekeres-worker
npm install
npx wrangler login
npx wrangler d1 create kozgazfm-zenekeres
```

A kapott `database_id`-t írd be a `wrangler.toml`-ba, majd:

```sh
npx wrangler d1 execute kozgazfm-zenekeres --remote --file schema.sql
openssl rand -hex 24 | tee /dev/tty | npx wrangler secret put KFM_GEP_KULCS
npx wrangler deploy
```

Az iskolai gépen: **Zene → Zenekérés diákoktól**
- *Szerver címe*: a deploy után kiírt `https://kozgazfm-zenekeres.<fiók>.workers.dev`
- *Szerver kulcsa*: a fenti kulcs
- *Kérő oldal címe*: `https://botirocky.github.io/kozgaz-fm/`

A `docs/zenekeres.js` `SZERVER` állandójának a Worker címére kell mutatnia.

Ellenőrzés: `curl https://…workers.dev/egeszseg`, ebben `"radio": true`, ha az iskolai gép kapcsolódik.

## Helyi próba

```sh
echo 'KFM_GEP_KULCS=helyi-proba-kulcs-0123456789abcdef' > .dev.vars
npx wrangler d1 execute kozgazfm-zenekeres --local --file schema.sql
npx wrangler dev --local
npm test
```

## Keret és kikapcsolás

Az ingyenes csomag napi 100 000 kérést enged. Az iskolai gép napi kb. 21 600 kérést küld,
a többi a diákoké. A gép adatait legfeljebb 30 másodpercenként írja, ha nem változtak.

Kikapcsolás: `npx wrangler delete`, vagy a Cloudflare-felületen a Worker letiltása.
