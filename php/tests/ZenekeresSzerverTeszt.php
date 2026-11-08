<?php

declare(strict_types=1);

use KozgazFM\Hatter;
use KozgazFM\Szam;
use KozgazFM\Vezerlo;
use KozgazFM\Zenekeres;
use KozgazFM\ZenekeresSzerver;

function teszt_zenekeres_szerver_hely_a_sorban(): void
{
    $z = kert_lejatszo(['A', 'B'], 0);
    $z->szamok[] = new Szam('Más', null, 'yt0', true, true);
    $z->szamok[] = new Szam('Queen', null, 'yt1', true, true);
    $v = (new ReflectionClass(Vezerlo::class))->newInstanceWithoutConstructor();
    $v->zene = $z;
    $v->keresek = new Zenekeres();
    $v->keresek->lista = [['azon' => 'a1', 'szoveg' => 'Queen', 'cim' => 'Queen', 'allapot' => 'elfogadva', 'ok' => '',
        'ido' => '2026-11-08T10:00:00+01:00', 'yt' => 'yt1']];
    $sz = new ZenekeresSzerver(new Hatter(), $v);
    (new ReflectionProperty($sz, 'tavoli'))->setValue($sz, ['a1' => true]);
    $allapotok = new ReflectionMethod($sz, 'allapotok');
    egyezik(2, $allapotok->invoke($sz)[0]['hely']);
    $v->keresek->lista[0]['allapot'] = 'szol';
    egyezik(0, $allapotok->invoke($sz)[0]['hely']);
}
