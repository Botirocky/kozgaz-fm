<?php

declare(strict_types=1);

namespace KozgazFM;

use PDO;

final class Adatbazis
{
    private const SEMA = <<<'SQL'
CREATE TABLE IF NOT EXISTS parancs (
    id INTEGER PRIMARY KEY,
    muvelet TEXT NOT NULL,
    adat TEXT NOT NULL DEFAULT '{}',
    ido REAL NOT NULL,
    allapot TEXT NOT NULL DEFAULT 'uj',
    eredmeny TEXT
);
CREATE INDEX IF NOT EXISTS parancs_allapot ON parancs (allapot, id);
CREATE TABLE IF NOT EXISTS keres (
    azon TEXT PRIMARY KEY,
    sorrend INTEGER NOT NULL,
    adat TEXT NOT NULL
);
SQL;

    private static ?PDO $db = null;

    public static function kapcsolat(): PDO
    {
        if (self::$db === null) {
            $db = new PDO('sqlite:' . Utvonalak::adatbazis(), null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
            $db->exec('PRAGMA journal_mode=WAL');
            $db->exec('PRAGMA busy_timeout=4000');
            $db->exec('PRAGMA synchronous=NORMAL');
            $db->exec(self::SEMA);
            self::$db = $db;
        }
        return self::$db;
    }

    public static function parancs(string $muvelet, array $adat = [], float $varakozas = 6.0): mixed
    {
        $db = self::kapcsolat();
        $db->prepare('INSERT INTO parancs (muvelet, adat, ido) VALUES (?, ?, ?)')
            ->execute([$muvelet, json_encode($adat, JSON_UNESCAPED_UNICODE), microtime(true)]);
        $id = (int)$db->lastInsertId();
        $hatarido = microtime(true) + $varakozas;
        $lekerdez = $db->prepare('SELECT allapot, eredmeny FROM parancs WHERE id = ?');
        while (microtime(true) < $hatarido) {
            usleep(40000);
            $lekerdez->execute([$id]);
            $sor = $lekerdez->fetch(PDO::FETCH_ASSOC);
            if ($sor && $sor['allapot'] !== 'uj') {
                $eredmeny = json_decode((string)$sor['eredmeny'], true);
                if ($sor['allapot'] === 'hiba') {
                    throw new Hiba((string)($eredmeny['uzenet'] ?? 'Ismeretlen hiba.'), (string)($eredmeny['kod'] ?? 'error'),
                        (int)($eredmeny['statusz'] ?? 409));
                }
                return $eredmeny;
            }
        }
        $db->prepare("UPDATE parancs SET allapot = 'lejart' WHERE id = ? AND allapot = 'uj'")->execute([$id]);
        throw new Hiba('A lejátszó démon nem válaszol (nem fut, vagy épp elfoglalt). Nézd meg a naplót.', 'unavailable', 503);
    }

    public static function uj(): array
    {
        $db = self::kapcsolat();
        $sorok = $db->query("SELECT id, muvelet, adat, ido FROM parancs WHERE allapot = 'uj' ORDER BY id LIMIT 50")
            ->fetchAll(PDO::FETCH_ASSOC);
        return array_map(static fn($s) => ['id' => (int)$s['id'], 'muvelet' => $s['muvelet'],
            'adat' => json_decode($s['adat'], true) ?: [], 'ido' => (float)$s['ido']], $sorok);
    }

    public static function valasz(int $id, bool $siker, mixed $eredmeny): void
    {
        self::kapcsolat()->prepare('UPDATE parancs SET allapot = ?, eredmeny = ? WHERE id = ?')
            ->execute([$siker ? 'kesz' : 'hiba', json_encode($eredmeny, JSON_UNESCAPED_UNICODE), $id]);
    }

    public static function takarit(): void
    {
        self::kapcsolat()->prepare('DELETE FROM parancs WHERE ido < ?')->execute([microtime(true) - 3600]);
    }

    public static function keresekMent(array $lista): void
    {
        $db = self::kapcsolat();
        $db->beginTransaction();
        $db->exec('DELETE FROM keres');
        $be = $db->prepare('INSERT INTO keres (azon, sorrend, adat) VALUES (?, ?, ?)');
        foreach (array_values($lista) as $i => $k) {
            $be->execute([$k['azon'], $i, json_encode($k, JSON_UNESCAPED_UNICODE)]);
        }
        $db->commit();
    }

    public static function keresek(): array
    {
        $sorok = self::kapcsolat()->query('SELECT adat FROM keres ORDER BY sorrend')->fetchAll(PDO::FETCH_COLUMN);
        return array_map(static fn($s) => json_decode($s, true), $sorok);
    }
}
