import os
import subprocess
import sys

PROBA = r"""
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QComboBox, QSpinBox, QVBoxLayout, QWidget

app = QApplication([])
from kozgaz_fm.ui.elemek import GorgetesSzuro, gorgeto

szuro = GorgetesSzuro()
app.installEventFilter(szuro)
belso = QWidget()
e = QVBoxLayout(belso)
kombo = QComboBox()
kombo.addItems([str(i) for i in range(20)])
szam = QSpinBox()
szam.setRange(0, 100)
szam.setValue(50)
e.addWidget(kombo)
e.addWidget(szam)
for _ in range(40):
    e.addWidget(QComboBox())
terulet = gorgeto(belso)
terulet.resize(300, 200)
terulet.show()
app.processEvents()


def gorget(widget):
    kozep = QPointF(widget.rect().center())
    esemeny = QWheelEvent(kozep, QPointF(widget.mapToGlobal(QPoint(5, 5))), QPoint(0, 0), QPoint(0, -120),
                          Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase,
                          False)
    QApplication.sendEvent(widget, esemeny)
    app.processEvents()


gorget(kombo)
gorget(szam)
szam.setFocus()
gorget(szam)
assert kombo.currentIndex() == 0, kombo.currentIndex()
assert szam.value() == 50, szam.value()
assert terulet.verticalScrollBar().value() > 0
print("OK")
"""


def test_gorgetes_nem_valt_erteket():
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONPATH=os.pathsep.join(sys.path))
    eredmeny = subprocess.run([sys.executable, "-c", PROBA], capture_output=True, text=True, env=env, timeout=60)
    assert eredmeny.returncode == 0 and "OK" in eredmeny.stdout, eredmeny.stderr[-2000:]
