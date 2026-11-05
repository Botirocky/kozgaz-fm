<?php

declare(strict_types=1);

namespace KozgazFM;

final class Szuro
{
    public const KORHATAR = 18;

    public const ALAP_SZAVAK = [
        'explicit', 'fuck*', 'motherfuck*', 'shit', 'shitty', 'bitch*', 'nigga*',
        'kurva*', 'geci*', 'fasz', 'faszom', 'faszt', 'faszfej*', 'faszkalap*', 'faszság*',
        'bazd*', 'baszd*', 'baszo*', 'baszt*', 'baszni', 'baszik', 'baszott', 'kibasz*', 'elbasz*', 'megbasz*',
        'picsa*', 'pöcs', 'pöcsfej*', 'segg*', 'ribanc*', 'köcsög*', 'buzi*', 'szar', 'szaros', 'szarság*',
    ];

    private const EROS = [
        'fuck*', 'fuk', 'fuks', 'fucc*', 'motherfuck*', 'mothafuck*', 'muthafuck*', 'cunt*', 'nigger*', 'faggot*',
        'kurva*', 'kurvá*', 'geci*', 'fasz*', 'basz*', 'bazd*', 'bazm*', 'kibasz*', 'elbasz*', 'megbasz*', 'lebasz*',
        'felbasz*', 'rabasz*', 'szetbasz*', 'buzi*',
    ];
    private const KOZEPES = [
        'shit*', 'bullshit*', 'bitch*', 'biatch*', 'asshole*', 'pussy', 'pussies', 'dick', 'dicks', 'dickhead*', 'cock',
        'cocks', 'cocksuck*', 'whore*', 'slut*', 'nigga*', 'fag', 'fags', 'ribanc*', 'kocsog*', 'picsa*', 'picsat',
        'picsad*', 'pina', 'pinat', 'pinad', 'pinaja*', 'pocs', 'pocsom', 'pocsod', 'pocsfej*', 'seggfej*', 'szopd*',
        'szopj*', 'szopo*', 'lofasz*',
    ];
    private const ENYHE = [
        'damn', 'goddamn', 'ass', 'asses', 'bastard*', 'crap', 'hoe', 'hoes', 'szar', 'szart', 'szaros*', 'szarsag*',
        'szarni', 'szarik', 'szarok', 'segg', 'seggem', 'segged', 'segget', 'seggbe', 'fasza',
    ];
    private const KIVETELEK = ['baszk*', 'faszin*', 'fasza', 'fasziz*', 'shitake*'];

    public const SULY_EROS = 5;
    public const SULY_KOZEPES = 3;
    public const SULY_ENYHE = 1;
    public const MIN_SZAVAK = 100;

    public const ERZEKENYSEGEK = ['szigoru' => 'Szigorú', 'normal' => 'Normál', 'laza' => 'Laza'];
    public const HATAROK = ['szigoru' => [2, 3.0], 'normal' => [5, 5.0], 'laza' => [15, 20.0]];

    private const ROVIDITETT = ['0' => 'o', '1' => 'i', '3' => 'e', '4' => 'a', '5' => 's', '7' => 't', '@' => 'a', '$' => 's', '!' => 'i'];
    private const SZO = '/(*UCP)[\w@$*#]+(?:!+[\w@$*#]+)*/u';

    private static ?array $minták = null;
    private static ?array $tovek = null;

    public readonly array $szavak;
    public readonly bool $alap;
    private ?string $re;

    public function __construct(array $szavak = [], bool $alap = true)
    {
        $this->szavak = array_values(array_filter(array_map('trim', $szavak), static fn($s) => $s !== ''));
        $this->alap = $alap;
        $mintak = array_filter(array_map([self::class, 'minta'], array_merge($this->szavak, $alap ? self::ALAP_SZAVAK : [])));
        $this->re = $mintak ? '/(*UCP)(?:' . implode('|', $mintak) . ')/u' : null;
    }

    public function kulcs(): string
    {
        return json_encode([$this->szavak, $this->alap], JSON_UNESCAPED_UNICODE);
    }

    public function van(): bool
    {
        return $this->re !== null;
    }

    public static function egyszerusit(string $szoveg): string
    {
        $bontott = \Normalizer::normalize($szoveg, \Normalizer::FORM_KD);
        if ($bontott === false) {
            $bontott = $szoveg;
        }
        $bontott = (string)preg_replace('/\p{Mn}/u', '', $bontott);
        return mb_strtolower($bontott);
    }

    private static function szolistaRe(array $szavak): string
    {
        $reszek = [];
        foreach ($szavak as $szo) {
            $szo = self::egyszerusit($szo);
            $reszek[] = str_ends_with($szo, '*') ? preg_quote(substr($szo, 0, -1), '/') . '\w*' : preg_quote($szo, '/');
        }
        return '(?:' . implode('|', $reszek) . ')';
    }

