<?php

declare(strict_types=1);

namespace KozgazFM;

use DateTimeImmutable;

final class Zenekeres
{
    public const MAX_SZOVEG = 150;
    public const MAX_NEV = 30;
    public const MAX_VARAKOZO = 40;
    public const IP_ORANKENT = 20;
    public const AUTO_MAX_SOR = 10;
    public const TELEFON_TILTAS_NAP = 7;
    public const MEGORZES_MP = 12 * 3600;
    public const YOUTUBE_GAZDAK = ['youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com', 'youtu.be'];

    public const ALLAPOT_NEVEK = [
        'kereses' => 'Keresés és ellenőrzés…',
        'varakozik' => 'Jóváhagyásra vár',
        'elfogadva' => 'Elfogadva, hamarosan szól',
        'szol' => 'Most szól',
        'elutasitva' => 'Elutasítva',
        'levett' => 'Levették a sorból',
    ];

    public array $lista = [];

    public function __construct(private readonly ?\Closure $ido = null)
    {
    }

    private function most(): DateTimeImmutable
    {
        return $this->ido ? ($this->ido)() : new DateTimeImmutable();
    }

    public static function nyilvanos(array $k): array
    {
        return ['azon' => $k['azon'], 'szoveg' => $k['szoveg'], 'cim' => $k['cim'], 'allapot' => $k['allapot'],
            'allapot_nev' => self::ALLAPOT_NEVEK[$k['allapot']] ?? $k['allapot'], 'ok' => $k['ok'],
            'ido' => substr($k['ido'], 11, 5)];
    }

    public static function admin(array $k): array
    {
        return self::nyilvanos($k) + ['nev' => $k['nev'], 'hossz' => $k['hossz'], 'ip' => $k['ip'],
            'megjegyzes' => $k['megjegyzes'], 'yt_van' => $k['yt'] !== '',
            'link' => $k['yt'] !== '' ? 'https://www.youtube.com/watch?v=' . $k['yt'] : ''];
    }

    public static function telefonKulcs(string $eszkoz): string
    {
        return substr(hash('sha256', $eszkoz), 0, 32);
    }

    public static function youtubeCel(string $szoveg): string
    {
        $szoveg = trim($szoveg);
        $kis = mb_strtolower($szoveg);
        $gazdaval = false;
        foreach (self::YOUTUBE_GAZDAK as $g) {
            if (str_starts_with($kis, $g)) {
                $gazdaval = true;
            }
        }
        if (!str_contains($szoveg, '://') && !$gazdaval) {
            return 'ytsearch1:' . $szoveg;
        }
        $cim = str_contains($szoveg, '://') ? $szoveg : 'https://' . $szoveg;
        $r = parse_url($cim);
        if (!is_array($r) || !in_array($r['scheme'] ?? '', ['http', 'https'], true)
            || !in_array(strtolower($r['host'] ?? ''), self::YOUTUBE_GAZDAK, true)) {
            throw new Hiba('Csak YouTube-link vagy a szám címe adható meg.', 'bad_link', 422);
        }
        return $cim;
    }

    public static function tiltottE(string $szoveg, array $tiltott): bool
    {
        $kis = mb_strtolower($szoveg);
        foreach ($tiltott as $t) {
            $t = mb_strtolower(trim($t));
            if ($t !== '' && str_contains($kis, $t)) {
                return true;
            }
        }
        return false;
    }

    private static function egysor(string $s): string
    {
        return implode(' ', preg_split('/\s+/u', trim($s), -1, PREG_SPLIT_NO_EMPTY) ?: []);
    }

    public function takarit(): void
    {
        $hatar = $this->most()->getTimestamp() - self::MEGORZES_MP;
        $this->lista = array_values(array_filter($this->lista, static fn($k) => strtotime($k['ido']) >= $hatar
            || in_array($k['allapot'], ['kereses', 'varakozik'], true)));
    }

