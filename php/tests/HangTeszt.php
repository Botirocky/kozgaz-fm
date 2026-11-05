<?php

declare(strict_types=1);

use KozgazFM\Beallitasok;
use KozgazFM\SajatHangok;

function teszt_beepitett_hangok_leteznek(): void
{
    foreach (array_keys(Beallitasok::BEEPITETT_HANGOK) as $nev) {
        $ut = SajatHangok::hangUt("beepitett:{$nev}");
        igaz($ut !== null && is_file($ut) && filesize($ut) > 10000, "hiányzik: {$nev}");
    }
    egyezik(SajatHangok::hangUt('beepitett:becsengo'), SajatHangok::hangUt('beepitett:csengo'));
    egyezik('Jelzőcsengő', SajatHangok::hangNev('beepitett:gong'));
    egyezik(null, SajatHangok::hangUt('beepitett:nincs'));
}

function teszt_regi_hangok_atirasa(): void
{
    $ut = getenv('KOZGAZ_FM_ADAT') . '/regi-hangok.json';
    file_put_contents($ut, json_encode(['hang_becsengo' => 'beepitett:csengo', 'hang_kicsengo' => 'beepitett:csengo',
        'hang_jelzo' => 'beepitett:rovid', 'hang_gong' => 'beepitett:gong', 'hang_riasztas' => 'beepitett:riasztas',
        'rendkivuli' => [['nev' => 'x', 'datum' => '2026-11-10', 'hang' => 'beepitett:dallam']]]));
    $b = Beallitasok::betolt($ut);
    egyezik(['beepitett:becsengo', 'beepitett:kicsengo', 'beepitett:jelzo', 'beepitett:jelzo', 'beepitett:kicsengo'],
        [$b['hang_becsengo'], $b['hang_kicsengo'], $b['hang_jelzo'], $b['hang_gong'], $b['hang_riasztas']]);
    egyezik('beepitett:becsengo', $b['rendkivuli'][0]['hang']);
}
