__lazy_modules__ = [
    "json",
    "dataclasses",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtMultimedia",
    "PySide6.QtWidgets",
    "kozgaz_fm",
    "kozgaz_fm.beallitasok",
    "kozgaz_fm.ertesites",
    "kozgaz_fm.hang",
    "kozgaz_fm.tartalek",
    "kozgaz_fm.ui.elemek",
    "kozgaz_fm.ui.pin_ablak",
    "kozgaz_fm.ui.tema",
    "kozgaz_fm.utvonalak",
    "kozgaz_fm.vezerlo",
]

import json
from dataclasses import asdict

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QSpinBox,
)

from kozgaz_fm import APP_NEV, KESZITO, __version__, rendszer
from kozgaz_fm.beallitasok import Beallitasok, _ebbol
from kozgaz_fm.ertesites import ESEMENYEK, SMTP_MODOK, ErtesitesHiba, ntfy_cel
from kozgaz_fm.hang import eszkoz_azonosito
from kozgaz_fm.tartalek import SZEREPEK, TartalekHiba, cim_normalizal, uj_kulcs
from kozgaz_fm.ui.elemek import Kartya, Oldal, cimke, gomb, ido_mezo, kapcsolo, keskeny, sor
from kozgaz_fm.ui.pin_ablak import UjJelszoAblak, UjPinAblak
from kozgaz_fm.ui.tema import SZIN, TEMA_NEVEK, logo_pixmap
from kozgaz_fm.utvonalak import adat_mappa
from kozgaz_fm.vezerlo import Vezerlo

HELYI_MEZOK = ("admin_pin", "web_panel", "web_port", "web_jelszo", "tartalek_mod", "tartalek_cim", "tartalek_kulcs",
               "ertesites_ntfy", "ertesites_ntfy_token", "ertesites_email", "smtp_szerver", "smtp_port", "smtp_mod",
               "smtp_felhasznalo", "smtp_jelszo", "smtp_felado")


