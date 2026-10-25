__lazy_modules__ = [
    "contextlib",
    "logging",
    "shutil",
    "collections",
    "dataclasses",
    "datetime",
    "pathlib",
    "PySide6.QtCore",
    "kozgaz_fm",
    "kozgaz_fm.beallitasok",
    "kozgaz_fm.bemondo",
    "kozgaz_fm.ertesites",
    "kozgaz_fm.frissito",
    "kozgaz_fm.hang",
    "kozgaz_fm.hangossag",
    "kozgaz_fm.kimenetek",
    "kozgaz_fm.orarend",
    "kozgaz_fm.spotify",
    "kozgaz_fm.statisztika",
    "kozgaz_fm.tartalek",
    "kozgaz_fm.utvonalak",
    "kozgaz_fm.webpanel",
    "kozgaz_fm.youtube",
    "kozgaz_fm.zenekeres",
]

import contextlib
import logging
import shutil
from collections import deque
from dataclasses import dataclass, fields
from datetime import date, datetime, time, timedelta
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtMultimedia import QMediaDevices

from kozgaz_fm import __version__, hatter, sajat_hangok, youtube
from kozgaz_fm.beallitasok import Beallitasok, Bemondas, Rendkivuli
from kozgaz_fm.bemondo import Bemondo
from kozgaz_fm.ertesites import Ertesito, kimaradt_csengetesek, reggeli_jelentes
from kozgaz_fm.frissito import Frissito
from kozgaz_fm.hang import CsengoLejatszo, Szam, ZeneLejatszo, eszkoz_azonosito
from kozgaz_fm.hangossag import Kiegyenlito
from kozgaz_fm.kimenetek import ZonaKimenet, kimeneti_eszkoz
from kozgaz_fm.orarend import (
    CSENGOK,
    Esemeny,
    Tipus,
    csendes_idoszakok,
    napi_esemenyek,
    napi_rend,
    zene_ablakban,
)
from kozgaz_fm.spotify import Spotify
from kozgaz_fm.statisztika import Statisztika
from kozgaz_fm.tartalek import Tartalek
from kozgaz_fm.utvonalak import adat_mappa, eletjel_fajl, naplo_fajl
from kozgaz_fm.webpanel import WebPanel
from kozgaz_fm.zenekeres import Keres, Keresek, KeresHiba, youtube_cel

naplo = logging.getLogger(__name__)

HANG_MEZOK = {f.name: f.default for f in fields(Beallitasok) if f.name.startswith("hang_")}


@dataclass
class _Feladat:
    tipus: str
    ertek: str = ""
    ismetles: bool = False
    tartalek: str = ""
    hangero: int | None = None
    cel: str = "csengo"


