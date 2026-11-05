<?php

declare(strict_types=1);

namespace KozgazFM;

use DateInterval;
use DateTimeImmutable;
use DateTimeZone;

final class NaptarImport
{
    public const MAX_MERET = 2000000;
    public const MAX_ESEMENY = 3000;
    public const MAX_HOSSZ_NAP = 120;
    public const SZUNNAP = 'szunnap';
    public const ROVIDITETT = 'rovidített';
    public const TANITASI_NAP = 'tanitasi_nap';
    public const KIHAGY = 'kihagy';
    public const MUVELET_NEV = [
        self::SZUNNAP => 'szünnap (nincs csengetés)',
        self::ROVIDITETT => 'rövidített órák',
        self::TANITASI_NAP => 'tanítási nap (van csengetés)',
        self::KIHAGY => 'nem érinti a csengetést',
    ];
    private const SZUNNAP_MINTA = '/tanítás\s*nélküli|tanitas\s*nelkuli|tanításmentes|tanitasmentes|szünet|szunet|szünidő|munkaszüneti|pihenőnap|ünnepnap|ünnep(?![a-záéíóöőúüű])|igazgatói\s*nap/iu';
    private const ROVID_MINTA = '/rövidített|rovidített|rovidítet|rövid\s+órá/iu';
    private const MUNKANAP_MINTA = '/munkanap|tanítási\s*nap|tanitasi\s*nap/iu';
    private const TANITASI_JELZO = '/(utolsó|első|utolso|elso)\s+tanítási|szünet\s+(előtti|utáni)|szunet\s+(elotti|utani)/iu';
    private const NELKULI = '/nélküli|nelkuli/iu';

    public static function esemeny(string $nev, DateTimeImmutable $tol, DateTimeImmutable $ig): array
    {
        return ['nev' => $nev, 'tol' => $tol->format('Y-m-d'), 'ig' => $ig->format('Y-m-d')];
    }

    private static function kibont(string $szoveg): array
    {
        $darabok = [];
        foreach (explode("\n", str_replace(["\r\n", "\r"], "\n", $szoveg)) as $sor) {
            if ($sor !== '' && ($sor[0] === ' ' || $sor[0] === "\t") && $darabok) {
                $darabok[count($darabok) - 1] .= substr($sor, 1);
            } else {
                $darabok[] = $sor;
            }
        }
        return $darabok;
    }

    private static function szoveg(string $ertek): string
    {
        return trim((string)preg_replace_callback('/\\\\([\\\\;,nN])/', static fn($m) => in_array($m[1], ['n', 'N'], true) ? "\n" : $m[1], $ertek));
    }

    private static function datum(string $parameterek, string $ertek): array
    {
        $ertek = trim($ertek);
        $tipus = strtoupper($parameterek);
        if ((str_contains($tipus, 'VALUE=DATE') && !str_contains($tipus, 'VALUE=DATE-TIME')) || strlen($ertek) === 8) {
            $d = DateTimeImmutable::createFromFormat('!Ymd', substr($ertek, 0, 8));
            if (!$d) {
                throw new \ValueError('rossz dátum');
            }
            return [$d, true];
        }
        $alap = DateTimeImmutable::createFromFormat('Ymd\THis', substr($ertek, 0, 15), str_ends_with($ertek, 'Z') ? new DateTimeZone('UTC') : null);
        if (!$alap) {
            throw new \ValueError('rossz időpont');
        }
        $alap = $alap->setTimezone(new DateTimeZone(date_default_timezone_get()));
        return [$alap->setTime(0, 0), $alap->format('Hi') === '0000'];
    }

