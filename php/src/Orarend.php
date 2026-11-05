<?php

declare(strict_types=1);

namespace KozgazFM;

use DateInterval;
use DateTimeImmutable;

final class Orarend
{
    public const SZ_ORA = 'óra';
    public const SZ_SZUNET = 'szünet';
    public const SZ_REGGEL = 'tanítás előtt';
    public const SZ_VEGE = 'tanítás után';
    public const SZ_SZUNNAP = 'szünnap';
    public const SZ_NINCS = 'nincs csengetés';

    public const NAP_RAGOS = ['hétfőn', 'kedden', 'szerdán', 'csütörtökön', 'pénteken', 'szombaton', 'vasárnap'];

    public static function nap(DateTimeImmutable $ido): DateTimeImmutable
    {
        return $ido->setTime(0, 0);
    }

    public static function het(DateTimeImmutable $nap): int
    {
        return (int)$nap->format('N') - 1;
    }

    public static function idopont(DateTimeImmutable $nap, string $szoveg): DateTimeImmutable
    {
        [$ora, $perc] = array_map('intval', array_slice(explode(':', trim($szoveg)), 0, 2)) + [0, 0];
        return $nap->setTime($ora, $perc);
    }

    public static function mp(int $masodperc): DateInterval
    {
        return new DateInterval('PT' . max(0, $masodperc) . 'S');
    }

    public static function kulonbseg(DateTimeImmutable $a, DateTimeImmutable $b): int
    {
        return $a->getTimestamp() - $b->getTimestamp();
    }

    public static function szunnapNev(array $b, DateTimeImmutable $nap): ?string
    {
        $iso = $nap->format('Y-m-d');
        foreach ($b['szunnapok'] as $sz) {
            if ($sz['tol'] <= $iso && $iso <= ($sz['ig'] ?: $sz['tol'])) {
                return $sz['nev'] ?: 'Szünnap';
            }
        }
        return null;
    }

    public static function napiRend(array $b, DateTimeImmutable $nap): ?array
    {
        $iso = $nap->format('Y-m-d');
        if ($b['ma_nincs_csengetes'] === $iso) {
            return null;
        }
        if (isset($b['kivetelek'][$iso])) {
            return Beallitasok::rend($b, $b['kivetelek'][$iso]);
        }
        if (self::szunnapNev($b, $nap) !== null) {
            return null;
        }
        $nev = $b['het'][self::het($nap)] ?? '';
        return $nev !== '' ? Beallitasok::rend($b, $nev) : null;
    }

    public static function idopontok(array $rend, DateTimeImmutable $nap): array
    {
        $parok = [];
        foreach ($rend['orak'] as $o) {
            $k = self::idopont($nap, $o['kezdet']);
            $v = self::idopont($nap, $o['vege']);
            if ($v > $k) {
                $parok[] = [$k, $v];
            }
        }
        usort($parok, static fn($a, $c) => $a[0] <=> $c[0] ?: $a[1] <=> $c[1]);
        return $parok;
    }

    public static function napiOrak(array $b, DateTimeImmutable $nap): array
    {
        $rend = self::napiRend($b, $nap);
        return $rend ? self::idopontok($rend, $nap) : [];
    }

    private static function jelzoIdo(array $b, DateTimeImmutable $kezdet, ?DateTimeImmutable $elozoVege): ?DateTimeImmutable
    {
        if (!$b['jelzo'] || $b['jelzo_perc'] <= 0) {
            return null;
        }
        $jelzo = $kezdet->sub(self::mp($b['jelzo_perc'] * 60));
        if ($elozoVege !== null && $jelzo <= $elozoVege) {
            return null;
        }
        return $jelzo;
    }

    public static function csendesIdoszakok(array $b, DateTimeImmutable $nap): array
    {
        $iso = $nap->format('Y-m-d');
        $lista = [];
        foreach ($b['rendkivuli'] as $r) {
            if (!$r['aktiv'] || $r['tipus'] !== 'csend' || $r['datum'] !== $iso || !$r['ig']) {
                continue;
            }
            $k = self::idopont($nap, $r['tol']);
            $v = self::idopont($nap, $r['ig']);
            if ($v > $k) {
                $lista[] = [$k, $v, $r];
            }
        }
        usort($lista, static fn($a, $c) => $a[0] <=> $c[0]);
        return $lista;
    }

