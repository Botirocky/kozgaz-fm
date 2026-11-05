<?php

declare(strict_types=1);

require dirname(__DIR__) . '/src/bootstrap.php';

use KozgazFM\Beallitasok;
use KozgazFM\Bemondo;
use KozgazFM\Dalszoveg;
use KozgazFM\Ertesito;
use KozgazFM\Hangossag;
use KozgazFM\Hiba;
use KozgazFM\SajatHangok;
use KozgazFM\Spotify;
use KozgazFM\Tartalek;
use KozgazFM\YouTube;
use KozgazFM\ZeneSzinkron;
use KozgazFM\ZenekeresSzerver;

function mappa_szamai(string $mappa): array
{
    if (!is_dir($mappa)) {
        throw new Hiba("A mappa nem található: {$mappa}");
    }
    $lista = [];
    $iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($mappa, FilesystemIterator::SKIP_DOTS | FilesystemIterator::FOLLOW_SYMLINKS));
    foreach ($iterator as $f) {
        if ($f->isFile() && in_array(strtolower($f->getExtension()), SajatHangok::HANGFAJLOK, true)) {
            $lista[] = $f->getPathname();
        }
    }
    sort($lista, SORT_NATURAL | SORT_FLAG_CASE);
    return array_map(static fn($ut) => ['cim' => pathinfo($ut, PATHINFO_FILENAME), 'helyi' => $ut, 'yt' => ''], $lista);
}

function fajl_lista(string $cim): array
{
    $szamok = [];
    foreach (preg_split('/\R/', $cim) ?: [] as $sor) {
        $ut = trim($sor);
        if ($ut === '' || !is_file($ut)) {
            continue;
        }
        $kit = strtolower(pathinfo($ut, PATHINFO_EXTENSION));
        if (in_array($kit, ['m3u', 'm3u8'], true)) {
            foreach (file($ut, FILE_IGNORE_NEW_LINES) ?: [] as $elem) {
                $elem = trim($elem);
                if ($elem === '' || str_starts_with($elem, '#')) {
                    continue;
                }
                $cel = str_starts_with($elem, '/') ? $elem : dirname($ut) . '/' . $elem;
                if (is_file($cel)) {
                    $szamok[] = ['cim' => pathinfo($cel, PATHINFO_FILENAME), 'helyi' => $cel, 'yt' => ''];
                }
            }
        } elseif (in_array($kit, SajatHangok::HANGFAJLOK, true)) {
            $szamok[] = ['cim' => pathinfo($ut, PATHINFO_FILENAME), 'helyi' => $ut, 'yt' => ''];
        }
    }
    return $szamok;
}

function dalszoveg_lekeres(string $cim, int $hossz, string $tobblet): ?array
{
    $ismert = Dalszoveg::tarKeres($cim);
    if ($ismert !== null && $ismert['talalt']) {
        return $ismert;
    }
    try {
        $e = Dalszoveg::vizsgal($cim, $hossz, $tobblet);
    } catch (Hiba) {
        return null;
    }
    Dalszoveg::tarBeir($cim, $e);
    return $e;
}