    public function &keres(string $azon): array
    {
        foreach ($this->lista as &$k) {
            if ($k['azon'] === $azon) {
                return $k;
            }
        }
        unset($k);
        throw new Hiba('Nincs ilyen kérés.', 'not_found', 404);
    }

    public function maiSzam(string $eszkoz): int
    {
        $ma = $this->most()->format('Y-m-d');
        return count(array_filter($this->lista, static fn($k) => $k['eszkoz'] === $eszkoz && str_starts_with($k['ido'], $ma)
            && !($k['allapot'] === 'elutasitva' && $k['ok'] !== '')));
    }

    public function maradek(string $eszkoz, int $napi): int
    {
        return max(0, $napi - $this->maiSzam($eszkoz));
    }

    public function sajat(string $eszkoz): array
    {
        $ma = $this->most()->format('Y-m-d');
        return array_values(array_reverse(array_filter($this->lista, static fn($k) => $k['eszkoz'] === $eszkoz && str_starts_with($k['ido'], $ma))));
    }

    public function mai(): array
    {
        $ma = $this->most()->format('Y-m-d');
        return array_values(array_reverse(array_filter($this->lista, static fn($k) => str_starts_with($k['ido'], $ma))));
    }

    public function fuggo(): array
    {
        return array_values(array_filter($this->lista, static fn($k) => in_array($k['allapot'], ['kereses', 'varakozik'], true)));
    }

    public function uj(string $szoveg, string $nev, string $eszkoz, string $ip, int $napi, array $tiltott, ?Szuro $szuro = null, string $azon = ''): array
    {
        $this->takarit();
        $szoveg = self::egysor($szoveg);
        $nev = self::egysor($nev);
        if ($szoveg === '') {
            throw new Hiba('Írd be a szám címét vagy a YouTube-linkjét.', 'validation_error', 422);
        }
        if (mb_strlen($szoveg) > self::MAX_SZOVEG || mb_strlen($nev) > self::MAX_NEV) {
            throw new Hiba('Legfeljebb ' . self::MAX_SZOVEG . ' karakter lehet a kérés, ' . self::MAX_NEV . ' a név.', 'validation_error', 422);
        }
        self::youtubeCel($szoveg);
        if (self::tiltottE($szoveg, $tiltott) || self::tiltottE($nev, $tiltott) || ($szuro && $szuro->talalat($szoveg, $nev) !== null)) {
            throw new Hiba('Ezt a kérést nem lehet elküldeni.', 'forbidden_word', 422);
        }
        if ($this->maradek($eszkoz, $napi) <= 0) {
            throw new Hiba("Ma már nem kérhetsz több számot (napi {$napi}).", 'daily_limit', 429);
        }
        $egyOraja = $this->most()->getTimestamp() - 3600;
        if (count(array_filter($this->lista, static fn($k) => $k['ip'] === $ip && strtotime($k['ido']) >= $egyOraja)) >= self::IP_ORANKENT) {
            throw new Hiba('Erről a hálózatról most túl sok kérés jött, próbáld később.', 'rate_limited', 429);
        }
        if (count($this->fuggo()) >= self::MAX_VARAKOZO) {
            throw new Hiba('Most túl sok kérés vár jóváhagyásra, próbáld később.', 'queue_full', 429);
        }
        if ($azon !== '' && array_filter($this->lista, static fn($k) => $k['azon'] === $azon)) {
            throw new Hiba('Ez a kérés már megérkezett.', 'conflict', 409);
        }
        $k = ['azon' => $azon !== '' ? $azon : rtrim(strtr(base64_encode(random_bytes(8)), '+/', '-_'), '='),
            'szoveg' => $szoveg, 'nev' => $nev, 'eszkoz' => $eszkoz, 'ip' => $ip, 'ido' => $this->most()->format('Y-m-d H:i:s'),
            'allapot' => 'kereses', 'cim' => '', 'yt' => '', 'hossz' => 0, 'ok' => '', 'megjegyzes' => ''];
        $this->lista[] = $k;
        return $k;
    }