    private static function mintak(): array
    {
        if (self::$minták === null) {
            self::$minták = [
                'eros' => '/(*UCP)^' . self::szolistaRe(self::EROS) . '\\z/u',
                'kozepes' => '/(*UCP)^' . self::szolistaRe(self::KOZEPES) . '\\z/u',
                'enyhe' => '/(*UCP)^' . self::szolistaRe(self::ENYHE) . '\\z/u',
                'kivetel' => '/(*UCP)^' . self::szolistaRe(self::KIVETELEK) . '\\z/u',
            ];
            $tovek = [];
            foreach (array_merge(self::EROS, self::KOZEPES, self::ENYHE) as $s) {
                $tovek[rtrim(self::egyszerusit($s), '*')] = true;
            }
            self::$tovek = array_keys($tovek);
        }
        return self::$minták;
    }

    private static function fullmatch(string $minta, string $szo): bool
    {
        return preg_match($minta, $szo) === 1;
    }

    private static function cenzurazott(string $szo): string
    {
        self::mintak();
        $hossz = mb_strlen($szo);
        $elso = mb_substr($szo, 0, 1);
        if ($hossz < 3 || !preg_match('/^\p{L}$/u', $elso)) {
            return $szo;
        }
        $minta = '';
        foreach (mb_str_split($szo) as $c) {
            $minta .= str_contains('*#_', $c) ? '.' : preg_quote($c, '/');
        }
        foreach (self::$tovek as $t) {
            if (mb_strlen($t) >= $hossz && preg_match('/^' . $minta . '\z/u', mb_substr($t, 0, $hossz))) {
                return $t;
            }
        }
        return str_replace('_', '', $szo);
    }

    private static function nyersSzavak(string $szoveg): array
    {
        preg_match_all(self::SZO, self::egyszerusit($szoveg), $t);
        return array_values(array_filter($t[0], static fn($s) => preg_match('/\p{L}/u', $s) === 1));
    }

    public static function szavakKibontva(string $szoveg): array
    {
        $lista = [];
        foreach (self::nyersSzavak($szoveg) as $nyers) {
            $szo = preg_match('/^\p{L}+$/u', $nyers) ? $nyers : strtr($nyers, self::ROVIDITETT);
            if (strpbrk($szo, '*#_') !== false) {
                $szo = self::cenzurazott($szo);
            }
            $lista[] = (string)preg_replace('/(.)\1{2,}/u', '$1', $szo);
        }
        return $lista;
    }

    private static function fokozat(string $szo): int
    {
        $m = self::mintak();
        $enyhe = self::fullmatch($m['enyhe'], $szo);
        if (self::fullmatch($m['kivetel'], $szo) && !$enyhe) {
            return 0;
        }
        if (self::fullmatch($m['eros'], $szo) && !$enyhe) {
            return self::SULY_EROS;
        }
        if (self::fullmatch($m['kozepes'], $szo)) {
            return self::SULY_KOZEPES;
        }
        return $enyhe ? self::SULY_ENYHE : 0;
    }

    public static function ertekel(string $szoveg): array
    {
        $szavak = self::szavakKibontva($szoveg);
        $db = [self::SULY_EROS => 0, self::SULY_KOZEPES => 0, self::SULY_ENYHE => 0, 0 => 0];
        foreach ($szavak as $szo) {
            $db[self::fokozat($szo)]++;
        }
        return ['szavak' => count($szavak), 'eros' => $db[self::SULY_EROS], 'kozepes' => $db[self::SULY_KOZEPES],
            'enyhe' => $db[self::SULY_ENYHE]];
    }

    public static function pont(array $e): int
    {
        return $e['eros'] * self::SULY_EROS + $e['kozepes'] * self::SULY_KOZEPES + $e['enyhe'] * self::SULY_ENYHE;
    }

    public static function suruseg(array $e): float
    {
        return self::pont($e) * 100 / max($e['szavak'], self::MIN_SZAVAK);
    }

    public static function tragar(array $e, string $erzekenyseg = 'normal'): bool
    {
        [$maxEros, $maxSuruseg] = self::HATAROK[$erzekenyseg] ?? self::HATAROK['normal'];
        return $e['eros'] >= $maxEros || self::suruseg($e) >= $maxSuruseg;
    }

    public static function ertekelesSzoveg(array $e): string
    {
        return sprintf('%d erős, %d közepes, %d enyhe szó %d szóból (%.1f pont/100 szó)',
            $e['eros'], $e['kozepes'], $e['enyhe'], $e['szavak'], self::suruseg($e));
    }

    private static function minta(string $szo): ?string
    {
        $szo = self::egyszerusit(implode(' ', preg_split('/\s+/u', trim($szo)) ?: []));
        $elotag = str_ends_with($szo, '*');
        $szo = trim(rtrim($szo, '*'));
        if ($szo === '') {
            return null;
        }
        return '(?<!\w)' . preg_quote($szo, '/') . ($elotag ? '' : '(?!\w)');
    }

    public function talalat(string ...$szovegek): ?string
    {
        if ($this->re === null) {
            return null;
        }
        foreach ($szovegek as $szoveg) {
            if ($szoveg === '') {
                continue;
            }
            if (preg_match($this->re, self::egyszerusit($szoveg), $m)) {
                return $m[0];
            }
            $kibontott = self::szavakKibontva($szoveg);
            if ($kibontott !== self::nyersSzavak($szoveg) && preg_match($this->re, implode(' ', $kibontott), $m)) {
                return $m[0];
            }
        }
        return null;
    }
}
