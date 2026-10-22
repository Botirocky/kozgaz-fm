__lazy_modules__ = [
    "base64",
    "contextlib",
    "hashlib",
    "json",
    "re",
    "secrets",
    "threading",
    "time",
    "urllib.error",
    "urllib.parse",
    "urllib.request",
    "webbrowser",
    "http.server",
    "pathlib",
]

import base64
import contextlib
import hashlib
import json
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PORT = 8898
ATIRANYITAS = f"http://127.0.0.1:{PORT}/callback"
JOGOK = ("user-read-playback-state user-modify-playback-state user-read-currently-playing "
         "playlist-read-private playlist-read-collaborative")
API = "https://api.spotify.com/v1"
TOKEN_URL = "https://accounts.spotify.com/api/token"

_URI_MINTA = re.compile(r"(?:open\.spotify\.com/(?:intl-[a-z-]+/)?|spotify:)(playlist|album|track|artist|show)[/:]"
                        r"([A-Za-z0-9]{10,})")


class SpotifyHiba(Exception):
    pass


def spotify_uri(cim: str) -> str | None:
    talalat = _URI_MINTA.search(cim.strip())
    return f"spotify:{talalat.group(1)}:{talalat.group(2)}" if talalat else None


class Spotify:
    def __init__(self, client_id: str, token_ut: Path) -> None:
        self.client_id = client_id.strip()
        self.token_ut = token_ut
        self._zar = threading.Lock()
        self._token: dict = {}
        with contextlib.suppress(FileNotFoundError, json.JSONDecodeError):
            self._token = json.loads(token_ut.read_text(encoding="utf-8"))

    @property
    def bejelentkezve(self) -> bool:
        return bool(self._token.get("refresh_token")) and bool(self.client_id)

    def kijelentkezes(self) -> None:
        self._token = {}
        self.token_ut.unlink(missing_ok=True)

    def bejelentkezes(self, idokorlat: float = 180.0) -> None:
        if not self.client_id:
            raise SpotifyHiba("Előbb add meg a Spotify Client ID-t a beállításokban.")
        ellenorzo = secrets.token_urlsafe(64)
        kihivas = base64.urlsafe_b64encode(hashlib.sha256(ellenorzo.encode()).digest()).rstrip(b"=").decode()
        allapot = secrets.token_urlsafe(16)
        eredmeny: dict[str, str] = {}

        class Kezelo(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                kerdes = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                if kerdes.get("state", [""])[0] == allapot:
                    eredmeny.update({k: v[0] for k, v in kerdes.items()})
                siker = "code" in eredmeny
                uzenet = ("Sikeres Spotify-bejelentkezés! Ezt az ablakot bezárhatod, és visszatérhetsz "
                          "a Közgáz FM-hez." if siker else "A bejelentkezés nem sikerült, próbáld újra.")
                torzs = (f"<!doctype html><meta charset=utf-8><title>Közgáz FM</title><body style='font-family:"
                         f"sans-serif;background:#0b1220;color:#f1f5f9;display:grid;place-items:center;"
                         f"height:100vh;margin:0'><h2>{uzenet}</h2></body>").encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(torzs)))
                self.end_headers()
                self.wfile.write(torzs)

            def log_message(self, *args) -> None:
                pass

        try:
            szerver = HTTPServer(("127.0.0.1", PORT), Kezelo)
        except OSError as e:
            raise SpotifyHiba(f"A {PORT}-es port foglalt, a bejelentkezés nem indítható.") from e
        szerver.timeout = 1.0
        webbrowser.open("https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
            "client_id": self.client_id, "response_type": "code", "redirect_uri": ATIRANYITAS,
            "code_challenge_method": "S256", "code_challenge": kihivas, "scope": JOGOK, "state": allapot,
        }))
        hatarido = time.monotonic() + idokorlat
        try:
            while not eredmeny and time.monotonic() < hatarido:
                szerver.handle_request()
        finally:
            szerver.server_close()
        if "code" not in eredmeny:
            raise SpotifyHiba(eredmeny.get("error") and f"A Spotify elutasította: {eredmeny['error']}"
                              or "Lejárt az idő, a bejelentkezés megszakadt.")
        self._token_keres({"grant_type": "authorization_code", "code": eredmeny["code"],
                           "redirect_uri": ATIRANYITAS, "client_id": self.client_id, "code_verifier": ellenorzo})

    def _token_keres(self, adat: dict) -> None:
        keres = urllib.request.Request(TOKEN_URL, data=urllib.parse.urlencode(adat).encode(),
                                       headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(keres, timeout=15) as v:
                uj = json.loads(v.read())
        except urllib.error.HTTPError as e:
            if e.code in (400, 401):
                self.kijelentkezes()
                raise SpotifyHiba("A Spotify-bejelentkezés lejárt, jelentkezz be újra.") from e
            raise SpotifyHiba(f"Spotify tokenhiba ({e.code})") from e
        except urllib.error.URLError as e:
            raise SpotifyHiba("Nem érhető el a Spotify (nincs internet?).") from e
        uj["lejar"] = time.time() + int(uj.get("expires_in", 3600)) - 60
        uj.setdefault("refresh_token", self._token.get("refresh_token"))
        self._token = uj
        self.token_ut.write_text(json.dumps(uj), encoding="utf-8")

    def _hozzaferes(self) -> str:
        with self._zar:
            if not self.bejelentkezve:
                raise SpotifyHiba("Nincs Spotify-bejelentkezés.")
            if time.time() >= self._token.get("lejar", 0):
                self._token_keres({"grant_type": "refresh_token", "refresh_token": self._token["refresh_token"],
                                   "client_id": self.client_id})
            return self._token["access_token"]

    def _keres(self, metodus: str, ut: str, parameterek: dict | None = None, torzs: dict | None = None):
        url = API + ut
        if parameterek:
            url += "?" + urllib.parse.urlencode({k: v for k, v in parameterek.items() if v not in (None, "")})
        adat = json.dumps(torzs).encode() if torzs is not None else (b"" if metodus in ("PUT", "POST") else None)
        keres = urllib.request.Request(url, data=adat, method=metodus, headers={
            "Authorization": f"Bearer {self._hozzaferes()}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(keres, timeout=15) as v:
                nyers = v.read()
                return json.loads(nyers) if nyers else None
        except urllib.error.HTTPError as e:
            raise SpotifyHiba(_hiba_szoveg(e)) from e
        except urllib.error.URLError as e:
            raise SpotifyHiba("Nem érhető el a Spotify (nincs internet?).") from e

    def eszkozok(self) -> list[dict]:
        return (self._keres("GET", "/me/player/devices") or {}).get("devices", [])

    def _eszkoz(self, kert: str) -> str | None:
        eszkozok = self.eszkozok()
        if not eszkozok:
            raise SpotifyHiba("Nincs elérhető Spotify-eszköz. Indítsd el a Spotify alkalmazást ezen a gépen.")
        for e in eszkozok:
            if kert and kert in (e.get("id"), e.get("name")):
                return e["id"]
        aktiv = next((e for e in eszkozok if e.get("is_active")), None)
        return (aktiv or eszkozok[0])["id"]

    def lejatszas(self, uri: str, eszkoz: str = "", keveres: bool = True, hangero: int | None = None) -> None:
        azonosito = self._eszkoz(eszkoz)
        if hangero is not None:
            self.hangero(hangero, azonosito)
        torzs = {"uris": [uri]} if uri.startswith("spotify:track:") else {"context_uri": uri}
        self._keres("PUT", "/me/player/play", {"device_id": azonosito}, torzs)
        with contextlib.suppress(SpotifyHiba):
            self._keres("PUT", "/me/player/shuffle", {"state": "true" if keveres else "false",
                                                       "device_id": azonosito})

    def folytatas(self, eszkoz: str = "") -> None:
        self._keres("PUT", "/me/player/play", {"device_id": self._eszkoz(eszkoz)})

    def szunet(self) -> None:
        try:
            self._keres("PUT", "/me/player/pause")
        except SpotifyHiba as e:
            if "nincs aktív" not in str(e).lower() and "már szünetel" not in str(e).lower():
                raise

    def hangero(self, szazalek: int, eszkoz_id: str | None = None) -> None:
        self._keres("PUT", "/me/player/volume", {"volume_percent": max(0, min(100, int(szazalek))),
                                                 "device_id": eszkoz_id})

    def elhalkit(self, honnan: int, mp: float, lepes: int = 6) -> None:
        for i in range(1, lepes + 1):
            self.hangero(round(honnan * (1 - i / lepes)))
            time.sleep(mp / lepes)

    def kovetkezo(self) -> None:
        self._keres("POST", "/me/player/next")

    def elozo(self) -> None:
        self._keres("POST", "/me/player/previous")

    def most_szol(self) -> dict | None:
        adat = self._keres("GET", "/me/player/currently-playing")
        if not adat or not adat.get("item"):
            return None
        elem = adat["item"]
        eloado = ", ".join(a["name"] for a in elem.get("artists", []))
        return {"cim": elem.get("name", ""), "eloado": eloado, "szol": bool(adat.get("is_playing")),
                "hossz": elem.get("duration_ms", 0) / 1000, "pozicio": (adat.get("progress_ms") or 0) / 1000}


def _hiba_szoveg(e: urllib.error.HTTPError) -> str:
    try:
        reszlet = json.loads(e.read()).get("error", {})
        ok = reszlet.get("reason", "") if isinstance(reszlet, dict) else ""
        uzenet = reszlet.get("message", "") if isinstance(reszlet, dict) else str(reszlet)
    except (json.JSONDecodeError, ValueError, AttributeError):
        ok, uzenet = "", ""
    if ok == "PREMIUM_REQUIRED" or (e.code == 403 and "premium" in uzenet.lower()):
        return "A Spotify vezérléséhez Premium-előfizetés kell."
    if ok == "NO_ACTIVE_DEVICE" or e.code == 404:
        return "Nincs aktív Spotify-eszköz. Indítsd el a Spotify alkalmazást."
    if e.code == 401:
        return "A Spotify-bejelentkezés érvénytelen, jelentkezz be újra."
    if e.code == 429:
        return "Túl sok Spotify-kérés, várj egy kicsit."
    if e.code == 403 and "restriction" in uzenet.lower():
        return "A Spotify ezt most nem engedi (már szünetel, vagy nem vezérelhető)."
    return f"Spotify-hiba ({e.code}): {uzenet or e.reason}"
