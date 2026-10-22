from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QSpinBox,
)

from kozgaz_fm import hatter, youtube
from kozgaz_fm.beallitasok import ZeneForras
from kozgaz_fm.hang import FORRAS_TIPUSOK, HANGFAJLOK
from kozgaz_fm.spotify import ATIRANYITAS, SpotifyHiba, spotify_uri
from kozgaz_fm.ui.elemek import Kartya, Oldal, cimke, gomb, ido_mezo, kapcsolo, sor
from kozgaz_fm.ui.tema import SZIN, ikon
from kozgaz_fm.utvonalak import gyorsitotar_mappa
from kozgaz_fm.vezerlo import Vezerlo

FORRAS_IKON = {"mappa": "mappa", "fajlok": "fajl", "youtube": "youtube", "spotify": "spotify"}


class ZeneOldal(Oldal):
    def __init__(self, v: Vezerlo) -> None:
        super().__init__("Zene", "Szünetzene forrásai: helyi mappa vagy MP3-fájlok, YouTube-lejátszási lista "
                         "vagy Spotify. A kiválasztott forrás szól a szünetekben.")
        self.v = v
        felso = QGridLayout()
        felso.setSpacing(16)
        felso.addWidget(self._forras_kartya(), 0, 0)
        felso.addWidget(self._lista_kartya(), 0, 1)
        felso.setColumnStretch(0, 3)
        felso.setColumnStretch(1, 2)
        self.add(felso)
        also = QGridLayout()
        also.setSpacing(16)
        also.addWidget(self._beallitas_kartya(), 0, 0)
        also.addWidget(self._spotify_kartya(), 0, 1)
        also.setColumnStretch(0, 1)
        also.setColumnStretch(1, 1)
        self.add(also)
        self.elrendezes.addStretch(1)
        v.zene.lista_valtozott.connect(self._lista_frissit)
        v.zene.szam_valtozott.connect(lambda *_: self._lista_kijeloles())
        self._forrasok_frissit()
        self._lista_frissit()
        self._spotify_allapot()

    def _forras_kartya(self) -> Kartya:
        k = Kartya("Zeneforrások")
        self.forrasok = QListWidget()
        self.forrasok.setMinimumHeight(240)
        self.forrasok.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.forrasok.itemDoubleClicked.connect(lambda _: self._kivalaszt())
        self.forrasok.itemChanged.connect(self._aktiv_valtozott)
        uj_gombok = []
        for tipus, felirat in (("mappa", "Mappa"), ("fajlok", "MP3-fájlok"), ("youtube", "YouTube"),
                               ("spotify", "Spotify")):
            g = gomb(felirat, "plusz", tipp=f"{FORRAS_TIPUSOK[tipus]} forrás hozzáadása")
            g.clicked.connect(lambda _=False, t=tipus: self._uj(t))
            uj_gombok.append(g)
        kivalaszt = gomb("Ez szóljon", "pipa", "fo", "A kijelölt forrás lesz a szünetzene")
        kivalaszt.clicked.connect(self._kivalaszt)
        szerkeszt = gomb("Szerkesztés")
        szerkeszt.clicked.connect(self._szerkeszt)
        fel = gomb("", "fel", tipp="Feljebb")
        fel.clicked.connect(lambda: self._mozgat(-1))
        le = gomb("", "le", tipp="Lejjebb")
        le.clicked.connect(lambda: self._mozgat(1))
        torol = gomb("", "kuka", tipp="Forrás törlése")
        torol.clicked.connect(self._torol)
        k.add(cimke("Új forrás:", "halvany"))
        k.add(sor(*uj_gombok, nyujt=True))
        k.add(self.forrasok)
        k.add(sor(kivalaszt, szerkeszt, None, fel, le, torol))
        k.add(cimke("A pipa nélküli forrás nem jelenik meg a vezérlőpulton. Dupla kattintás = kiválasztás.",
                    "halvany", sortores=True))
        return k

    def _lista_kartya(self) -> Kartya:
        k = Kartya("Lejátszási sor")
        self.sor_cim = cimke("", "halvany")
        self.lista = QListWidget()
        self.lista.setMinimumHeight(300)
        self.lista.itemDoubleClicked.connect(lambda e: self.v.zene.ugras(self.lista.row(e)))
        ujratolt = gomb("Újratöltés", "frissites", tipp="A forrás újraolvasása (pl. új fájlok a mappában)")
        ujratolt.clicked.connect(lambda: self.v.zene.betoltes())
        k.add(self.sor_cim)
        k.add(self.lista)
        k.add(sor(cimke("Dupla kattintás: lejátszás onnan", "halvany"), None, ujratolt))
        return k

    def _beallitas_kartya(self) -> Kartya:
        b = self.v.b
        k = Kartya("Szünetzene beállításai")
        auto = kapcsolo("Automatikus zene a szünetekben", b.zene_szunetben)
        auto.toggled.connect(lambda e: self._allit("zene_szunetben", e))
        keveres = kapcsolo("Véletlen sorrend (keverés)", b.keveres)
        keveres.toggled.connect(lambda e: self._allit("keveres", e))
        reggeli = kapcsolo("Reggeli zene az első óra előtt, ettől:", b.reggeli_zene)
        reggeli.toggled.connect(lambda e: self._allit("reggeli_zene", e))
        reggel_ido = ido_mezo(b.reggeli_zene_tol)
        reggel_ido.timeChanged.connect(lambda t: self._allit("reggeli_zene_tol", t.toString("HH:mm")))
        racs = QGridLayout()
        racs.setVerticalSpacing(10)
        mezok = [
            ("Csak ennél hosszabb szünetben:", QSpinBox(minimum=1, maximum=60, suffix=" perc"), "zene_min_szunet"),
            ("Kicsengetés után ennyivel indul:", QSpinBox(minimum=0, maximum=300, suffix=" mp"), "zene_kesleltetes"),
            ("A következő csengő előtt ennyivel áll le:", QSpinBox(minimum=0, maximum=600, suffix=" mp"),
             "zene_leall_elotte"),
            ("Elhalkítás hossza:", QDoubleSpinBox(minimum=0, maximum=15, singleStep=0.5, suffix=" mp"), "elhalkitas"),
            ("Átúsztatás a számok között:", QDoubleSpinBox(minimum=0, maximum=12, singleStep=0.5, suffix=" mp",
                                                          specialValueText="nincs (szünet nélkül egymás után)"),
             "atusztatas"),
        ]
        for i, (felirat, mezo, nev) in enumerate(mezok):
            mezo.setValue(getattr(b, nev))
            mezo.valueChanged.connect(lambda e, n=nev: self._allit(n, e))
            racs.addWidget(cimke(felirat), i, 0)
            racs.addWidget(mezo, i, 1)
        racs.setColumnStretch(0, 1)
        k.add(auto)
        k.add(racs)
        k.add(sor(reggeli, reggel_ido, nyujt=True))
        k.add(keveres)
        gyors = kapcsolo("YouTube-számok előre letöltése (akadásmentes, net nélkül is szól)", b.youtube_gyorsitotar)
        gyors.toggled.connect(lambda e: self._allit("youtube_gyorsitotar", e))
        self.gyors_cimke = cimke("", "halvany")
        urit = gomb("Gyorsítótár ürítése", "kuka")
        urit.clicked.connect(self._urit)
        k.add(gyors)
        k.add(sor(self.gyors_cimke, None, urit))
        self._gyors_meret()
        return k

    def _spotify_kartya(self) -> Kartya:
        b = self.v.b
        k = Kartya("Spotify")
        k.add(cimke(
            "A Spotify vezérléséhez <b>Premium</b> fiók és a gépen futó Spotify alkalmazás kell. Egyszeri "
            "beállítás: <a href='https://developer.spotify.com/dashboard' style='color:" + SZIN["kek"] + "'>"
            "developer.spotify.com/dashboard</a> → <i>Create app</i> → Redirect URI: <b>" + ATIRANYITAS +
            "</b>, API: <i>Web API</i>. A kapott <b>Client ID</b>-t másold ide.", "halvany", sortores=True))
        k.elrendezes.itemAt(k.elrendezes.count() - 1).widget().setOpenExternalLinks(True)
        self.client_id = QLineEdit(b.spotify_client_id)
        self.client_id.setPlaceholderText("Client ID (32 karakter)")
        self.client_id.editingFinished.connect(self._client_id)
        masol = gomb("URI másolása", "masol", tipp="Redirect URI vágólapra")
        masol.clicked.connect(lambda: QGuiApplication.clipboard().setText(ATIRANYITAS))
        k.add(sor(self.client_id, masol))
        self.spotify_allapot = cimke("", "halvany", sortores=True)
        self.belep = gomb("Bejelentkezés", "spotify", "fo")
        self.belep.clicked.connect(self._belep)
        self.kilep = gomb("Kijelentkezés")
        self.kilep.clicked.connect(self._kilep)
        k.add(sor(self.belep, self.kilep, None))
        k.add(self.spotify_allapot)
        self.eszkozok = QComboBox()
        self.eszkozok.setToolTip("Melyik eszközön szóljon a Spotify (általában ez a gép)")
        self.eszkozok.activated.connect(self._eszkoz_valasztva)
        frissit = gomb("", "frissites", tipp="Eszközök frissítése")
        frissit.clicked.connect(self._eszkozok_frissit)
        k.add(sor(cimke("Lejátszó eszköz:"), self.eszkozok, frissit))
        return k

    def _allit(self, mezo: str, ertek) -> None:
        setattr(self.v.b, mezo, ertek)
        self.v.mentes_kesobb()

    def _forrasok_frissit(self, valasztott: int | None = None) -> None:
        b = self.v.b
        aktiv = self.v.aktiv_forras()
        self.forrasok.blockSignals(True)
        self.forrasok.clear()
        for f in b.forrasok:
            jelzes = "   ▶ most ez szól" if f is aktiv else ""
            cim = f.cim if f.tipus != "fajlok" else f"{len(f.cim.splitlines())} fájl"
            cim = cim if len(cim) <= 60 else cim[:57] + "…"
            elem = QListWidgetItem(ikon(FORRAS_IKON[f.tipus], SZIN["kiemelt"] if f is aktiv else SZIN["szoveg"]),
                                   f"{f.nev}{jelzes}\n{FORRAS_TIPUSOK[f.tipus]} · {cim}")
            elem.setFlags(elem.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            elem.setCheckState(Qt.CheckState.Checked if f.aktiv else Qt.CheckState.Unchecked)
            self.forrasok.addItem(elem)
        if valasztott is not None:
            self.forrasok.setCurrentRow(valasztott)
        self.forrasok.blockSignals(False)

    def _aktiv_valtozott(self, elem: QListWidgetItem) -> None:
        i = self.forrasok.row(elem)
        if 0 <= i < len(self.v.b.forrasok):
            self.v.b.forrasok[i].aktiv = elem.checkState() == Qt.CheckState.Checked
            self.v.mentes()
            self._forrasok_frissit(i)

    def _uj(self, tipus: str) -> None:
        forras = self._forras_bekeres(tipus)
        if forras is None:
            return
        self.v.b.forrasok.append(forras)
        if len(self.v.b.forrasok) == 1:
            self.v.b.aktiv_forras = 0
        self.v.mentes()
        self._forrasok_frissit(len(self.v.b.forrasok) - 1)

    def _forras_bekeres(self, tipus: str, regi: ZeneForras | None = None) -> ZeneForras | None:
        cim = regi.cim if regi else ""
        alap_nev = regi.nev if regi else ""
        if tipus == "mappa":
            cim = QFileDialog.getExistingDirectory(self, "Zenék mappája", cim)
            if not cim:
                return None
            alap_nev = alap_nev or Path(cim).name
        elif tipus == "fajlok":
            szuro = "Hangfájlok és listák (" + " ".join(f"*{k}" for k in (*HANGFAJLOK, ".m3u", ".m3u8")) + ")"
            fajlok, _ = QFileDialog.getOpenFileNames(self, "Zenefájlok kiválasztása", "", szuro)
            if not fajlok:
                return None
            cim = "\n".join(fajlok)
            alap_nev = alap_nev or (Path(fajlok[0]).stem if len(fajlok) == 1 else f"{len(fajlok)} kiválasztott szám")
        elif tipus == "youtube":
            cim, ok = QInputDialog.getText(self, "YouTube", "YouTube-videó vagy lejátszási lista linkje\n"
                                           "(vagy keresőszó, pl. „slágerek 2025”):", text=cim)
            cim = cim.strip()
            if not ok or not cim:
                return None
            alap_nev = alap_nev or "YouTube-lista"
        else:
            cim, ok = QInputDialog.getText(self, "Spotify", "Spotify lejátszási lista, album vagy szám linkje:",
                                           text=cim)
            cim = cim.strip()
            if not ok or not cim:
                return None
            if spotify_uri(cim) is None:
                QMessageBox.warning(self, "Spotify", "Ez nem érvényes Spotify-link. Másold ki a Spotifyban: "
                                    "Megosztás → Link másolása.")
                return None
            alap_nev = alap_nev or "Spotify-lista"
        nev, ok = QInputDialog.getText(self, "Forrás neve", "Milyen néven jelenjen meg?", text=alap_nev)
        if not ok:
            return None
        return ZeneForras(tipus, nev.strip() or alap_nev, cim, regi.aktiv if regi else True)

    def _kijelolt(self) -> int:
        i = self.forrasok.currentRow()
        return i if 0 <= i < len(self.v.b.forrasok) else -1

    def _kivalaszt(self) -> None:
        i = self._kijelolt()
        if i < 0:
            return
        self.v.b.forrasok[i].aktiv = True
        self.v.forras_valtas(i)
        self._forrasok_frissit(i)

    def _szerkeszt(self) -> None:
        i = self._kijelolt()
        if i < 0:
            return
        regi = self.v.b.forrasok[i]
        uj = self._forras_bekeres(regi.tipus, regi)
        if uj is None:
            return
        self.v.b.forrasok[i] = uj
        self.v.mentes()
        self._forrasok_frissit(i)

    def _mozgat(self, irany: int) -> None:
        i = self._kijelolt()
        j = i + irany
        f = self.v.b.forrasok
        if i < 0 or not 0 <= j < len(f):
            return
        aktiv = self.v.aktiv_forras()
        f[i], f[j] = f[j], f[i]
        if aktiv is not None:
            self.v.b.aktiv_forras = f.index(aktiv)
        self.v.mentes()
        self._forrasok_frissit(j)

    def _torol(self) -> None:
        i = self._kijelolt()
        if i < 0:
            return
        f = self.v.b.forrasok
        if QMessageBox.question(self, "Törlés", f"Törlöd a(z) „{f[i].nev}” forrást?") != QMessageBox.StandardButton.Yes:
            return
        aktiv = self.v.aktiv_forras()
        f.pop(i)
        self.v.b.aktiv_forras = f.index(aktiv) if aktiv in f else 0
        self.v.mentes()
        self._forrasok_frissit()

    def _lista_frissit(self) -> None:
        z = self.v.zene
        self.lista.clear()
        if z.forras is None:
            self.sor_cim.setText("Nincs kiválasztott forrás.")
        elif z.spotify_mod:
            self.sor_cim.setText(f"{z.forras.nev}: a sorrendet a Spotify kezeli.")
        elif not z.szamok:
            self.sor_cim.setText(f"{z.forras.nev}: betöltés indításkor…")
        else:
            self.sor_cim.setText(f"{z.forras.nev}: {len(z.szamok)} szám")
            for i, szam in enumerate(z.szamok, start=1):
                self.lista.addItem(f"{i}. {szam.cim}")
        self._lista_kijeloles()
        self._forrasok_frissit(self._kijelolt() if self._kijelolt() >= 0 else None)

    def _lista_kijeloles(self) -> None:
        z = self.v.zene
        if z.szamok and 0 <= z.index < self.lista.count():
            self.lista.setCurrentRow(z.index)
        self._gyors_meret()

    def _gyors_meret(self) -> None:
        mappa = gyorsitotar_mappa() / "youtube"
        meret = youtube.gyorsitotar_meret(mappa) if mappa.exists() else 0
        self.gyors_cimke.setText(f"Letöltve: {meret / 1024 / 1024:.0f} MB")

    def _urit(self) -> None:
        mappa = gyorsitotar_mappa() / "youtube"
        if mappa.exists():
            youtube.gyorsitotar_urites(mappa)
        for szam in self.v.zene.szamok:
            if szam.yt:
                szam.helyi = None
        self._gyors_meret()

    def _client_id(self) -> None:
        uj = self.client_id.text().strip()
        if uj != self.v.b.spotify_client_id:
            self.v.b.spotify_client_id = uj
            self.v.mentes()
            self._spotify_allapot()

    def _spotify_allapot(self) -> None:
        s = self.v.spotify
        be = bool(s and s.bejelentkezve)
        self.belep.setEnabled(bool(self.v.b.spotify_client_id))
        self.kilep.setEnabled(be)
        if not self.v.b.spotify_client_id:
            self.spotify_allapot.setText("Nincs Client ID megadva.")
        elif be:
            self.spotify_allapot.setText("✓ Összekapcsolva a Spotify-jal.")
            self._eszkozok_frissit()
        else:
            self.spotify_allapot.setText("Nincs bejelentkezve.")

    def _belep(self) -> None:
        self._client_id()
        s = self.v.spotify
        if s is None:
            return
        self.belep.setEnabled(False)
        self.spotify_allapot.setText("A böngészőben fejezd be a bejelentkezést… (3 perc van rá)")

        def kesz(_) -> None:
            self.v.log("Spotify összekapcsolva")
            self._spotify_allapot()

        def hiba(e: Exception) -> None:
            self._spotify_allapot()
            self.spotify_allapot.setText(str(e) if isinstance(e, SpotifyHiba) else f"Hiba: {e}")

        hatter.futtat(s.bejelentkezes, kesz, hiba)

    def _kilep(self) -> None:
        if self.v.spotify:
            self.v.spotify.kijelentkezes()
        self._spotify_allapot()

    def _eszkozok_frissit(self) -> None:
        s = self.v.spotify
        if not s or not s.bejelentkezve:
            return

        def kesz(eszkozok: list[dict]) -> None:
            self.eszkozok.clear()
            self.eszkozok.addItem("Automatikus (az aktív eszköz)", "")
            for e in eszkozok:
                self.eszkozok.addItem(f"{e.get('name')} ({e.get('type', '').lower()})", e.get("name"))
            if not eszkozok:
                self.eszkozok.addItem("Nincs eszköz – indítsd el a Spotify appot", "")
            self.eszkozok.setCurrentIndex(max(0, self.eszkozok.findData(self.v.b.spotify_eszkoz)))

        hatter.futtat(s.eszkozok, kesz, lambda e: self.spotify_allapot.setText(str(e)))

    def _eszkoz_valasztva(self, _sor: int) -> None:
        self.v.b.spotify_eszkoz = self.eszkozok.currentData() or ""
        self.v.mentes()
