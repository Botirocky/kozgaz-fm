import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

GYOKER = Path(SPECPATH).parent
FORRAS = GYOKER / "src"
CSOMAG = FORRAS / "kozgaz_fm"
WINDOWS = sys.platform.startswith("win")

KIHAGYOTT = [
    "PySide6.Qt3DAnimation", "PySide6.Qt3DCore", "PySide6.Qt3DExtras", "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic", "PySide6.Qt3DRender", "PySide6.QtBluetooth", "PySide6.QtCharts",
    "PySide6.QtDataVisualization", "PySide6.QtGraphs", "PySide6.QtLocation", "PySide6.QtNetworkAuth",
    "PySide6.QtNfc", "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtPositioning",
    "PySide6.QtQuick3D", "PySide6.QtQuickControls2", "PySide6.QtQuickWidgets", "PySide6.QtRemoteObjects",
    "PySide6.QtScxml", "PySide6.QtSensors", "PySide6.QtSerialBus", "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio", "PySide6.QtSql", "PySide6.QtStateMachine", "PySide6.QtTest",
    "PySide6.QtWebChannel", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineQuick", "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets", "PySide6.QtWebView", "PySide6.QtMultimediaWidgets", "tkinter", "unittest", "pydoc",
]

adatok = [
    (str(CSOMAG / "hangok"), "kozgaz_fm/hangok"),
    (str(CSOMAG / "kepek"), "kozgaz_fm/kepek"),
    (str(CSOMAG / "web"), "kozgaz_fm/web"),
    (str(CSOMAG / "sugo.md"), "kozgaz_fm"),
]
adatok += collect_data_files("yt_dlp_ejs")

a = Analysis(
    [str(CSOMAG / "__main__.py")],
    pathex=[str(FORRAS)],
    datas=adatok,
    hiddenimports=collect_submodules("kozgaz_fm") + collect_submodules("yt_dlp") + collect_submodules("yt_dlp_ejs")
    + ["PySide6.QtTextToSpeech", "PySide6.QtMultimedia", "PySide6.QtNetwork", "PySide6.QtSvg"],
    excludes=KIHAGYOTT,
    noarchive=False,
)
FELESLEGES = ("Qt6Pdf", "Qt6Quick3D", "Qt6VirtualKeyboard", "qtvirtualkeyboard", "Qt6WebEngine", "opengl32sw",
              "libqgtk3", "libgtk-3", "libgdk-3", "libgdk_pixbuf", "libatk", "libatspi", "libcairo", "libpango",
              "libglycin", "libtinysparql", "libcloudproviders", "libjson-glib", "libicudata.so.78",
              "libicuuc.so.78", "libepoxy", "libthai", "libdatrie", "libpixman", "libxml2", "libseccomp",
              "libfontconfig", "libfreetype", "libharfbuzz", "/translations/qtwebengine")


def _kell(elem) -> bool:
    return not any(minta.lower() in elem[0].lower() for minta in FELESLEGES)


a.binaries = [b for b in a.binaries if _kell(b)]
a.datas = [d for d in a.datas if _kell(d)]
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="KozgazFM",
    console=False,
    icon=str(GYOKER / "assets" / ("ikon.ico" if WINDOWS else "ikon-256.png")),
    version=str(GYOKER / "packaging" / "windows" / "verzio.txt") if WINDOWS else None,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="KozgazFM")
