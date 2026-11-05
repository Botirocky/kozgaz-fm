<?php

declare(strict_types=1);

namespace KozgazFM;

final class Dalszoveg
{
    public const API = 'https://lrclib.net/api/search';
    private const IDOKORLAT_MP = 10;
    private const PROBALKOZAS = 3;
    private const HOSSZ_TURES_MP = 25;
    public const NINCS_MEGORZES_MP = 14 * 24 * 3600;

    private const ZAROJEL = '/(*UCP)\([^)]*\)|\[[^\]]*\]|\{[^}]*\}|【[^】]*】/u';
    private const VENDEG = '/(*UCP)\b(?:ft|feat|featuring)\b\.?.*$/iu';
    private const ZAJ = '/(*UCP)\b(?:official(?: music| lyric)?(?: video| audio)?|music video|lyric video|lyrics?|videoklip|klip|hd|hq|4k|remaster(?:ed)?)\b\.?\s*$/iu';
    private const ELSZAM = '/(*UCP)^\s*\d{1,3}\s*[.)_-]+\s*/u';
    private const ELVALASZTO = '/(*UCP)\s+[-–—:|]\s+/u';

    public static function cimBontas(string $cim): array
    {
        $tiszta = (string)preg_replace(self::ELSZAM, '', (string)preg_replace(self::ZAROJEL, ' ', $cim));
        $tiszta = explode(' | ', $tiszta)[0];
        $reszek = [];
        foreach (preg_split(self::ELVALASZTO, $tiszta) ?: [] as $r) {
            $r = (string)preg_replace(self::ZAJ, ' ', (string)preg_replace(self::VENDEG, '', $r));
            $r = (string)preg_replace('/^[ \-–—_.,]+|[ \-–—_.,]+$/u', '', $r);
            if ($r !== '') {
                $reszek[] = $r;
            }
        }
        $egy = static fn(string $s) => implode(' ', preg_split('/\s+/u', trim($s), -1, PREG_SPLIT_NO_EMPTY) ?: []);
        if (count($reszek) >= 2) {
            return [$egy($reszek[0]), $egy($reszek[count($reszek) - 1])];
        }
        return ['', $reszek ? $egy($reszek[0]) : ''];
    }

    public static function szotar(string $szoveg): array
    {
        preg_match_all('/(*UCP)\w+/u', Szuro::egyszerusit($szoveg), $t);
        return array_fill_keys($t[0], true);
    }

    public static function kulcs(string $cim): string
    {
        [$eloado, $szam] = self::cimBontas($cim);
        $resz = static function (string $r): string {
            preg_match_all('/(*UCP)\w+/u', Szuro::egyszerusit($r), $t);
            return implode(' ', $t[0]);
        };
        return $resz($eloado) . ' | ' . $resz($szam);
    }

    private static function lekeres(array $parameterek): array
    {
        $url = self::API . '?' . http_build_query($parameterek);
        for ($p = 0; $p < self::PROBALKOZAS; $p++) {
            [$kod, $torzs, $hiba] = Http::keres('GET', $url, null, ['User-Agent: KozgazFM/' . KFM_VERZIO], self::IDOKORLAT_MP);
            if ($kod === 200) {
                $adat = json_decode($torzs, true);
                if (!is_array($adat) || !array_is_list($adat)) {
                    throw new Hiba('A dalszöveg-szolgáltatás érvénytelen választ adott.');
                }
                return $adat;
            }
            if ($kod >= 400 && $kod < 500 && $kod !== 429) {
                throw new Hiba("A dalszöveg-szolgáltatás hibája: {$kod}");
            }
            if ($p === self::PROBALKOZAS - 1) {
                throw new Hiba('A dalszöveg-szolgáltatás nem érhető el: ' . ($hiba ?: $kod));
            }
            usleep((int)(1.5 * ($p + 1) * 1e6));
        }
        return [];
    }

    private static function illik(array $j, array $cimSzavak, array $keresett, int $hossz): bool
    {
        $cim = self::szotar((string)($j['trackName'] ?? ''));
        $eloado = self::szotar((string)($j['artistName'] ?? ''));
        if (!$cim || array_diff_key($cim, $cimSzavak) || !array_intersect_key($eloado, $keresett)) {
            return false;
        }
        $tartam = $j['duration'] ?? null;
        return !($hossz && is_numeric($tartam) && abs((float)$tartam - $hossz) > self::HOSSZ_TURES_MP);
    }

