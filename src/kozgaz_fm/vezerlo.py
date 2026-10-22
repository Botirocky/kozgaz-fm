import logging
from collections import deque
from dataclasses import dataclass, fields
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, Signal

from kozgaz_fm import __version__, sajat_hangok
from kozgaz_fm.beallitasok import Beallitasok, Bemondas
from kozgaz_fm.bemondo import Bemondo
from kozgaz_fm.frissito import Frissito
from kozgaz_fm.hang import CsengoLejatszo, ZeneLejatszo
from kozgaz_fm.orarend import Esemeny, Tipus, napi_esemenyek, zene_ablakban
from kozgaz_fm.spotify import Spotify
from kozgaz_fm.utvonalak import adat_mappa, naplo_fajl

naplo = logging.getLogger(__name__)

HANG_MEZOK = {f.name: f.default for f in fields(Beallitasok) if f.name.startswith("hang_")}


@dataclass
class _Feladat:
    tipus: str
    ertek: str = ""
    ismetles: bool = False
    tartalek: str = ""


class Vezerlo(QObject):
    frissult = Signal()
    naplo_bejegyzes = Signal(str)
    uzenet = Signal(str, str)
    riasztas_valtozott = Signal(bool)
    hangok_valtoztak = Signal()

    def __init__(self, beallitasok: Beallitasok, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.b = beallitasok
        self.csengo = CsengoLejatszo(self)
        self.zene = ZeneLejatszo(self)
        self.bemondo = Bemondo(self)
        self.spotify: Spotify | None = None
        self.naplo: deque[str] = deque(maxlen=1000)
        self.riasztas = False
        self._esemenyek: list[Esemeny] = []
        self._nap: date | None = None
        self._utolso: datetime | None = None
        self._auto_zene = False
        self._sor: deque[_Feladat] = deque()
        self.csengo.kesz.connect(self._kovetkezo_feladat)
        self.bemondo.kesz.connect(self._kovetkezo_feladat)
        self.zene.hiba.connect(lambda s: self._jelez(s, "hiba"))
        self.zene.szam_valtozott.connect(lambda cim, forras: self.log(f"Zene: {cim} ({forras})"))
        self.zene.allapot_valtozott.connect(lambda _: self.frissult.emit())
        self._ora = QTimer(self)
        self._ora.setInterval(250)
        self._ora.timeout.connect(self._tick)
        self._mento = QTimer(self)
        self._mento.setSingleShot(True)
        self._mento.setInterval(600)
        self._mento.timeout.connect(self.mentes)
        self.frissito = Frissito(self, self)
        self.beallitasok_alkalmazasa()

    def indit(self) -> None:
        self.log(f"Közgáz FM {__version__} elindult")
        self._ora.start()
        self.frissito.indit()
        QTimer.singleShot(1500, self._szinkron)

    def leallit(self) -> None:
        if self._mento.isActive():
            self.mentes()
        self._ora.stop()
        self.zene.allj()
        self.csengo.megallit()
        self.bemondo.megallit()

    def log(self, szoveg: str) -> None:
        sor = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {szoveg}"
        self.naplo.append(sor)
        naplo.info(szoveg)
        try:
            with naplo_fajl().open("a", encoding="utf-8") as f:
                f.write(sor + "\n")
        except OSError:
            pass
        self.naplo_bejegyzes.emit(sor)

    def _jelez(self, szoveg: str, szint: str = "info") -> None:
        self.log(szoveg if szint == "info" else f"HIBA: {szoveg}")
        self.uzenet.emit(szoveg, szint)

    def beallitasok_alkalmazasa(self) -> None:
        b = self.b
        self.csengo.eszkoz(b.kimenet)
        self.zene.eszkoz(b.kimenet)
        self.zene.keveres = b.keveres
        self.zene.gyorsitotar = b.youtube_gyorsitotar
        self.zene.elhalkitas_mp = b.elhalkitas
        self.zene.hangero(b.zene_hangero)
        self.zene.spotify_eszkoz = b.spotify_eszkoz
        self.bemondo.beallit(b.tts_hang, b.csengo_hangero)
        if b.spotify_client_id and (self.spotify is None or self.spotify.client_id != b.spotify_client_id.strip()):
            self.spotify = Spotify(b.spotify_client_id, adat_mappa() / "spotify_token.json")
        elif not b.spotify_client_id:
            self.spotify = None
        self.zene.spotify = self.spotify
        self.zene.forras_beallitas(self.aktiv_forras())
        self._nap = None
        self.frissult.emit()

    def _tartalek(self, hang: str) -> str:
        for mezo, alap in HANG_MEZOK.items():
            if getattr(self.b, mezo) == hang:
                return alap
        return HANG_MEZOK["hang_becsengo"]

    def sajat_hang_hozzaadas(self, forras: Path, nev: str | None = None) -> sajat_hangok.SajatHang:
        hang = sajat_hangok.hozzaad(forras, nev)
        self.log(f"Saját hang hozzáadva: {hang.nev}")
        self.hangok_valtoztak.emit()
        return hang

    def _csengo_elenged(self) -> None:
        if self.csengo.szol:
            self.csengo.megallit()
        self.csengo.lejatszo.setSource(QUrl())

    def sajat_hang_atnevezes(self, ertek: str, nev: str) -> sajat_hangok.SajatHang:
        self._csengo_elenged()
        hang = sajat_hangok.atnevez(ertek, nev)
        for mezo in HANG_MEZOK:
            if getattr(self.b, mezo) == ertek:
                setattr(self.b, mezo, hang.ertek)
        self.mentes()
        self.hangok_valtoztak.emit()
        return hang

    def sajat_hang_hasznalat(self, ertek: str) -> list[str]:
        return [mezo for mezo in HANG_MEZOK if getattr(self.b, mezo) == ertek]

    def sajat_hang_torles(self, ertek: str) -> None:
        self._csengo_elenged()
        sajat_hangok.torol(ertek)
        for mezo in self.sajat_hang_hasznalat(ertek):
            setattr(self.b, mezo, HANG_MEZOK[mezo])
        self.log(f"Saját hang törölve: {sajat_hangok.nev(ertek)}")
        self.mentes()
        self.hangok_valtoztak.emit()

    def mentes_kesobb(self) -> None:
        self._mento.start()

    def mentes(self) -> None:
        self._mento.stop()
        self.b.mentes()
        self.beallitasok_alkalmazasa()
        self._szinkron()

    def aktiv_forras(self):
        forrasok = [f for f in self.b.forrasok if f.aktiv]
        if not self.b.forrasok:
            return None
        if 0 <= self.b.aktiv_forras < len(self.b.forrasok) and self.b.forrasok[self.b.aktiv_forras].aktiv:
            return self.b.forrasok[self.b.aktiv_forras]
        return forrasok[0] if forrasok else None

    def mai_esemenyek(self) -> list[Esemeny]:
        self._frissit_nap(datetime.now())
        return list(self._esemenyek)

    def _frissit_nap(self, most: datetime) -> None:
        if self._nap != most.date():
            self._nap = most.date()
            self._esemenyek = napi_esemenyek(self.b, self._nap)

    def _tick(self) -> None:
        most = datetime.now()
        elozo = self._utolso
        self._frissit_nap(most)
        self._utolso = most
        if elozo is None or most < elozo or most - elozo > timedelta(seconds=20):
            if elozo is not None:
                self.log("Óraugrás vagy alvás után újraszinkronizálás")
            self._szinkron()
            return
        if elozo.date() != most.date():
            esemenyek = napi_esemenyek(self.b, elozo.date()) + self._esemenyek
        else:
            esemenyek = self._esemenyek
        for e in esemenyek:
            if elozo < e.ido <= most:
                self._kezel(e)

    def _szinkron(self) -> None:
        most = datetime.now()
        if self.riasztas:
            return
        ablak = zene_ablakban(self.b, most)
        if ablak and not self.zene.szol:
            self._auto_zene = True
            self.zene.indit()
        elif not ablak and self._auto_zene and self.zene.szol:
            self._auto_zene = False
            self.zene.megallit()
        self.frissult.emit()

    def _kezel(self, e: Esemeny) -> None:
        if self.riasztas and e.tipus is not Tipus.ZENE_LEALL:
            self.log(f"Kihagyva riasztás miatt: {e.leiras}")
            return
        if e.tipus is Tipus.ZENE_INDUL:
            if self.aktiv_forras() is None:
                return
            self.log("Szünetzene indul")
            self._auto_zene = True
            self.zene.indit()
        elif e.tipus is Tipus.ZENE_LEALL:
            if self.zene.szol and self._auto_zene:
                self.log("Szünetzene leáll")
                self.zene.megallit()
            self._auto_zene = False
        elif e.tipus is Tipus.BEMONDAS and e.bemondas:
            self.bemondas(e.bemondas)
        elif e.tipus in (Tipus.JELZO, Tipus.BECSENGO):
            if self.zene.szol:
                self._auto_zene = False
                self.zene.megallit(elhalkitas=False)
            hang = self.b.hang_jelzo if e.tipus is Tipus.JELZO else self.b.hang_becsengo
            self.csengetes(hang, e.leiras)
        elif e.tipus is Tipus.KICSENGO:
            self.csengetes(self.b.hang_kicsengo, e.leiras)
        self.frissult.emit()

    def _foglalt(self) -> bool:
        if self.csengo.szol:
            self.csengo.megallit()
            return True
        if self.bemondo.beszel:
            self.bemondo.megallit()
            return True
        return False

    def csengetes(self, hang: str, leiras: str = "Kézi csengetés") -> None:
        if self.riasztas:
            self._jelez("Riasztás közben nincs csengetés.", "hiba")
            return
        self.log(f"Csengetés: {leiras}")
        self._sor.appendleft(_Feladat("hang", hang, tartalek=self._tartalek(hang)))
        if not self._foglalt():
            self._kovetkezo_feladat()

    def bemondas(self, bem: Bemondas) -> None:
        if self.riasztas:
            self._jelez("Riasztás közben nincs bemondás.", "hiba")
            return
        self.log(f"Bemondás: {bem.nev}")
        if bem.gong:
            self._sor.append(_Feladat("hang", self.b.hang_gong, tartalek=HANG_MEZOK["hang_gong"]))
        self._sor.append(_Feladat("szoveg" if bem.tipus == "szoveg" else "fajl", bem.tartalom))
        if not self.csengo.szol and not self.bemondo.beszel:
            self._kovetkezo_feladat()

    def gyors_bemondas(self, szoveg: str, gong: bool = True) -> None:
        self.bemondas(Bemondas("Gyors bemondás", "00:00", tipus="szoveg", tartalom=szoveg, gong=gong))

    def _kovetkezo_feladat(self) -> None:
        while self._sor:
            feladat = self._sor.popleft()
            self.zene.halkit(True)
            if feladat.tipus == "szoveg":
                if self.bemondo.mond(feladat.ertek):
                    return
                self._jelez("A gépen nincs elérhető felolvasó hang (TTS).", "hiba")
                continue
            forras = Path(feladat.ertek) if feladat.tipus == "fajl" else feladat.ertek
            hangero = 100 if feladat.ismetles else self.b.csengo_hangero
            if self.csengo.lejatszas(forras, hangero, feladat.ismetles):
                return
            if feladat.tartalek and feladat.tartalek != feladat.ertek:
                self._jelez("A beállított csengőhang nem található, a beépített hang szól helyette.", "hiba")
                if self.csengo.lejatszas(feladat.tartalek, hangero, feladat.ismetles):
                    return
            self._jelez(f"A hangfájl nem található: {feladat.ertek}", "hiba")
        if not self.riasztas:
            self.zene.halkit(False)

    def riasztas_indit(self) -> None:
        if self.riasztas:
            return
        self.riasztas = True
        self._auto_zene = False
        self.zene.megallit(elhalkitas=False)
        self.log("RIASZTÁS ELINDÍTVA")
        self._sor.clear()
        self._sor.append(_Feladat("hang", self.b.hang_riasztas, ismetles=True,
                                  tartalek=HANG_MEZOK["hang_riasztas"]))
        if not self._foglalt():
            self._kovetkezo_feladat()
        self.riasztas_valtozott.emit(True)
        self.frissult.emit()

    def riasztas_leallit(self) -> None:
        if not self.riasztas:
            return
        self.riasztas = False
        self._sor.clear()
        self.log("Riasztás leállítva")
        if not self._foglalt():
            self.zene.halkit(False)
        self.riasztas_valtozott.emit(False)
        self.frissult.emit()

    def zene_indit(self) -> None:
        self._auto_zene = False
        self.zene.indit()

    def zene_leallit(self) -> None:
        self._auto_zene = False
        self.zene.megallit()

    def zene_valt(self) -> None:
        if self.zene.szol:
            self.zene_leallit()
        else:
            self.zene_indit()

    def forras_valtas(self, index: int) -> None:
        self.b.aktiv_forras = index
        self.b.mentes()
        self.zene.forras_beallitas(self.aktiv_forras())
        self.frissult.emit()

    def ma_kapcsolo(self, mezo: str, be: bool) -> None:
        setattr(self.b, mezo, date.today().isoformat() if be else "")
        self.b.mentes()
        self._nap = None
        if mezo == "ma_nincs_zene" and be and self._auto_zene:
            self.zene_leallit()
        self._szinkron()
        self.log(("Ma nincs csengetés" if mezo == "ma_nincs_csengetes" else "Ma nincs szünetzene")
                 + (" – bekapcsolva" if be else " – kikapcsolva"))

    def ma_rend(self, nev: str) -> None:
        ma = date.today().isoformat()
        if nev:
            self.b.kivetelek[ma] = nev
        else:
            self.b.kivetelek.pop(ma, None)
        self.b.mentes()
        self._nap = None
        self.log(f"Mai csengetési rend: {nev or 'alapértelmezett'}")
        self._szinkron()
