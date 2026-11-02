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

function eszkoz(): string
{
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

biztonsagi_fejlecek();
$ut = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
$modszer = $_SERVER['REQUEST_METHOD'] ?? 'GET';

try {
    if ($ut === '/api/gep') {
        $kulcs = (string)(getenv('KFM_GEP_KULCS') ?: '');
        $kapott = (string)($_SERVER['HTTP_X_KOZGAZ_FM_KULCS'] ?? '');
        if (strlen($kulcs) < 24 || !hash_equals($kulcs, $kapott)) {
            usleep(300000);
            hiba(401, 'unauthorized', 'Hibás kulcs.');
        }
        if ($modszer !== 'POST') {
            hiba(405, 'method_not_allowed', 'Csak POST.');
        }
        valasz(200, ['data' => gep_szinkron(json_test())]);
    }

    if ($ut === '/api/zenekeres') {
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
        if ($origin !== '' && parse_url($origin, PHP_URL_HOST) !== explode(':', $gazda)[0]) {
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
