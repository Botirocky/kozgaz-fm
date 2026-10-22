__lazy_modules__ = ["functools", "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtSvg", "kozgaz_fm.utvonalak"]

from functools import cache

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QFont, QGuiApplication, QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from kozgaz_fm.utvonalak import csomag_mappa

SOTET = {
    "hatter": "#101317",
    "oldalsav": "#0C0F12",
    "felulet": "#171B21",
    "felulet2": "#1F242C",
    "keret": "#262C35",
    "keret_eros": "#363E4A",
    "keret_hover": "#4A5462",
    "szoveg": "#E8EBEF",
    "halvany": "#8D96A3",
    "tiltott": "#5F6773",
    "kiemelt": "#DCBD31",
    "kiemelt_sotet": "#C4A722",
    "kiemelt_szoveg": "#16140A",
    "elo_szin": "#DCBD31",
    "elo_hatter": "#2A2610",
    "kek": "#4085C0",
    "kek_sotet": "#336DA0",
    "kek_halvany": "#1B2B3B",
    "halad_kitoltes": "#336DA0",
    "aktiv_szoveg": "#FFFFFF",
    "mult_blokk": "#232A33",
    "mult_szoveg": "#5F6773",
    "szol": "#3FB66B",
    "info": "#4085C0",
    "figyelem": "#E0A43A",
    "hiba": "#D9483B",
    "hiba_sotet": "#A8342A",
    "riaszt_hatter": "#2E1412",
    "veszely_szoveg": "#F2B8B2",
    "fejlec": "#101317",
    "fejlec_szoveg": "#E8EBEF",
    "fejlec_halvany": "#8D96A3",
    "fejlec_keret": "#262C35",
    "kapcsolo": "",
}

VILAGOS = {
    "hatter": "#EEF1F5",
    "oldalsav": "#FFFFFF",
    "felulet": "#FFFFFF",
    "felulet2": "#F3F5F8",
    "keret": "#DCE1E8",
    "keret_eros": "#C3CBD6",
    "keret_hover": "#97A3B4",
    "szoveg": "#17202C",
    "halvany": "#5E6A7A",
    "tiltott": "#A3ACB9",
    "kiemelt": "#DCBD31",
    "kiemelt_sotet": "#C9A91F",
    "kiemelt_szoveg": "#16140A",
    "elo_szin": "#A8860F",
    "elo_hatter": "#FBF3D0",
    "kek": "#2F6CA6",
    "kek_sotet": "#255A8C",
    "kek_halvany": "#E2EDF8",
    "halad_kitoltes": "#B9D3EE",
    "aktiv_szoveg": "#0F2A44",
    "mult_blokk": "#E6EAF0",
    "mult_szoveg": "#9AA6B6",
    "szol": "#1E9150",
    "info": "#2F6CA6",
    "figyelem": "#A86A12",
    "hiba": "#C4382C",
    "hiba_sotet": "#A32D23",
    "riaszt_hatter": "#FBE8E6",
    "veszely_szoveg": "#C4382C",
    "fejlec": "#2F6CA6",
    "fejlec_szoveg": "#FFFFFF",
    "fejlec_halvany": "#D3E3F3",
    "fejlec_keret": "#255A8C",
    "kapcsolo": "_vilagos",
}

TEMAK = {"vilagos": VILAGOS, "sotet": SOTET}
TEMA_NEVEK = {"vilagos": "Világos", "sotet": "Sötét", "auto": "Rendszer szerint"}
SZIN = dict(VILAGOS)


def rendszer_sotet() -> bool:
    app = QGuiApplication.instance()
    return app is not None and QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark


def tenyleges(nev: str) -> str:
    if nev == "auto":
        return "sotet" if rendszer_sotet() else "vilagos"
    return nev if nev in TEMAK else "vilagos"


def sotet_aktiv() -> bool:
    return SZIN.get("kapcsolo") == ""


def alkalmaz(nev: str) -> None:
    SZIN.clear()
    SZIN.update(TEMAK[tenyleges(nev)])
    ikon.cache_clear()