class Vezerlo(QObject):
    frissult = Signal()
    naplo_bejegyzes = Signal(str)
    uzenet = Signal(str, str)
    riasztas_valtozott = Signal(bool)
    hangok_valtoztak = Signal()
    keresek_valtoztak = Signal()

    def __init__(self, beallitasok: Beallitasok, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.b = beallitasok
        self.csengo = CsengoLejatszo(self)
        self.proba = CsengoLejatszo(self)
        self.zene = ZeneLejatszo(self)
        self.kiegyenlito = Kiegyenlito(self)
        self.zene.kiegyenlito = self.kiegyenlito
        self.kiegyenlito.mert.connect(self.zene.mert_jott)
        self.bemondo = Bemondo(self)
        self.stat = self._statisztika_nyit()
        self.ertesito = Ertesito(lambda: self.b, self.log)
        self._reggeli_nap: date | None = None
        self._eszkoz_tar: set[str] | None = None
        self._media = QMediaDevices(self)
        self._media.audioOutputsChanged.connect(self._eszkozok_valtoztak)
        self._kovetkezo_kert = False
        self.spotify: Spotify | None = None
        self.naplo: deque[str] = deque(maxlen=1000)
        self.riasztas = False
        self.keresek = Keresek()
        self._kihagyott: Esemeny | None = None
        self._esemenyek: list[Esemeny] = []
        self._nap: date | None = None
        self._utolso: datetime | None = None
        self._auto_zene = False
        self._auto_riado = False
        self._sor: deque[_Feladat] = deque()
        self.csengo.kesz.connect(self._kovetkezo_feladat)
        self.bemondo.kesz.connect(self._kovetkezo_feladat)
        self.bemondo.hangfajl_kesz.connect(self._bemondas_hangfajl)
        self.zene.hiba.connect(self._zenehiba)
        self.zene.szam_valtozott.connect(lambda cim, forras: self.log(f"Zene: {cim} ({forras})"))
        self.zene.szam_valtozott.connect(self._szam_stat)
        self.zene.allapot_valtozott.connect(lambda _: self.frissult.emit())
        self.zene.allapot_valtozott.connect(self._zene_allapot_stat)
        self.zene.kert_szol.connect(self._kert_szol)
        self._ora = QTimer(self)
        self._ora.setInterval(250)
        self._ora.timeout.connect(self._tick)
        self._mento = QTimer(self)
        self._mento.setSingleShot(True)
        self._mento.setInterval(600)
        self._mento.timeout.connect(self.mentes)
        self.frissito = Frissito(self, self)
        self.tartalek = Tartalek(beallitasok, self)
        self.tartalek.valtozott.connect(self.frissult.emit)
        self.tartalek.atvetel.connect(self._atvetel)
        self.tartalek.visszaadas.connect(self._visszaadas)
        self.tartalek.atvetel.connect(lambda: self.ertesito.kuld(
            "tartalek", "A tartalékgép átvette a csengetést", "A fő gép nem válaszol, ez a gép csenget helyette.",
            "hiba", ismetles_mp=60))
        self.tartalek.visszaadas.connect(lambda: self.ertesito.kuld(
            "tartalek", "A fő gép újra működik", "A tartalékgép visszaadta a csengetést a fő gépnek.", "info",
            ismetles_mp=60))
        self.tartalek.szinkronizalt.connect(self._szinkronizalt)
        self._web_indult = False
        self.web = WebPanel(self)
        self.beallitasok_alkalmazasa()

    def indit(self) -> None:
        self.log(f"Közgáz FM {__version__} elindult")
        self.ertesito.kuld("indulas", "A Közgáz FM elindult", f"Verzió: {__version__}. Ha nem te indítottad "
                           "újra, lehet, hogy összeomlott vagy áramszünet volt.", "info", ismetles_mp=60)
        QTimer.singleShot(20000, self._kimenet_ellenoriz)
        self._leallas_alatt_kimaradt()
        self._eletjel = QTimer(self)
        self._eletjel.setInterval(60000)
        self._eletjel.timeout.connect(self._eletjel_ir)
        self._eletjel.start()
        self._eletjel_ir()
        self._ora.start()
        self.frissito.indit()
        self._web_indult = True
        self.web.alkalmaz()
        self.tartalek.alkalmaz()
        QTimer.singleShot(1500, self._szinkron)

    def leallit(self) -> None:
        if self._mento.isActive():
            self.mentes()
        self._ora.stop()
        self.tartalek.leallit()
        self.web.leallit()
        self.kiegyenlito.leallit()
        self.zene.allj()
        if self.stat:
            self.stat.bezar()
        self.csengo.megallit()
        self.proba.megallit()
        self.bemondo.megallit()

    @staticmethod
    def _statisztika_nyit() -> Statisztika | None:
        try:
            stat = Statisztika()
            stat.takarit()
            return stat
        except Exception as e:
            naplo.warning("A statisztika nem nyitható meg: %s", e)
            return None

    def _zene_allapot_stat(self, szol: bool) -> None:
        if self.stat is None:
            return
        if not szol:
            self.stat.szam_vege()
        else:
            QTimer.singleShot(1500, self._folytatas_stat)

    def _folytatas_stat(self) -> None:
        if self.stat and self.zene.szol and not self.stat.nyitott and self.zene.most_cim:
            forras = self.zene.forras.nev if self.zene.forras else ""
            self.stat.szam_kezd(self.zene.most_cim, forras)

    def _szam_stat(self, cim: str, forras: str) -> None:
        kert, self._kovetkezo_kert = self._kovetkezo_kert, False
        if self.stat:
            self.stat.szam_kezd(cim, forras, kert)

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

    def _jelez(self, szoveg: str, szint: str = "info", ertesit: bool = True) -> None:
        self.log(szoveg if szint == "info" else f"HIBA: {szoveg}")
        self.uzenet.emit(szoveg, szint)
        if szint == "hiba" and ertesit:
            self.ertesito.kuld("hiba", "Hiba a csengetőn", szoveg, "figy")

    def _tiltas(self, szoveg: str) -> None:
        self.log(szoveg)
        self.uzenet.emit(szoveg, "hiba")

    def _zenehiba(self, szoveg: str) -> None:
        self._jelez(szoveg, "hiba", ertesit=False)
        self.ertesito.kuld("hiba", "Zenehiba", szoveg, "figy", kulcs_szoveg="zenehiba")

    def _eletjel_ir(self) -> None:
        with contextlib.suppress(OSError):
            eletjel_fajl().write_text(datetime.now().isoformat(timespec="seconds"), encoding="utf-8")

    def _leallas_alatt_kimaradt(self) -> None:
        try:
            utolso = datetime.fromisoformat(eletjel_fajl().read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return
        most = datetime.now()
        if most - utolso > timedelta(minutes=2):
            self._kimaradtak(utolso, most)

    def zona_kimenetek(self) -> list[ZonaKimenet]:
        if not self.b.zonak:
            return [ZonaKimenet("Alapértelmezett", self.b.kimenet)]
        return [ZonaKimenet(z.nev or f"{i}. zóna", z.kimenet, z.csengo, z.zene, z.bemondas,
                            max(0, min(100, z.hangero)) / 100) for i, z in enumerate(self.b.zonak, 1)]

    def _bemondas_hangfajl(self, ut: str) -> None:
        if not self.csengo.lejatszas(Path(ut), self.b.csengo_hangero, cel="bemondas"):
            self._kovetkezo_feladat()

    def kimenet_nev(self) -> str | None:
        kimenetek = QMediaDevices.audioOutputs()
        if not kimenetek:
            return None
        if self.b.zonak:
            return None if self.hianyzo_zonak() else ", ".join(
                f"{z.nev}: {kimeneti_eszkoz(z.kimenet).description()}" for z in self.b.zonak)
        if self.b.kimenet:
            return next((e.description() for e in kimenetek if eszkoz_azonosito(e) == self.b.kimenet), None)
        return QMediaDevices.defaultAudioOutput().description() or kimenetek[0].description()

    def _kimenet_ellenoriz(self) -> None:
        if self.kimenet_nev() is not None:
            return
        if not QMediaDevices.audioOutputs():
            szoveg = "A gépen nincs elérhető hangkimenet, a csengő nem fog szólni. Ellenőrizd a hangkártyát, " \
                     "a HDMI- vagy USB-kábelt."
        elif self.b.zonak:
            szoveg = f"Nem érhető el ezeknek a zónáknak a hangkimenete: {', '.join(self.hianyzo_zonak())}. " \
                     "Ott az alapértelmezett kimenet szól; ellenőrizd a kábeleket és az erősítőket."
        else:
            szoveg = "A beállított hangkimenet nem érhető el (pl. kihúzták a kábelt), a csengő az alapértelmezett " \
                     "kimeneten szól. Ellenőrizd az erősítő bekötését."
        self.log(f"HIBA: {szoveg}")
        self.ertesito.kuld("hangkimenet", "Hangkimenet-gond", szoveg, "hiba")

    def _reggeli_onteszt(self, most: datetime) -> None:
        if self._reggeli_nap == most.date() or self.tartalek.passziv or not self.ertesito.bekapcsolt("reggel"):
            return
        try:
            ido_ = datetime.combine(most.date(), time.fromisoformat(self.b.ertesites_reggel_ido))
        except ValueError:
            return
        if most < ido_ or most - ido_ > timedelta(hours=3):
            return
        self._reggeli_nap = most.date()
        rend = napi_rend(self.b, most.date())
        if rend is None:
            return
        csengok = [e for e in self._esemenyek if e.tipus in CSENGOK]
        forras = self.aktiv_forras()
        tegnap = self.stat.osszegzes(most.date() - timedelta(days=1), most.date() - timedelta(days=1)) \
            if self.stat else None
        hatar = f"{most - timedelta(hours=24):%Y-%m-%d %H:%M:%S}"
        hibak = sum(1 for sor in self.naplo if sor[:19] >= hatar and "HIBA:" in sor)
        try:
            szabad = shutil.disk_usage(adat_mappa()).free / 1e9
        except OSError:
            szabad = None
        cim, uzenet, szint = reggeli_jelentes(
            nap=most.date(), rend=rend.nev, elso=min((e.ido for e in csengok), default=None),
            csengetesek=len(csengok), kimenet=self.kimenet_nev(), forras=forras.nev if forras else None,
            szamok=len(self.zene.szamok), tegnap=tegnap, hibak=hibak,
            uj_verzio=self.frissito.kiadas.verzio if self.frissito.kiadas else None, szabad_gb=szabad)
        self.log(f"Reggeli önteszt: {cim}")
        self.ertesito.kuld("reggel", cim, uzenet, szint, ismetles_mp=0)

    def beallitasok_alkalmazasa(self) -> None:
        b = self.b
        zonak = self.zona_kimenetek()
        self.csengo.zonak(zonak)
        self.proba.zonak(zonak)
        self.zene.zonak(zonak)
        self.bemondo.zona_mod = bool(b.zonak)
        self.zene.keveres = b.keveres
        self.zene.gyorsitotar = b.youtube_gyorsitotar
        self.zene.elhalkitas_mp = b.elhalkitas
        self.zene.atusztatas_mp = b.atusztatas
        self.zene.hangero(b.zene_hangero)
        self.zene.spotify_eszkoz = b.spotify_eszkoz
        self.kiegyenlito.bekapcsolva = b.hangero_kiegyenlites
        self.zene.erosites_ujra()
        for szam in self.zene.szamok:
            self.kiegyenlito.kell(szam.helyi)
        self.bemondo.beallit(b.tts_hang, b.csengo_hangero)
        if b.spotify_client_id and (self.spotify is None or self.spotify.client_id != b.spotify_client_id.strip()):
            self.spotify = Spotify(b.spotify_client_id, adat_mappa() / "spotify_token.json")
        elif not b.spotify_client_id:
            self.spotify = None
        self.zene.spotify = self.spotify
        self.zene.forras_beallitas(self.aktiv_forras())
        if self._web_indult:
            self.web.alkalmaz()
            self.tartalek.alkalmaz()
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

    def _csengo_elenged(self, ertek: str) -> None:
        self.proba.elenged()
        if not self.csengo.szol:
            self.csengo.elenged()
            return
        if sajat_hangok.ut(ertek) in self.csengo.lejatszo.forrasok():
            raise sajat_hangok.SajatHangHiba("Ez a hang most szól. Várd meg, amíg elhallgat, és próbáld újra.")

    def hang_proba(self, ertek: str) -> bool:
        if self.proba.szol:
            self.proba.megallit()
            return True
        if self.riasztas or self.csengo.szol:
            self._tiltas("Csengetés vagy riasztás közben nincs meghallgatás.")
            return True
        return self.proba.lejatszas(ertek, self.b.csengo_hangero, cel="elso")

    def zona_proba(self, index: int) -> bool:
        if self.riasztas or self.csengo.szol:
            self._tiltas("Csengetés vagy riasztás közben nincs próbahang.")
            return False
        self.proba.zonak(self.zona_kimenetek())
        return self.proba.lejatszas(self.b.hang_gong, self.b.csengo_hangero, cel=f"zona:{index}")

    def hianyzo_zonak(self) -> list[str]:
        if self._eszkoz_tar is None:
            self._eszkoz_tar = {eszkoz_azonosito(e) for e in QMediaDevices.audioOutputs()}
        return [z.nev or "névtelen" for z in self.b.zonak if z.kimenet and z.kimenet not in self._eszkoz_tar]

    def _eszkozok_valtoztak(self) -> None:
        self._eszkoz_tar = None
        self._kimenet_ellenoriz()

    def sajat_hang_atnevezes(self, ertek: str, nev: str) -> sajat_hangok.SajatHang:
        self._csengo_elenged(ertek)
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
        self._csengo_elenged(ertek)
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
                self._kimaradtak(elozo, most)
            self._szinkron()
            return
        self._reggeli_onteszt(most)
        if elozo.date() != most.date():
            esemenyek = napi_esemenyek(self.b, elozo.date()) + self._esemenyek
        else:
            esemenyek = self._esemenyek
        for e in esemenyek:
            if elozo < e.ido <= most:
                self._kezel(e)

    def _kimaradtak(self, elozo: datetime, most: datetime) -> None:
        if self.tartalek.passziv:
            return
        esemenyek = [e for nap in sorted({elozo.date(), most.date()}) for e in
                     (self._esemenyek if nap == self._nap else napi_esemenyek(self.b, nap))]
        kimaradt = kimaradt_csengetesek(esemenyek, elozo, most, (*CSENGOK, Tipus.RENDKIVULI))
        if not kimaradt:
            return
        lista = ", ".join(f"{e.ido:%H:%M} {e.leiras}" for e in kimaradt[:8])
        tovabbi = f" és még {len(kimaradt) - 8}" if len(kimaradt) > 8 else ""
        szoveg = f"{len(kimaradt)} csengetés kimaradt ({elozo:%m.%d. %H:%M} és {most:%m.%d. %H:%M} között a " \
                 f"program nem futott, a gép aludt vagy ugrott az órája): {lista}{tovabbi}"
        self.log(f"HIBA: {szoveg}")
        self.ertesito.kuld("kimaradt", "Kimaradt csengetés", szoveg, "hiba")

    def _szinkron(self) -> None:
        most = datetime.now()
        if self.riasztas:
            return
        if self.tartalek.passziv:
            if self._auto_zene and self.zene.szol:
                self.zene.megallit()
            self._auto_zene = False
            self.frissult.emit()
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
        if self.tartalek.passziv:
            if e.tipus in CSENGOK or e.tipus is Tipus.RENDKIVULI:
                self._kihagyott = e
            return
        if self.riasztas and e.tipus not in (Tipus.ZENE_LEALL, Tipus.RIADO_VEGE, Tipus.CSEND, Tipus.CSEND_VEGE):
            self.log(f"Kihagyva riasztás miatt: {e.leiras}")
            return
        if e.tipus is Tipus.RIADO:
            self.log(f"Rendkívüli esemény: {e.leiras}")
            self.riasztas_indit()
            self._auto_riado = True
        elif e.tipus is Tipus.RIADO_VEGE:
            if self.riasztas and self._auto_riado:
                self.riasztas_leallit()
        elif e.tipus in (Tipus.CSEND, Tipus.CSEND_VEGE):
            self.log(f"Csendes időszak {'kezdődik' if e.tipus is Tipus.CSEND else 'véget ért'}: "
                     f"{e.rendkivuli.nev if e.rendkivuli else ''}")
            if e.tipus is Tipus.CSEND and self.zene.szol:
                self.zene_leallit()
        elif e.tipus is Tipus.RENDKIVULI and e.rendkivuli:
            if self.zene.szol:
                self._auto_zene = False
                self.zene.megallit(elhalkitas=False)
            self.csengetes(e.rendkivuli.hang, e.leiras, tervezett=e.ido, tipus=e.tipus.name.lower())
        elif e.tipus is Tipus.ZENE_INDUL:
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
            self.csengetes(hang, e.leiras, e.hangero, tervezett=e.ido, tipus=e.tipus.name.lower())
        elif e.tipus is Tipus.KICSENGO:
            self.csengetes(self.b.hang_kicsengo, e.leiras, e.hangero, tervezett=e.ido, tipus="kicsengo")
        self.frissult.emit()

    def _foglalt(self) -> bool:
        if self.csengo.szol:
            self.csengo.megallit()
            return True
        if self.bemondo.beszel:
            self.bemondo.megallit()
            return True
        return False

    def csengetes(self, hang: str, leiras: str = "Kézi csengetés", hangero: int | None = None,
                  tervezett: datetime | None = None, tipus: str = "kezi") -> None:
        if self.riasztas:
            self._tiltas("Riasztás közben nincs csengetés.")
            return
        self.log(f"Csengetés: {leiras}" + (f" (halkan, {hangero}%)" if hangero is not None else ""))
        if self.stat:
            self.stat.csengetes(tipus, leiras, tervezett)
        self._sor.appendleft(_Feladat("hang", hang, tartalek=self._tartalek(hang), hangero=hangero))
        if not self._foglalt():
            self._kovetkezo_feladat()

    def bemondas(self, bem: Bemondas) -> None:
        if self.riasztas:
            self._tiltas("Riasztás közben nincs bemondás.")
            return
        self.log(f"Bemondás: {bem.nev}")
        if bem.gong:
            self._sor.append(_Feladat("hang", self.b.hang_gong, tartalek=HANG_MEZOK["hang_gong"], cel="bemondas"))
        self._sor.append(_Feladat("szoveg" if bem.tipus == "szoveg" else "fajl", bem.tartalom, cel="bemondas"))
        if not self.csengo.szol and not self.bemondo.beszel:
            self._kovetkezo_feladat()

    def gyors_bemondas(self, szoveg: str, gong: bool = True) -> None:
        self.bemondas(Bemondas("Gyors bemondás", "00:00", tipus="szoveg", tartalom=szoveg, gong=gong))

    def bemondas_leallit(self) -> None:
        self._sor = deque(f for f in self._sor if f.tipus == "hang" and f.ertek != self.b.hang_gong)
        if self.bemondo.beszel:
            self.bemondo.megallit()
        elif self.csengo.szol and not self.riasztas:
            self.csengo.megallit()

    def _kovetkezo_feladat(self) -> None:
        self.proba.megallit()
        while self._sor:
            feladat = self._sor.popleft()
            self.zene.halkit(True)
            if feladat.tipus == "szoveg":
                if self.bemondo.mond(feladat.ertek):
                    return
                self._jelez("A gépen nincs elérhető felolvasó hang (TTS).", "hiba")
                continue
            forras = Path(feladat.ertek) if feladat.tipus == "fajl" else feladat.ertek
            hangero = 100 if feladat.ismetles else feladat.hangero or self.b.csengo_hangero
            if self.csengo.lejatszas(forras, hangero, feladat.ismetles, cel=feladat.cel):
                return
            if feladat.tartalek and feladat.tartalek != feladat.ertek:
                self._jelez("A beállított csengőhang nem található, a beépített hang szól helyette.", "hiba")
                if self.csengo.lejatszas(feladat.tartalek, hangero, feladat.ismetles, cel=feladat.cel):
                    return
            self._jelez(f"A hangfájl nem található: {feladat.ertek}", "hiba")
        if not self.riasztas:
            self.zene.halkit(False)

    def riasztas_indit(self) -> None:
        if self.riasztas:
            return
        self.riasztas = True
        self._auto_riado = False
        self._auto_zene = False
        self.zene.megallit(elhalkitas=False)
        self.log("RIASZTÁS ELINDÍTVA")
        self.ertesito.kuld("riasztas", "Riasztás indult", f"{datetime.now():%H:%M}-kor elindult a riasztás a "
                           "Közgáz FM-en.", "hiba", ismetles_mp=60)
        self._sor.clear()
        self._sor.append(_Feladat("hang", self.b.hang_riasztas, ismetles=True, cel="mind",
                                  tartalek=HANG_MEZOK["hang_riasztas"]))
        if not self._foglalt():
            self._kovetkezo_feladat()
        self.riasztas_valtozott.emit(True)
        self.frissult.emit()

    def riasztas_leallit(self) -> None:
        if not self.riasztas:
            return
        self.riasztas = False
        self._auto_riado = False
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

    def _atvetel(self) -> None:
        self._jelez("A fő gép nem válaszol – a tartalék gép átvette a csengetést.", "hiba", ertesit=False)
        e, self._kihagyott = self._kihagyott, None
        if e is not None and timedelta() <= datetime.now() - e.ido <= timedelta(seconds=60):
            self.log(f"Kimaradt csengetés pótlása: {e.leiras}")
            self._kezel(e)
        self._szinkron()

    def _visszaadas(self) -> None:
        self.log("A fő gép újra elérhető – a tartalék gép visszaállt készenlétbe")
        self._kihagyott = None
        self._szinkron()

    def _szinkronizalt(self, valtozott: list) -> None:
        if valtozott:
            self.log(f"Beállítások átvéve a fő gépről ({len(valtozott)} csoport)")
            self.mentes()

    def zenekeres_uj(self, szoveg: str, nev: str, eszkoz: str, ip: str) -> Keres:
        if not self.b.zenekeres:
            raise KeresHiba("disabled", "A zenekérés most nincs bekapcsolva.")
        k = self.keresek.uj(szoveg, nev, eszkoz, ip, self.b.zenekeres_napi, self.b.zenekeres_tiltott)
        self.log(f"Zenekérés érkezett ({ip}): {k.szoveg}")
        if self.stat:
            self.stat.keres("erkezett")
        azon, cel = k.azon, youtube_cel(k.szoveg)

        def kesz(talalat: tuple[str, str, int] | None) -> None:
            if talalat is None:
                self.keresek.nem_talalt(azon, "Nem található ilyen szám a YouTube-on.")
            else:
                k = self.keresek.talalat(azon, *talalat, self.b.zenekeres_max_perc, self.b.zenekeres_tiltott)
                if k.allapot == "varakozik":
                    self.uzenet.emit(f"Új zenekérés: {k.cim}", "info")
            self.keresek_valtoztak.emit()

        def hiba(_e: Exception) -> None:
            self.keresek.nem_talalt(azon, "A keresés nem sikerült, próbáld újra később.")
            self.keresek_valtoztak.emit()

        hatter.futtat(lambda: youtube.egy_szam(cel), kesz, hiba)
        self.keresek_valtoztak.emit()
        return k

    def zenekeres_dontes(self, azon: str, elfogad: bool, ki: str = "") -> Keres:
        k = self.keresek.keres(azon)
        if elfogad and k.allapot == "varakozik" and not self.zene.beszur(Szam(k.cim, yt=k.yt)):
            raise KeresHiba("no_source", "A kért szám csak mappa, MP3 vagy YouTube forrás mellett játszható "
                                         "(Spotify mellett nem).")
        k = self.keresek.dont(azon, elfogad)
        self.log(f"Zenekérés {'elfogadva' if elfogad else 'elutasítva'}{f' ({ki})' if ki else ''}: {k.cim}")
        if self.stat:
            self.stat.keres("elfogadva" if elfogad else "elutasitva")
        self.keresek_valtoztak.emit()
        return k

    def _kert_szol(self, yt: str) -> None:
        self._kovetkezo_kert = True
        if self.keresek.szol(yt):
            self.keresek_valtoztak.emit()

    def aktiv_csend(self, most: datetime | None = None) -> Rendkivuli | None:
        most = most or datetime.now()
        return next((r for kezdet, vege, r in csendes_idoszakok(self.b, most.date()) if kezdet <= most < vege), None)

    def csend_most(self, perc: int, hangero: int = 0, nev: str = "Csendes időszak") -> Rendkivuli:
        most = datetime.now()
        kezdet = most.replace(second=0, microsecond=0)
        vege = min(kezdet + timedelta(minutes=perc), datetime.combine(most.date(), time(23, 59)))
        if vege <= most:
            raise ValueError("A nap végéig már nem fér bele csendes időszak.")
        r = Rendkivuli(nev, most.date().isoformat(), f"{kezdet:%H:%M}", tipus="csend", ig=f"{vege:%H:%M}",
                       csengo_hangero=hangero)
        self.b.rendkivuli.append(r)
        self.log(f"Csendes időszak kezdődik: {nev} ({r.tol}–{r.ig})")
        if self.zene.szol:
            self.zene_leallit()
        self.mentes()
        return r

    def csend_vege(self) -> bool:
        most = datetime.now()
        r = self.aktiv_csend(most)
        if r is None:
            return False
        r.ig = f"{most:%H:%M}"
        if r.ig <= r.tol:
            self.b.rendkivuli.remove(r)
        self.log(f"Csendes időszak befejezve: {r.nev}")
        self.mentes()
        return True

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
