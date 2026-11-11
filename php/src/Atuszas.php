<?php

declare(strict_types=1);

namespace KozgazFM;

final class Atuszas
{
    public const CSEND_KUSZOB_DB = -50;
    public const CSEND_MIN_MP = 0.3;
    public const CSEND_MAX_MP = 20.0;
    public const MIN_LEVAGAS_MP = 0.15;
    public const MAX_ATUSZTATAS_MP = 12.0;
    public const KEZI_ATUSZTATAS_MP = 2.0;
    public const CSENGO_ELHALKITAS_MP = 0.25;

    public static function gorbeBe(float $t): float
    {
        return sin(max(0.0, min(1.0, $t)) * M_PI / 2);
    }

    public static function gorbeKi(float $t): float
    {
        return cos(max(0.0, min(1.0, $t)) * M_PI / 2);
    }

    public static function hossz(bool $be, float $mp): float
    {
        return $be ? max(0.0, min(self::MAX_ATUSZTATAS_MP, $mp)) : 0.0;
    }

    public static function kezdetMp(float $hossz, float $vegeCsend, float $atuszas): float
    {
        return max(0.0, $hossz - $vegeCsend - $atuszas);
    }

    public static function csendErtelmez(string $kimenet): array
    {
        $hossz = null;
        if (preg_match('/Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)/', $kimenet, $m)) {
            $hossz = (int)$m[1] * 3600 + (int)$m[2] * 60 + (float)$m[3];
        }
        preg_match_all('/silence_(start|end):\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)/', $kimenet, $talalatok, PREG_SET_ORDER);
        $szakaszok = [];
        foreach ($talalatok as [, $jel, $ertek]) {
            if ($jel === 'start') {
                $szakaszok[] = [(float)$ertek, null];
            } elseif ($szakaszok && $szakaszok[count($szakaszok) - 1][1] === null) {
                $szakaszok[count($szakaszok) - 1][1] = (float)$ertek;
            }
        }
        $eleje = $vege = 0.0;
        if ($szakaszok && $szakaszok[0][0] <= 0.05 && $szakaszok[0][1] !== null) {
            $eleje = $szakaszok[0][1];
        }
        if ($hossz !== null && $szakaszok) {
            [$kezdet, $veg] = $szakaszok[count($szakaszok) - 1];
            if (($veg === null || $veg >= $hossz - 0.1) && $kezdet > $eleje) {
                $vege = $hossz - $kezdet;
            }
        }
        if ($hossz !== null && $eleje + $vege > $hossz / 2) {
            return [0.0, 0.0];
        }
        return [min($eleje, self::CSEND_MAX_MP), min(max($vege, 0.0), self::CSEND_MAX_MP)];
    }

    public static function meres(string $ut): array
    {
        $szuro = 'silencedetect=n=' . self::CSEND_KUSZOB_DB . 'dB:d=' . self::CSEND_MIN_MP;
        $parancs = ['nice', '-n', '15', 'ffmpeg', '-nostdin', '-hide_banner', '-nostats', '-i', $ut, '-vn', '-sn',
            '-af', $szuro, '-f', 'null', '-'];
        $f = proc_open($parancs, [1 => ['file', '/dev/null', 'w'], 2 => ['pipe', 'w']], $csovek);
        if (!is_resource($f)) {
            throw new Hiba('az ffmpeg nem indult');
        }
        $hiba = (string)stream_get_contents($csovek[2]);
        fclose($csovek[2]);
        if (proc_close($f) !== 0) {
            $sorok = array_filter(explode("\n", trim($hiba)));
            throw new Hiba(mb_substr((string)end($sorok) ?: 'ismeretlen hiba', 0, 200));
        }
        return self::csendErtelmez($hiba);
    }

    private static function tarFajl(): string
    {
        return Utvonalak::gyorsitotar() . '/csend.json';
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
        if ((float)($e['m'] ?? 0) !== (float)filemtime($ut) || (int)($e['s'] ?? -1) !== filesize($ut)
            || !isset($e['e'], $e['v'])) {
            return null;
        }
        return [(float)$e['e'], (float)$e['v']];
    }

    public static function beir(string $ut, float $eleje, float $vege): void
    {
        $fajl = self::tarFajl();
        $zar = fopen($fajl . '.zar', 'c');
        flock($zar, LOCK_EX);
        $adat = json_decode((string)@file_get_contents($fajl), true);
        $adat = is_array($adat) ? $adat : [];
        $adat[$ut] = ['m' => (float)filemtime($ut), 's' => filesize($ut), 'e' => $eleje, 'v' => $vege];
        file_put_contents($fajl . '.tmp', json_encode($adat, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
        rename($fajl . '.tmp', $fajl);
        flock($zar, LOCK_UN);
        fclose($zar);
        self::$tar = null;
    }

    public static function csendMp(?string $ut): array
    {
        $mert = $ut === null ? null : self::keres($ut);
        if ($mert === null) {
            return [0.0, 0.0];
        }
        return [$mert[0] >= self::MIN_LEVAGAS_MP ? $mert[0] : 0.0, $mert[1] >= self::MIN_LEVAGAS_MP ? $mert[1] : 0.0];
    }
}
