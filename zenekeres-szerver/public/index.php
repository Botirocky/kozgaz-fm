<?php
declare(strict_types=1);

require __DIR__ . '/../src/adat.php';

date_default_timezone_set(getenv('TZ') ?: 'Europe/Budapest');

function valasz(int $statusz, array $test): never
{
    http_response_code($statusz);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($test, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function hiba(int $statusz, string $kod, string $uzenet): never
{
    valasz($statusz, ['error' => ['code' => $kod, 'message' => $uzenet]]);
}

function kliens_ip(): string
{
    $tavoli = $_SERVER['REMOTE_ADDR'] ?? '';
    $belso = filter_var($tavoli, FILTER_VALIDATE_IP, FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE) === false;
    $lanc = explode(',', $_SERVER['HTTP_X_FORWARDED_FOR'] ?? '');
    $tovabbitott = trim((string)end($lanc));
    if ($belso && filter_var($tovabbitott, FILTER_VALIDATE_IP)) {
        return $tovabbitott;
    }
    return $tavoli;
}

function json_test(): array
{
    $nyers = file_get_contents('php://input', false, null, 0, 1_000_000);
    $adat = json_decode((string)$nyers, true);
    if (!is_array($adat)) {
        hiba(400, 'bad_json', 'Hibás kérés.');
    }
    return $adat;
}

function engedett_origin(): ?string
{
    $origin = (string)($_SERVER['HTTP_ORIGIN'] ?? '');
    $engedett = array_filter(array_map('trim', explode(',', (string)(getenv('KFM_ENGEDETT_ORIGIN') ?: 'https://botirocky.github.io'))));
    return $origin !== '' && in_array($origin, $engedett, true) ? $origin : null;
}

function eszkoz(): string
{
    $fejlec = (string)($_SERVER['HTTP_X_KOZGAZ_FM_ESZKOZ'] ?? '');
    if (engedett_origin() !== null && preg_match('/^[0-9a-f]{64}$/', $fejlec)) {
        return hash('sha256', 'kulso:' . $fejlec);
    }
    $suti = $_COOKIE[SUTI] ?? '';
    if (!is_string($suti) || !preg_match('/^[0-9a-f]{64}$/', $suti)) {
        $suti = bin2hex(random_bytes(32));
        setcookie(SUTI, $suti, [
            'expires' => time() + 400 * 86400,
            'path' => '/',
            'secure' => ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https' || !empty($_SERVER['HTTPS']),
            'httponly' => true,
            'samesite' => 'Lax',
        ]);
    }
    return hash('sha256', $suti);
}

function biztonsagi_fejlecek(): void
{
    header('X-Content-Type-Options: nosniff');
    header('Referrer-Policy: no-referrer');
    header('X-Frame-Options: DENY');
    header("Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        . "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'");
    header('Permissions-Policy: camera=(), microphone=(), geolocation=()');
}

function gep_kulcs_ellenoriz(): void
{
    $kulcs = (string)(getenv('KFM_GEP_KULCS') ?: '');
    $kapott = (string)($_SERVER['HTTP_X_KOZGAZ_FM_KULCS'] ?? '');
    if (strlen($kulcs) < 24 || !hash_equals($kulcs, $kapott)) {
        usleep(300000);
        hiba(401, 'unauthorized', 'Hibás kulcs.');
    }
}

const ZENE_KITERJESZTESEK = ['mp3', 'm4a', 'aac', 'ogg', 'opus', 'flac', 'wav', 'wma'];

function zene_gyoker(): ?string
{
    $gyoker = realpath((string)(getenv('KFM_ZENE_MAPPA') ?: '/zene'));
    return $gyoker !== false && is_dir($gyoker) ? $gyoker : null;
}

function zene_lista(): array
{
    $gyoker = zene_gyoker();
    if ($gyoker === null) {
        hiba(503, 'no_music', 'A zenemappa nem érhető el a szerveren.');
    }
    $lista = [];
    $bejaro = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($gyoker, FilesystemIterator::SKIP_DOTS));
    foreach ($bejaro as $f) {
        if (!$f->isFile() || str_starts_with($f->getFilename(), '.')
            || !in_array(strtolower($f->getExtension()), ZENE_KITERJESZTESEK, true)) {
            continue;
        }
        $relativ = substr($f->getPathname(), strlen($gyoker) + 1);
        if (!mb_check_encoding($relativ, 'UTF-8')) {
            continue;
        }
        $lista[] = ['ut' => $relativ, 'meret' => $f->getSize(), 'ido' => $f->getMTime()];
    }
    usort($lista, static fn($a, $b) => strcmp($a['ut'], $b['ut']));
    return $lista;
}

function zene_fajl(string $relativ): never
{
    $gyoker = zene_gyoker();
    if ($gyoker === null) {
        hiba(503, 'no_music', 'A zenemappa nem érhető el a szerveren.');
    }
    $teljes = realpath($gyoker . '/' . $relativ);
    if ($relativ === '' || str_contains($relativ, "\0") || $teljes === false || !is_file($teljes)
        || !str_starts_with($teljes, $gyoker . '/')
        || !in_array(strtolower(pathinfo($teljes, PATHINFO_EXTENSION)), ZENE_KITERJESZTESEK, true)) {
        hiba(404, 'not_found', 'Nincs ilyen zenefájl.');
    }
    while (ob_get_level() > 0) {
        ob_end_clean();
    }
    $meret = (int)filesize($teljes);
    $kezdet = 0;
    if (preg_match('/^bytes=(\d+)-$/', (string)($_SERVER['HTTP_RANGE'] ?? ''), $t) && (int)$t[1] < $meret) {
        $kezdet = (int)$t[1];
        http_response_code(206);
        header("Content-Range: bytes {$kezdet}-" . ($meret - 1) . "/{$meret}");
    }
    header('Content-Type: application/octet-stream');
    header('Accept-Ranges: bytes');
    header('Content-Length: ' . ($meret - $kezdet));
    header('Cache-Control: no-store');
    $f = fopen($teljes, 'rb');
    fseek($f, $kezdet);
    fpassthru($f);
    fclose($f);
    exit;
}

biztonsagi_fejlecek();
$ut = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
$modszer = $_SERVER['REQUEST_METHOD'] ?? 'GET';

try {
    if ($ut === '/api/zenek' || $ut === '/api/zenek/fajl') {
        gep_kulcs_ellenoriz();
        if ($modszer !== 'GET') {
            hiba(405, 'method_not_allowed', 'Csak GET.');
        }
        if ($ut === '/api/zenek') {
            valasz(200, ['data' => zene_lista()]);
        }
        zene_fajl((string)($_GET['ut'] ?? ''));
    }

    if ($ut === '/api/gep') {
        gep_kulcs_ellenoriz();
        if ($modszer !== 'POST') {
            hiba(405, 'method_not_allowed', 'Csak POST.');
        }
        valasz(200, ['data' => gep_szinkron(json_test())]);
    }

    if ($ut === '/api/zenekeres') {
        $kulso = engedett_origin();
        if ($kulso !== null) {
            header('Access-Control-Allow-Origin: ' . $kulso);
            header('Vary: Origin');
            header('Access-Control-Allow-Headers: Content-Type, X-Kozgaz-FM, X-Kozgaz-FM-Eszkoz');
            header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
            header('Access-Control-Max-Age: 600');
            if ($modszer === 'OPTIONS') {
                http_response_code(204);
                exit;
            }
        }
        $eszkoz = eszkoz();
        if ($modszer === 'GET') {
            valasz(200, ['data' => diak_allapot($eszkoz)]);
        }
        if ($modszer !== 'POST') {
            hiba(405, 'method_not_allowed', 'Nem támogatott művelet.');
        }
        if (($_SERVER['HTTP_X_KOZGAZ_FM'] ?? '') !== '1') {
            hiba(403, 'forbidden', 'Hibás kérés.');
        }
        $origin = $_SERVER['HTTP_ORIGIN'] ?? '';
        $gazda = $_SERVER['HTTP_X_FORWARDED_HOST'] ?? ($_SERVER['HTTP_HOST'] ?? '');
        if ($origin !== '' && $kulso === null && parse_url($origin, PHP_URL_HOST) !== explode(':', $gazda)[0]) {
            hiba(403, 'forbidden', 'Hibás kérés.');
        }
        $adat = json_test();
        uj_keres($eszkoz, kliens_ip(), $adat['szoveg'] ?? '', $adat['nev'] ?? '');
        valasz(200, ['data' => diak_allapot($eszkoz)]);
    }

    if ($ut === '/egeszseg') {
        $g = gep();
        valasz(200, ['data' => ['ok' => true, 'radio' => gep_elerheto($g), 'verzio' => $g['verzio']]]);
    }

    if ($ut === '/' || $ut === '/keres') {
        eszkoz();
        header('Content-Type: text/html; charset=utf-8');
        header('Cache-Control: no-cache');
        readfile(__DIR__ . '/../src/oldal.html');
        exit;
    }

    http_response_code(404);
    header('Content-Type: text/plain; charset=utf-8');
    echo 'Nincs ilyen oldal.';
} catch (KeresHiba $e) {
    hiba($e->statusz, $e->kod, $e->getMessage());
} catch (Throwable $e) {
    error_log('zenekeres: ' . $e);
    hiba(500, 'server_error', 'Váratlan hiba, próbáld újra.');
}