class BeallitasOldal(Oldal):
    kijelzo_kerelem = Signal(int)
    importalva = Signal()
    zar_valtozott = Signal()
    frissites_kerelem = Signal()
    tema_kerelem = Signal(str)

    def __init__(self, v: Vezerlo) -> None:
        super().__init__("Beállítások")
        self.v = v
        racs = QGridLayout()
        racs.setSpacing(16)
        racs.addWidget(self._hang_kartya(), 0, 0)
        racs.addWidget(self._inditas_kartya(), 0, 1)
        racs.addWidget(self._kijelzo_kartya(), 1, 0)
        racs.addWidget(self._mentes_kartya(), 1, 1)
        racs.addWidget(self._frissites_kartya(), 2, 0)
        racs.addWidget(self._rendszer_kartya(), 2, 1)
        racs.addWidget(self._hozzaferes_kartya(), 3, 0, 1, 2)
        racs.addWidget(self._web_kartya(), 4, 0, 1, 2)
        racs.addWidget(self._tartalek_kartya(), 5, 0, 1, 2)
        racs.addWidget(self._ertesites_kartya(), 6, 0, 1, 2)
        racs.addWidget(self._nevjegy_kartya(), 7, 0, 1, 2)
        racs.setColumnStretch(0, 1)
        racs.setColumnStretch(1, 1)
        self.add(racs)
        self.elrendezes.addStretch(1)
        self._media = QMediaDevices(self)
        self._media.audioOutputsChanged.connect(self._kimenetek)
        self._kimenetek()

    def _hang_kartya(self) -> Kartya:
        k = Kartya("Hangkimenet")
        k.add(cimke("Válaszd ki azt a hangkártyát / kimenetet, amelyik az iskolai hangosításra (erősítőre) "
                    "van kötve. A csengő, a zene és a bemondás is ide szól. (A Spotify a saját alkalmazásában "
                    "beállított kimenetet használja.)", "halvany", sortores=True))
        self.kimenet = keskeny(QComboBox(), 18)
        self.kimenet.activated.connect(self._kimenet_valasztva)
        proba = gomb("Próbahang", "lejatszas")
        proba.clicked.connect(lambda: self.v.hang_proba(self.v.b.hang_gong))
        k.add(sor(self.kimenet, proba))
        return k

    def _inditas_kartya(self) -> Kartya:
        k = Kartya("Indítás és működés")
        try:
            auto_be = rendszer.automatikus_inditas()
        except OSError:
            auto_be = False
        auto = kapcsolo("Automatikus indítás bejelentkezéskor", auto_be,
                        "Bejelentkezés után a tálcán indul, és azonnal csenget a rend szerint")
        auto.toggled.connect(self._auto)
        talca = kapcsolo("Bezáráskor fusson tovább a tálcán", self.v.b.talcara_zar,
                         "Kikapcsolva az ablak bezárása leállítja a csengetést is")
        talca.toggled.connect(lambda e: self._allit("talcara_zar", e))
        self.tema_valaszto = QComboBox()
        for kulcs, nev in TEMA_NEVEK.items():
            self.tema_valaszto.addItem(nev, kulcs)
        self.tema_valaszto.setCurrentIndex(max(0, self.tema_valaszto.findData(self.v.b.tema)))
        self.tema_valaszto.activated.connect(self._tema)
        k.add(auto)
        k.add(talca)
        k.add(sor(cimke("Megjelenés:"), self.tema_valaszto, None))
        k.add(cimke("Fontos: a csengetés csak akkor működik, ha a program fut. Az energiagazdálkodásban "
                    "kapcsold ki a gép alvó állapotát.", "halvany", sortores=True))
        return k

    def _kijelzo_kartya(self) -> Kartya:
        k = Kartya("Folyosói kijelző")
        k.add(cimke("Teljes képernyős óra és visszaszámláló kivetítőre vagy folyosói TV-re. Kilépés: Esc "
                    "vagy dupla kattintás.", "halvany", sortores=True))
        self.kijelzo_cim = QLineEdit(self.v.b.kijelzo_cim)
        self.kijelzo_cim.editingFinished.connect(lambda: self._allit("kijelzo_cim", self.kijelzo_cim.text().strip()))
        self.kepernyo = keskeny(QComboBox(), 12)
        for i, kep in enumerate(QGuiApplication.screens()):
            meret = kep.size()
            self.kepernyo.addItem(f"{i + 1}. képernyő – {kep.name()} ({meret.width()}×{meret.height()})", i)
        nyit = gomb("Kijelző indítása", "kijelzo", "fo")
        nyit.clicked.connect(lambda: self.kijelzo_kerelem.emit(self.kepernyo.currentData() or 0))
        k.add(sor(cimke("Felirat:"), self.kijelzo_cim))
        k.add(sor(self.kepernyo, nyit))
        return k

    def _mentes_kartya(self) -> Kartya:
        k = Kartya("Beállítások mentése")
        k.add(cimke("Minden beállítás (csengetési rendek, naptár, zeneforrások) egy fájlba menthető, és másik "
                    "gépre vihető.", "halvany", sortores=True))
        export = gomb("Exportálás…", "le")
        export.clicked.connect(self._export)
        imp = gomb("Importálás…", "fel")
        imp.clicked.connect(self._import)
        k.add(sor(export, imp, None))
        k.add(cimke(f"Adatmappa: {adat_mappa()}", "halvany", sortores=True))
        return k

    def _frissites_kartya(self) -> Kartya:
        f = self.v.frissito
        k = Kartya("Frissítések")
        modok = {"windows": "Windows-telepítő", "linux-csomag": "Linux-csomag", "venv": "Közgáz FM OS / Python",
                 "fejlesztoi": "fejlesztői futtatás (git)"}
        k.add(cimke(f"Telepített verzió: <b>{__version__}</b> ({modok.get(f.mod, f.mod)})", sortores=True))
        self.frissites_allapot = cimke(f.allapot or "Az új verziókat a GitHubról tölti le, ellenőrzött "
                                       "csomagból.", "halvany", sortores=True)
        self.frissites_halad = QProgressBar()
        self.frissites_halad.setRange(0, 1000)
        self.frissites_halad.setTextVisible(False)
        self.frissites_halad.hide()
        keres = gomb("Keresés most", "frissites")
        keres.clicked.connect(lambda: f.kereses(kezi=True))
        self.telepites_gomb = gomb("Részletek és telepítés…", "le", "fo")
        self.telepites_gomb.clicked.connect(self.frissites_kerelem.emit)
        auto_kereses = kapcsolo("Új verzió keresése automatikusan", self.v.b.frissites_kereses)
        auto_kereses.toggled.connect(lambda e: self._allit("frissites_kereses", e))
        auto = kapcsolo("Automatikus telepítés tanítási időn kívül", self.v.b.frissites_auto,
                        "Csak ha nincs óra, zene és riasztás, és a következő csengetésig van még 45 perc")
        auto.toggled.connect(lambda e: self._allit("frissites_auto", e))
        k.add(self.frissites_allapot)
        k.add(self.frissites_halad)
        k.add(sor(keres, self.telepites_gomb, None))
        k.add(auto_kereses)
        k.add(auto)
        f.allapot_valtozott.connect(self.frissites_allapot.setText)
        f.halad.connect(self._halad)
        f.kiadas_valtozott.connect(self._kiadas)
        self._kiadas(f.kiadas)
        return k

    def _rendszer_kartya(self) -> Kartya:
        k = Kartya("Rendszer")
        self.ido_cimke = cimke("", "halvany", sortores=True)
        ujra = gomb("Gép újraindítása", "frissites")
        ujra.clicked.connect(lambda: self._gep("újraindítod", rendszer.gep_ujrainditas))
        le = gomb("Gép leállítása", "stop", "veszely")
        le.clicked.connect(lambda: self._gep("leállítod", rendszer.gep_leallitas))
        k.add(cimke("A pontos csengetéshez a gép órájának pontosnak kell lennie (internetes időszinkron).",
                    "halvany", sortores=True))
        k.add(self.ido_cimke)
        os_adat = rendszer.kozgazfm_os()
        if os_adat is not None:
            ip = rendszer.ip_cim() or "nincs hálózat"
            k.add(cimke(f"Közgáz FM OS {os_adat.get('KOZGAZFM_OS_VERZIO', '?')}, IP-cím: <b>{ip}</b> "
                        f"(távoli asztal: {ip}:5900)", sortores=True))
        k.add(sor(ujra, le, None))
        self._ido_frissit()
        return k

    def _ido_frissit(self) -> None:
        allapot = rendszer.ido_szinkronban()
        if allapot is None:
            self.ido_cimke.setText("Időszinkron: a Windows kezeli (Gépház → Idő és nyelv → Szinkronizálás most).")
        elif allapot:
            self.ido_cimke.setText("Az óra szinkronban van az internetes időszerverrel.")
        else:
            self.ido_cimke.setText("Az óra nincs szinkronban. Ellenőrizd a hálózatot, különben a csengetés elcsúszhat.")

    def _gep(self, mit: str, muvelet) -> None:
        if QMessageBox.question(self, "Rendszer", f"Biztosan {mit} a gépet? Addig nem lesz csengetés."
                                ) == QMessageBox.StandardButton.Yes:
            self.v.leallit()
            muvelet()

    def _halad(self, ertek: float) -> None:
        self.frissites_halad.show()
        self.frissites_halad.setValue(int(ertek * 1000))

    def _kiadas(self, kiadas) -> None:
        self.telepites_gomb.setText(f"Új verzió: {kiadas.verzio}…" if kiadas is not None else "Részletek…")

    def _tema(self, _sor: int) -> None:
        nev = self.tema_valaszto.currentData()
        if nev == self.v.b.tema:
            return
        self.v.b.tema = nev
        self.v.mentes()
        self.tema_kerelem.emit(nev)

    def _hozzaferes_kartya(self) -> Kartya:
        k = Kartya("Hozzáférés")
        k.add(cimke("PIN-kóddal védheted a beállító oldalakat (Csengetési rend, Zene, Naptár, Bemondások, "
                    "Beállítások), hogy a hangosító gépnél ne lehessen véletlenül vagy kéretlenül átírni a "
                    "csengetést. A Vezérlőpult PIN nélkül is használható marad.", "halvany", sortores=True))
        self.pin_allapot = cimke()
        self.pin_beallit = gomb("PIN beállítása…", "pipa", "fo")
        self.pin_beallit.clicked.connect(self._pin_beallit)
        self.pin_ki = gomb("PIN kikapcsolása", "kuka")
        self.pin_ki.clicked.connect(self._pin_ki)
        self.zar_perc = QSpinBox(minimum=1, maximum=60, suffix=" perc tétlenség után")
        self.zar_perc.setValue(self.v.b.admin_zar_perc)
        self.zar_perc.setMaximumWidth(230)
        self.zar_perc.valueChanged.connect(self._zar_perc)
        k.add(self.pin_allapot)
        k.add(sor(self.pin_beallit, self.pin_ki, None, cimke("Automatikus zárolás:"), self.zar_perc))
        k.add(cimke("Elfelejtett PIN: futtasd egyszer így: <b>kozgaz-fm --pin-torles</b> (Windows-on: "
                    "<b>KozgazFM.exe --pin-torles</b>) – a futó program is azonnal megkapja.", "halvany",
                    sortores=True))
        self._pin_frissit()
        return k

    def _pin_frissit(self) -> None:
        van = bool(self.v.b.admin_pin)
        self.pin_allapot.setText("A beállítások PIN-kóddal védettek." if van else
                                 "Nincs PIN-kód: a beállításokat bárki módosíthatja.")
        self.pin_beallit.setText("PIN módosítása…" if van else "PIN beállítása…")
        self.pin_ki.setEnabled(van)
        self.zar_perc.setEnabled(van)

    def _pin_beallit(self) -> None:
        ablak = UjPinAblak(self)
        if ablak.exec() != QDialog.DialogCode.Accepted:
            return
        self.v.b.admin_pin = ablak.tarolt
        self.v.mentes()
        self.v.log("Rendszergazda PIN beállítva")
        self._pin_frissit()
        self.zar_valtozott.emit()

    def _pin_ki(self) -> None:
        if QMessageBox.question(self, "PIN kikapcsolása", "Kikapcsolod a PIN-védelmet? Utána bárki "
                                "módosíthatja a beállításokat.") != QMessageBox.StandardButton.Yes:
            return
        self.v.b.admin_pin = ""
        self.v.mentes()
        self.v.log("Rendszergazda PIN kikapcsolva")
        self._pin_frissit()
        self.zar_valtozott.emit()

    def _zar_perc(self, perc: int) -> None:
        self.v.b.admin_zar_perc = perc
        self.v.mentes_kesobb()
        self.zar_valtozott.emit()

    def _web_kartya(self) -> Kartya:
        k = Kartya("Webes vezérlés")
        k.add(cimke("Telefonról vagy a tanári gépéről, böngészőben is lehet csengetni, zenét indítani, bemondani "
                    "és riasztani – az iskolai hálózaton belül, jelszóval. A beállító oldalak csak itt, a programban "
                    "módosíthatók. Minden webes művelet bekerül a naplóba.", "halvany", sortores=True))
        self.web_be = kapcsolo("Webpanel bekapcsolása", self.v.b.web_panel)
        self.web_be.toggled.connect(self._web_kapcsolo)
        self.web_port = QSpinBox(minimum=1024, maximum=65535, prefix="Port: ")
        self.web_port.setValue(self.v.b.web_port)
        self.web_port.setMaximumWidth(160)
        self.web_port.editingFinished.connect(self._web_port)
        self.web_jelszo = gomb("Jelszó beállítása…", "lakat")
        self.web_jelszo.clicked.connect(self._web_jelszo_beallit)
        self.web_masol = gomb("Cím másolása", "masol")
        self.web_masol.clicked.connect(self._web_cim_masol)
        self.web_allapot = cimke(sortores=True)
        self.web_allapot.setTextFormat(Qt.TextFormat.RichText)
        self.web_allapot.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        k.add(sor(self.web_be, None, self.web_port, self.web_jelszo, self.web_masol))
        k.add(self.web_allapot)
        k.add(cimke("Windows-on az első bekapcsoláskor a tűzfal rákérdez: engedélyezd a <b>magánhálózaton</b>. "
                    "A jelszót csak annak add meg, aki csengethet; jelszócserekor mindenki kilép.", "halvany",
                    sortores=True))
        self.v.frissult.connect(self._web_frissit)
        self._web_frissit()
        return k

    def _web_frissit(self) -> None:
        b, web = self.v.b, self.v.web
        self.web_jelszo.setText("Jelszó módosítása…" if b.web_jelszo else "Jelszó beállítása…")
        cimek = web.cimek()
        self.web_masol.setEnabled(bool(cimek))
        if web.hiba:
            szoveg = f"<span style='color:{SZIN['hiba']}'>{web.hiba} Válassz másik portot.</span>"
        elif cimek:
            linkek = " vagy ".join(f"<b>{c}</b>" for c in cimek)
            szoveg = f"<span style='color:{SZIN['szol']}'>&#9679;</span>&nbsp; Elérhető: {linkek}"
        elif b.web_panel and not b.web_jelszo:
            szoveg = "Állíts be jelszót, utána indul el a webpanel."
        else:
            szoveg = "A webpanel ki van kapcsolva."
        if self.web_allapot.text() != szoveg:
            self.web_allapot.setText(szoveg)

    def _web_kapcsolo(self, be: bool) -> None:
        if be and not self.v.b.web_jelszo and not self._web_jelszo_beallit():
            self.web_be.blockSignals(True)
            self.web_be.setChecked(False)
            self.web_be.blockSignals(False)
            return
        self.v.b.web_panel = be
        self.v.mentes()
        self._web_frissit()

    def _web_port(self) -> None:
        if self.web_port.value() != self.v.b.web_port:
            self.v.b.web_port = self.web_port.value()
            self.v.mentes()
            self._web_frissit()

    def _web_jelszo_beallit(self) -> bool:
        ablak = UjJelszoAblak(self)
        if ablak.exec() != QDialog.DialogCode.Accepted:
            return False
        self.v.b.web_jelszo = ablak.tarolt
        self.v.mentes()
        self.v.log("Webpanel jelszava beállítva")
        self._web_frissit()
        return True

    def _web_cim_masol(self) -> None:
        cimek = self.v.web.cimek()
        if cimek:
            QGuiApplication.clipboard().setText(cimek[0])

    def _ertesites_kartya(self) -> Kartya:
        b = self.v.b
        k = Kartya("Értesítések a rendszergazdának")
        k.add(cimke("Telefonos értesítés, ha baj van (kimaradt csengetés, hiba, eltűnt hangkimenet, riasztás, "
                    "tartalékgép-átvétel), és reggeli önteszt tanítási napokon. Telefonra a legegyszerűbb az "
                    "ingyenes ntfy alkalmazás: válassz egy hosszú, nehezen kitalálható témanevet, iratkozz fel rá "
                    "az appban, és írd ide a teljes címet. E-mailhez az iskola SMTP-szervere kell.",
                    "halvany", sortores=True))
        racs = QGridLayout()
        racs.setHorizontalSpacing(12)
        racs.setVerticalSpacing(8)

        def mezo(nev: str, ertek: str, tipp: str, jelszo: bool = False) -> QLineEdit:
            m = QLineEdit(ertek)
            m.setPlaceholderText(tipp)
            if jelszo:
                m.setEchoMode(QLineEdit.EchoMode.Password)
            m.editingFinished.connect(lambda: self._ertesites_mezo(nev, m.text().strip() if not jelszo
                                                                   else m.text()))
            return m

        self.ntfy = mezo("ertesites_ntfy", b.ertesites_ntfy, "https://ntfy.sh/kozgaz-fm-sajat-hosszu-tema")
        sorok = [
            ("ntfy-cím:", self.ntfy),
            ("ntfy-token (ha kell):", mezo("ertesites_ntfy_token", b.ertesites_ntfy_token,
                                           "csak saját, védett ntfy-szervernél", jelszo=True)),
            ("E-mail címzett(ek):", mezo("ertesites_email", b.ertesites_email, "rendszergazda@iskola.hu, …")),
            ("SMTP-szerver:", mezo("smtp_szerver", b.smtp_szerver, "pl. smtp.gmail.com")),
            ("SMTP-felhasználó:", mezo("smtp_felhasznalo", b.smtp_felhasznalo, "általában az e-mail-cím")),
            ("SMTP-jelszó:", mezo("smtp_jelszo", b.smtp_jelszo, "alkalmazásjelszó", jelszo=True)),
            ("Feladó (ha más):", mezo("smtp_felado", b.smtp_felado, "üresen a felhasználónév")),
        ]
        for i, (felirat, elem) in enumerate(sorok):
            racs.addWidget(cimke(felirat), i, 0)
            racs.addWidget(elem, i, 1)
        port = QSpinBox(minimum=1, maximum=65535, prefix="Port: ")
        port.setValue(b.smtp_port)
        port.valueChanged.connect(lambda e: self._ertesites_mezo("smtp_port", e))
        mod = QComboBox()
        for kulcs, nev in SMTP_MODOK.items():
            mod.addItem(nev, kulcs)
        mod.setCurrentIndex(max(0, mod.findData(b.smtp_mod)))
        def mod_valtozott() -> None:
            uj = mod.currentData()
            self._ertesites_mezo("smtp_mod", uj)
            alap = {"ssl": 465, "starttls": 587}.get(uj)
            if alap and port.value() in (465, 587, 25):
                port.setValue(alap)

        mod.activated.connect(lambda _: mod_valtozott())
        racs.addLayout(sor(port, mod, nyujt=True), len(sorok), 1)
        racs.setColumnStretch(1, 1)
        k.add(racs)
        k.add(cimke("Miről kapj értesítést:", "alcim"))
        esemenyek = QGridLayout()
        for i, (kulcs, nev) in enumerate(ESEMENYEK.items()):
            pipa = kapcsolo(nev, kulcs in b.ertesites_esemenyek)
            pipa.toggled.connect(lambda e, kk=kulcs: self._ertesites_esemeny(kk, e))
            esemenyek.addWidget(pipa, i // 2, i % 2)
        k.add(esemenyek)
        reggel = ido_mezo(b.ertesites_reggel_ido)
        reggel.timeChanged.connect(lambda t: self._ertesites_mezo("ertesites_reggel_ido", t.toString("HH:mm")))
        self.proba_gomb = gomb("Próbaértesítés küldése", "bemondas")
        self.proba_gomb.clicked.connect(self._ertesites_proba)
        k.add(sor(cimke("A reggeli önteszt ideje:"), reggel, None, self.proba_gomb))
        self.ertesites_allapot = cimke("", "halvany", sortores=True)
        k.add(self.ertesites_allapot)
        return k

    def _ertesites_mezo(self, mezo: str, ertek) -> None:
        if mezo == "ertesites_ntfy" and ertek:
            try:
                ntfy_cel(ertek)
            except ErtesitesHiba as e:
                self.ertesites_allapot.setText(str(e))
                return
        if getattr(self.v.b, mezo) != ertek:
            setattr(self.v.b, mezo, ertek)
            self.v.mentes_kesobb()
        self.ertesites_allapot.setText("")

    def _ertesites_esemeny(self, kulcs: str, be: bool) -> None:
        lista = [e for e in self.v.b.ertesites_esemenyek if e != kulcs]
        self.v.b.ertesites_esemenyek = [*lista, kulcs] if be else lista
        self.v.mentes_kesobb()

    def _ertesites_proba(self) -> None:
        self.proba_gomb.setEnabled(False)
        self.ertesites_allapot.setText("Küldés…")

        def kesz(hibak: list[str]) -> None:
            self.proba_gomb.setEnabled(True)
            self.ertesites_allapot.setText("\n".join(hibak) if hibak else "Elküldve. Nézd meg a telefonodat vagy "
                                                                            "a postafiókodat.")

        self.v.ertesito.proba(kesz)

    def _tartalek_kartya(self) -> Kartya:
        b = self.v.b
        k = Kartya("Tartalékgép")
        k.add(cimke("Két gép (pl. a hangosító Windows-gép és egy Közgáz FM OS-es Raspberry Pi) figyeli egymást. "
                    "A tartalék gép csak akkor csenget, ha a fő gép kb. 15 másodpercig nem válaszol (leállt, "
                    "lefagyott, elment az áram), és visszaadja a vezérlést, amint a fő gép újra működik. A "
                    "csengetési rendet, a naptárt és a bemondásokat a tartalék magától átveszi a fő gépről. Mindkét "
                    "gép hangkimenete legyen az erősítőre kötve (pl. keverőn át), és ugyanazt a kulcsot kapják.",
                    "halvany", sortores=True))
        self.tartalek_szerep = QComboBox()
        for kulcs, nev in SZEREPEK.items():
            self.tartalek_szerep.addItem(nev, kulcs)
        self.tartalek_szerep.setCurrentIndex(max(0, self.tartalek_szerep.findData(b.tartalek_mod)))
        self.tartalek_szerep.activated.connect(self._tartalek_szerep)
        self.tartalek_cim = QLineEdit(b.tartalek_cim)
        self.tartalek_cim.setPlaceholderText("A másik gép címe, pl. 192.168.1.20:8080")
        self.tartalek_cim.editingFinished.connect(self._tartalek_cim)
        self.tartalek_kulcs = QLineEdit(b.tartalek_kulcs)
        self.tartalek_kulcs.setEchoMode(QLineEdit.EchoMode.Password)
        self.tartalek_kulcs.setPlaceholderText("Közös kulcs (a fő gépen generáld, a tartalékba másold be)")
        self.tartalek_kulcs.editingFinished.connect(self._tartalek_kulcs)
        uj = gomb("Új kulcs", "lakat", tipp="Új, véletlen kulcs a fő gépen")
        uj.clicked.connect(self._tartalek_uj_kulcs)
        masol = gomb("", "masol", tipp="Kulcs másolása a vágólapra")
        masol.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.v.b.tartalek_kulcs))
        self.tartalek_szinkron = gomb("Szinkronizálás most", "frissites",
                                      tipp="A csengetési rend és a naptár átvétele a fő gépről")
        self.tartalek_szinkron.clicked.connect(self.v.tartalek.szinkron)
        self.tartalek_allapot = cimke(sortores=True)
        self.tartalek_allapot.setTextFormat(Qt.TextFormat.RichText)
        racs = QGridLayout()
        racs.setVerticalSpacing(10)
        racs.addWidget(cimke("Ennek a gépnek a szerepe:"), 0, 0)
        racs.addWidget(self.tartalek_szerep, 0, 1)
        racs.addWidget(cimke("A másik gép címe:"), 1, 0)
        racs.addLayout(sor(self.tartalek_cim, self.tartalek_szinkron), 1, 1)
        racs.addWidget(cimke("Közös kulcs:"), 2, 0)
        racs.addLayout(sor(self.tartalek_kulcs, uj, masol), 2, 1)
        racs.setColumnStretch(1, 1)
        k.add(racs)
        k.add(self.tartalek_allapot)
        k.add(cimke("A webes vezérlés portján kommunikálnak (jelszó nélkül is elindul, de csak a kulccsal "
                    "válaszol). A tűzfalon engedélyezd a magánhálózaton.", "halvany", sortores=True))
        self.v.frissult.connect(self._tartalek_frissit)
        self._tartalek_frissit()
        return k

    def _tartalek_frissit(self) -> None:
        szoveg, szin = self.v.tartalek.leiras()
        if not szoveg:
            szoveg, szin = "Kikapcsolva: ez a gép egyedül csenget.", "halvany"
        html = f"<span style='color:{SZIN[szin]}'>&#9679;</span>&nbsp; {szoveg}"
        if self.tartalek_allapot.text() != html:
            self.tartalek_allapot.setText(html)
        self.tartalek_szinkron.setVisible(self.v.b.tartalek_mod == "tartalek")

    def _tartalek_mentes(self) -> None:
        self.v.mentes()
        self._tartalek_frissit()

    def _tartalek_szerep(self, _i: int) -> None:
        b = self.v.b
        b.tartalek_mod = self.tartalek_szerep.currentData() or ""
        if b.tartalek_mod == "fo" and not b.tartalek_kulcs:
            b.tartalek_kulcs = uj_kulcs()
            self.tartalek_kulcs.setText(b.tartalek_kulcs)
        self.v.log(f"Tartalékgép-szerep: {SZEREPEK[b.tartalek_mod]}")
        self._tartalek_mentes()

    def _tartalek_cim(self) -> None:
        try:
            cim = cim_normalizal(self.tartalek_cim.text())
        except TartalekHiba as e:
            QMessageBox.warning(self, "Tartalékgép", str(e))
            return
        self.tartalek_cim.setText(cim)
        if cim != self.v.b.tartalek_cim:
            self.v.b.tartalek_cim = cim
            self._tartalek_mentes()

    def _tartalek_kulcs(self) -> None:
        kulcs = self.tartalek_kulcs.text().strip()
        if kulcs and len(kulcs) < 16:
            QMessageBox.warning(self, "Tartalékgép", "A kulcs legalább 16 karakter legyen. A fő gépen az "
                                "„Új kulcs” gombbal generálj egyet.")
            return
        if kulcs != self.v.b.tartalek_kulcs:
            self.v.b.tartalek_kulcs = kulcs
            self._tartalek_mentes()

    def _tartalek_uj_kulcs(self) -> None:
        if self.v.b.tartalek_kulcs and QMessageBox.question(
                self, "Tartalékgép", "Új kulcsot generálsz? A tartalék gépbe is be kell majd másolnod."
        ) != QMessageBox.StandardButton.Yes:
            return
        self.v.b.tartalek_kulcs = uj_kulcs()
        self.tartalek_kulcs.setText(self.v.b.tartalek_kulcs)
        self._tartalek_mentes()

    def _nevjegy_kartya(self) -> Kartya:
        k = Kartya("Névjegy")
        logo = cimke()
        logo.setPixmap(logo_pixmap(96))
        szoveg = cimke(f"<b>{APP_NEV}</b> {__version__}<br>Iskolai csengetőrendszer és szünetzene-lejátszó."
                       f"<br>Készítette: {KESZITO}", sortores=True)
        szoveg.setTextFormat(Qt.TextFormat.RichText)
        k.add(sor(logo, szoveg, nyujt=True, terkoz=18))
        return k

    def _allit(self, mezo: str, ertek) -> None:
        setattr(self.v.b, mezo, ertek)
        self.v.mentes_kesobb()

    def _kimenetek(self) -> None:
        self.kimenet.clear()
        alap = QMediaDevices.defaultAudioOutput()
        self.kimenet.addItem(f"Rendszer alapértelmezett ({alap.description()})", "")
        for e in QMediaDevices.audioOutputs():
            self.kimenet.addItem(e.description(), eszkoz_azonosito(e))
        self.kimenet.setCurrentIndex(max(0, self.kimenet.findData(self.v.b.kimenet)))

    def _kimenet_valasztva(self, _i: int) -> None:
        self.v.b.kimenet = self.kimenet.currentData() or ""
        self.v.mentes()

    def _auto(self, be: bool) -> None:
        try:
            rendszer.automatikus_inditas_beallit(be)
            self.v.b.automatikus_inditas = be
            self.v.mentes()
        except OSError as e:
            QMessageBox.warning(self, "Automatikus indítás", f"Nem sikerült beállítani: {e}")

    def _export(self) -> None:
        ut, _ = QFileDialog.getSaveFileName(self, "Beállítások exportálása", "kozgaz-fm-beallitasok.json",
                                            "JSON (*.json)")
        if ut:
            adat = asdict(self.v.b)
            for mezo in HELYI_MEZOK:
                adat.pop(mezo, None)
            with open(ut, "w", encoding="utf-8") as f:
                json.dump(adat, f, ensure_ascii=False, indent=2)

    def _import(self) -> None:
        ut, _ = QFileDialog.getOpenFileName(self, "Beállítások importálása", "", "JSON (*.json)")
        if not ut:
            return
        try:
            with open(ut, encoding="utf-8") as f:
                uj = _ebbol(Beallitasok, json.load(f))
        except (OSError, ValueError, TypeError) as e:
            QMessageBox.warning(self, "Importálás", f"A fájl nem olvasható be: {e}")
            return
        if QMessageBox.question(self, "Importálás", "Felülírod a jelenlegi beállításokat?"
                                ) != QMessageBox.StandardButton.Yes:
            return
        for mezo in HELYI_MEZOK:
            setattr(uj, mezo, getattr(self.v.b, mezo))
        self.v.b.__dict__.update(uj.__dict__)
        self.v.mentes()
        self.importalva.emit()
