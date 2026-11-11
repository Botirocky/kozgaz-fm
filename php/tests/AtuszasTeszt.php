<?php

declare(strict_types=1);

use KozgazFM\Atuszas;

function teszt_atuszas_gorbe_egyenlo_teljesitmenyu(): void
{
    for ($i = 0; $i <= 100; $i++) {
        $t = $i / 100;
        igaz(abs(Atuszas::gorbeBe($t) ** 2 + Atuszas::gorbeKi($t) ** 2 - 1.0) < 1e-9, "t={$t}");
    }
    egyezik(0.0, Atuszas::gorbeBe(0.0));
    egyezik(1.0, Atuszas::gorbeKi(0.0));
    igaz(abs(Atuszas::gorbeBe(0.5) - sqrt(0.5)) < 1e-9 && Atuszas::gorbeBe(0.5) > 0.5);
    igaz(abs(Atuszas::gorbeKi(2.0)) < 1e-9);
}

function teszt_atuszas_hossz_es_kezdet(): void
{
    egyezik(5.0, Atuszas::hossz(true, 5.0));
    egyezik(0.0, Atuszas::hossz(false, 5.0));
    egyezik(12.0, Atuszas::hossz(true, 30.0));
    egyezik(0.0, Atuszas::hossz(true, -3.0));
    egyezik(192.0, Atuszas::kezdetMp(200.0, 3.0, 5.0));
    egyezik(0.0, Atuszas::kezdetMp(4.0, 3.0, 5.0));
}

function teszt_atuszas_csend_ertelmezes(): void
{
    $kimenet = "  Duration: 00:03:20.50, start: 0.025057, bitrate: 192 kb/s\n"
        . "[silencedetect @ 0x1] silence_start: 0\n[silencedetect @ 0x1] silence_end: 1.85 | silence_duration: 1.85\n"
        . "[silencedetect @ 0x1] silence_start: 100.2\n[silencedetect @ 0x1] silence_end: 101.0 | silence_duration: 0.8\n"
        . "[silencedetect @ 0x1] silence_start: 196.5\n";
    [$eleje, $vege] = Atuszas::csendErtelmez($kimenet);
    igaz(abs($eleje - 1.85) < 1e-9 && abs($vege - 4.0) < 1e-9, "{$eleje} / {$vege}");
    egyezik([0.0, 0.0], Atuszas::csendErtelmez("Duration: 00:03:20.00,\nsilence_start: 100\nsilence_end: 102 | silence_duration: 2\n"));
    egyezik([0.0, 0.0], Atuszas::csendErtelmez("Duration: 00:00:10.00,\nsilence_start: 0\nsilence_end: 10 | silence_duration: 10\n"));
    egyezik([0.0, 0.0], Atuszas::csendErtelmez(''));
    egyezik([20.0, 20.0], Atuszas::csendErtelmez("Duration: 00:10:00.00,\nsilence_start: 0\nsilence_end: 45 | d\nsilence_start: 560\n"));
}

function teszt_atuszas_csend_tar(): void
{
    $fajl = getenv('KOZGAZ_FM_ADAT') . '/csend-teszt.mp3';
    file_put_contents($fajl, 'a');
    egyezik(null, Atuszas::keres($fajl));
    Atuszas::beir($fajl, 1.25, 3.5);
    egyezik([1.25, 3.5], Atuszas::keres($fajl));
    egyezik([1.25, 3.5], Atuszas::csendMp($fajl));
    file_put_contents($fajl, 'bb');
    clearstatcache();
    egyezik(null, Atuszas::keres($fajl));
    egyezik([0.0, 0.0], Atuszas::csendMp(null));
}