function feladat(string $nev, array $a): mixed
{
    switch ($nev) {
        case 'meres':
            [$lufs, $csucs] = Hangossag::meres((string)$a['ut']);
            Hangossag::beir((string)$a['ut'], $lufs, $csucs);
            return true;
        case 'forras':
            $f = (array)$a['forras'];
            return match ($f['tipus']) {
                'mappa' => mappa_szamai((string)$f['cim']),
                'fajlok' => fajl_lista((string)$f['cim']),
                'youtube' => array_map(static fn($e) => ['cim' => $e['cim'], 'helyi' => null, 'yt' => $e['yt']], YouTube::lista((string)$f['cim'])),
                default => [],
            };
        case 'letoltes':
            return YouTube::letoltes((string)$a['yt'], (string)$a['mappa'], (bool)$a['korhatar']);
        case 'kert_mp3':
            $mappa = rtrim((string)$a['mappa'], '/');
            $nev = trim((string)preg_replace('/\s+/u', ' ', (string)preg_replace('/[<>:"\/\\\\|?*\x00-\x1f]/u', '', (string)$a['cim'])), ' .');
            $cel = $mappa . '/' . (mb_substr($nev, 0, 120) ?: 'Kért szám') . '.mp3';
            if (is_file($cel)) {
                return null;
            }
            $forras = YouTube::letoltes((string)$a['yt'], KozgazFM\Utvonalak::mappa('gyorsitotar/youtube'));
            @mkdir($mappa, 0775, true);
            $ideiglenes = $cel . '.tmp.mp3';
            $f = proc_open(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y', '-i', $forras, '-vn', '-codec:a', 'libmp3lame',
                '-q:a', '2', '-metadata', 'title=' . $a['cim'], '-metadata', 'comment=Közgáz FM – kért szám', $ideiglenes],
                [1 => ['file', '/dev/null', 'w'], 2 => ['pipe', 'w']], $csovek);
            $hiba = (string)stream_get_contents($csovek[2]);
            fclose($csovek[2]);
            if (proc_close($f) !== 0 || !is_file($ideiglenes)) {
                @unlink($ideiglenes);
                throw new Hiba(mb_substr(trim($hiba), 0, 200) ?: 'az ffmpeg hibát jelzett');
            }
            rename($ideiglenes, $cel);
            return $cel;
        case 'tts':
            return Bemondo::wav((string)$a['szoveg'], (string)($a['hang'] ?? 'hu'));
        case 'dalszoveg':
            $e = Dalszoveg::vizsgal((string)$a['cim'], (int)$a['hossz'], (string)$a['tobblet']);
            Dalszoveg::tarBeir((string)$a['cim'], $e);
            return $e;
        case 'zenekeres':
            $talalat = YouTube::egySzam((string)$a['cel']);
            $radio = '';
            if ($talalat !== null && $talalat['yt'] !== '' && $talalat['hossz'] > (int)$a['max_mp']) {
                try {
                    $rovid = YouTube::radioEdit($talalat['cim'], (int)$a['max_mp']);
                } catch (Throwable) {
                    $rovid = null;
                }
                if ($rovid !== null) {
                    $radio = $talalat['cim'];
                    $talalat = $rovid;
                }
            }
            $szoveg = null;
            if ($talalat !== null && !empty($a['dalszoveg']) && $talalat['yt'] !== '') {
                $szoveg = dalszoveg_lekeres($talalat['cim'], $talalat['hossz'], (string)$a['tobblet']);
            }
            return ['talalat' => $talalat, 'szoveg' => $szoveg, 'radio' => $radio];
        case 'ertesites':
            return Ertesito::kikuld(Beallitasok::betolt(), (string)$a['cim'], (string)$a['uzenet'], (string)$a['szint']);
        case 'tartalek':
            return Tartalek::lekeres((string)$a['cim'], (string)$a['ut'], (string)$a['kulcs']);
        case 'zene_szinkron':
            $haladas = ZeneSzinkron::haladasFajl();
            return ZeneSzinkron::szinkron((string)$a['cim'], (string)$a['kulcs'], (string)$a['mappa'], (int)$a['kbps'],
                static function (int $i, int $osszes, string $ut) use ($haladas): void {
                    @file_put_contents($haladas, json_encode(compact('i', 'osszes', 'ut'), JSON_UNESCAPED_UNICODE));
                },
                static fn() => is_file(ZeneSzinkron::leallFajl()));
        case 'zenekeres_szerver':
            return ZenekeresSzerver::kuld((string)$a['cim'], (string)$a['kulcs'], (array)$a['adat']);
        case 'spotify':
            $s = new Spotify((string)$a['client_id']);
            switch ($a['muvelet']) {
                case 'lejatszas':
                    $s->lejatszas((string)$a['uri'], (string)$a['eszkoz'], (bool)$a['keveres'], (int)$a['hangero']);
                    return true;
                case 'megallit':
                    if (!empty($a['elhalkitas'])) {
                        try {
                            $s->elhalkit((int)$a['honnan'], (float)$a['mp']);
                        } catch (Hiba) {
                        }
                    }
                    $s->szunet();
                    try {
                        $s->hangero((int)$a['vissza']);
                    } catch (Hiba) {
                    }
                    return true;
                case 'kovetkezo':
                    $s->kovetkezo();
                    return true;
                case 'elozo':
                    $s->elozo();
                    return true;
                case 'hangero':
                    $s->hangero((int)$a['szazalek']);
                    return true;
                case 'most_szol':
                    return $s->mostSzol();
            }
            throw new Hiba('Ismeretlen Spotify-művelet.');
    }
    throw new Hiba("Ismeretlen feladat: {$nev}");
}

$nev = $argv[1] ?? '';
$adat = json_decode((string)stream_get_contents(STDIN), true) ?: [];
try {
    $eredmeny = feladat($nev, $adat);
    echo json_encode(['ok' => true, 'eredmeny' => $eredmeny], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PARTIAL_OUTPUT_ON_ERROR);
} catch (Hiba $e) {
    echo json_encode(['ok' => false, 'hiba' => $e->getMessage(), 'kod' => $e->kod], JSON_UNESCAPED_UNICODE);
} catch (Throwable $e) {
    echo json_encode(['ok' => false, 'hiba' => get_class($e) . ': ' . $e->getMessage(), 'kod' => 'internal'], JSON_UNESCAPED_UNICODE);
}
