__lazy_modules__ = [
    "PySide6.QtCore",
    "PySide6.QtWidgets",
    "kozgaz_fm.szuro",
    "kozgaz_fm.ui.elemek",
    "kozgaz_fm.vezerlo",
]

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLineEdit, QPlainTextEdit

from kozgaz_fm.szuro import Szuro
from kozgaz_fm.ui.elemek import Kartya, cimke, kapcsolo, sor
from kozgaz_fm.vezerlo import Vezerlo


class SzuroKartya(Kartya):
    def __init__(self, v: Vezerlo) -> None:
        super().__init__("Szűrő")
        self.v = v
        b = v.b
        self.add(cimke("A szűrőn fennakadó szám nem kerül a lejátszási sorba, és diák sem kérheti. A cím, a fájl "
                       "mappája és (Spotifynál) az előadó számít; a kis- és nagybetű, valamint az ékezet mindegy.",
                       "halvany", sortores=True))
        alap = kapcsolo("Beépített lista: trágár szavak és az „Explicit” jelölésű számok", b.szuro_alap,
                        "Néhány gyakori magyar és angol trágár szó, a Spotifyon az explicit jelölésű számok")
        alap.toggled.connect(lambda e: self._allit("szuro_alap", e))
        korhatar = kapcsolo("Korhatáros (18+) YouTube-videók kihagyása", b.szuro_korhataros,
                            "Letöltés előtt ellenőrzi a videó korhatár-besorolását")
        korhatar.toggled.connect(lambda e: self._allit("szuro_korhataros", e))
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
        self.proba_eredmeny = cimke("", "halvany")
        self.add(alap)
        self.add(korhatar)
        self.add(cimke("Saját tiltólista:"))
        self.add(self.szavak)
        self.add(sor(self.proba, self.proba_eredmeny, nyujt=True))

    def _allit(self, mezo: str, ertek) -> None:
        setattr(self.v.b, mezo, ertek)
        self.v.mentes_kesobb()
        self._probal()

    def _szavak_mentes(self) -> None:
        self.v.b.szuro_szavak = [s.strip() for s in self.szavak.toPlainText().splitlines() if s.strip()]
        self.v.mentes_kesobb()
        self._probal()

    def _probal(self, *_) -> None:
        szoveg = self.proba.text().strip()
        if not szoveg:
            self.proba_eredmeny.setText("")
            return
        b = self.v.b
        talalt = Szuro(b.szuro_szavak, b.szuro_alap).talalat(szoveg)
        self.proba_eredmeny.setText(f"Kiszűrné („{talalt}”)" if talalt else "Átengedné")
