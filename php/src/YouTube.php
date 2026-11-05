<?php

declare(strict_types=1);

namespace KozgazFM;

final class YouTube
{
    public const HANG_FORMATUM = 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best';
    public const KITERJESZTESEK = ['m4a', 'webm', 'opus', 'mp3', 'ogg'];
    private const KORHATAR_JELEK = ['confirm your age', 'age-restricted', 'age restricted', 'inappropriate for some users'];
    public const RADIO_JELEK = ['radio edit', 'radio version', 'radio mix', 'radio cut'];
    private const CIM_ZAJ = '/(*UCP)[\(\[][^\)\]]*[\)\]]|\b(official|video|audio|lyrics?|hd|4k|music|clip|visualizer|remaster(ed)?|extended|version|full|album)\b/iu';

    private static function alap(): array
    {
        return ['yt-dlp', '--no-warnings', '--socket-timeout', '20', '--js-runtimes', 'node',
            '--use-extractors', 'youtube,youtube:search,youtube:tab'];
    }

    private static function futtat(array $parancs, int $idokorlat = 120): array
    {
        $leirok = [1 => ['pipe', 'w'], 2 => ['pipe', 'w']];
        $f = proc_open($parancs, $leirok, $csovek);
        if (!is_resource($f)) {
            throw new Hiba('A yt-dlp nem indult el.');
        }
        stream_set_blocking($csovek[1], false);
        stream_set_blocking($csovek[2], false);
        $ki = $hiba = '';
        $hatarido = microtime(true) + $idokorlat;
        while (true) {
            $ki .= (string)stream_get_contents($csovek[1]);
            $hiba .= (string)stream_get_contents($csovek[2]);
            $allapot = proc_get_status($f);
            if (!$allapot['running']) {
                break;
            }
            if (microtime(true) > $hatarido) {
                proc_terminate($f, 9);
                throw new Hiba('A YouTube-lekérés túl sokáig tartott.');
            }
            usleep(50000);
        }
        $ki .= (string)stream_get_contents($csovek[1]);
        $hiba .= (string)stream_get_contents($csovek[2]);
        fclose($csovek[1]);
        fclose($csovek[2]);
        proc_close($f);
        return [$allapot['exitcode'], $ki, $hiba];
    }

    private static function korhatarosHiba(string $szoveg): bool
    {
        $kis = mb_strtolower($szoveg);
        foreach (self::KORHATAR_JELEK as $j) {
            if (str_contains($kis, $j)) {
                return true;
            }
        }
        return false;
    }

    private static function json(array $argumentumok, int $idokorlat = 120): array
    {
        [$kod, $ki, $hiba] = self::futtat(array_merge(self::alap(), ['-J'], $argumentumok), $idokorlat);
        if ($kod !== 0) {
            if (self::korhatarosHiba($hiba)) {
                throw new Hiba('Korhatáros videó.', 'korhatar');
            }
            $sor = trim((string)preg_replace('/^ERROR:\s*/m', '', (string)strtok(trim($hiba) ?: 'ismeretlen hiba', "\n")));
            throw new Hiba('YouTube-hiba: ' . mb_substr($sor, 0, 200));
        }
        $adat = json_decode($ki, true);
        if (!is_array($adat)) {
            throw new Hiba('A YouTube érthetetlen választ adott.');
        }
        return $adat;
    }

    public static function lista(string $cim, int $maxDb = 500): array
    {
        $adat = self::json(['--flat-playlist', '--playlist-end', (string)$maxDb, $cim], 300);
        $elemek = $adat['entries'] ?? [$adat];
        $lista = [];
        foreach ($elemek as $e) {
            if (is_array($e) && !empty($e['id']) && strlen((string)$e['id']) === 11) {
                $lista[] = ['cim' => (string)($e['title'] ?? $e['id']), 'yt' => (string)$e['id']];
            }
        }
        return $lista;
    }

    public static function egySzam(string $cel): ?array
    {
        $kereses = str_starts_with($cel, 'ytsearch');
        try {
            $info = self::json(['--flat-playlist', '--no-playlist', $cel]);
        } catch (Hiba $e) {
            if ($e->kod === 'korhatar') {
                return $kereses ? null : ['yt' => '', 'cim' => '', 'hossz' => 0, 'korhatar' => 18];
            }
            throw $e;
        }
        if (array_key_exists('entries', $info)) {
            if (!$kereses) {
                return null;
            }
            $talalt = null;
            foreach ($info['entries'] as $e) {
                if (is_array($e) && !empty($e['id'])) {
                    $talalt = $e;
                    break;
                }
            }
            if ($talalt === null) {
                return null;
            }
            try {
                $info = self::json(['--no-playlist', 'https://www.youtube.com/watch?v=' . $talalt['id']]);
            } catch (Hiba $e) {
                if ($e->kod !== 'korhatar') {
                    throw $e;
                }
                return ['yt' => $talalt['id'], 'cim' => (string)($talalt['title'] ?? $talalt['id']),
                    'hossz' => (int)($talalt['duration'] ?? 0), 'korhatar' => 18];
            }
        }
        $korhatar = (int)($info['age_limit'] ?? 0);
        $elo = !empty($info['is_live']) || in_array($info['live_status'] ?? '', ['is_live', 'is_upcoming'], true);
        return ['yt' => (string)$info['id'], 'cim' => (string)($info['title'] ?? $info['id']),
            'hossz' => $elo ? 0 : (int)($info['duration'] ?? 0), 'korhatar' => $korhatar];
    }

