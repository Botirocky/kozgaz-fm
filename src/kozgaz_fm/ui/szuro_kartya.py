__lazy_modules__ = [
    "PySide6.QtCore",
    "PySide6.QtWidgets",
    "kozgaz_fm.dalszoveg",
    "kozgaz_fm.szuro",
    "kozgaz_fm.ui.elemek",
    "kozgaz_fm.vezerlo",
]

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox, QLineEdit, QPlainTextEdit

from kozgaz_fm import dalszoveg, hatter
from kozgaz_fm.dalszoveg import Eredmeny
from kozgaz_fm.szuro import ERZEKENYSEGEK, Szuro
from kozgaz_fm.ui.elemek import Kartya, cimke, gomb, kapcsolo, keskeny, sor
from kozgaz_fm.vezerlo import Vezerlo


class SzuroKartya(Kartya):
    def __init__(self, v: Vezerlo) -> None:
        super().__init__("Szűrő")
        self.v = v
        b = v.b
        self.add(cimke("A szűrőn fennakadó szám nem kerül a lejátszási sorba, és diák sem kérheti. A cím, a fájl "
                       "mappája és (Spotifynál) az előadó számít; a kis- és nagybetű, valamint az ékezet mindegy. A "
                       "dalszöveg-szűrő a cím alapján letölti a szöveget az LRCLIB-ről, és a trágár szavak szerint dönt.",
                       "halvany", sortores=True))
        alap = kapcsolo("Beépített lista: trágár szavak és az „Explicit” jelölésű számok", b.szuro_alap,
                        "Néhány gyakori magyar és angol trágár szó, a Spotifyon az explicit jelölésű számok")
        alap.toggled.connect(lambda e: self._allit("szuro_alap", e))
        korhatar = kapcsolo("Korhatáros (18+) YouTube-videók kihagyása", b.szuro_korhataros,
                            "Letöltés előtt ellenőrzi a videó korhatár-besorolását")
        korhatar.toggled.connect(lambda e: self._allit("szuro_korhataros", e))
        szoveg = kapcsolo("Nagyon trágár dalszövegek kiszűrése", b.szuro_dalszoveg,
                          "A szám címe alapján letölti a dalszöveget az LRCLIB-ről, és pontozza a trágár szavakat")
        szoveg.toggled.connect(lambda e: self._allit("szuro_dalszoveg", e))
        self.erzekenyseg = keskeny(QComboBox())
        for kulcs, nev in ERZEKENYSEGEK.items():
            self.erzekenyseg.addItem(nev, kulcs)
        self.erzekenyseg.setCurrentIndex(max(0, self.erzekenyseg.findData(b.szuro_erzekenyseg)))
        self.erzekenyseg.currentIndexChanged.connect(
            lambda _: self._allit("szuro_erzekenyseg", self.erzekenyseg.currentData()))
        self.szavak = QPlainTextEdit("\n".join(b.szuro_szavak))
        self.szavak.setPlaceholderText("Soronként egy szó, előadó vagy cím.\nCsillag a végén = szókezdet, "
                                       "pl. „bunkó*” a „bunkók”-at is kiszűri.")
        self.szavak.setMaximumHeight(110)
        self._mento = QTimer(self)
        self._mento.setSingleShot(True)
        self._mento.setInterval(800)
        self._mento.timeout.connect(self._szavak_mentes)
        self.szavak.textChanged.connect(self._mento.start)
        self.proba = QLineEdit()
        self.proba.setPlaceholderText("Próba: írj be egy számcímet…")
        self.proba.textChanged.connect(self._probal)
        self.proba_eredmeny = cimke("", "halvany", sortores=True)
        self.add(alap)
        self.add(korhatar)
        self.add(szoveg)
        self.add(sor(cimke("Dalszöveg-szűrő érzékenysége:"), self.erzekenyseg, None))
        self.add(cimke("Saját tiltólista:"))
        self.add(self.szavak)
        self.szoveg_proba = gomb("Dalszöveg ellenőrzése", tipp="A Próba mezőbe írt szám szövegét pontozza")
        self.szoveg_proba.clicked.connect(self._szoveg_proba)
        self.add(sor(self.proba, self.szoveg_proba))
        self.add(self.proba_eredmeny)

    def _allit(self, mezo: str, ertek) -> None:
        setattr(self.v.b, mezo, ertek)
        self.v.mentes_kesobb()
        self._probal()

    def _szavak_mentes(self) -> None:
        self.v.b.szuro_szavak = [s.strip() for s in self.szavak.toPlainText().splitlines() if s.strip()]
        self.v.mentes_kesobb()
        self._probal()

    def _szoveg_proba(self) -> None:
        cim = self.proba.text().strip()
        if not cim:
            self.proba_eredmeny.setText("Írj be egy „előadó - cím” párost.")
            return
        self.szoveg_proba.setEnabled(False)
        self.proba_eredmeny.setText("Dalszöveg keresése…")

        def kesz(eredmeny: Eredmeny) -> None:
            self.szoveg_proba.setEnabled(True)
            if not eredmeny.talalt:
                self.proba_eredmeny.setText("Nincs meg a dalszövege")
            elif eredmeny.instrumental:
                self.proba_eredmeny.setText("Instrumentális, átengedné")
            else:
                itelet = "Kiszűrné" if eredmeny.ertekeles.tragar(self.v.b.szuro_erzekenyseg) else "Átengedné"
                self.proba_eredmeny.setText(f"{itelet}: {eredmeny.ertekeles.szoveg()}")

        def hiba(e: Exception) -> None:
            self.szoveg_proba.setEnabled(True)
            self.proba_eredmeny.setText(str(e))

        hatter.futtat(lambda: dalszoveg.vizsgal(cim), kesz, hiba)

    def _probal(self, *_) -> None:
        szoveg = self.proba.text().strip()
        if not szoveg:
            self.proba_eredmeny.setText("")
            return
        b = self.v.b
        talalt = Szuro(b.szuro_szavak, b.szuro_alap).talalat(szoveg)
        self.proba_eredmeny.setText(f"Kiszűrné („{talalt}”)" if talalt else "Átengedné")
