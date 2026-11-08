<?php

declare(strict_types=1);

use KozgazFM\Hatter;
use KozgazFM\Kiegyenlito;
use KozgazFM\Szam;
use KozgazFM\ZeneLejatszo;

function kert_lejatszo(array $cimek, int $index): ZeneLejatszo
{
    $hatter = new Hatter();
    $k = new Kiegyenlito($hatter);
    $k->bekapcsolva = false;
    $z = new ZeneLejatszo($hatter, $k);
    $z->gyorsitotar = false;
    $z->forras = ['tipus' => 'mappa', 'nev' => 'Teszt', 'cim' => '/x', 'aktiv' => true];
    $z->szamok = array_map(static fn($c) => new Szam($c, "/x/{$c}.mp3"), $cimek);
    $z->index = $index;
    (new ReflectionProperty($z, 'szol'))->setValue($z, true);
    return $z;
}

function kert_indul(ZeneLejatszo $z, int $index): string
{
    $z->index = ($index + count($z->szamok)) % count($z->szamok);
    $szam = $z->szamok[$z->index];
    $volt = $szam->kert;
    $szam->kert = false;
    (new ReflectionMethod($z, 'lejatszottKereseketKivesz'))->invoke($z, $szam, $volt);
    return $szam->cim;
}

function kert_cimek(ZeneLejatszo $z): array
{
    return array_map(static fn(Szam $s) => $s->cim, $z->szamok);
}

function teszt_kert_zenek_kerese_sorrendjeben_aztan_az_alap_folytatodik(): void
{
    $z = kert_lejatszo(['a', 'b', 'c', 'd', 'e'], 1);
    $z->beszur(new Szam('k1', '/x/k1.mp3', '1'));
    $z->beszur(new Szam('k2', '/x/k2.mp3', '2'));
    egyezik(['k1', 'k2'], array_map(static fn($p) => $p[1]->cim, $z->kertSor()));
    $szolt = [];
    for ($i = 0; $i < 4; $i++) {
        $szolt[] = kert_indul($z, $z->index + 1);
    }
    egyezik(['k1', 'k2', 'c', 'd'], $szolt);
    egyezik(['a', 'b', 'c', 'd', 'e'], kert_cimek($z));
}

function teszt_lejatszott_keres_nem_jon_vissza(): void
{
    $z = kert_lejatszo(['a', 'b', 'c'], 0);
    $z->beszur(new Szam('k', '/x/k.mp3', '1'));
    egyezik('k', kert_indul($z, $z->index + 1));
    igaz($z->mostKert());
    for ($i = 0; $i < 6; $i++) {
        igaz(kert_indul($z, $z->index + 1) !== 'k', 'a kért szám újra szólt');
    }
}

function teszt_keres_kozben_erkezo_keresek_a_sor_vegere(): void
{
    $z = kert_lejatszo(['a', 'b', 'c', 'd'], 2);
    $z->beszur(new Szam('k1', '/x/k1.mp3', '1'));
    kert_indul($z, $z->index + 1);
    $z->beszur(new Szam('k2', '/x/k2.mp3', '2'));
    $z->beszur(new Szam('k3', '/x/k3.mp3', '3'));
    $szolt = [];
    for ($i = 0; $i < 3; $i++) {
        $szolt[] = kert_indul($z, $z->index + 1);
    }
    egyezik(['k2', 'k3', 'd'], $szolt);
}

function teszt_alap_pozicio_kert_zene_alatt(): void
{
    $z = kert_lejatszo(['a', 'b', 'c', 'd', 'e'], 2);
    $z->beszur(new Szam('k', '/x/k.mp3', '1'));
    kert_indul($z, $z->index + 1);
    egyezik(['a', 'b', 'c', 'd', 'e'], array_map(static fn($p) => $p[1]->cim, $z->alapLista()));
    egyezik('c', $z->szamok[$z->alapPozicio()]->cim);
}

function teszt_ujrakever_a_kerteket_elol_hagyja(): void
{
    $z = kert_lejatszo(['a', 'b', 'c', 'd', 'e', 'f'], 1);
    $z->beszur(new Szam('k', '/x/k.mp3', '1'));
    igaz($z->ujrakever());
    egyezik(['a', 'b', 'k'], array_slice(kert_cimek($z), 0, 3));
    $maradek = array_slice(kert_cimek($z), 3);
    sort($maradek);
    egyezik(['c', 'd', 'e', 'f'], $maradek);
}

function teszt_kert_szavazat_szerint_rendez_a_most_szolot_nem_mozditja(): void
{
    $z = kert_lejatszo(['a', 'b', 'c'], 1);
    foreach (['1', '2', '3'] as $n) {
        $z->beszur(new Szam("k{$n}", "/x/k{$n}.mp3", $n));
    }
    $z->kertRendez(['3' => 2, '2' => 1]);
    egyezik(['k3', 'k2', 'k1'], array_map(static fn($p) => $p[1]->cim, $z->kertSor()));
    egyezik([2, 1, 0], array_map(static fn($p) => $p[1]->szavazat, $z->kertSor()));
    egyezik('b', $z->szamok[$z->index]->cim);
    $z->kertRendez(['1' => 1, '2' => 1, '3' => 1]);
    egyezik(['k3', 'k2', 'k1'], array_map(static fn($p) => $p[1]->cim, $z->kertSor()));
}