    private static function legrosszabb(array $jeloltek, array $cimSzavak, array $keresett, int $hossz): ?array
    {
        $illok = array_values(array_filter($jeloltek, fn($j) => is_array($j) && self::illik($j, $cimSzavak, $keresett, $hossz)));
        $szoveges = array_values(array_filter($illok, static fn($j) => !empty($j['plainLyrics'])));
        if ($szoveges) {
            $legrosszabb = null;
            foreach ($szoveges as $j) {
                $e = Szuro::ertekel((string)$j['plainLyrics']);
                if ($legrosszabb === null || Szuro::pont($e) > Szuro::pont($legrosszabb)) {
                    $legrosszabb = $e;
                }
            }
            return ['talalt' => true, 'ertekeles' => $legrosszabb, 'instrumental' => false];
        }
        foreach ($illok as $j) {
            if (!empty($j['instrumental'])) {
                return ['talalt' => true, 'ertekeles' => ['szavak' => 0, 'eros' => 0, 'kozepes' => 0, 'enyhe' => 0], 'instrumental' => true];
            }
        }
        return null;
    }

    public static function vizsgal(string $cim, int $hossz = 0, string $tobblet = ''): array
    {
        [$eloado, $szam] = self::cimBontas($cim);
        $cimSzavak = self::szotar("{$eloado} {$szam}");
        $keresett = $cimSzavak + self::szotar($tobblet);
        $ures = ['talalt' => false, 'ertekeles' => ['szavak' => 0, 'eros' => 0, 'kozepes' => 0, 'enyhe' => 0], 'instrumental' => false];
        if ($szam === '') {
            return $ures;
        }
        $kerdesek = [];
        if ($eloado !== '') {
            $kerdesek[] = ['track_name' => $szam, 'artist_name' => $eloado];
        }
        $kerdesek[] = ['q' => trim(preg_replace('/\s+/u', ' ', "{$eloado} {$szam}"))];
        if ($tobblet !== '') {
            $kerdesek[] = ['q' => trim(preg_replace('/\s+/u', ' ', $tobblet))];
        }
        foreach ($kerdesek as $k) {
            $e = self::legrosszabb(self::lekeres($k), $cimSzavak, $keresett, $hossz);
            if ($e !== null) {
                return $e;
            }
        }
        return $ures;
    }

    private static function tarFajl(): string
    {
        return Utvonalak::gyorsitotar() . '/dalszoveg.json';
    }

    public static function tarKeres(string $cim): ?array
    {
        $adat = json_decode((string)@file_get_contents(self::tarFajl()), true);
        $e = is_array($adat) ? ($adat[self::kulcs($cim)] ?? null) : null;
        if (!is_array($e)) {
            return null;
        }
        if (empty($e['t'])) {
            return time() - (float)($e['i'] ?? 0) < self::NINCS_MEGORZES_MP
                ? ['talalt' => false, 'ertekeles' => ['szavak' => 0, 'eros' => 0, 'kozepes' => 0, 'enyhe' => 0], 'instrumental' => false]
                : null;
        }
        return ['talalt' => true, 'ertekeles' => $e['e'], 'instrumental' => !empty($e['n'])];
    }

    public static function tarBeir(string $cim, array $eredmeny): void
    {
        $fajl = self::tarFajl();
        $f = fopen($fajl . '.zar', 'c');
        flock($f, LOCK_EX);
        $adat = json_decode((string)@file_get_contents($fajl), true);
        $adat = is_array($adat) ? $adat : [];
        $adat[self::kulcs($cim)] = ['t' => $eredmeny['talalt'], 'e' => $eredmeny['ertekeles'], 'n' => $eredmeny['instrumental'], 'i' => time()];
        file_put_contents($fajl . '.tmp', json_encode($adat, JSON_UNESCAPED_UNICODE));
        rename($fajl . '.tmp', $fajl);
        flock($f, LOCK_UN);
        fclose($f);
    }

    public static function tragar(?array $eredmeny, string $erzekenyseg): bool
    {
        return $eredmeny !== null && $eredmeny['talalt'] && Szuro::tragar($eredmeny['ertekeles'], $erzekenyseg);
    }
}
