__lazy_modules__ = [
    "contextlib",
    "logging",
    "random",
    "time",
    "dataclasses",
    "pathlib",
    "PySide6.QtCore",
    "PySide6.QtMultimedia",
    "kozgaz_fm",
    "kozgaz_fm.beallitasok",
    "kozgaz_fm.hangossag",
    "kozgaz_fm.sajat_hangok",
    "kozgaz_fm.spotify",
    "kozgaz_fm.utvonalak",
]

import contextlib
import logging
import random
import time
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, QVariantAnimation, Signal
from PySide6.QtMultimedia import QAudioDevice, QAudioOutput, QMediaDevices, QMediaPlayer

from kozgaz_fm import hatter, sajat_hangok, youtube
from kozgaz_fm.beallitasok import BEEPITETT_HANGOK, ZeneForras
from kozgaz_fm.hangossag import Kiegyenlito
from kozgaz_fm.sajat_hangok import HANGFAJLOK
from kozgaz_fm.spotify import Spotify, SpotifyHiba, spotify_uri
from kozgaz_fm.utvonalak import beepitett_hang, gyorsitotar_mappa

naplo = logging.getLogger(__name__)

FORRAS_TIPUSOK = {"mappa": "Mappa", "fajlok": "Fájlok", "youtube": "YouTube", "spotify": "Spotify"}
VEDELEM_MS = 350
KESO_MERES_MS = 8000


def hang_ut(ertek: str) -> Path | None:
    if ertek.startswith("beepitett:"):
        nev = ertek.split(":", 1)[1]
        return beepitett_hang(nev) if nev in BEEPITETT_HANGOK else None
    if sajat_hangok.sajat(ertek):
        return sajat_hangok.ut(ertek)
    ut = Path(ertek)
    return ut if ut.is_file() else None


def hang_nev(ertek: str) -> str:
    if ertek.startswith("beepitett:"):
        return BEEPITETT_HANGOK.get(ertek.split(":", 1)[1], "Ismeretlen")
    if sajat_hangok.sajat(ertek):
        return sajat_hangok.nev(ertek)
    return Path(ertek).name


def kimeneti_eszkoz(azonosito: str) -> QAudioDevice:
    for eszkoz in QMediaDevices.audioOutputs():
        if azonosito and bytes(eszkoz.id().data()).decode(errors="replace") == azonosito:
            return eszkoz
    return QMediaDevices.defaultAudioOutput()


def eszkoz_azonosito(eszkoz: QAudioDevice) -> str:
    return bytes(eszkoz.id().data()).decode(errors="replace")


def _hangero(szazalek: float) -> float:
    return max(0.0, min(1.0, szazalek / 100.0)) ** 2


def _kimeneti_szint(szazalek: float, erosites: float) -> float:
    return min(1.0, _hangero(szazalek) * erosites)


def _helyi_ut(url: QUrl) -> Path | None:
    return Path(url.toLocalFile()) if url.isLocalFile() else None


class _Vedelem:
    def __init__(self) -> None:
        self._ig = 0.0

    def indit(self) -> None:
        self._ig = time.monotonic() + VEDELEM_MS / 1000

    def hatra_ms(self) -> int:
        return max(0, int((self._ig - time.monotonic()) * 1000) + 1) if self._ig > time.monotonic() else 0