    public static function gyorsitott(string $azon, string $mappa): ?string
    {
        if (!preg_match('/^[A-Za-z0-9_-]{11}$/', $azon)) {
            return null;
        }
        foreach (self::KITERJESZTESEK as $k) {
            $ut = "{$mappa}/{$azon}.{$k}";
            if (is_file($ut) && filesize($ut) > 0) {
                return $ut;
            }
        }
        return null;
    }

    public static function letoltes(string $azon, string $mappa, bool $korhatarTiltas = false): string
    {
        if (!preg_match('/^[A-Za-z0-9_-]{11}$/', $azon)) {
            throw new Hiba('Érvénytelen YouTube-azonosító.');
        }
        if ($meglevo = self::gyorsitott($azon, $mappa)) {
            return $meglevo;
        }
        @mkdir($mappa, 0775, true);
        $url = 'https://www.youtube.com/watch?v=' . $azon;
        if ($korhatarTiltas) {
            $info = self::json(['--no-playlist', $url]);
            if ((int)($info['age_limit'] ?? 0) >= Szuro::KORHATAR) {
                throw new Hiba('Korhatáros videó.', 'korhatar');
            }
        }
        [$kod, , $hiba] = self::futtat(array_merge(self::alap(), ['--no-playlist', '--no-part', '-f', self::HANG_FORMATUM,
            '-o', "{$mappa}/%(id)s.%(ext)s", $url]), 600);
        if ($kod !== 0) {
            if (self::korhatarosHiba($hiba)) {
                throw new Hiba('Korhatáros videó.', 'korhatar');
            }
            throw new Hiba('A letöltés nem sikerült: ' . mb_substr(trim((string)strtok(trim($hiba), "\n")), 0, 200));
        }
        $kesz = self::gyorsitott($azon, $mappa);
        if ($kesz === null) {
            throw new Hiba('A letöltött fájl nem található.');
        }
        return $kesz;
    }

    public static function meret(string $mappa): int
    {
        $osszes = 0;
        foreach (glob($mappa . '/*') ?: [] as $f) {
            $osszes += is_file($f) ? filesize($f) : 0;
        }
        return $osszes;
    }

    public static function urites(string $mappa): void
    {
        foreach (glob($mappa . '/*') ?: [] as $f) {
            is_file($f) && @unlink($f);
        }
    }

    private static function szavak(string $szoveg): array
    {
        return array_values(array_filter(preg_split('/[^a-z0-9]+/', Szuro::egyszerusit($szoveg)) ?: [], 'strlen'));
    }

    public static function radioAlapCim(string $cim): string
    {
        return implode(' ', preg_split('/\s+/u', trim((string)preg_replace(self::CIM_ZAJ, ' ', $cim)), -1, PREG_SPLIT_NO_EMPTY) ?: []);
    }

    public static function radioEditValaszt(array $elemek, string $eredetiCim, int $maxMp): ?array
    {
        $fontos = array_values(array_unique(array_filter(self::szavak(self::radioAlapCim($eredetiCim)), static fn($w) => strlen($w) > 2)));
        foreach ($elemek as $e) {
            if (!is_array($e) || empty($e['id'])) {
                continue;
            }
            $cim = (string)($e['title'] ?? '');
            $szoveg = implode(' ', self::szavak($cim));
            $radio = false;
            foreach (self::RADIO_JELEK as $j) {
                if (str_contains($szoveg, $j)) {
                    $radio = true;
                }
            }
            if (!$radio) {
                continue;
            }
            $hossz = (int)($e['duration'] ?? 0);
            if ($hossz <= 0 || $hossz > $maxMp) {
                continue;
            }
            if ($fontos && count(array_intersect($fontos, self::szavak($cim))) * 2 < count($fontos)) {
                continue;
            }
            return $e;
        }
        return null;
    }

    public static function radioEdit(string $eredetiCim, int $maxMp): ?array
    {
        $info = self::json(['--flat-playlist', 'ytsearch8:' . self::radioAlapCim($eredetiCim) . ' radio edit']);
        $talalt = self::radioEditValaszt($info['entries'] ?? [], $eredetiCim, $maxMp);
        if ($talalt === null) {
            return null;
        }
        $teljes = self::egySzam('https://www.youtube.com/watch?v=' . $talalt['id']);
        if ($teljes === null || $teljes['yt'] === '' || $teljes['hossz'] <= 0 || $teljes['hossz'] > $maxMp) {
            return null;
        }
        return $teljes;
    }
}
