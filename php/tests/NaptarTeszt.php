<?php

declare(strict_types=1);

use KozgazFM\Beallitasok;
use KozgazFM\Kghsz;
use KozgazFM\NaptarImport;

function teszt_kghsz_egyezik_a_python_valtozattal(): void
{
    $vart = json_decode((string)file_get_contents(minta('kghsz_minta.json')), true);
    foreach (['tanev', 'csengetes', 'hazirend', 'esemenyek'] as $nev) {
        minta("kghsz_{$nev}.html");
    }
    $html = static fn(string $nev) => (string)file_get_contents(minta("kghsz_{$nev}.html"));
    $b = Beallitasok::alapertelmezett();
    egyezik($vart['sorok_tanev'], Kghsz::sorok((string)((Kghsz::oldalAdat($html('tanev'))['data'] ?? [])['currentInfo'] ?? '')), 'tanév sorai');
    [$normal, $rovid] = Kghsz::csengetesiRend($html('csengetes'), $html('hazirend'));
    egyezik($vart['normal'], $normal, 'normál rend');
    egyezik($vart['rovid'], $rovid, 'rövidített rend');
    $tanev = Kghsz::tanevEsemenyek($html('tanev'));
    egyezik($vart['tanev'], $tanev, 'tanév rendje');
    $honlapi = Kghsz::honlapiEsemenyek($html('esemenyek'), new DateTimeImmutable('2026-11-04'));
    egyezik($vart['honlapi'], $honlapi, 'honlapi események');
    $ossz = Kghsz::osszevon($tanev, $honlapi, $b);
    egyezik($vart['ossz'], $ossz, 'összevonás');
    $ics = NaptarImport::icsBeolvas((string)file_get_contents(minta('minta.ics')));
    $javaslatok = array_merge(NaptarImport::javaslatok($ics, $b, '2026-01-01'), NaptarImport::javaslatok($ossz, $b, '2026-01-01'));
    egyezik($vart['javaslatok'], $javaslatok, 'javaslatok');
}

function teszt_naptar_alkalmaz(): void
{
    $b = Beallitasok::alapertelmezett();
    $ics = NaptarImport::icsBeolvas((string)file_get_contents(minta('minta.ics')));
    $kiv = array_filter(NaptarImport::javaslatok($ics, $b, '2026-01-01'), static fn($j) => $j['muvelet'] !== NaptarImport::KIHAGY);
    [$uj, $sz, $k] = NaptarImport::alkalmaz($b, array_values($kiv));
    egyezik(2, $sz, 'új szünnapok');
    egyezik('Rövidített', $uj['kivetelek']['2026-12-10'] ?? null);
    egyezik('Normál', $uj['kivetelek']['2026-12-05'] ?? null);
    igaz($k === 2);
}
