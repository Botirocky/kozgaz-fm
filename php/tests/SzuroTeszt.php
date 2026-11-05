<?php

declare(strict_types=1);

use KozgazFM\Dalszoveg;
use KozgazFM\Szuro;
use KozgazFM\Unnepek;
use KozgazFM\Zar;

function teszt_szuro_egyezik_a_python_valtozattal(): void
{
    $adat = json_decode((string)file_get_contents(minta('szuro_minta.json')), true);
    $sajat = new Szuro(['saját*', 'tiltott szó'], true);
    $alap = new Szuro();
    foreach ($adat['ertekeles'] as [$szoveg, $ertekeles, $kibontva, $talalat, $alapTalalat]) {
        egyezik($ertekeles, array_values(Szuro::ertekel($szoveg)), "értékelés: {$szoveg}");
        egyezik($kibontva, Szuro::szavakKibontva($szoveg), "kibontás: {$szoveg}");
        egyezik($talalat, $sajat->talalat($szoveg), "saját szűrő: {$szoveg}");
        egyezik($alapTalalat, $alap->talalat($szoveg), "alapszűrő: {$szoveg}");
    }
    foreach ($adat['dal'] as [$cim, $bontas, $kulcs]) {
        egyezik($bontas, Dalszoveg::cimBontas($cim), "címbontás: {$cim}");
        egyezik($kulcs, Dalszoveg::kulcs($cim), "kulcs: {$cim}");
    }
}

function teszt_szuro_sajat_szavak(): void
{
    $sz = new Szuro(['alma', 'kör*'], false);
    egyezik('alma', $sz->talalat('Piros ALMA dal'));
    egyezik(null, $sz->talalat('almafa'));
    egyezik('kor', $sz->talalat('Körhinta'));
    igaz(!(new Szuro([], false))->van());
}

function teszt_tragar_hatarok(): void
{
    $e = ['szavak' => 400, 'eros' => 2, 'kozepes' => 0, 'enyhe' => 0];
    igaz(Szuro::tragar($e, 'szigoru'));
    igaz(!Szuro::tragar($e, 'normal'));
}

function teszt_pin_kompatibilis_a_python_kivonattal(): void
{
    $py = 'pbkdf2_sha256$1000$00112233445566778899aabbccddeeff$' .
        bin2hex(hash_pbkdf2('sha256', '1234', hex2bin('00112233445566778899aabbccddeeff'), 1000, 32, true));
    igaz(Zar::ellenoriz('1234', $py));
    igaz(!Zar::ellenoriz('1235', $py));
    $h = Zar::pinHash('4321', 1000);
    igaz(Zar::ellenoriz('4321', $h));
    dobja(fn() => Zar::pinHash('12'), \KozgazFM\Hiba::class);
    dobja(fn() => Zar::jelszoHash(' rövid'), \KozgazFM\Hiba::class);
}

function teszt_husvet_es_unnepek(): void
{
    egyezik('2027-03-28', Unnepek::husvet(2027)->format('Y-m-d'));
    egyezik('2026-04-05', Unnepek::husvet(2026)->format('Y-m-d'));
    $nevek = array_map(static fn($u) => $u[0]->format('m-d') . ' ' . $u[1], Unnepek::unnepnapok(2026));
    igaz(in_array('04-03 Nagypéntek', $nevek, true) && in_array('05-25 Pünkösdhétfő', $nevek, true));
}