    public function talalat(string $azon, string $yt, string $cim, int $hossz, int $maxPerc, array $tiltott, int $korhatar = 0,
                            ?Szuro $szuro = null, bool $korhatarTiltas = true, bool $tragarSzoveg = false, bool $tiltottSzam = false): array
    {
        $k = &$this->keres($azon);
        if ($k['allapot'] !== 'kereses') {
            return $k;
        }
        $k['yt'] = $yt;
        $k['cim'] = $cim;
        $k['hossz'] = $hossz;
        $masik = function (array $allapotok) use ($azon, $yt): bool {
            foreach ($this->lista as $m) {
                if ($m['azon'] !== $azon && $m['yt'] === $yt && in_array($m['allapot'], $allapotok, true)) {
                    return true;
                }
            }
            return false;
        };
        $ok = match (true) {
            $tiltottSzam => 'Ezt a számot a rendszergazda letiltotta.',
            $korhatarTiltas && $korhatar >= Szuro::KORHATAR => 'Korhatáros videó nem kérhető.',
            self::tiltottE($cim, $tiltott) || ($szuro && $szuro->talalat($cim) !== null) => 'A szám nem engedélyezett.',
            $tragarSzoveg => 'A szám szövege túl trágár a szünetzenéhez.',
            $hossz <= 0 => 'Élő adás vagy ismeretlen hosszú videó nem kérhető.',
            $hossz > $maxPerc * 60 => "Túl hosszú (legfeljebb {$maxPerc} perc lehet), és nincs rövidebb rádiós változata (radio edit).",
            $masik(['varakozik', 'elfogadva']) => 'Ezt a számot már kérték, hamarosan szólhat.',
            $masik(['szol']) => 'Ez a szám nemrég már szólt.',
            $masik(['levett']) => 'Ezt a számot nemrég levették a sorból.',
            default => null,
        };
        if ($ok !== null) {
            $k['allapot'] = 'elutasitva';
            $k['ok'] = $ok;
        } else {
            $k['allapot'] = 'varakozik';
        }
        return $k;
    }

    public function automatikusHelye(): bool
    {
        return count(array_filter($this->lista, static fn($k) => $k['allapot'] === 'elfogadva')) < self::AUTO_MAX_SOR;
    }

    public function nemTalalt(string $azon, string $ok): array
    {
        $k = &$this->keres($azon);
        if ($k['allapot'] === 'kereses') {
            $k['allapot'] = 'elutasitva';
            $k['ok'] = $ok;
        }
        return $k;
    }

    public function dont(string $azon, bool $elfogad): array
    {
        $k = &$this->keres($azon);
        if ($k['allapot'] !== 'varakozik') {
            throw new Hiba('Erről a kérésről már döntöttek.', 'conflict', 409);
        }
        if ($elfogad) {
            $k['allapot'] = 'elfogadva';
        } else {
            $k['allapot'] = 'elutasitva';
            $k['ok'] = '';
        }
        return $k;
    }

    public function levesz(string $azon): array
    {
        $k = &$this->keres($azon);
        if (in_array($k['allapot'], ['elfogadva', 'szol'], true)) {
            $k['allapot'] = 'levett';
        } elseif (in_array($k['allapot'], ['kereses', 'varakozik'], true)) {
            $k['allapot'] = 'elutasitva';
            $k['ok'] = '';
        }
        return $k;
    }

    public function megjegyzes(string $azon, string $szoveg): void
    {
        $k = &$this->keres($azon);
        $k['megjegyzes'] = $szoveg;
    }

    public function szol(string $yt): ?array
    {
        foreach ($this->lista as &$k) {
            if ($k['yt'] === $yt && $k['allapot'] === 'elfogadva') {
                $k['allapot'] = 'szol';
                return $k;
            }
        }
        return null;
    }
}
