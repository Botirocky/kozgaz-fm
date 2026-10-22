import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

naplo = logging.getLogger(__name__)
_vegrehajto = ThreadPoolExecutor(max_workers=4, thread_name_prefix="kozgaz-fm")


class _Hid(QObject):
    kesz = Signal(object, object)

    def __init__(self) -> None:
        super().__init__()
        self.kesz.connect(self._lefut)

    @Slot(object, object)
    def _lefut(self, visszahivas: Callable[[Any], None], ertek: Any) -> None:
        try:
            visszahivas(ertek)
        except Exception:
            naplo.exception("Hiba a háttérfeladat visszahívásában")


_hid: _Hid | None = None


def futtat(fuggveny: Callable[[], Any], siker: Callable[[Any], None] | None = None,
           hiba: Callable[[Exception], None] | None = None) -> None:
    global _hid
    if _hid is None:
        _hid = _Hid()
    hid = _hid

    def munka() -> None:
        try:
            eredmeny = fuggveny()
        except Exception as e:
            naplo.warning("Háttérfeladat hibája: %s", e)
            if hiba:
                hid.kesz.emit(hiba, e)
            return
        if siker:
            hid.kesz.emit(siker, eredmeny)

    _vegrehajto.submit(munka)


def leallit() -> None:
    _vegrehajto.shutdown(wait=False, cancel_futures=True)