class CsengoLejatszo(QObject):
    kesz = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.kimenet = QAudioOutput(self)
        self.lejatszo = QMediaPlayer(self)
        self.lejatszo.setAudioOutput(self.kimenet)
        self.lejatszo.mediaStatusChanged.connect(self._statusz)
        self.lejatszo.errorOccurred.connect(self._hiba)
        self._aktiv = False
        self._vedelem = _Vedelem()
        self._jel = 0

    @property
    def szol(self) -> bool:
        return self._aktiv

    def eszkoz(self, azonosito: str) -> None:
        self.kimenet.setDevice(kimeneti_eszkoz(azonosito))

    def lejatszas(self, ertek: str | Path, hangero: int, ismetles: bool = False) -> bool:
        ut = ertek if isinstance(ertek, Path) else hang_ut(ertek)
        if ut is None or not ut.exists():
            naplo.warning("A hangfájl nem található: %s", ertek)
            return False
        self._aktiv = True
        self._jel += 1
        jel = self._jel
        hatra = self._vedelem.hatra_ms()
        if hatra:
            QTimer.singleShot(hatra, lambda: self._indit(jel, ut, hangero, ismetles))
        else:
            self._indit(jel, ut, hangero, ismetles)
        return True

    def _indit(self, jel: int, ut: Path, hangero: int, ismetles: bool) -> None:
        if jel != self._jel or not self._aktiv:
            return
        self.kimenet.setVolume(_hangero(hangero))
        self.lejatszo.stop()
        self.lejatszo.setLoops(QMediaPlayer.Loops.Infinite if ismetles else 1)
        self.lejatszo.setSource(QUrl.fromLocalFile(str(ut)))
        self.lejatszo.play()
        self._vedelem.indit()

    def megallit(self) -> None:
        if self._aktiv:
            self._jel += 1
            self.lejatszo.stop()
            self._vedelem.indit()
            self._vege()

    def elenged(self) -> None:
        self.megallit()
        self.lejatszo.setSource(QUrl())
        self._vedelem.indit()

    def _statusz(self, statusz: QMediaPlayer.MediaStatus) -> None:
        if statusz in (QMediaPlayer.MediaStatus.EndOfMedia, QMediaPlayer.MediaStatus.InvalidMedia):
            self._vege()

    def _hiba(self, _hiba, szoveg: str) -> None:
        naplo.warning("Csengőhang-hiba: %s", szoveg)
        self._vege()

    def _vege(self) -> None:
        if self._aktiv:
            self._aktiv = False
            self._vedelem.indit()
            QTimer.singleShot(VEDELEM_MS, self._kesz_jelzes)

    def _kesz_jelzes(self) -> None:
        if not self._aktiv:
            self.kesz.emit()


@dataclass
class Szam:
    cim: str
    helyi: Path | None = None
    yt: str = ""
    kert: bool = False


def mappa_szamai(mappa: Path) -> list[Szam]:
    fajlok = sorted(p for p in mappa.rglob("*") if p.suffix.lower() in HANGFAJLOK and p.is_file())
    return [Szam(p.stem, p) for p in fajlok]


def fajl_lista(cim: str) -> list[Szam]:
    szamok = []
    for sor in cim.splitlines():
        ut = Path(sor.strip())
        if not sor.strip() or not ut.is_file():
            continue
        if ut.suffix.lower() in (".m3u", ".m3u8"):
            for elem in ut.read_text(encoding="utf-8", errors="replace").splitlines():
                elem = elem.strip()
                if elem and not elem.startswith("#"):
                    cel = Path(elem) if Path(elem).is_absolute() else ut.parent / elem
                    if cel.is_file():
                        szamok.append(Szam(cel.stem, cel))
        elif ut.suffix.lower() in HANGFAJLOK:
            szamok.append(Szam(ut.stem, ut))
    return szamok


