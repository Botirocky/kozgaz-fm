from kozgaz_fm.beallitasok import Beallitasok, Csengetesirend, ora_lista


def minta_beallitas() -> Beallitasok:
    normal = Csengetesirend("Normál", ora_lista(
        ("08:00", "08:45"), ("08:55", "09:40"), ("09:50", "10:35"), ("10:50", "11:35"),
        ("11:45", "12:30"), ("12:40", "13:25"), ("13:35", "14:20"), ("14:25", "15:10"),
    ))
    rovid = Csengetesirend("Rövidített", ora_lista(
        ("08:00", "08:30"), ("08:40", "09:10"), ("09:20", "09:50"), ("10:00", "10:30"),
        ("10:40", "11:10"), ("11:20", "11:50"), ("12:00", "12:30"), ("12:35", "13:05"),
    ))
    return Beallitasok(rendek=[normal, rovid])