    public static function icsBeolvas(string $szoveg): array
    {
        if (!str_contains(strtoupper($szoveg), 'BEGIN:VCALENDAR')) {
            throw new Hiba('Ez nem iCalendar (.ics) naptár.', 'validation_error', 422);
        }
        $esemenyek = [];
        $akt = null;
        foreach (self::kibont($szoveg) as $sor) {
            $felso = strtoupper($sor);
            if ($felso === 'BEGIN:VEVENT') {
                $akt = [];
                continue;
            }
            if ($felso === 'END:VEVENT') {
                if ($akt !== null && ($e = self::icsEsemeny($akt)) !== null) {
                    $esemenyek[] = $e;
                    if (count($esemenyek) > self::MAX_ESEMENY) {
                        throw new Hiba('Túl sok esemény van a naptárban.', 'validation_error', 422);
                    }
                }
                $akt = null;
                continue;
            }
            if ($akt === null || !str_contains($sor, ':')) {
                continue;
            }
            [$fej, $ertek] = explode(':', $sor, 2);
            $reszek = explode(';', $fej, 2);
            $nev = strtoupper($reszek[0]);
            $akt[$nev] ??= [$reszek[1] ?? '', $ertek];
        }
        usort($esemenyek, static fn($a, $b) => [$a['tol'], $a['ig'], $a['nev']] <=> [$b['tol'], $b['ig'], $b['nev']]);
        return $esemenyek;
    }

    private static function icsEsemeny(array $akt): ?array
    {
        if (!isset($akt['DTSTART']) || strtoupper(trim($akt['STATUS'][1] ?? '')) === 'CANCELLED') {
            return null;
        }
        try {
            [$tol, $egesz] = self::datum(...$akt['DTSTART']);
            if (isset($akt['DTEND'])) {
                [$ig, $ejfel] = self::datum(...$akt['DTEND']);
                if (($egesz || $ejfel) && $ig > $tol) {
                    $ig = $ig->sub(new DateInterval('P1D'));
                }
            } else {
                $ig = $tol;
            }
        } catch (\ValueError) {
            return null;
        }
        if ($ig < $tol) {
            $ig = $tol;
        }
        if ((int)$tol->diff($ig)->format('%a') > self::MAX_HOSSZ_NAP) {
            return null;
        }
        $nev = mb_substr(self::szoveg($akt['SUMMARY'][1] ?? ''), 0, 120) ?: 'Névtelen esemény';
        return self::esemeny($nev, $tol, $ig);
    }

    public static function rovidRend(array $b): ?string
    {
        foreach ($b['rendek'] as $r) {
            $kis = mb_strtolower($r['nev']);
            if (str_contains($kis, 'rövid') || str_contains($kis, 'rovid')) {
                return $r['nev'];
            }
        }
        return null;
    }

    public static function alapRend(array $b): ?string
    {
        foreach (array_slice($b['het'], 0, 5) as $n) {
            if ($n !== '' && Beallitasok::rend($b, $n)) {
                return $n;
            }
        }
        return $b['rendek'][0]['nev'] ?? null;
    }

    public static function napok(array $e): array
    {
        $lista = [];
        for ($n = new DateTimeImmutable($e['tol']); $n <= new DateTimeImmutable($e['ig']); $n = $n->add(new DateInterval('P1D'))) {
            $lista[] = $n;
        }
        return $lista;
    }

