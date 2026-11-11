<?php

declare(strict_types=1);

namespace KozgazFM;

final class Beallitasok
{
    public const BEEPITETT_HANGOK = [
        'becsengo' => 'Becsengő',
        'kicsengo' => 'Kicsengő',
        'jelzo' => 'Jelzőcsengő',
        'riaszto' => 'Riasztó',
    ];

    public const REGI_HANGOK = ['csengo' => 'becsengo', 'dallam' => 'becsengo', 'rovid' => 'jelzo', 'gong' => 'jelzo', 'riasztas' => 'kicsengo'];

    public const ALAP_SABLONOK = [
        'Kedves Diákok! Felhívjuk figyelmeteket, hogy a mai napon rövidített órák lesznek.',
        'Figyelem! Az osztályfőnöki órák után rendkívüli diákközgyűlést tartunk az aulában.',
        'Kedves Diákok és Tanárok! A tanítás vége után a tornateremben kezdődik a ballagási próba.',
        'Kérjük az ügyeletes diákokat, hogy jelentkezzenek a titkárságon.',
    ];

    public const NAPOK = ['Hétfő', 'Kedd', 'Szerda', 'Csütörtök', 'Péntek', 'Szombat', 'Vasárnap'];

    public const RENDKIVULI_TIPUSOK = [
        'csengetes' => 'Rendkívüli csengetés',
        'riado' => 'Tűzriadó-gyakorlat',
        'csend' => 'Csendes időszak',
    ];

    public const FORRAS_TIPUSOK = ['mappa' => 'Mappa', 'fajlok' => 'Fájlok', 'youtube' => 'YouTube', 'spotify' => 'Spotify'];

    public const HELYI_MEZOK = [
        'admin_pin', 'web_panel', 'web_port', 'web_jelszo', 'tartalek_mod', 'tartalek_cim', 'tartalek_kulcs',
        'zenekeres_szerver_kulcs', 'zenekeres_mp3_mappa', 'zene_szinkron_mappa', 'ertesites_ntfy', 'ertesites_ntfy_token', 'ertesites_email', 'smtp_szerver',
        'smtp_port', 'smtp_mod', 'smtp_felhasznalo', 'smtp_jelszo', 'smtp_felado', 'kimenet', 'zonak',
        'tiltott_telefonok',
    ];

    public const HANG_MEZOK = [
        'hang_becsengo' => 'beepitett:becsengo',
        'hang_kicsengo' => 'beepitett:kicsengo',
        'hang_jelzo' => 'beepitett:jelzo',
        'hang_gong' => 'beepitett:jelzo',
        'hang_riasztas' => 'beepitett:riaszto',
    ];

    private const ELEMEK = [
        'rendek' => ['nev' => '', 'orak' => []],
        'szunnapok' => ['tol' => '', 'ig' => '', 'nev' => ''],
        'bemondasok' => ['nev' => '', 'ido' => '08:00', 'napok' => [0, 1, 2, 3, 4], 'datum' => '', 'tipus' => 'szoveg',
            'tartalom' => '', 'gong' => true, 'aktiv' => true],
        'rendkivuli' => ['nev' => '', 'datum' => '', 'tol' => '08:00', 'tipus' => 'csengetes', 'ig' => '',
            'hang' => 'beepitett:becsengo', 'riado_perc' => 3, 'csengo_hangero' => 0, 'aktiv' => true],
        'tiltott_szamok' => ['azon' => '', 'cim' => '', 'yt' => '', 'ido' => ''],
        'tiltott_telefonok' => ['kulcs' => '', 'nev' => '', 'ig' => ''],
        'zonak' => ['nev' => '', 'kimenet' => '', 'csengo' => true, 'zene' => true, 'bemondas' => true, 'hangero' => 100],
        'forrasok' => ['tipus' => 'mappa', 'nev' => '', 'cim' => '', 'aktiv' => true],
        'musorblokkok' => ['nev' => '', 'forras' => '', 'napok' => [0, 1, 2, 3, 4], 'szunetek' => [], 'aktiv' => true],
    ];