IKONOK = {
    "hold": '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
    "nap": ('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4'
            'M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'),
    "lakat": '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    "pult": '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/>'
            '<rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
    "csengo": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    "zene": '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
    "naptar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    "bemondas": '<path d="m3 11 18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/>',
    "naplo": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M16 13H8'
             'M16 17H8M10 9H8"/>',
    "beallitas": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 '
                 '2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 '
                 '0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a'
                 '1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-'
                 '.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09'
                 'a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 '
                 '0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    "lejatszas": '<path d="m7 4 13 8-13 8V4Z"/>',
    "szunet": '<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>',
    "stop": '<rect x="5" y="5" width="14" height="14" rx="2"/>',
    "kovetkezo": '<path d="m5 4 10 8-10 8V4zM19 5v14"/>',
    "elozo": '<path d="m19 20-10-8 10-8v16zM5 19V5"/>',
    "hangero": '<path d="M11 5 6 9H2v6h4l5 4V5z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M19 5a10 10 0 0 1 0 14"/>',
    "riasztas": '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>'
                '<path d="M12 9v4M12 17h.01"/>',
    "kijelzo": '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>',
    "plusz": '<path d="M12 5v14M5 12h14"/>',
    "kuka": '<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/>',
    "masol": '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 '
             '2 0 0 1 2 2v1"/>',
    "mappa": '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
    "youtube": '<path d="M2.5 17a24 24 0 0 1 0-10 2 2 0 0 1 1.4-1.4 49.6 49.6 0 0 1 16.2 0A2 2 0 0 1 21.5 7a24 24 '
               '0 0 1 0 10 2 2 0 0 1-1.4 1.4 49.6 49.6 0 0 1-16.2 0A2 2 0 0 1 2.5 17"/><path d="m10 15 5-3-5-3z"/>',
    "spotify": '<circle cx="12" cy="12" r="10"/><path d="M7 9.5c3.5-1 7.5-.6 10.5 1.2M7.5 12.8c2.8-.8 6-.4 8.4 1'
               'M8 16c2.2-.6 4.6-.3 6.4.8"/>',
    "fajl": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
    "pipa": '<path d="M20 6 9 17l-5-5"/>',
    "ora": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "kever": '<path d="M16 3h5v5M4 20 21 3M21 16v5h-5M15 15l6 6M4 4l5 5"/>',
    "kulso": '<path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    "nevjegy": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
    "frissites": '<path d="M21 12a9 9 0 1 1-2.6-6.4L21 8"/><path d="M21 3v5h-5"/>',
    "le": '<path d="M12 5v14M19 12l-7 7-7-7"/>',
    "fel": '<path d="M12 19V5M5 12l7-7 7 7"/>',
}


