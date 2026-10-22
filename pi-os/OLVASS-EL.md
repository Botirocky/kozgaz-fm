# Közgáz FM OS – Raspberry Pi

Saját Raspberry Pi rendszer az iskolai csengetéshez: bekapcsolás után magától elindul a Közgáz FM teljes
képernyőn, és csenget, zenét játszik a beállítások szerint. Billentyűzet és egér nélkül is működik, távolról
(VNC) kezelhető például a hangosító Windows-gépről.

Alap: hivatalos Raspberry Pi OS Lite (Debian 13 „trixie”, 64 bit) + labwc kioszk-felület + PipeWire hang +
magyar felolvasó (espeak-ng) + Spotify Connect (librespot) + wayvnc távoli asztal + automatikus
biztonsági frissítések.

## Mi kell hozzá?

| Eszköz | Megjegyzés |
| --- | --- |
| Raspberry Pi 4 (2 GB+) vagy Pi 5 | Pi 3 túl gyenge |
| microSD-kártya, 16 GB+ | A1/A2 osztályú ajánlott |
| Hangkimenet az erősítőhöz | Pi 4: 3,5 mm-es jack vagy HDMI; Pi 5: USB-hangkártya vagy HDMI |
| Hálózat | Kábel ajánlott (pontos idő, YouTube, Spotify, frissítés) |
| Monitor / érintőkijelző | Nem kötelező – VNC-n is kezelhető |

## Telepítés

1. Töltsd le a kiadásból a `KozgazFM-OS-<verzió>-arm64.img.xz` fájlt.
2. **Raspberry Pi Imager** → *Eszköz:* a Pi típusa → *Operációs rendszer:* *Saját kép használata* → a
   letöltött fájl → *Tároló:* az SD-kártya.
3. Az Imager *OS-testreszabás* ablakában beállítható a wifi, az SSH és a nyelv (nem kötelező).
4. **Jelszavak (erősen ajánlott):** írás után a kártya *bootfs* meghajtója Windows-on is megnyílik. Hozz létre
   rajta egy `kozgazfm.txt` fájlt:

   ```
   ADMIN_JELSZO=ide-az-uj-admin-jelszo
   VNC_JELSZO=ide-a-tavoli-asztal-jelszava
   GEPNEV=kozgaz-fm
   ```

   Az első indításkor a rendszer beállítja, majd biztonsági okból törli a fájlt.
5. Tedd be a kártyát, kösd a Pi hangkimenetét az erősítőre, és kapcsold be. Az első indítás 1–2 perc.

Alapértelmezett jelszavak (ha nincs `kozgazfm.txt`): rendszergazda `admin` / `kozgazfm`, VNC `kozgaz` /
`kozgazfm`. **Ezeket változtasd meg!** Amíg alapjelszó van a gépen, a Közgáz FM állapotsora pirosan figyelmeztet.
A figyelmeztetés eltűnik, ha a `kozgazfm.txt`-ben mindkét jelszót megadod. Ha kézzel (SSH-n, `passwd`) változtattál,
töröld a jelzőt: `sudo rm /etc/kozgaz-fm/alap-jelszo`.

## Távoli kezelés a Windows-gépről (VNC)

1. Telepítsd a **TigerVNC Viewer** programot (ingyenes).
2. Cím: `kozgaz-fm.local:5900` (vagy a Pi IP-címe, ez a Pi képernyőjén is látszik).
3. Felhasználó: `kozgaz`, jelszó: a VNC-jelszó.

VNC-hez monitor kell a Pi-n, vagy egy olcsó HDMI-„dummy” dugó.

## Beállítás

- **Hangkimenet:** a programban *Beállítások → Hangkimenet* (jack / HDMI / USB), *Próbahang* gombbal.
- **Pontos idő:** a Pi interneten szinkronizálja az órát. Ha nincs net, a bal alsó sarokban figyelmeztetés
  jelenik meg (*⚠ Az óra nincs szinkronban*). A Pi 5 elemmel működő órát (RTC) is tud tartani.
- **Spotify:** a Pi a hálózaton *Közgáz FM* nevű Spotify-hangszóróként jelenik meg. Első alkalommal egy
  telefonos/asztali Spotify appból (ugyanazon a hálózaton) válaszd ki egyszer, utána a Közgáz FM *Zene →
  Spotify* részében a *Lejátszó eszköz* listában is szerepel.
- **Újraindítás, leállítás:** *Beállítások → Rendszer*.

## Megbízhatóság

A csengetésnek akkor is mennie kell, ha valami elromlik – ezért a rendszer több szinten védekezik:

| Mi történik | Mit csinál a rendszer |
| --- | --- |
| A Közgáz FM összeomlik | 3 másodperc múlva magától újraindul |
| A Közgáz FM lefagy (nem válaszol) | 2 perc után az őr (`kozgaz-fm-or`) leállítja, és újraindul |
| Az egész rendszer megakad | A Pi hardveres watchdogja 15 másodperc után újraindítja a gépet |
| Áramszünet mentés közben | A beállítások biztonságosan íródnak (ideiglenes fájl + `fsync` + `.bak` tartalék) |
| Indulás pontos idő nélkül | A program legfeljebb 2 percig vár az internetes időszinkronra, hogy ne csengessen rossz időben |
| Az óra hirtelen ugrik | A kimaradt csengetéseket nem pótolja (nincs csengetés-sorozat), csak újraszinkronizál |

A rendszernapló legfeljebb 64 MB-ot foglal, hogy kímélje az SD-kártyát. Indításkor nincs szivárványos kép és
kernelszöveg, egyből a Közgáz FM jelenik meg.

Az őr és az újraindítások nyoma: `journalctl -t kozgaz-fm-or -t kozgaz-fm-kioszk`.

## Frissítés

- **A Közgáz FM** magától frissül a GitHubról, tanítási időn kívül (*Beállítások → Frissítések*).
- **A rendszer** biztonsági frissítéseit az `unattended-upgrades` naponta telepíti.
- Új lemezképet csak nagyobb változásnál kell írni – a beállítások exportálhatók (*Beállítások → Exportálás*).

## Hibakeresés (SSH: `ssh admin@kozgaz-fm.local`)

| Mit | Hol |
| --- | --- |
| Program naplója | `/home/kozgazfm/.config/kozgaz-fm/naplo.txt`, `hibanaplo.txt` |
| Felület naplója | `/home/kozgazfm/.cache/labwc.log` |
| Rendszer | `journalctl -b` |
| Idő | `timedatectl` |

## Építés (fejlesztőknek)

```bash
pi-os/epit.sh                 # Docker kell; x86 gépen arm64-emulációval (30–60 perc)
ADMIN_JELSZO=titok pi-os/epit.sh
```

Az eredmény: `dist/KozgazFM-OS-<verzió>-arm64.img.xz`. A kiadásnál a GitHub Actions natív arm64-gépen építi.