    public static function csendben(array $csendek, DateTimeImmutable $mikor): ?array
    {
        foreach ($csendek as [$k, $v, $r]) {
            if ($k <= $mikor && $mikor < $v) {
                return $r;
            }
        }
        return null;
    }

    private static function zeneCsendNelkul(array $parok, array $csendek): array
    {
        foreach ($csendek as [$kezdet, $vege]) {
            $maradek = [];
            foreach ($parok as [$indul, $leall, $szam]) {
                if ($leall <= $kezdet || $indul >= $vege) {
                    $maradek[] = [$indul, $leall, $szam];
                    continue;
                }
                if ($indul < $kezdet) {
                    $maradek[] = [$indul, $kezdet, $szam];
                }
                if ($leall > $vege) {
                    $maradek[] = [$vege, $leall, $szam];
                }
            }
            $parok = $maradek;
        }
        return array_values(array_filter($parok, static fn($p) => self::kulonbseg($p[1], $p[0]) >= 30));
    }

    private static function rendkivuliEsemenyek(array $b, DateTimeImmutable $nap): array
    {
        $iso = $nap->format('Y-m-d');
        $lista = [];
        foreach ($b['rendkivuli'] as $r) {
            if (!$r['aktiv'] || $r['datum'] !== $iso) {
                continue;
            }
            $kezdet = self::idopont($nap, $r['tol']);
            if ($r['tipus'] === 'csengetes') {
                $lista[] = new Esemeny($kezdet, Esemeny::RENDKIVULI, rendkivuli: $r);
            } elseif ($r['tipus'] === 'riado') {
                $lista[] = new Esemeny($kezdet, Esemeny::RIADO, rendkivuli: $r);
                if ($r['riado_perc'] > 0) {
                    $lista[] = new Esemeny($kezdet->add(self::mp($r['riado_perc'] * 60)), Esemeny::RIADO_VEGE, rendkivuli: $r);
                }
            }
        }
        foreach (self::csendesIdoszakok($b, $nap) as [$k, $v, $r]) {
            $lista[] = new Esemeny($k, Esemeny::CSEND, rendkivuli: $r);
            $lista[] = new Esemeny($v, Esemeny::CSEND_VEGE, rendkivuli: $r);
        }
        return $lista;
    }

    private static function zeneAblak(array $b, ?DateTimeImmutable $elozoVege, DateTimeImmutable $kovetkezo): ?array
    {
        $leall = $kovetkezo->sub(self::mp($b['zene_leall_elotte']));
        if ($elozoVege === null) {
            if (!$b['reggeli_zene']) {
                return null;
            }
            $indul = self::idopont(self::nap($kovetkezo), $b['reggeli_zene_tol']);
        } else {
            if (self::kulonbseg($kovetkezo, $elozoVege) < $b['zene_min_szunet'] * 60) {
                return null;
            }
            $indul = $elozoVege->add(self::mp($b['zene_kesleltetes']));
        }
        if (self::kulonbseg($leall, $indul) < 30) {
            return null;
        }
        return [$indul, $leall];
    }