def svg_ikon_szoveg(nev: str, szin: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{szin}" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{IKONOK[nev]}</svg>')


def _render(svg: bytes, szel: int, mag: int | None = None) -> QPixmap:
    mag = mag or szel
    renderer = QSvgRenderer(QByteArray(svg))
    kep = QImage(szel, mag, QImage.Format.Format_ARGB32_Premultiplied)
    kep.fill(Qt.GlobalColor.transparent)
    festo = QPainter(kep)
    festo.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(festo, QRectF(0, 0, szel, mag))
    festo.end()
    return QPixmap.fromImage(kep)


@cache
def ikon(nev: str, szin: str | None = None, aktiv: str | None = None) -> QIcon:
    szin = szin or SZIN["halvany"]
    i = QIcon()
    for meret in (16, 20, 24, 32, 48, 64):
        i.addPixmap(_render(svg_ikon_szoveg(nev, szin).encode(), meret), QIcon.Mode.Normal, QIcon.State.Off)
        if aktiv:
            i.addPixmap(_render(svg_ikon_szoveg(nev, aktiv).encode(), meret), QIcon.Mode.Normal, QIcon.State.On)
    return i


def _kep(nev: str, meret: int) -> QPixmap:
    ut = csomag_mappa() / "kepek" / nev
    kep = QPixmap(str(ut))
    if kep.isNull():
        return QPixmap()
    return kep.scaled(meret, meret, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)


def logo_pixmap(meret: int) -> QPixmap:
    return _kep("logo.png", meret)


def jel_pixmap(meret: int) -> QPixmap:
    return _kep("jel.png", meret)


@cache
def logo_ikon() -> QIcon:
    i = QIcon()
    for meret in (16, 24, 32, 48, 64, 128, 256):
        kep = jel_pixmap(meret)
        if not kep.isNull():
            i.addPixmap(kep)
    return i


def szam_betu(meret: float, suly: QFont.Weight = QFont.Weight.DemiBold) -> QFont:
    f = betutipus()
    f.setPointSizeF(meret)
    f.setWeight(suly)
    f.setFeature(QFont.Tag("tnum"), 1)
    return f


def betutipus() -> QFont:
    f = QFont()
    f.setFamilies(["Segoe UI Variable Text", "Segoe UI", "Inter", "Noto Sans", "Cantarell", "sans-serif"])
    f.setPointSizeF(10.5)
    f.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return f


def stilus() -> str:
    s = SZIN
    kepek = (csomag_mappa() / "kepek").as_posix()
    k = s["kapcsolo"]
    return f"""
    QWidget {{ background: {s['hatter']}; color: {s['szoveg']}; }}
    QToolTip {{ background: {s['felulet2']}; color: {s['szoveg']}; border: 1px solid {s['keret_eros']};
                padding: 6px 8px; border-radius: 4px; }}
    QLabel {{ background: transparent; }}
    QLabel[szerep="halvany"] {{ color: {s['halvany']}; }}
    QLabel[szerep="cim"] {{ font-size: 17pt; font-weight: 600; }}
    QLabel[szerep="alcim"] {{ font-size: 12.5pt; font-weight: 600; }}
    QLabel[szerep="szekcio"] {{ color: {s['szoveg']}; font-size: 11pt; font-weight: 600; }}
    QFrame#oldalsav {{ background: {s['oldalsav']}; border-right: 1px solid {s['keret']}; }}
    QFrame#oldalsav QLabel {{ background: transparent; }}
    QFrame#fejlec {{ background: {s['fejlec']}; border-bottom: 1px solid {s['fejlec_keret']}; }}
    QFrame#fejlec QLabel {{ background: transparent; color: {s['fejlec_szoveg']}; }}
    QFrame#fejlec QLabel[szerep="halvany"] {{ color: {s['fejlec_halvany']}; }}
    QFrame#fejlec QPushButton[szerep="fo"] {{ background: {s['felulet']}; color: {s['kek']};
                                             border-color: {s['felulet']}; }}
    QFrame#fejlec QPushButton[szerep="fo"]:hover {{ background: {s['kek_halvany']}; }}
    QFrame#allapotsor {{ background: {s['oldalsav']}; border-top: 1px solid {s['keret']}; }}
    QFrame#allapotsor QLabel {{ background: transparent; color: {s['halvany']}; font-size: 9pt; }}
    QFrame#elo {{ background: {s['elo_hatter']}; border: 1px solid {s['kiemelt_sotet']}; border-radius: 4px; }}
    QFrame#elo QLabel {{ color: {s['szoveg']}; }}
    QFrame[szerep="kartya"] {{ background: {s['felulet']}; border: 1px solid {s['keret']}; border-radius: 6px; }}
    QFrame[szerep="kartya"] QLabel, QFrame[szerep="kartya"] QCheckBox,
    QFrame[szerep="kartya"] QRadioButton {{ background: transparent; }}
    QFrame[szerep="kartya"][allapot="riasztas"] {{ background: {s['riaszt_hatter']}; border-color: {s['hiba']}; }}
    QPushButton {{ background: {s['felulet2']}; border: 1px solid {s['keret_eros']}; border-radius: 5px;
                   padding: 7px 14px; color: {s['szoveg']}; font-weight: 600; }}
    QPushButton:hover {{ background: {s['keret']}; border-color: {s['keret_hover']}; }}
    QPushButton:pressed {{ background: {s['keret_eros']}; }}
    QPushButton:disabled {{ color: {s['tiltott']}; border-color: {s['keret']}; background: {s['felulet']}; }}
    QPushButton:focus {{ outline: none; border-color: {s['kek']}; }}
    QPushButton[szerep="fo"] {{ background: {s['kek']}; color: #FFFFFF; border-color: {s['kek']}; }}
    QPushButton[szerep="fo"]:hover {{ background: {s['kek_sotet']}; border-color: {s['kek_sotet']}; }}
    QPushButton[szerep="fo"]:disabled {{ background: {s['felulet2']}; color: {s['tiltott']};
                                         border-color: {s['keret']}; }}
    QPushButton[szerep="adas"] {{ background: {s['kiemelt']}; color: {s['kiemelt_szoveg']};
                                  border-color: {s['kiemelt_sotet']}; font-size: 11pt; }}
    QPushButton[szerep="adas"]:hover {{ background: {s['kiemelt_sotet']}; border-color: {s['kiemelt_sotet']}; }}
    QPushButton[szerep="veszely"] {{ background: transparent; border: 1px solid {s['hiba']};
                                     color: {s['veszely_szoveg']}; }}
    QPushButton[szerep="veszely"]:hover {{ background: {s['hiba_sotet']}; color: #FFFFFF; }}
    QPushButton[szerep="veszely"][allapot="aktiv"] {{ background: {s['hiba']}; color: #FFFFFF; }}
    QPushButton[szerep="nagy"] {{ padding: 12px 18px; font-size: 11.5pt; }}
    QPushButton[szerep="kerek"] {{ border-radius: 20px; padding: 0; min-width: 40px; min-height: 40px;
                                   max-width: 40px; max-height: 40px; }}
    QPushButton[szerep="kerek_fo"] {{ border-radius: 26px; padding: 0; min-width: 52px; min-height: 52px;
                                      max-width: 52px; max-height: 52px; background: {s['kiemelt']};
                                      border-color: {s['kiemelt_sotet']}; }}
    QPushButton[szerep="kerek_fo"]:hover {{ background: {s['kiemelt_sotet']}; }}
    QPushButton[szerep="nav"] {{ background: transparent; border: none; border-left: 3px solid transparent;
                                 border-radius: 0; text-align: left; padding: 10px 14px 10px 17px;
                                 color: {s['halvany']}; font-weight: 600; }}
    QPushButton[szerep="nav"]:hover {{ background: {s['felulet2']}; color: {s['szoveg']}; }}
    QPushButton[szerep="nav"]:checked {{ background: {s['kek_halvany']}; color: {s['szoveg']};
                                         border-left-color: {s['kek']}; }}
    QPushButton[szerep="sav"] {{ background: transparent; border: 1px solid {s['keret_eros']}; padding: 6px 10px;
                                 color: {s['halvany']}; }}
    QPushButton[szerep="sav"]:hover {{ color: {s['szoveg']}; background: {s['felulet2']}; }}
    QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QTimeEdit, QDateEdit, QComboBox {{
        background: {s['felulet']}; border: 1px solid {s['keret_eros']}; border-radius: 4px; padding: 6px 9px;
        selection-background-color: {s['kek']}; selection-color: #FFFFFF; }}
    QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QTimeEdit:hover, QComboBox:hover {{
        border-color: {s['keret_hover']}; }}
    QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QTimeEdit:focus, QDateEdit:focus, QComboBox:focus,
    QDoubleSpinBox:focus {{ border-color: {s['kek']}; }}
    QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QTimeEdit:disabled, QComboBox:disabled {{
        color: {s['tiltott']}; border-color: {s['keret']}; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{ background: {s['felulet']}; border: 1px solid {s['keret_eros']};
                                   selection-background-color: {s['kek_halvany']}; selection-color: {s['szoveg']};
                                   outline: none; }}
    QAbstractSpinBox {{ padding-left: 10px; }}
    QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{ width: 16px; border: none; }}
    QCheckBox {{ spacing: 10px; background: transparent; }}
    QCheckBox::indicator {{ width: 36px; height: 20px; image: url({kepek}/kapcsolo_ki{k}.svg); }}
    QCheckBox::indicator:checked {{ image: url({kepek}/kapcsolo_be.svg); }}
    QCheckBox::indicator:disabled {{ image: url({kepek}/kapcsolo_tiltott{k}.svg); }}
    QCheckBox:disabled {{ color: {s['tiltott']}; }}
    QRadioButton {{ background: transparent; spacing: 8px; }}
    QSlider::groove:horizontal {{ height: 4px; background: {s['keret_eros']}; border-radius: 2px; }}
    QSlider::sub-page:horizontal {{ background: {s['kek']}; border-radius: 2px; }}
    QSlider::handle:horizontal {{ background: {s['kek']}; border: 2px solid {s['felulet']}; width: 12px;
                                  height: 12px; margin: -6px 0; border-radius: 8px; }}
    QProgressBar {{ background: {s['keret']}; border: none; border-radius: 2px; height: 4px; }}
    QProgressBar::chunk {{ background: {s['kek']}; border-radius: 2px; }}
    QListWidget, QTableWidget, QTreeWidget {{ background: {s['felulet']}; border: 1px solid {s['keret']};
        border-radius: 4px; outline: none; alternate-background-color: {s['felulet2']}; }}
    QListWidget::item {{ padding: 6px 10px; min-height: 26px; border-radius: 0; }}
    QListWidget::item:hover {{ background: {s['felulet2']}; }}
    QListWidget::item:selected, QTableWidget::item:selected, QTreeWidget::item:selected {{
        background: {s['kek_halvany']}; color: {s['szoveg']}; }}
    QTableWidget {{ gridline-color: {s['keret']}; }}
    QHeaderView::section {{ background: {s['felulet2']}; color: {s['halvany']}; border: none;
        border-bottom: 1px solid {s['keret']}; padding: 7px; font-weight: 600; }}
    QTableCornerButton::section {{ background: {s['felulet2']}; border: none; }}
    QTextBrowser {{ background: {s['felulet']}; border: 1px solid {s['keret']}; border-radius: 4px; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {s['keret_eros']}; border-radius: 3px; min-height: 30px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
    QScrollBar::handle:horizontal {{ background: {s['keret_eros']}; border-radius: 3px; min-width: 30px; }}
    QTabWidget::pane {{ border: none; }}
    QTabBar::tab {{ background: transparent; color: {s['halvany']}; padding: 9px 16px; font-weight: 600;
                    border-bottom: 2px solid transparent; }}
    QTabBar::tab:selected {{ color: {s['szoveg']}; border-bottom-color: {s['kek']}; }}
    QCalendarWidget QWidget {{ alternate-background-color: {s['felulet2']}; }}
    QCalendarWidget QToolButton {{ background: transparent; color: {s['szoveg']}; font-weight: 600;
                                   padding: 6px; border-radius: 4px; }}
    QCalendarWidget QToolButton:hover {{ background: {s['felulet2']}; }}
    QCalendarWidget QAbstractItemView {{ background: {s['felulet']}; selection-background-color: {s['kek']};
                                         selection-color: #FFFFFF; }}
    QCalendarWidget #qt_calendar_navigationbar {{ background: {s['felulet2']}; border-radius: 4px; }}
    QMenu {{ background: {s['felulet']}; border: 1px solid {s['keret_eros']}; padding: 4px; border-radius: 4px; }}
    QMenu::item {{ padding: 7px 18px; border-radius: 3px; }}
    QMenu::item:selected {{ background: {s['kek_halvany']}; color: {s['szoveg']}; }}
    QMenu::section {{ color: {s['halvany']}; padding: 6px 12px 2px; }}
    QMenu::separator {{ height: 1px; background: {s['keret']}; margin: 4px 6px; }}
    QMessageBox, QDialog {{ background: {s['hatter']}; }}
    """
