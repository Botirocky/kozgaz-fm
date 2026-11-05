<?php

declare(strict_types=1);

namespace KozgazFM;

final class Hangossag
{
    public const CEL_LUFS = -16.0;
    public const MAX_EMELES_DB = 6.0;
    public const MAX_CSOKKENTES_DB = -20.0;
    public const CSUCS_HATAR_DBTP = -1.0;
    public const CSEND_LUFS = -60.0;

    public static function kimenetErtelmez(string $kimenet): array
    {
        $osszegzes = str_contains($kimenet, 'Summary:') ? substr($kimenet, (int)strrpos($kimenet, 'Summary:')) : $kimenet;
        preg_match_all('/^\s*I:\s*(-?\d+(?:\.\d+)?|-inf)\s*LUFS/m', $osszegzes, $i);
        preg_match_all('/^\s*Peak:\s*(-?\d+(?:\.\d+)?|-inf)\s*dBFS/m', $osszegzes, $p);
        if (!$i[1]) {
            throw new Hiba('az ffmpeg nem adott hangosságot');
        }
        $szam = static fn(string $s): float => $s === '-inf' ? -INF : (float)$s;
        return [$szam(end($i[1])), $p[1] ? $szam(end($p[1])) : 0.0];
    }

    public static function meres(string $ut): array
    {
        $parancs = ['nice', '-n', '15', 'ffmpeg', '-nostdin', '-hide_banner', '-nostats', '-i', $ut, '-vn', '-sn',
            '-af', 'ebur128=peak=true', '-f', 'null', '-'];
        $f = proc_open($parancs, [1 => ['file', '/dev/null', 'w'], 2 => ['pipe', 'w']], $csovek);
        if (!is_resource($f)) {
            throw new Hiba('az ffmpeg nem indult');
        }
        $hiba = (string)stream_get_contents($csovek[2]);
        fclose($csovek[2]);
        $kod = proc_close($f);
        if ($kod !== 0) {
            $sorok = array_filter(explode("\n", trim($hiba)));
            throw new Hiba(mb_substr((string)end($sorok) ?: 'ismeretlen hiba', 0, 200));
        }
        return self::kimenetErtelmez($hiba);
    }

    public static function erositesDb(float $lufs, float $csucs, float $cel = self::CEL_LUFS): float
    {
        if (is_infinite($lufs) || $lufs < self::CSEND_LUFS) {
            return 0.0;
        }
        $db = $cel - $lufs;
        if ($db > 0 && !is_infinite($csucs)) {
            $db = min($db, self::CSUCS_HATAR_DBTP - $csucs);
        }
        return max(self::MAX_CSOKKENTES_DB, min(self::MAX_EMELES_DB, $db));
    }

    public static function szorzo(float $db): float
    {
        return 10 ** ($db / 20);
    }

    private static function tarFajl(): string
    {
        return Utvonalak::gyorsitotar() . '/hangossag.json';
    }

    private static ?array $tar = null;
    private static int $tarIdo = 0;

    private static function tar(): array
    {
        $fajl = self::tarFajl();
        $mtime = is_file($fajl) ? (int)filemtime($fajl) : 0;
        if (self::$tar === null || $mtime !== self::$tarIdo) {
            $adat = json_decode((string)@file_get_contents($fajl), true);
            self::$tar = is_array($adat) ? $adat : [];
            self::$tarIdo = $mtime;
        }
        return self::$tar;
    }

    public static function keres(string $ut): ?array
    {
        $e = self::tar()[$ut] ?? null;
        if (!is_array($e) || !is_file($ut)) {
            return null;
        }
        clearstatcache(true, $ut);
        if ((float)($e['m'] ?? 0) !== (float)filemtime($ut) || (int)($e['s'] ?? -1) !== filesize($ut)) {
            return null;
        }
        $szam = static fn(string $s): float => $s === '-inf' ? -INF : (float)$s;
        return [$szam((string)$e['i']), $szam((string)$e['p'])];
    }

    public static function beir(string $ut, float $lufs, float $csucs): void
    {
        $fajl = self::tarFajl();
        $zar = fopen($fajl . '.zar', 'c');
        flock($zar, LOCK_EX);
        $adat = json_decode((string)@file_get_contents($fajl), true);
        $adat = is_array($adat) ? $adat : [];
        $adat[$ut] = ['m' => (float)filemtime($ut), 's' => filesize($ut),
            'i' => is_infinite($lufs) ? '-inf' : (string)$lufs, 'p' => is_infinite($csucs) ? '-inf' : (string)$csucs];
        file_put_contents($fajl . '.tmp', json_encode($adat, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
        rename($fajl . '.tmp', $fajl);
        flock($zar, LOCK_UN);
        fclose($zar);
        self::$tar = null;
    }

    public static function darab(): int
    {
        return count(self::tar());
    }

    public static function erosites(?string $ut, bool $bekapcsolva = true): float
    {
        if (!$bekapcsolva || $ut === null) {
            return 1.0;
        }
        $mert = self::keres($ut);
        return $mert === null ? 1.0 : self::szorzo(self::erositesDb($mert[0], $mert[1]));
    }
}