    public static function besorol(array $e, array $b): array
    {
        if (preg_match(self::TANITASI_JELZO, $e['nev']) && !preg_match(self::NELKULI, $e['nev'])) {
            return ['esemeny' => $e, 'muvelet' => self::KIHAGY, 'megjegyzes' => 'tanítási nap'];
        }
        if (preg_match(self::SZUNNAP_MINTA, $e['nev'])) {
            return ['esemeny' => $e, 'muvelet' => self::SZUNNAP, 'megjegyzes' => ''];
        }
        if (preg_match(self::ROVID_MINTA, $e['nev'])) {
            $rend = self::rovidRend($b);
            return $rend ? ['esemeny' => $e, 'muvelet' => self::ROVIDITETT, 'megjegyzes' => $rend]
                : ['esemeny' => $e, 'muvelet' => self::KIHAGY, 'megjegyzes' => 'nincs „Rövidített” nevű csengetési rend'];
        }
        $hetvege = false;
        foreach (self::napok($e) as $n) {
            if ((int)$n->format('N') >= 6) {
                $hetvege = true;
            }
        }
        if (preg_match(self::MUNKANAP_MINTA, $e['nev']) && $hetvege) {
            $rend = self::alapRend($b);
            return $rend ? ['esemeny' => $e, 'muvelet' => self::TANITASI_NAP, 'megjegyzes' => $rend]
                : ['esemeny' => $e, 'muvelet' => self::KIHAGY, 'megjegyzes' => 'nincs csengetési rend'];
        }
        return ['esemeny' => $e, 'muvelet' => self::KIHAGY, 'megjegyzes' => 'rendezvény'];
    }

    public static function javaslatok(array $esemenyek, array $b, ?string $tol = null): array
    {
        $tol ??= (new DateTimeImmutable('yesterday'))->format('Y-m-d');
        return array_values(array_map(static fn($e) => self::besorol($e, $b), array_filter($esemenyek, static fn($e) => $e['ig'] >= $tol)));
    }

    public static function alkalmaz(array $b, array $kivalasztott): array
    {
        $meglevo = [];
        foreach ($b['szunnapok'] as $s) {
            $meglevo[$s['tol'] . '|' . $s['ig']] = true;
        }
        $ujSzunnap = $ujKivetel = $megtartott = 0;
        foreach ($kivalasztott as $j) {
            $e = $j['esemeny'];
            if ($j['muvelet'] === self::SZUNNAP) {
                $kulcs = $e['tol'] . '|' . $e['ig'];
                if (!isset($meglevo[$kulcs])) {
                    $b['szunnapok'][] = ['tol' => $e['tol'], 'ig' => $e['ig'], 'nev' => $e['nev']];
                    $meglevo[$kulcs] = true;
                    $ujSzunnap++;
                }
            } elseif (in_array($j['muvelet'], [self::ROVIDITETT, self::TANITASI_NAP], true) && $j['megjegyzes'] && Beallitasok::rend($b, $j['megjegyzes'])) {
                foreach (self::napok($e) as $nap) {
                    $kulcs = $nap->format('Y-m-d');
                    if ($j['muvelet'] === self::ROVIDITETT && (int)$nap->format('N') >= 6) {
                        continue;
                    }
                    if (isset($b['kivetelek'][$kulcs])) {
                        $megtartott += (int)($b['kivetelek'][$kulcs] !== $j['megjegyzes']);
                        continue;
                    }
                    $b['kivetelek'][$kulcs] = $j['megjegyzes'];
                    $ujKivetel++;
                }
            }
        }
        usort($b['szunnapok'], static fn($a, $c) => strcmp($a['tol'], $c['tol']));
        return [$b, $ujSzunnap, $ujKivetel, $megtartott];
    }

    public static function letoltes(string $cim): string
    {
        $cim = trim($cim);
        if (str_starts_with(strtolower($cim), 'webcal://')) {
            $cim = 'https://' . substr($cim, 9);
        }
        $r = parse_url($cim);
        if (!is_array($r) || !in_array($r['scheme'] ?? '', ['http', 'https'], true) || empty($r['host'])) {
            throw new Hiba('Csak http(s):// vagy webcal:// naptárlink adható meg.', 'validation_error', 422);
        }
        [$kod, $adat, $hiba] = Http::keres('GET', $cim, null, ['User-Agent: KozgazFM', 'Accept: text/calendar, */*'], 15, self::MAX_MERET);
        if ($kod !== 200) {
            throw new Hiba('A naptár nem tölthető le: ' . ($hiba ?: "HTTP {$kod}"));
        }
        return mb_convert_encoding($adat, 'UTF-8', 'UTF-8');
    }
}
