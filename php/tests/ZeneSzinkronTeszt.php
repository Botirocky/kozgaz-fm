<?php

declare(strict_types=1);

use KozgazFM\Hiba;
use KozgazFM\ZeneSzinkron;

function szinkron_szerver(string $zene): array
{
    $port = random_int(20000, 40000);
    $folyamat = proc_open([PHP_BINARY, '-S', "127.0.0.1:{$port}", __DIR__ . '/eszkozok/zene_szerver.php'],
        [0 => ['file', '/dev/null', 'r'], 1 => ['file', '/dev/null', 'w'], 2 => ['file', '/dev/null', 'w']], $csovek, null,
        ['KFM_TESZT_ZENE' => $zene]);
    for ($i = 0; $i < 50; $i++) {
        $s = @fsockopen('127.0.0.1', $port, $kod, $hiba, 0.1);
        if ($s) {
            fclose($s);
            break;
        }
        usleep(100000);
    }
    return [$folyamat, "http://127.0.0.1:{$port}"];
}

function teszt_zene_szinkron_letolt_folytat_es_torol(): void
{
    $alap = getenv('KOZGAZ_FM_ADAT') . '/szinkron-' . random_int(1, 99999);
    $zene = "{$alap}/szerver";
    $helyi = "{$alap}/helyi";
    mkdir("{$zene}/Mappa", 0777, true);
    file_put_contents("{$zene}/a.mp3", str_repeat('a', 300000));
    file_put_contents("{$zene}/Mappa/b.mp3", str_repeat('b', 1000));
    [$folyamat, $cim] = szinkron_szerver($zene);
    try {
        mkdir("{$helyi}/Mappa", 0777, true);
        file_put_contents("{$helyi}/a.mp3" . ZeneSzinkron::RESZ, str_repeat('a', 1000));
        $e = ZeneSzinkron::szinkron($cim, 'jo-kulcs', $helyi);
        egyezik(2, $e['uj']);
        egyezik(299000 + 1000, $e['bajt']);
        egyezik(str_repeat('a', 300000), file_get_contents("{$helyi}/a.mp3"));
        egyezik(str_repeat('b', 1000), file_get_contents("{$helyi}/Mappa/b.mp3"));
        egyezik(0, ZeneSzinkron::szinkron($cim, 'jo-kulcs', $helyi)['uj']);
        unlink("{$zene}/Mappa/b.mp3");
        egyezik(1, ZeneSzinkron::szinkron($cim, 'jo-kulcs', $helyi)['torolt']);
        igaz(!is_dir("{$helyi}/Mappa"), 'az üres mappa megmaradt');
        unlink("{$zene}/a.mp3");
        dobja(fn() => ZeneSzinkron::szinkron($cim, 'jo-kulcs', $helyi), Hiba::class);
        igaz(is_file("{$helyi}/a.mp3"), 'üres listánál törölt');
        dobja(fn() => ZeneSzinkron::szinkron($cim, 'rossz', $helyi), Hiba::class);
    } finally {
        proc_terminate($folyamat);
        proc_close($folyamat);
    }
}

function teszt_zene_szinkron_biztonsagos_ut(): void
{
    egyezik('a/b.mp3', ZeneSzinkron::biztonsagosUt('a/b.mp3'));
    foreach (['../x.mp3', '/abs.mp3', 'a//b', '.rejtett/x.mp3', 'a\\b.mp3', ''] as $rossz) {
        egyezik(null, ZeneSzinkron::biztonsagosUt($rossz), $rossz);
    }
}