    public static function alapok(): array
    {
        return [
            'rendek' => [],
            'het' => ['Normál', 'Normál', 'Normál', 'Normál', 'Normál', '', ''],
            'kivetelek' => [],
            'szunnapok' => [],
            'jelzo' => true,
            'jelzo_perc' => 2,
            'kicsengo' => true,
            'hang_becsengo' => 'beepitett:becsengo',
            'hang_kicsengo' => 'beepitett:kicsengo',
            'hang_jelzo' => 'beepitett:jelzo',
            'hang_gong' => 'beepitett:jelzo',
            'hang_riasztas' => 'beepitett:riaszto',
            'csengo_hangero' => 90,
            'zene_hangero' => 60,
            'zene_szunetben' => true,
            'zene_min_szunet' => 5,
            'zene_kesleltetes' => 10,
            'zene_leall_elotte' => 20,
            'elhalkitas' => 3.0,
            'atusztatas' => 5.0,
            'atusztatas_be' => true,
            'reggeli_zene' => false,
            'reggeli_zene_tol' => '07:30',
            'zene_kihagyott_szunetek' => [],
            'forrasok' => [],
            'aktiv_forras' => 0,
            'keveres' => true,
            'youtube_gyorsitotar' => true,
            'hangero_kiegyenlites' => true,
            'musorblokkok' => [],
            'szuro_alap' => true,
            'szuro_korhataros' => true,
            'szuro_szavak' => [],
            'szuro_dalszoveg' => true,
            'szuro_erzekenyseg' => 'normal',
            'bemondasok' => [],
            'rendkivuli' => [],
            'bemondas_sablonok' => self::ALAP_SABLONOK,
            'spotify_client_id' => '',
            'spotify_eszkoz' => '',
            'tts_hang' => '',
            'kimenet' => '',
            'zonak' => [],
            'talcara_zar' => true,
            'automatikus_inditas' => false,
            'admin_pin' => '',
            'tema' => 'vilagos',
            'admin_zar_perc' => 5,
            'web_panel' => true,
            'web_port' => 8080,
            'web_jelszo' => '',
            'zenekeres' => false,
            'zenekeres_auto' => true,
            'zenekeres_napi' => 3,
            'zenekeres_max_perc' => 7,
            'zenekeres_tiltott' => [],
            'zenekeres_szerver' => '',
            'zenekeres_szerver_kulcs' => '',
            'zenekeres_oldal' => '',
            'zenekeres_mp3' => true,
            'zenekeres_mp3_mappa' => '',
            'zene_szinkron' => false,
            'zene_szinkron_mappa' => '',
            'zene_szinkron_kbps' => 0,
            'tiltott_szamok' => [],
            'tiltott_telefonok' => [],
            'tartalek_mod' => '',
            'tartalek_cim' => '',
            'tartalek_kulcs' => '',
            'kijelzo_cim' => 'Közgáz FM',
            'ertesites_ntfy' => '',
            'ertesites_ntfy_token' => '',
            'ertesites_email' => '',
            'smtp_szerver' => '',
            'smtp_port' => 587,
            'smtp_mod' => 'starttls',
            'smtp_felhasznalo' => '',
            'smtp_jelszo' => '',
            'smtp_felado' => '',
            'ertesites_esemenyek' => ['kimaradt', 'hiba', 'hangkimenet', 'riasztas', 'tartalek', 'indulas', 'reggel'],
            'ertesites_reggel_ido' => '07:15',
            'frissites_kereses' => true,
            'frissites_auto' => true,
            'ma_nincs_csengetes' => '',
            'ma_nincs_zene' => '',
        ];
    }

