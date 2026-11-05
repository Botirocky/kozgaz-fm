<?php

declare(strict_types=1);

use KozgazFM\Beallitasok;
use KozgazFM\Esemeny;
use KozgazFM\Orarend;

function orarend_esemeny(Esemeny $e): array
{
    return [$e->ido->format('Y-m-d\TH:i:s'), $e->tipus, $e->ora, $e->leiras(), $e->hangero];
}

function teszt_orarend_egyezik_a_python_valtozattal(): void
{
    $minta = minta('orarend_minta.json');
    $adat = json_decode((string)file_get_contents($minta), true);
    foreach ($adat as $nev => $v) {
        $b = Beallitasok::normalizal($v['beallitasok']);
        foreach ($v['napok'] as $nap => $vart) {
            $kapott = array_map('orarend_esemeny', Orarend::napiEsemenyek($b, new DateTimeImmutable($nap)));
            egyezik($vart, $kapott, "{$nev} {$nap}");
        }
        foreach ($v['allapotok'] as [$ido, $szakasz, $ora, $cim, $vege, $csend, $kov, $szunet]) {
            $most = new DateTimeImmutable($ido);
            $a = Orarend::allapot($b, $most);
            $k = $a['kovetkezo'];
            egyezik([$szakasz, $ora, $cim, $vege, $csend, $kov, $szunet], [
                $a['szakasz'], $a['ora'], Orarend::allapotCim($a), $a['vege']?->format('Y-m-d\TH:i:s'), $a['csend'],
                $k ? orarend_esemeny($k) : null, Orarend::zeneSzunet($b, $most),
            ], "{$nev} állapot {$ido}");
        }
    }
}

function teszt_rend_generalas(): void
{
    egyezik([['08:00', '08:45'], ['08:55', '09:40'], ['09:50', '10:35'], ['10:50', '11:35']],
        Orarend::rendGeneralas('08:00', 4, 45, 10, 3, 15));
}

function teszt_nap_szoveg(): void
{
    $most = new DateTimeImmutable('2026-11-04 10:00');
    egyezik('ma', Orarend::napSzoveg(new DateTimeImmutable('2026-11-04 15:00'), $most));
    egyezik('holnap', Orarend::napSzoveg(new DateTimeImmutable('2026-11-05 07:00'), $most));
    egyezik('pénteken', Orarend::napSzoveg(new DateTimeImmutable('2026-11-06 07:00'), $most));
    egyezik('11. 20.', Orarend::napSzoveg(new DateTimeImmutable('2026-11-20 07:00'), $most));
}
