__lazy_modules__ = ["hashlib", "hmac", "math", "secrets", "time", "collections.abc"]

import hashlib
import hmac
import math
import secrets
import time
from collections.abc import Callable

ALGORITMUS = "pbkdf2_sha256"
KOROK = 200_000
MIN_HOSSZ = 4
MAX_HOSSZ = 8
MAX_HIBA = 5
TILTAS_MP = 60


class PinHiba(Exception):
    pass


def pin_ervenyes(pin: str) -> bool:
    return MIN_HOSSZ <= len(pin) <= MAX_HOSSZ and pin.isascii() and pin.isdigit()


def van_pin(tarolt: str) -> bool:
    return bool(tarolt)


def pin_hash(pin: str, kor: int = KOROK) -> str:
    if not pin_ervenyes(pin):
        raise PinHiba(f"A PIN {MIN_HOSSZ}–{MAX_HOSSZ} számjegyből álljon.")
    so = secrets.token_bytes(16)
    kivonat = hashlib.pbkdf2_hmac("sha256", pin.encode(), so, kor)
    return f"{ALGORITMUS}${kor}${so.hex()}${kivonat.hex()}"


def pin_ellenoriz(pin: str, tarolt: str) -> bool:
    try:
        algoritmus, kor, so, kivonat = tarolt.split("$")
        if algoritmus != ALGORITMUS:
            return False
        vart = bytes.fromhex(kivonat)
        szamolt = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(so), int(kor))
    except ValueError:
        return False
    return hmac.compare_digest(szamolt, vart)


class Zar:
    def __init__(self, ido: Callable[[], float] = time.monotonic) -> None:
        self._ido = ido
        self._hibak = 0
        self._tiltas_vege = 0.0

    def hatralevo_tiltas(self) -> int:
        return max(0, math.ceil(self._tiltas_vege - self._ido()))

    def probal(self, pin: str, tarolt: str) -> bool:
        hatra = self.hatralevo_tiltas()
        if hatra:
            raise PinHiba(f"Túl sok hibás próbálkozás, várj még {hatra} másodpercet.")
        if pin_ellenoriz(pin, tarolt):
            self._hibak = 0
            return True
        self._hibak += 1
        if self._hibak >= MAX_HIBA:
            self._hibak = 0
            self._tiltas_vege = self._ido() + TILTAS_MP
        return False