    public static function alapertelmezett(): array
    {
        $b = self::alapok();
        $b['rendek'] = [
            ['nev' => 'Normál', 'orak' => self::orak([
                ['07:30', '08:15'], ['08:25', '09:10'], ['09:25', '10:10'], ['10:20', '11:05'], ['11:20', '12:05'],
                ['12:15', '13:00'], ['13:20', '14:05'], ['14:15', '15:00'], ['15:10', '15:55'],
            ])],
            ['nev' => 'Rövidített', 'orak' => self::orak([
                ['07:30', '08:00'], ['08:10', '08:40'], ['08:50', '09:20'], ['09:30', '10:00'],
                ['10:10', '10:40'], ['10:50', '11:20'], ['11:30', '12:00'], ['12:05', '12:35'],
            ])],
        ];
        $b['szunnapok'] = [
            ['tol' => '2026-11-30', 'ig' => '2026-11-30', 'nev' => 'Tanításmentes munkanap: Pályaorientációs nap'],
            ['tol' => '2026-12-12', 'ig' => '2026-12-12', 'nev' => 'Tanításmentes munkanap: Nevelési értekezlet'],
            ['tol' => '2026-12-19', 'ig' => '2027-01-03', 'nev' => 'Téli szünet'],
            ['tol' => '2027-03-24', 'ig' => '2027-03-24', 'nev' => 'Tanításmentes munkanap: Diákönkormányzati nap'],
            ['tol' => '2027-03-25', 'ig' => '2027-04-04', 'nev' => 'Tavaszi szünet'],
            ['tol' => '2027-04-30', 'ig' => '2027-04-30', 'nev' => 'Tanításmentes munkanap: Ballagás'],
            ['tol' => '2027-06-16', 'ig' => '2027-08-31', 'nev' => 'Nyári szünet'],
        ];
        return $b;
    }

    public static function orak(array $parok): array
    {
        return array_map(static fn(array $p): array => ['kezdet' => $p[0], 'vege' => $p[1]], $parok);
    }

    public static function normalizal(array $adat): array
    {
        $alap = self::alapok();
        $b = [];
        foreach ($alap as $kulcs => $ertek) {
            $b[$kulcs] = array_key_exists($kulcs, $adat) ? self::tipusra($ertek, $adat[$kulcs], $kulcs) : $ertek;
        }
        foreach (self::ELEMEK as $kulcs => $minta) {
            $b[$kulcs] = array_values(array_map(static fn($e): array => self::elem($minta, is_array($e) ? $e : []),
                array_filter($b[$kulcs], 'is_array')));
        }
        foreach ($b['rendek'] as &$rend) {
            $rend['orak'] = array_values(array_map(static fn($o): array => [
                'kezdet' => (string)($o['kezdet'] ?? '08:00'), 'vege' => (string)($o['vege'] ?? '08:45'),
            ], array_filter((array)$rend['orak'], 'is_array')));
        }
        unset($rend);
        $b['het'] = array_slice(array_pad(array_map('strval', array_values($b['het'])), 7, ''), 0, 7);
        $b['kivetelek'] = array_map('strval', array_filter($b['kivetelek'], 'is_scalar'));
        foreach (['szuro_szavak', 'zenekeres_tiltott', 'bemondas_sablonok', 'ertesites_esemenyek'] as $lista) {
            $b[$lista] = array_values(array_map('strval', array_filter($b[$lista], 'is_scalar')));
        }
        return $b;
    }

    private static function elem(array $minta, array $adat): array
    {
        $kesz = [];
        foreach ($minta as $kulcs => $ertek) {
            $kesz[$kulcs] = array_key_exists($kulcs, $adat) ? self::tipusra($ertek, $adat[$kulcs], $kulcs) : $ertek;
        }
        return $kesz;
    }