    public static function napiEsemenyek(array $b, DateTimeImmutable $nap): array
    {
        $nap = self::nap($nap);
        $iso = $nap->format('Y-m-d');
        $csengok = [];
        $zeneParok = [];
        $rend = self::napiRend($b, $nap);
        $orak = $rend ? self::idopontok($rend, $nap) : [];
        $zeneMa = $b['zene_szunetben'] && $b['ma_nincs_zene'] !== $iso;
        $elozoVege = null;
        foreach ($orak as $i => [$kezdet, $vege]) {
            $szam = $i + 1;
            $jelzo = self::jelzoIdo($b, $kezdet, $elozoVege);
            if ($jelzo) {
                $csengok[] = new Esemeny($jelzo, Esemeny::JELZO, $szam);
            }
            $csengok[] = new Esemeny($kezdet, Esemeny::BECSENGO, $szam);
            if ($b['kicsengo']) {
                $csengok[] = new Esemeny($vege, Esemeny::KICSENGO, $szam);
            }
            if ($zeneMa && !in_array($szam - 1, $b['zene_kihagyott_szunetek'], true)) {
                $ablak = self::zeneAblak($b, $elozoVege, $jelzo ?? $kezdet);
                if ($ablak) {
                    $zeneParok[] = [$ablak[0], $ablak[1], $szam - 1];
                }
            }
            $elozoVege = $vege;
        }
        $csendek = self::csendesIdoszakok($b, $nap);
        $esemenyek = [];
        foreach ($csengok as $e) {
            $csend = self::csendben($csendek, $e->ido);
            if ($csend === null) {
                $esemenyek[] = $e;
            } elseif ($csend['csengo_hangero'] > 0) {
                $esemenyek[] = $e->halkan($csend['csengo_hangero']);
            }
        }
        foreach (self::zeneCsendNelkul($zeneParok, $csendek) as [$indul, $leall, $szam]) {
            $esemenyek[] = new Esemeny($indul, Esemeny::ZENE_INDUL, $szam);
            $esemenyek[] = new Esemeny($leall, Esemeny::ZENE_LEALL, $szam);
        }
        array_push($esemenyek, ...self::rendkivuliEsemenyek($b, $nap));
        $szunnap = self::szunnapNev($b, $nap) !== null;
        foreach ($b['bemondasok'] as $bem) {
            if (!$bem['aktiv']) {
                continue;
            }
            if ($bem['datum']) {
                if ($bem['datum'] !== $iso) {
                    continue;
                }
            } elseif (!in_array(self::het($nap), $bem['napok'], true) || $szunnap) {
                continue;
            }
            $mikor = self::idopont($nap, $bem['ido']);
            if (self::csendben($csendek, $mikor) === null) {
                $esemenyek[] = new Esemeny($mikor, Esemeny::BEMONDAS, bemondas: $bem);
            }
        }
        usort($esemenyek, static fn(Esemeny $a, Esemeny $c) => $a->ido <=> $c->ido ?: $a->sorrend() <=> $c->sorrend());
        return $esemenyek;
    }

    public static function zeneSzunet(array $b, DateTimeImmutable $most): ?int
    {
        $szunet = null;
        foreach (self::napiEsemenyek($b, $most) as $e) {
            if ($e->ido > $most) {
                break;
            }
            if ($e->tipus === Esemeny::ZENE_INDUL) {
                $szunet = $e->ora;
            } elseif ($e->tipus === Esemeny::ZENE_LEALL) {
                $szunet = null;
            }
        }
        return $szunet;
    }

    public static function zeneAblakban(array $b, DateTimeImmutable $most): bool
    {
        return self::zeneSzunet($b, $most) !== null;
    }

    public static function musorblokk(array $b, int $nap, int $szunet): ?array
    {
        $forrasok = [];
        foreach ($b['forrasok'] as $f) {
            if ($f['aktiv']) {
                $forrasok[$f['nev']] = true;
            }
        }
        foreach ($b['musorblokkok'] as $m) {
            if ($m['aktiv'] && isset($forrasok[$m['forras']]) && in_array($nap, $m['napok'], true)
                && (!$m['szunetek'] || in_array($szunet, $m['szunetek'], true))) {
                return $m;
            }
        }
        return null;
    }

    public static function szunetNev(int $szunet): string
    {
        return $szunet === 0 ? 'Tanítás előtt' : "{$szunet}. szünet";
    }

    public static function kovetkezoEsemeny(array $b, DateTimeImmutable $most, bool $csakCsengo = true, int $napok = 14): ?Esemeny
    {
        $nap = self::nap($most);
        for ($i = 0; $i < $napok; $i++) {
            foreach (self::napiEsemenyek($b, $nap->add(new DateInterval("P{$i}D"))) as $e) {
                if ($e->ido > $most && (!$csakCsengo || $e->csengo())) {
                    return $e;
                }
            }
        }
        return null;
    }

