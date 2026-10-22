__lazy_modules__ = ["datetime"]

from datetime import date, timedelta


def husvet(ev: int) -> date:
    a = ev % 19
    b, c = divmod(ev, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    el = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * el) // 451
    honap, nap = divmod(h + el - 7 * m + 114, 31)
    return date(ev, honap, nap + 1)


def unnepnapok(ev: int) -> list[tuple[date, str]]:
    h = husvet(ev)
    lista = [
        (date(ev, 1, 1), "Újév"),
        (date(ev, 3, 15), "Nemzeti ünnep"),
        (h - timedelta(days=2), "Nagypéntek"),
        (h + timedelta(days=1), "Húsvéthétfő"),
        (date(ev, 5, 1), "A munka ünnepe"),
        (h + timedelta(days=50), "Pünkösdhétfő"),
        (date(ev, 8, 20), "Államalapítás ünnepe"),
        (date(ev, 10, 23), "Nemzeti ünnep"),
        (date(ev, 11, 1), "Mindenszentek"),
        (date(ev, 12, 24), "Szenteste"),
        (date(ev, 12, 25), "Karácsony"),
        (date(ev, 12, 26), "Karácsony"),
    ]
    return sorted(lista)
