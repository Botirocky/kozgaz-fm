<?php

declare(strict_types=1);

namespace KozgazFM;

final class Naplo
{
    private const MAX_MERET = 5 * 1024 * 1024;

    public static function ir(string $szoveg): string
    {
        $sor = date('Y-m-d H:i:s') . '  ' . str_replace(["\r", "\n"], ' ', $szoveg);
        $fajl = Utvonalak::naploFajl();
        if (is_file($fajl) && filesize($fajl) > self::MAX_MERET) {
            @rename($fajl, $fajl . '.1');
        }
        @file_put_contents($fajl, $sor . "\n", FILE_APPEND | LOCK_EX);
        return $sor;
    }

    public static function utolso(int $darab = 1000): array
    {
        $fajl = Utvonalak::naploFajl();
        if (!is_file($fajl)) {
            return [];
        }
        $f = fopen($fajl, 'rb');
        if ($f === false) {
            return [];
        }
        $meret = filesize($fajl);
        $olvas = min($meret, max(65536, $darab * 200));
        fseek($f, -$olvas, SEEK_END);
        $adat = (string)fread($f, $olvas);
        fclose($f);
        $sorok = explode("\n", rtrim($adat, "\n"));
        if ($olvas < $meret) {
            array_shift($sorok);
        }
        return array_slice($sorok, -$darab);
    }
}
