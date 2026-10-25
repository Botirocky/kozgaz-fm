__lazy_modules__ = ["dataclasses", "pathlib", "PySide6.QtCore", "PySide6.QtMultimedia"]

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioDevice, QAudioOutput, QMediaDevices, QMediaPlayer

CELOK = ("csengo", "zene", "bemondas")


@dataclass(frozen=True)
class ZonaKimenet:
    nev: str
    eszkoz: str = ""
    csengo: bool = True
    zene: bool = True
    bemondas: bool = True
    szorzo: float = 1.0


def eszkoz_azonosito(eszkoz: QAudioDevice) -> str:
    return bytes(eszkoz.id().data()).decode(errors="replace")


def kimeneti_eszkoz(azonosito: str) -> QAudioDevice:
    for eszkoz in QMediaDevices.audioOutputs():
        if azonosito and eszkoz_azonosito(eszkoz) == azonosito:
            return eszkoz
    return QMediaDevices.defaultAudioOutput()


def cel_indexek(zonak: list[ZonaKimenet] | tuple[ZonaKimenet, ...], cel: str) -> list[int]:
    if cel == "mind":
        return list(range(len(zonak)))
    if cel == "elso":
        return [0] if zonak else []
    if cel.startswith("zona:"):
        i = int(cel[5:]) if cel[5:].isdigit() else -1
        return [i] if 0 <= i < len(zonak) else []
    return [i for i, z in enumerate(zonak) if getattr(z, cel, False)]


class TobbLejatszo(QObject):
    mediaStatusChanged = Signal(QMediaPlayer.MediaStatus)
    errorOccurred = Signal(QMediaPlayer.Error, str)
    playbackStateChanged = Signal(QMediaPlayer.PlaybackState)
    positionChanged = Signal(int)

    def __init__(self, parent: QObject | None = None, zonak: list[ZonaKimenet] | None = None) -> None:
        super().__init__(parent)
        self._tagok: list[tuple[QMediaPlayer, QAudioOutput, ZonaKimenet]] = []
        self._aktiv: list[int] = []
        self._fo = -1
        self._hangero = 1.0
        self._loops = 1
        self._cel = "mind"
        self._teljes = False
        self.zonak(zonak or [ZonaKimenet("Alapértelmezett")])

    @property
    def zona_lista(self) -> tuple[ZonaKimenet, ...]:
        return tuple(z for _l, _k, z in self._tagok)

    @property
    def aktiv_zonak(self) -> list[ZonaKimenet]:
        return [self._tagok[i][2] for i in self._aktiv]

    def ujraepitendo(self, lista: list[ZonaKimenet]) -> bool:
        return [z.eszkoz for z in lista] != [z.eszkoz for z in self.zona_lista]

    def zonak(self, lista: list[ZonaKimenet]) -> None:
        if not self.ujraepitendo(lista):
            self._tagok = [(lejatszo, kimenet, z) for (lejatszo, kimenet, _r), z in zip(self._tagok, lista,
                                                                                      strict=True)]
            for _l, kimenet, z in self._tagok:
                kimenet.setDevice(kimeneti_eszkoz(z.eszkoz))
            self._hangero_alkalmaz()
            self.aktiv(self._cel)
            return
        for lejatszo, kimenet, _z in self._tagok:
            lejatszo.stop()
            lejatszo.setSource(QUrl())
            lejatszo.deleteLater()
            kimenet.deleteLater()
        self._tagok = []
        for i, z in enumerate(lista):
            kimenet = QAudioOutput(self)
            kimenet.setDevice(kimeneti_eszkoz(z.eszkoz))
            lejatszo = QMediaPlayer(self)
            lejatszo.setAudioOutput(kimenet)
            lejatszo.setLoops(self._loops)
            lejatszo.mediaStatusChanged.connect(lambda s, i=i: self._fo == i and self.mediaStatusChanged.emit(s))
            lejatszo.errorOccurred.connect(lambda h, sz, i=i: self._fo == i and self.errorOccurred.emit(h, sz))
            lejatszo.playbackStateChanged.connect(
                lambda s, i=i: self._fo == i and self.playbackStateChanged.emit(s))
            lejatszo.positionChanged.connect(lambda p, i=i: self._fo == i and self.positionChanged.emit(p))
            self._tagok.append((lejatszo, kimenet, z))
        self._hangero_alkalmaz()
        self.aktiv(self._cel)

    def aktiv(self, cel: str) -> list[ZonaKimenet]:
        self._cel = cel
        self._teljes = cel == "mind"
        self._hangero_alkalmaz()
        uj = cel_indexek(self.zona_lista, cel)
        for i, (lejatszo, _k, _z) in enumerate(self._tagok):
            if i not in uj and lejatszo.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
                lejatszo.stop()
        self._aktiv = uj
        self._fo = uj[0] if uj else -1
        return self.aktiv_zonak

    def _aktiv_lejatszok(self) -> list[QMediaPlayer]:
        return [self._tagok[i][0] for i in self._aktiv]

    def _fo_lejatszo(self) -> QMediaPlayer | None:
        return self._tagok[self._fo][0] if self._fo >= 0 else None

    def setSource(self, url: QUrl) -> None:
        for lejatszo in self._aktiv_lejatszok():
            lejatszo.setSource(url)

    def elenged(self) -> None:
        for lejatszo, _k, _z in self._tagok:
            lejatszo.stop()
            lejatszo.setSource(QUrl())

    def forrasok(self) -> set[Path]:
        return {Path(lejatszo.source().toLocalFile()) for lejatszo, _k, _z in self._tagok
                if lejatszo.source().isLocalFile()}

    def play(self) -> None:
        for lejatszo in self._aktiv_lejatszok():
            lejatszo.play()

    def pause(self) -> None:
        for lejatszo in self._aktiv_lejatszok():
            lejatszo.pause()

    def stop(self) -> None:
        for lejatszo, _k, _z in self._tagok:
            if lejatszo.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
                lejatszo.stop()

    def setLoops(self, darab: int) -> None:
        self._loops = darab
        for lejatszo, _k, _z in self._tagok:
            lejatszo.setLoops(darab)

    def setPosition(self, pozicio: int) -> None:
        for lejatszo in self._aktiv_lejatszok():
            lejatszo.setPosition(pozicio)

    def source(self) -> QUrl:
        fo = self._fo_lejatszo()
        return fo.source() if fo else QUrl()

    def playbackState(self) -> QMediaPlayer.PlaybackState:
        fo = self._fo_lejatszo()
        return fo.playbackState() if fo else QMediaPlayer.PlaybackState.StoppedState

    def position(self) -> int:
        fo = self._fo_lejatszo()
        return fo.position() if fo else 0

    def duration(self) -> int:
        fo = self._fo_lejatszo()
        return fo.duration() if fo else 0

    def setVolume(self, ertek: float) -> None:
        self._hangero = ertek
        self._hangero_alkalmaz()

    def volume(self) -> float:
        return self._hangero

    def _hangero_alkalmaz(self) -> None:
        for _l, kimenet, z in self._tagok:
            szorzo = 1.0 if self._teljes else z.szorzo
            kimenet.setVolume(max(0.0, min(1.0, self._hangero * szorzo)))

    def setDevice(self, _eszkoz: QAudioDevice) -> None:
        pass
