__lazy_modules__ = [
    "collections.abc",
    "PySide6.QtCore",
    "PySide6.QtWidgets",
    "kozgaz_fm.ui.elemek",
    "kozgaz_fm.vezerlo",
    "kozgaz_fm.zenekeres",
]

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QMessageBox

from kozgaz_fm.ui.elemek import Kartya, cimke, gomb, sor
from kozgaz_fm.vezerlo import Vezerlo
from kozgaz_fm.zenekeres import ALLAPOT_NEVEK, KeresHiba


class ModeralasKartya(Kartya):
    def __init__(self, v: Vezerlo) -> None:
        super().__init__("Moderálás")
        self.v = v
        self.add(cimke("Ha valami mégsem való a folyosóra: a most szóló szám egy gombbal letiltható, a kért szám "
                       "levehető a sorból, a visszaélő telefon pedig egy hétre kizárható. A letiltott számok "
                       "minden forrásból kimaradnak, és nem kérhetők újra, amíg fel nem oldod a tiltást.",
                       "halvany", sortores=True))
        self.most = gomb("A most szóló szám tiltása", "kuka", tipp="Azonnal a következő számra lép")
        self.most.clicked.connect(lambda: self._futtat(lambda: v.most_szolo_tiltasa("a programból")))
        self.add(sor(self.most, None))
        self.mai = QListWidget()
        self.mai.setMinimumHeight(140)
        levetel = gomb("Levétel a sorból", "kuka")
        levetel.clicked.connect(lambda: self._valasztott(self.mai, v.zenekeres_levesz))
        tiltas = gomb("Szám tiltása")
        tiltas.clicked.connect(lambda: self._valasztott(self.mai, v.zenekeres_szam_tiltas))
        telefon = gomb("Telefon tiltása", tipp="Egy hétig nem kérhet számot, a függő kérései is törlődnek")
        telefon.clicked.connect(lambda: self._valasztott(self.mai, v.zenekeres_telefon_tiltas))
        self.add(cimke("Mai kérések", "alcim"))
        self.add(self.mai)
        self.add(sor(levetel, tiltas, telefon, None))
        self.szamok = QListWidget()
        self.szamok.setMaximumHeight(110)
        szam_feloldas = gomb("Feloldás")
        szam_feloldas.clicked.connect(lambda: self._valasztott(self.szamok, v.szam_feloldas))
        self.add(cimke("Letiltott számok", "alcim"))
        self.add(self.szamok)
        self.add(sor(szam_feloldas, None))
        self.telefonok = QListWidget()
        self.telefonok.setMaximumHeight(90)
        telefon_feloldas = gomb("Feloldás")
        telefon_feloldas.clicked.connect(lambda: self._valasztott(self.telefonok, v.telefon_feloldas))
        self.add(cimke("Letiltott telefonok", "alcim"))
        self.add(self.telefonok)
        self.add(sor(telefon_feloldas, None))
        v.keresek_valtoztak.connect(self.frissit)
        v.zene.allapot_valtozott.connect(self._gomb_frissit)
        self.frissit()

    def _gomb_frissit(self, *_) -> None:
        self.most.setEnabled(self.v.zene.szol)

    @staticmethod
    def _tolt(lista: QListWidget, elemek: list[tuple[str, str]], ures: str) -> None:
        kijelolt = lista.currentItem().data(Qt.ItemDataRole.UserRole) if lista.currentItem() else None
        lista.clear()
        for szoveg, azon in elemek:
            elem = QListWidgetItem(szoveg)
            elem.setData(Qt.ItemDataRole.UserRole, azon)
            lista.addItem(elem)
            if azon == kijelolt:
                lista.setCurrentItem(elem)
        if not elemek:
            lista.addItem(ures)

    def frissit(self) -> None:
        self._gomb_frissit()
        v = self.v
        mai = []
        for k in v.keresek.mai():
            allapot = ALLAPOT_NEVEK.get(k.allapot, k.allapot)
            telefon = "telefon letiltva" if v.telefon_tiltott(k.eszkoz) else ""
            reszletek = " · ".join(x for x in (f"{k.ido:%H:%M}", k.nev, allapot, k.ok, telefon) if x)
            mai.append((f"{k.cim or k.szoveg}\n{reszletek}", k.azon))
        self._tolt(self.mai, mai, "Ma még nem érkezett kérés.")
        self._tolt(self.szamok, [(f"{t.cim} · {t.ido}", t.azon) for t in v.b.tiltott_szamok],
                   "Nincs letiltott szám.")
        self._tolt(self.telefonok, [(f"{t.nev or 'Névtelen telefon'} · {t.ig}-ig", t.kulcs)
                                    for t in v.b.tiltott_telefonok], "Nincs letiltott telefon.")

    def _valasztott(self, lista: QListWidget, muvelet: Callable[[str, str], None]) -> None:
        elem = lista.currentItem()
        azon = elem.data(Qt.ItemDataRole.UserRole) if elem else None
        if azon:
            self._futtat(lambda: muvelet(azon, "a programból"))

    def _futtat(self, muvelet: Callable[[], None]) -> None:
        try:
            muvelet()
        except KeresHiba as e:
            QMessageBox.warning(self, "Moderálás", str(e))
