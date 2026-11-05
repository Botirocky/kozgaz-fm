<?php

declare(strict_types=1);

namespace KozgazFM;

final class Utvonalak
{
    public static function adat(): string
    {
        $ut = getenv('KOZGAZ_FM_ADAT') ?: dirname(__DIR__) . '/adat';
        if (!is_dir($ut)) {
            @mkdir($ut, 0775, true);
        }
        return rtrim($ut, '/');
    }

    public static function mappa(string $nev): string
    {
        $ut = self::adat() . '/' . $nev;
        if (!is_dir($ut)) {
            @mkdir($ut, 0775, true);
        }
        return $ut;
    }

    public static function beallitasFajl(): string
    {
        return self::adat() . '/beallitasok.json';
    }

    public static function gyorsitotar(): string
    {
        return self::mappa('gyorsitotar');
    }

    public static function sajatHangok(): string
    {
        return self::mappa('hangok');
    }

    public static function naploFajl(): string
    {
        return self::adat() . '/naplo.txt';
    }

    public static function eletjelFajl(): string
    {
        return self::adat() . '/utolso_futas.txt';
    }

    public static function allapotFajl(): string
    {
        return self::adat() . '/allapot.json';
    }

    public static function adatbazis(): string
    {
        return self::adat() . '/kozgaz.sqlite';
    }

    public static function beepitettHang(string $nev): string
    {
        return dirname(__DIR__) . '/eroforrasok/hangok/' . $nev . '.mp3';
    }

    public static function zeneGyoker(): string
    {
        return rtrim(getenv('KOZGAZ_FM_ZENE') ?: '/zene', '/');
    }

    public static function futas(): string
    {
        $ut = sys_get_temp_dir() . '/kozgazfm';
        if (!is_dir($ut)) {
            @mkdir($ut, 0700, true);
        }
        return $ut;
    }
}