class ZeneLejatszo(QObject):
    szam_valtozott = Signal(str, str)
    kert_szol = Signal(str)
    allapot_valtozott = Signal(bool)
    hiba = Signal(str)
    lista_valtozott = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.kimenet = QAudioOutput(self)
        self.lejatszo = QMediaPlayer(self)
        self.lejatszo.setAudioOutput(self.kimenet)
        self._kifuto_kimenet = QAudioOutput(self)
        self._kifuto = QMediaPlayer(self)
        self._kifuto.setAudioOutput(self._kifuto_kimenet)
        for lejatszo in (self.lejatszo, self._kifuto):
            lejatszo.mediaStatusChanged.connect(self._statusz)
            lejatszo.errorOccurred.connect(self._lejatszasi_hiba)
            lejatszo.playbackStateChanged.connect(self._lejatszas_allapot)
            lejatszo.positionChanged.connect(self._pozicio)
        self.kiegyenlito: Kiegyenlito | None = None
        self._erosites = 1.0
        self._kifuto_erosites = 1.0
        self._kifuto_animacio = QVariantAnimation(self)
        self._kifuto_animacio.valueChanged.connect(
            lambda v: self._kifuto_kimenet.setVolume(_kimeneti_szint(float(v), self._kifuto_erosites)))
        self._kifuto_animacio.finished.connect(self._kifuto_leallit)
        self.atusztatas_mp = 4.0
        self.forras: ZeneForras | None = None
        self.spotify: Spotify | None = None
        self.spotify_eszkoz = ""
        self.szamok: list[Szam] = []
        self._fuggo_kert: list[Szam] = []
        self.index = 0
        self.keveres = True
        self.gyorsitotar = True
        self.hangero_ertek = 60
        self.elhalkitas_mp = 3.0
        self._halkitva = False
        self._szol = False
        self._betoltes_alatt = False
        self._indit_betoltes_utan = False
        self._hibasorozat = 0
        self._letoltes_alatt: set[str] = set()
        self._varakozo: tuple[str, int, int] | None = None
        self._generacio = 0
        self._animacio = QVariantAnimation(self)
        self._animacio.valueChanged.connect(lambda v: self.kimenet.setVolume(_kimeneti_szint(float(v), self._erosites)))
        self._animacio_vege: list = []
        self._animacio.finished.connect(self._animacio_kesz)
        self._spotify_figyelo = QTimer(self)
        self._spotify_figyelo.setInterval(5000)
        self._spotify_figyelo.timeout.connect(self._spotify_frissit)
        self.most_cim = ""
        self._vedelem = _Vedelem()
        self._indito_jel = 0

    @property
    def szol(self) -> bool:
        return self._szol

    @property
    def spotify_mod(self) -> bool:
        return self.forras is not None and self.forras.tipus == "spotify"

    def eszkoz(self, azonosito: str) -> None:
        eszkoz = kimeneti_eszkoz(azonosito)
        self.kimenet.setDevice(eszkoz)
        self._kifuto_kimenet.setDevice(eszkoz)

    def _fo_jelzes(self) -> bool:
        kuldo = self.sender()
        return not isinstance(kuldo, QMediaPlayer) or kuldo is self.lejatszo

    def _kifuto_leallit(self) -> None:
        self._kifuto_animacio.stop()
        if self._kifuto.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            self._kifuto.stop()
            self._vedelem.indit()

    def _pozicio(self, pozicio: int) -> None:
        if not self._fo_jelzes() or not self._szol or self._halkitva or self.atusztatas_mp <= 0:
            return
        hossz = self.lejatszo.duration()
        atusztatas = int(self.atusztatas_mp * 1000)
        if hossz < atusztatas * 3 or hossz - pozicio > atusztatas or len(self.szamok) < 2:
            return
        if self._kifuto.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            return
        kovetkezo = (self.index + 1) % len(self.szamok)
        szam = self.szamok[kovetkezo]
        if not szam.helyi:
            return
        self.lejatszo, self._kifuto = self._kifuto, self.lejatszo
        self.kimenet, self._kifuto_kimenet = self._kifuto_kimenet, self.kimenet
        self._kifuto_erosites = self._erosites
        self._kifuto_animacio.stop()
        self._kifuto_animacio.setStartValue(float(self._cel_hangero()))
        self._kifuto_animacio.setEndValue(0.0)
        self._kifuto_animacio.setDuration(atusztatas)
        self._kifuto_animacio.start()
        self.index = kovetkezo
        if szam.kert:
            szam.kert = False
            self.kert_szol.emit(szam.yt)
        self.most_cim = szam.cim
        self.szam_valtozott.emit(szam.cim, self.forras.nev if self.forras else "")
        self._forrast_indit(QUrl.fromLocalFile(str(szam.helyi)), atusztatas)
        self._elore_letolt()

    def forras_beallitas(self, forras: ZeneForras | None) -> None:
        if forras == self.forras and (self.szamok or self.spotify_mod or self._betoltes_alatt):
            return
        folyt = self._szol
        if folyt:
            self.megallit(elhalkitas=False)
        self.forras = forras
        self._fuggo_kert = [s for s in self.szamok if s.kert] + self._fuggo_kert
        self.szamok = []
        self.index = 0
        self._generacio += 1
        self.lista_valtozott.emit()
        if forras is None or forras.tipus == "spotify":
            return
        self.betoltes(inditas=folyt)

    def betoltes(self, inditas: bool = False) -> None:
        forras = self.forras
        if forras is None or forras.tipus == "spotify":
            return
        self._betoltes_alatt = True
        self._indit_betoltes_utan = self._indit_betoltes_utan or inditas
        generacio = self._generacio

        def munka() -> list[Szam]:
            if forras.tipus == "mappa":
                return mappa_szamai(Path(forras.cim))
            if forras.tipus == "fajlok":
                return fajl_lista(forras.cim)
            return [Szam(s.cim, yt=s.azonosito) for s in youtube.lista(forras.cim)]

        def kesz(szamok: list[Szam]) -> None:
            if generacio != self._generacio:
                return
            self._betoltes_alatt = False
            if self.keveres:
                random.shuffle(szamok)
            self.szamok = [s for s in self.szamok if s.kert] + self._fuggo_kert + szamok
            self._fuggo_kert = []
            self.index = 0
            self.lista_valtozott.emit()
            if not szamok:
                self.hiba.emit(f"A(z) „{forras.nev}” forrásban nincs lejátszható szám.")
                self._indit_betoltes_utan = False
                return
            self._elore_letolt()
            if self.kiegyenlito:
                for s in szamok:
                    self.kiegyenlito.kell(s.helyi)
            if self._indit_betoltes_utan:
                self._indit_betoltes_utan = False
                self.indit()

        def rossz(e: Exception) -> None:
            if generacio != self._generacio:
                return
            self._betoltes_alatt = False
            self._indit_betoltes_utan = False
            self.hiba.emit(f"Nem sikerült betölteni: {forras.nev} ({e})")

        hatter.futtat(munka, kesz, rossz)

    def indit(self) -> None:
        if self.forras is None:
            self.hiba.emit("Nincs kiválasztott zeneforrás.")
            return
        if self.spotify_mod:
            self._spotify_indit()
            return
        if not self.szamok:
            if not self._betoltes_alatt:
                self.betoltes(inditas=True)
            else:
                self._indit_betoltes_utan = True
            return
        self._szol = True
        self.allapot_valtozott.emit(True)
        if self.lejatszo.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self._beuszas()
            self.lejatszo.play()
            return
        self._jatszd(self.index)

    def _jatszd(self, index: int) -> None:
        if not self.szamok:
            return
        self._kifuto_leallit()
        self.index = index % len(self.szamok)
        szam = self.szamok[self.index]
        if szam.kert:
            szam.kert = False
            self.kert_szol.emit(szam.yt)
        self.most_cim = szam.cim
        self.szam_valtozott.emit(szam.cim, self.forras.nev if self.forras else "")
        if szam.helyi:
            self._forrast_indit(QUrl.fromLocalFile(str(szam.helyi)))
        else:
            self._ideiglenes_takaritas(szam.yt)
            meglevo = youtube.gyorsitott(szam.yt, self._yt_mappa())
            if meglevo:
                szam.helyi = meglevo
                self._forrast_indit(QUrl.fromLocalFile(str(meglevo)))
            else:
                self.lejatszo.stop()
                self._vedelem.indit()
                self._varakozo = (szam.yt, self._generacio, self.index)
                self._letolt(szam)
        self._elore_letolt()

    def _letolt(self, szam: Szam) -> None:
        if szam.yt in self._letoltes_alatt:
            return
        self._letoltes_alatt.add(szam.yt)
        hatter.futtat(lambda: youtube.letoltes(szam.yt, self._yt_mappa()),
                      lambda ut: self._letoltve(szam, ut),
                      lambda e: self._letoltes_hiba(szam, e))

    def _forrast_indit(self, url: QUrl, beuszas_ms: int | None = None) -> None:
        self._indito_jel += 1
        jel = self._indito_jel
        hatra = self._vedelem.hatra_ms()
        if hatra:
            QTimer.singleShot(hatra, lambda: self._forrast_indit_most(jel, url, beuszas_ms))
        else:
            self._forrast_indit_most(jel, url, beuszas_ms)

    def _forrast_indit_most(self, jel: int, url: QUrl, beuszas_ms: int | None) -> None:
        if jel != self._indito_jel:
            return
        self._animacio.stop()
        self._animacio_vege.clear()
        self._erosites = self.kiegyenlito.szorzo(_helyi_ut(url)) if self.kiegyenlito else 1.0
        self.kimenet.setVolume(0.0)
        self.lejatszo.setSource(url)
        self.lejatszo.play()
        self._vedelem.indit()
        lejatszo = self.lejatszo
        QTimer.singleShot(VEDELEM_MS + 10, lambda: self._kesleltetett_beuszas(jel, lejatszo, beuszas_ms))

    def _kesleltetett_beuszas(self, jel: int, lejatszo: QMediaPlayer, beuszas_ms: int | None) -> None:
        if jel == self._indito_jel and lejatszo is self.lejatszo and self._szol:
            self._beuszas(beuszas_ms)

    def _yt_mappa(self) -> Path:
        return gyorsitotar_mappa() / ("youtube" if self.gyorsitotar else "youtube-ideiglenes")

    def _ideiglenes_takaritas(self, megtart: str) -> None:
        if self.gyorsitotar:
            return
        mappa = gyorsitotar_mappa() / "youtube-ideiglenes"
        for fajl in mappa.glob("*"):
            if fajl.is_file() and not fajl.name.startswith(megtart):
                with contextlib.suppress(OSError):
                    fajl.unlink()
        for szam in self.szamok:
            if szam.yt and szam.yt != megtart and szam.helyi and szam.helyi.parent == mappa:
                szam.helyi = None

    def _elore_letolt(self) -> None:
        if self.kiegyenlito and self.szamok:
            for eltolas in range(3, -1, -1):
                self.kiegyenlito.kell(self.szamok[(self.index + eltolas) % len(self.szamok)].helyi, elore=True)
        if not self.gyorsitotar or not self.szamok:
            return
        for eltolas in range(3):
            szam = self.szamok[(self.index + eltolas) % len(self.szamok)]
            if not szam.yt or szam.helyi or szam.yt in self._letoltes_alatt:
                continue
            if len(self._letoltes_alatt) >= 2:
                return
            self._letolt(szam)

    def _var_ra(self, szam: Szam) -> bool:
        if self._varakozo is None or self._varakozo[0] != szam.yt:
            return False
        _, generacio, index = self._varakozo
        self._varakozo = None
        return generacio == self._generacio and index == self.index and self._szol

    def _letoltve(self, szam: Szam, ut: Path) -> None:
        self._letoltes_alatt.discard(szam.yt)
        szam.helyi = ut
        if self._var_ra(szam):
            self._forrast_indit(QUrl.fromLocalFile(str(ut)))
        self._elore_letolt()

    def _letoltes_hiba(self, szam: Szam, e: Exception) -> None:
        self._letoltes_alatt.discard(szam.yt)
        if self._var_ra(szam):
            self._lejatszasi_hiba(None, str(e))

    def _beuszas(self, hossz_ms: int | None = None) -> None:
        self._animacio.stop()
        self._animacio_vege.clear()
        cel = self._cel_hangero()
        self._animacio.setStartValue(0.0)
        self._animacio.setEndValue(float(cel))
        self._animacio.setDuration(hossz_ms or int(min(self.elhalkitas_mp, 2.0) * 1000))
        self._animacio.start()

    def _cel_hangero(self) -> float:
        return self.hangero_ertek * (0.25 if self._halkitva else 1.0)

    def erosites_ujra(self) -> None:
        most = _helyi_ut(self.lejatszo.source())
        uj = self.kiegyenlito.szorzo(most) if self.kiegyenlito else 1.0
        if abs(uj - self._erosites) < 0.01:
            return
        self._erosites = uj
        if self._szol and self._animacio.state() != QVariantAnimation.State.Running and not self._vedelem.hatra_ms():
            self.kimenet.setVolume(_kimeneti_szint(self._cel_hangero(), uj))

    def mert_jott(self, ut_szoveg: str) -> None:
        if self.kiegyenlito is None or not self._szol or self.spotify_mod:
            return
        most = _helyi_ut(self.lejatszo.source())
        if most is None or str(most) != ut_szoveg or self.lejatszo.position() > KESO_MERES_MS:
            return
        regi, uj = self._erosites, self.kiegyenlito.szorzo(most)
        if abs(uj - regi) < 0.01:
            return
        self._erosites = uj
        if self._animacio.state() == QVariantAnimation.State.Running or self._vedelem.hatra_ms():
            return
        cel = self._cel_hangero()
        honnan = min(100.0, cel * (regi / uj) ** 0.5)
        self._animacio.setStartValue(float(honnan))
        self._animacio.setEndValue(float(cel))
        self._animacio.setDuration(1200)
        self._animacio.start()

    def _animacio_kesz(self) -> None:
        teendok, self._animacio_vege = self._animacio_vege, []
        for teendo in teendok:
            teendo()

    def megallit(self, elhalkitas: bool = True, kovetkezore: bool = True) -> None:
        if not self._szol:
            return
        self._szol = False
        self.allapot_valtozott.emit(False)
        self._kifuto_leallit()
        if self.spotify_mod:
            self._spotify_figyelo.stop()
            self._spotify_megallit(elhalkitas)
            return

        def vege() -> None:
            if self._szol:
                return
            if kovetkezore and self.szamok:
                self.lejatszo.stop()
                self._vedelem.indit()
                self.index = (self.index + 1) % len(self.szamok)
            else:
                self.lejatszo.pause()

        self._indito_jel += 1
        if (elhalkitas and self.lejatszo.playbackState() == QMediaPlayer.PlaybackState.PlayingState
                and not self._vedelem.hatra_ms()):
            self._animacio.stop()
            self._animacio.setStartValue(float(self._cel_hangero()))
            self._animacio.setEndValue(0.0)
            self._animacio.setDuration(int(self.elhalkitas_mp * 1000))
            self._animacio_vege = [vege]
            self._animacio.start()
        else:
            self._animacio.stop()
            vege()

    def valt(self) -> None:
        if self._szol:
            self.megallit(kovetkezore=False)
        else:
            self.indit()

    def kovetkezo(self) -> None:
        if self.spotify_mod:
            self._spotify_hivas(lambda s: s.kovetkezo())
            QTimer.singleShot(1200, self._spotify_frissit)
            return
        if self.szamok:
            self._szol = True
            self.allapot_valtozott.emit(True)
            self._jatszd(self.index + 1)

    def elozo(self) -> None:
        if self.spotify_mod:
            self._spotify_hivas(lambda s: s.elozo())
            QTimer.singleShot(1200, self._spotify_frissit)
            return
        if self.szamok:
            self._szol = True
            self.allapot_valtozott.emit(True)
            self._jatszd(self.index - 1)

    def beszur(self, szam: Szam) -> bool:
        if self.spotify_mod or self.forras is None:
            return False
        szam.kert = True
        if not self.szamok:
            self._fuggo_kert.append(szam)
            return True
        megallitva = not self._szol and self.lejatszo.playbackState() == QMediaPlayer.PlaybackState.StoppedState
        hely = self.index if megallitva else self.index + 1
        while hely < len(self.szamok) and self.szamok[hely].kert:
            hely += 1
        self.szamok.insert(hely, szam)
        self.lista_valtozott.emit()
        self._elore_letolt()
        return True

    def kovetkezok(self, darab: int = 5) -> list[tuple[int, str]]:
        if self.spotify_mod or not self.szamok:
            return []
        hossz = len(self.szamok)
        return [((self.index + i) % hossz, self.szamok[(self.index + i) % hossz].cim)
                for i in range(1, min(darab, hossz - 1) + 1)]

    def ugras(self, index: int) -> None:
        if self.szamok:
            self._szol = True
            self.allapot_valtozott.emit(True)
            self._jatszd(index)

    def hangero(self, szazalek: int) -> None:
        self.hangero_ertek = szazalek
        if self.spotify_mod:
            if self._szol:
                self._spotify_hivas(lambda s: s.hangero(round(self._cel_hangero())))
            return
        if self._animacio.state() != QVariantAnimation.State.Running and not self._vedelem.hatra_ms():
            self.kimenet.setVolume(_kimeneti_szint(self._cel_hangero(), self._erosites))

    def halkit(self, halkitva: bool) -> None:
        if self._halkitva == halkitva:
            return
        self._halkitva = halkitva
        if halkitva:
            self._kifuto_leallit()
        if not self._szol:
            return
        if self.spotify_mod:
            self._spotify_hivas(lambda s: s.hangero(round(self._cel_hangero())))
            return
        if self._vedelem.hatra_ms():
            return
        self._animacio.stop()
        self._animacio_vege.clear()
        self._animacio.setStartValue(float(self.hangero_ertek * (1.0 if halkitva else 0.25)))
        self._animacio.setEndValue(float(self._cel_hangero()))
        self._animacio.setDuration(600)
        self._animacio.start()

    def _statusz(self, statusz: QMediaPlayer.MediaStatus) -> None:
        if not self._fo_jelzes():
            return
        if statusz in (QMediaPlayer.MediaStatus.EndOfMedia, QMediaPlayer.MediaStatus.InvalidMedia):
            self._vedelem.indit()
        if statusz == QMediaPlayer.MediaStatus.EndOfMedia and self._szol:
            self._hibasorozat = 0
            self._jatszd(self.index + 1)
        elif statusz == QMediaPlayer.MediaStatus.BufferedMedia:
            self._hibasorozat = 0

    def _lejatszas_allapot(self, allapot: QMediaPlayer.PlaybackState) -> None:
        if not self._fo_jelzes():
            return
        if allapot == QMediaPlayer.PlaybackState.PlayingState:
            self._hibasorozat = 0

    def _lejatszasi_hiba(self, _hiba, szoveg: str) -> None:
        if not self._fo_jelzes():
            return
        naplo.warning("Lejátszási hiba (%s): %s", self.most_cim, szoveg)
        self._vedelem.indit()
        if not self._szol or not self.szamok:
            return
        self._hibasorozat += 1
        if self._hibasorozat >= min(len(self.szamok), 5):
            self._hibasorozat = 0
            self.megallit(elhalkitas=False)
            self.hiba.emit(f"A zene nem játszható le: {szoveg}")
            return
        hibas = self.szamok[self.index]
        if hibas.yt and hibas.helyi:
            hibas.helyi.unlink(missing_ok=True)
            hibas.helyi = None
        QTimer.singleShot(800, lambda: self._szol and self._jatszd(self.index + 1))

    def _spotify_hivas(self, muvelet, siker=None) -> None:
        if self.spotify is None or not self.spotify.bejelentkezve:
            self.hiba.emit("A Spotify nincs összekapcsolva (Zene → Spotify).")
            return
        spotify = self.spotify
        hatter.futtat(lambda: muvelet(spotify), siker,
                      lambda e: self.hiba.emit(str(e) if isinstance(e, SpotifyHiba) else f"Spotify-hiba: {e}"))

    def _spotify_indit(self) -> None:
        uri = spotify_uri(self.forras.cim) if self.forras else None
        if not uri:
            self.hiba.emit("Érvénytelen Spotify-link.")
            return
        self._szol = True
        self.allapot_valtozott.emit(True)
        eszkoz, keveres, hangero = self.spotify_eszkoz, self.keveres, round(self._cel_hangero())
        self._spotify_hivas(lambda s: s.lejatszas(uri, eszkoz, keveres, hangero),
                            lambda _: QTimer.singleShot(1000, self._spotify_frissit))
        self._spotify_figyelo.start()

    def _spotify_megallit(self, elhalkitas: bool) -> None:
        honnan, mp, vissza = round(self._cel_hangero()), self.elhalkitas_mp, self.hangero_ertek

        def muvelet(s: Spotify) -> None:
            if elhalkitas:
                with contextlib.suppress(SpotifyHiba):
                    s.elhalkit(honnan, mp)
            s.szunet()
            with contextlib.suppress(SpotifyHiba):
                s.hangero(vissza)

        self._spotify_hivas(muvelet)

    def _spotify_frissit(self) -> None:
        if not self.spotify_mod or self.spotify is None or not self.spotify.bejelentkezve:
            return

        def kesz(adat: dict | None) -> None:
            if adat and adat["cim"] != self.most_cim:
                self.most_cim = adat["cim"]
                felirat = f"{adat['eloado']} – {adat['cim']}" if adat["eloado"] else adat["cim"]
                self.szam_valtozott.emit(felirat, self.forras.nev if self.forras else "Spotify")

        spotify = self.spotify
        hatter.futtat(spotify.most_szol, kesz)

    def allj(self) -> None:
        self._generacio += 1
        self._animacio.stop()
        self._kifuto_leallit()
        self._indito_jel += 1
        self.lejatszo.stop()
        self._vedelem.indit()
        self._spotify_figyelo.stop()