    private static function tipusra(mixed $alap, mixed $ertek, string $kulcs): mixed
    {
        return match (true) {
            is_bool($alap) => is_bool($ertek) ? $ertek : (bool)$ertek,
            is_int($alap) => is_numeric($ertek) ? (int)$ertek : $alap,
            is_float($alap) => is_numeric($ertek) ? (float)$ertek : $alap,
            is_string($alap) => is_scalar($ertek) ? (string)$ertek : $alap,
            is_array($alap) => is_array($ertek) ? ($kulcs === 'kivetelek' || $kulcs === 'napok' || $kulcs === 'szunetek' || $kulcs === 'zene_kihagyott_szunetek'
                ? ($kulcs === 'kivetelek' ? $ertek : array_values(array_map('intval', $ertek))) : $ertek) : $alap,
            default => $ertek,
        };
    }

    public static function betolt(?string $ut = null): array
    {
        $ut ??= Utvonalak::beallitasFajl();
        foreach ([$ut, preg_replace('/\.json$/', '.bak', $ut)] as $jelolt) {
            if (!is_file($jelolt)) {
                continue;
            }
            $adat = json_decode((string)file_get_contents($jelolt), true);
            if (is_array($adat)) {
                $b = self::normalizal($adat);
                if (!array_key_exists('hang_riasztas', $adat) && !in_array('riasztas', $b['ertesites_esemenyek'], true)) {
                    $b['ertesites_esemenyek'][] = 'riasztas';
                }
                return self::regiHangok($b);
            }
        }
        return self::alapertelmezett();
    }

    public static function regiHang(string $ertek, string $mezo = ''): string
    {
        if (!str_starts_with($ertek, 'beepitett:')) {
            return $ertek;
        }
        $nev = substr($ertek, 10);
        if (isset(self::BEEPITETT_HANGOK[$nev])) {
            return $ertek;
        }
        if ($nev === 'csengo' && $mezo === 'hang_kicsengo') {
            return 'beepitett:kicsengo';
        }
        return 'beepitett:' . (self::REGI_HANGOK[$nev] ?? 'becsengo');
    }

    public static function regiHangok(array $b): array
    {
        foreach ($b as $kulcs => $ertek) {
            if (str_starts_with((string)$kulcs, 'hang_') && is_string($ertek)) {
                $b[$kulcs] = self::regiHang($ertek, (string)$kulcs);
            }
        }
        foreach ($b['rendkivuli'] ?? [] as $i => $r) {
            if (is_array($r) && is_string($r['hang'] ?? null)) {
                $b['rendkivuli'][$i]['hang'] = self::regiHang($r['hang']);
            }
        }
        return $b;
    }

    public static function ment(array $b, ?string $ut = null): void
    {
        $ut ??= Utvonalak::beallitasFajl();
        $b = self::normalizal($b);
        $json = json_encode($b, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR);
        $ideiglenes = $ut . '.tmp';
        $f = fopen($ideiglenes, 'wb');
        if ($f === false) {
            throw new \RuntimeException('A beállításfájl nem írható: ' . $ut);
        }
        fwrite($f, $json);
        fflush($f);
        fclose($f);
        if (is_file($ut)) {
            @copy($ut, preg_replace('/\.json$/', '.bak', $ut));
        }
        rename($ideiglenes, $ut);
    }

    public static function rend(array $b, string $nev): ?array
    {
        foreach ($b['rendek'] as $r) {
            if ($r['nev'] === $nev) {
                return $r;
            }
        }
        return null;
    }

    public static function export(array $b): array
    {
        $ki = $b;
        foreach (self::HELYI_MEZOK as $mezo) {
            unset($ki[$mezo]);
        }
        return $ki;
    }

    public static function import(array $jelenlegi, array $uj): array
    {
        $kesz = self::normalizal(array_merge($jelenlegi, array_diff_key($uj, array_flip(self::HELYI_MEZOK))));
        foreach (self::HELYI_MEZOK as $mezo) {
            $kesz[$mezo] = $jelenlegi[$mezo];
        }
        return $kesz;
    }
}
