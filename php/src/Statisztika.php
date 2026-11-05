<?php

declare(strict_types=1);

namespace KozgazFM;

use DateInterval;
use DateTimeImmutable;
use PDO;

final class Statisztika
{
    public const KESES_HATAR_MS = 2000;
    public const MEGORZES_NAP = 400;

    private const SEMA = <<<'SQL'
CREATE TABLE IF NOT EXISTS lejatszas (
    id INTEGER PRIMARY KEY, kezdet TEXT NOT NULL, cim TEXT NOT NULL, forras TEXT NOT NULL DEFAULT '',
    kert INTEGER NOT NULL DEFAULT 0, hossz_mp REAL
);
CREATE INDEX IF NOT EXISTS lejatszas_kezdet ON lejatszas (kezdet);
CREATE TABLE IF NOT EXISTS csengetes (
    id INTEGER PRIMARY KEY, ido TEXT NOT NULL, tipus TEXT NOT NULL, leiras TEXT NOT NULL DEFAULT '', keses_ms INTEGER
);
CREATE INDEX IF NOT EXISTS csengetes_ido ON csengetes (ido);
CREATE TABLE IF NOT EXISTS keres (id INTEGER PRIMARY KEY, ido TEXT NOT NULL, eredmeny TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS keres_ido ON keres (ido);
SQL;

    private PDO $db;
    private ?array $nyitott = null;

    public function __construct(?string $ut = null)
    {
        $this->db = new PDO('sqlite:' . ($ut ?? Utvonalak::adat() . '/statisztika.sqlite'), null, null,
            [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
        $this->db->exec('PRAGMA journal_mode=WAL');
        $this->db->exec('PRAGMA busy_timeout=3000');
        $this->db->exec(self::SEMA);
    }

    private static function ido(DateTimeImmutable $t): string
    {
        return $t->format('Y-m-d H:i:s');
    }

    private function ir(string $sql, array $p): int
    {
        try {
            $this->db->prepare($sql)->execute($p);
            return (int)$this->db->lastInsertId();
        } catch (\PDOException $e) {
            Naplo::ir('A statisztika nem írható: ' . $e->getMessage());
            return 0;
        }
    }

    private function olvas(string $sql, array $p): array
    {
        try {
            $q = $this->db->prepare($sql);
            $q->execute($p);
            return $q->fetchAll(PDO::FETCH_NUM);
        } catch (\PDOException $e) {
            return [];
        }
    }

    public function szamKezd(string $cim, string $forras = '', bool $kert = false, ?DateTimeImmutable $most = null): void
    {
        $most ??= new DateTimeImmutable();
        $this->szamVege($most);
        $id = $this->ir('INSERT INTO lejatszas (kezdet, cim, forras, kert) VALUES (?, ?, ?, ?)',
            [self::ido($most), mb_substr($cim, 0, 300), mb_substr($forras, 0, 120), (int)$kert]);
        $this->nyitott = $id ? [$id, $most] : null;
    }

    public function nyitott(): bool
    {
        return $this->nyitott !== null;
    }

    public function szamVege(?DateTimeImmutable $most = null): void
    {
        if ($this->nyitott === null) {
            return;
        }
        [$id, $kezdet] = $this->nyitott;
        $this->nyitott = null;
        $hossz = max(0, (($most ?? new DateTimeImmutable())->format('U.u') - $kezdet->format('U.u')));
        $this->ir('UPDATE lejatszas SET hossz_mp = ? WHERE id = ?', [round($hossz, 1), $id]);
    }

    public function csengetes(string $tipus, string $leiras = '', ?DateTimeImmutable $tervezett = null, ?DateTimeImmutable $most = null): void
    {
        $most ??= new DateTimeImmutable();
        $keses = $tervezett ? (int)round(((float)$most->format('U.u') - (float)$tervezett->format('U.u')) * 1000) : null;
        $this->ir('INSERT INTO csengetes (ido, tipus, leiras, keses_ms) VALUES (?, ?, ?, ?)',
            [self::ido($most), $tipus, mb_substr($leiras, 0, 200), $keses]);
    }

    public function keres(string $eredmeny): void
    {
        $this->ir('INSERT INTO keres (ido, eredmeny) VALUES (?, ?)', [self::ido(new DateTimeImmutable()), $eredmeny]);
    }

    public function osszegzes(DateTimeImmutable $tol, DateTimeImmutable $ig, int $top = 10): array
    {
        $a = $tol->format('Y-m-d') . ' 00:00:00';
        $b = $ig->add(new DateInterval('P1D'))->format('Y-m-d') . ' 00:00:00';
        $zene = $this->olvas('SELECT COUNT(*), COALESCE(SUM(hossz_mp), 0), COALESCE(SUM(kert), 0) FROM lejatszas WHERE kezdet >= ? AND kezdet < ?', [$a, $b])[0] ?? [0, 0, 0];
        $legtobb = $this->olvas('SELECT cim, COUNT(*) AS db, MAX(kert) FROM lejatszas WHERE kezdet >= ? AND kezdet < ? GROUP BY cim ORDER BY db DESC, MAX(kezdet) DESC LIMIT ?', [$a, $b, $top]);
        $cs = $this->olvas("SELECT COUNT(*), AVG(ABS(keses_ms)), MAX(keses_ms), SUM(CASE WHEN keses_ms > ? THEN 1 ELSE 0 END), SUM(CASE WHEN tipus = 'kezi' THEN 1 ELSE 0 END) FROM csengetes WHERE ido >= ? AND ido < ?", [self::KESES_HATAR_MS, $a, $b])[0] ?? [0, null, null, 0, 0];
        $keresek = [];
        foreach ($this->olvas('SELECT eredmeny, COUNT(*) FROM keres WHERE ido >= ? AND ido < ? GROUP BY eredmeny', [$a, $b]) as [$e, $d]) {
            $keresek[$e] = (int)$d;
        }
        $napiZene = [];
        foreach ($this->olvas('SELECT substr(kezdet, 1, 10), COALESCE(SUM(hossz_mp), 0) FROM lejatszas WHERE kezdet >= ? AND kezdet < ? GROUP BY 1', [$a, $b]) as [$n, $m]) {
            $napiZene[$n] = (float)$m;
        }
        $napiCsengo = [];
        foreach ($this->olvas('SELECT substr(ido, 1, 10), COUNT(*) FROM csengetes WHERE ido >= ? AND ido < ? GROUP BY 1', [$a, $b]) as [$n, $d]) {
            $napiCsengo[$n] = (int)$d;
        }
        $napok = [];
        for ($nap = $tol; $nap <= $ig; $nap = $nap->add(new DateInterval('P1D'))) {
            $k = $nap->format('Y-m-d');
            $napok[] = ['nap' => $k, 'zene_perc' => (int)round(($napiZene[$k] ?? 0) / 60), 'csengetes' => $napiCsengo[$k] ?? 0];
        }
        return [
            'tol' => $tol->format('Y-m-d'), 'ig' => $ig->format('Y-m-d'),
            'zene' => ['szamok' => (int)$zene[0], 'perc' => (int)round($zene[1] / 60), 'kert' => (int)$zene[2]],
            'legtobbet' => array_map(static fn($s) => ['cim' => $s[0], 'darab' => (int)$s[1], 'kert' => (bool)$s[2]], $legtobb),
            'csengetes' => ['darab' => (int)$cs[0], 'kezi' => (int)($cs[4] ?? 0),
                'atlag_keses_ms' => $cs[1] !== null ? (int)round((float)$cs[1]) : null,
                'max_keses_ms' => $cs[2] !== null ? (int)$cs[2] : null, 'kesett' => (int)($cs[3] ?? 0)],
            'keresek' => ['erkezett' => $keresek['erkezett'] ?? 0, 'elfogadva' => $keresek['elfogadva'] ?? 0,
                'elutasitva' => $keresek['elutasitva'] ?? 0],
            'napok' => $napok,
        ];
    }

    public function csv(DateTimeImmutable $tol, DateTimeImmutable $ig): string
    {
        $a = $tol->format('Y-m-d') . ' 00:00:00';
        $b = $ig->add(new DateInterval('P1D'))->format('Y-m-d') . ' 00:00:00';
        $f = fopen('php://temp', 'w+');
        fwrite($f, "\u{FEFF}");
        fputcsv($f, ['Dátum', 'Idő', 'Cím', 'Forrás', 'Kért szám', 'Hossz (mp)'], ';', '"', '');
        foreach ($this->olvas('SELECT kezdet, cim, forras, kert, hossz_mp FROM lejatszas WHERE kezdet >= ? AND kezdet < ? ORDER BY kezdet', [$a, $b]) as [$k, $c, $fo, $ke, $h]) {
            $biztos = in_array(mb_substr($c, 0, 1), ['=', '+', '-', '@', "\t", "\r"], true) ? "'" . $c : $c;
            fputcsv($f, [substr($k, 0, 10), substr($k, 11), $biztos, $fo, $ke ? 'igen' : '', $h === null ? '' : sprintf('%.0f', $h)], ';', '"', '');
        }
        rewind($f);
        $ki = (string)stream_get_contents($f);
        fclose($f);
        return $ki;
    }

    public function takarit(int $nap = self::MEGORZES_NAP): void
    {
        $hatar = self::ido((new DateTimeImmutable())->sub(new DateInterval("P{$nap}D")));
        foreach ([['lejatszas', 'kezdet'], ['csengetes', 'ido'], ['keres', 'ido']] as [$t, $o]) {
            $this->ir("DELETE FROM {$t} WHERE {$o} < ?", [$hatar]);
        }
    }
}
