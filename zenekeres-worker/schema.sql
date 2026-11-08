CREATE TABLE IF NOT EXISTS keresek (
    azon TEXT PRIMARY KEY,
    szoveg TEXT NOT NULL,
    nev TEXT NOT NULL DEFAULT '',
    eszkoz TEXT NOT NULL,
    ip TEXT NOT NULL,
    ido INTEGER NOT NULL,
    nap TEXT NOT NULL,
    allapot TEXT NOT NULL DEFAULT 'kereses',
    allapot_nev TEXT NOT NULL DEFAULT '',
    cim TEXT NOT NULL DEFAULT '',
    ok TEXT NOT NULL DEFAULT '',
    atadva INTEGER NOT NULL DEFAULT 0,
    hely INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS keresek_eszkoz ON keresek (eszkoz, nap);
CREATE INDEX IF NOT EXISTS keresek_atadva ON keresek (atadva);
CREATE INDEX IF NOT EXISTS keresek_ip ON keresek (ip, ido);
CREATE INDEX IF NOT EXISTS keresek_allapot ON keresek (allapot);
CREATE TABLE IF NOT EXISTS ertekek (kulcs TEXT PRIMARY KEY, ertek TEXT NOT NULL);
