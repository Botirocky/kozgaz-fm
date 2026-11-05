<?php

declare(strict_types=1);

namespace KozgazFM;

use DateInterval;
use DateTimeImmutable;

final class Unnepek
{
    public static function husvet(int $ev): DateTimeImmutable
    {
        $a = $ev % 19;
        $b = intdiv($ev, 100);
        $c = $ev % 100;
        $d = intdiv($b, 4);
        $e = $b % 4;
        $f = intdiv($b + 8, 25);
        $g = intdiv($b - $f + 1, 3);
        $h = (19 * $a + $b - $d - $g + 15) % 30;
        $i = intdiv($c, 4);
        $k = $c % 4;
        $l = (32 + 2 * $e + 2 * $i - $h - $k) % 7;
        $m = intdiv($a + 11 * $h + 22 * $l, 451);
        $honap = intdiv($h + $l - 7 * $m + 114, 31);
        $nap = ($h + $l - 7 * $m + 114) % 31;
        return new DateTimeImmutable(sprintf('%04d-%02d-%02d', $ev, $honap, $nap + 1));
    }

    public static function unnepnapok(int $ev): array
    {
        $h = self::husvet($ev);
        $d = static fn(int $ho, int $nap) => new DateTimeImmutable(sprintf('%04d-%02d-%02d', $ev, $ho, $nap));
        $lista = [
            [$d(1, 1), 'Újév'],
            [$d(3, 15), 'Nemzeti ünnep'],
            [$h->sub(new DateInterval('P2D')), 'Nagypéntek'],
            [$h->add(new DateInterval('P1D')), 'Húsvéthétfő'],
            [$d(5, 1), 'A munka ünnepe'],
            [$h->add(new DateInterval('P50D')), 'Pünkösdhétfő'],
            [$d(8, 20), 'Államalapítás ünnepe'],
            [$d(10, 23), 'Nemzeti ünnep'],
            [$d(11, 1), 'Mindenszentek'],
            [$d(12, 24), 'Szenteste'],
            [$d(12, 25), 'Karácsony'],
            [$d(12, 26), 'Karácsony'],
        ];
        usort($lista, static fn($a, $b) => $a[0] <=> $b[0] ?: strcmp($a[1], $b[1]));
        return $lista;
    }
}