    public static function napSzoveg(DateTimeImmutable $ido, DateTimeImmutable $most): string
    {
        $kulonbseg = (int)self::nap($most)->diff(self::nap($ido))->format('%r%a');
        return match (true) {
            $kulonbseg === 0 => 'ma',
            $kulonbseg === 1 => 'holnap',
            $kulonbseg > 1 && $kulonbseg < 7 => self::NAP_RAGOS[self::het($ido)],
            default => $ido->format('m. d.'),
        };
    }

    public static function allapot(array $b, DateTimeImmutable $most): array
    {
        $a = self::nyersAllapot($b, $most);
        $csend = self::csendben(self::csendesIdoszakok($b, self::nap($most)), $most);
        $a['csend'] = $csend['nev'] ?? '';
        return $a;
    }

    private static function nyersAllapot(array $b, DateTimeImmutable $most): array
    {
        $nap = self::nap($most);
        $alap = ['szakasz' => self::SZ_NINCS, 'ora' => 0, 'kezdet' => null, 'vege' => null,
            'kovetkezo' => self::kovetkezoEsemeny($b, $most), 'szunnap_nev' => '', 'csend' => ''];
        $rend = self::napiRend($b, $nap);
        if ($rend === null) {
            $nev = self::szunnapNev($b, $nap);
            if ($nev !== null && !isset($b['kivetelek'][$nap->format('Y-m-d')])) {
                return ['szakasz' => self::SZ_SZUNNAP, 'szunnap_nev' => $nev] + $alap;
            }
            return $alap;
        }
        $orak = self::idopontok($rend, $nap);
        if (!$orak) {
            return $alap;
        }
        if ($most < $orak[0][0]) {
            return ['szakasz' => self::SZ_REGGEL, 'vege' => $orak[0][0]] + $alap;
        }
        foreach ($orak as $i => [$kezdet, $vege]) {
            $szam = $i + 1;
            if ($kezdet <= $most && $most < $vege) {
                return ['szakasz' => self::SZ_ORA, 'ora' => $szam, 'kezdet' => $kezdet, 'vege' => $vege] + $alap;
            }
            if ($szam < count($orak) && $vege <= $most && $most < $orak[$szam][0]) {
                return ['szakasz' => self::SZ_SZUNET, 'ora' => $szam, 'kezdet' => $vege, 'vege' => $orak[$szam][0]] + $alap;
            }
        }
        return ['szakasz' => self::SZ_VEGE] + $alap;
    }

    public static function allapotCim(array $a): string
    {
        return match ($a['szakasz']) {
            self::SZ_ORA => "{$a['ora']}. óra",
            self::SZ_SZUNET => "Szünet ({$a['ora']}. óra után)",
            self::SZ_SZUNNAP => $a['szunnap_nev'] ?: 'Szünnap',
            default => mb_strtoupper(mb_substr($a['szakasz'], 0, 1)) . mb_substr($a['szakasz'], 1),
        };
    }

    public static function hatralevo(array $a, DateTimeImmutable $most): ?int
    {
        return $a['vege'] === null ? null : max(0, self::kulonbseg($a['vege'], $most));
    }

    public static function rendGeneralas(string $elso, int $darab, int $oraHossz, int $szunet, int $nagyszunetUtan = 3, int $nagyszunet = 15): array
    {
        $kezdet = self::idopont(new DateTimeImmutable('today'), $elso);
        $lista = [];
        for ($szam = 1; $szam <= $darab; $szam++) {
            $vege = $kezdet->add(self::mp($oraHossz * 60));
            $lista[] = [$kezdet->format('H:i'), $vege->format('H:i')];
            $kezdet = $vege->add(self::mp(($szam === $nagyszunetUtan ? $nagyszunet : $szunet) * 60));
        }
        return $lista;
    }
}
