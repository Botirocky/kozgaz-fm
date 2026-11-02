<?php
declare(strict_types=1);

const MAX_SZOVEG = 150;
const MAX_NEV = 30;
const MAX_VARAKOZO = 40;
const IP_ORANKENT = 20;
const GEP_ELAVULT_MP = 90;
const ATADATLAN_LEJAR_MP = 7200;
const MEGORZES_NAP = 2;
const SUTI = 'kfm_eszkoz';
const YOUTUBE_GAZDAK = ['youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com', 'youtu.be'];

final class KeresHiba extends RuntimeException
{
    public function __construct(public readonly int $statusz, public readonly string $kod, string $uzenet)
    {
        parent::__construct($uzenet);
    }
}

function adatbazis(): PDO
{
    static $db = null;
    if ($db instanceof PDO) {
        return $db;
    }
    $mappa = getenv('KFM_ADAT') ?: '/data';
    $db = new PDO('sqlite:' . $mappa . '/zenekeres.sqlite', null, null, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);
    $db->exec('PRAGMA journal_mode = WAL');
    $db->exec('PRAGMA busy_timeout = 5000');
    $db->exec('CREATE TABLE IF NOT EXISTS keresek (
        azon TEXT PRIMARY KEY,
        szoveg TEXT NOT NULL,
        nev TEXT NOT NULL DEFAULT \'\',
        eszkoz TEXT NOT NULL,
        ip TEXT NOT NULL,
        ido INTEGER NOT NULL,
        nap TEXT NOT NULL,
        allapot TEXT NOT NULL DEFAULT \'kereses\',
        allapot_nev TEXT NOT NULL DEFAULT \'\',
        cim TEXT NOT NULL DEFAULT \'\',
        ok TEXT NOT NULL DEFAULT \'\',
        atadva INTEGER NOT NULL DEFAULT 0
    )');
    $db->exec('CREATE INDEX IF NOT EXISTS keresek_eszkoz ON keresek (eszkoz, nap)');
    $db->exec('CREATE INDEX IF NOT EXISTS keresek_atadva ON keresek (atadva)');
    $db->exec('CREATE TABLE IF NOT EXISTS ertekek (kulcs TEXT PRIMARY KEY, ertek TEXT NOT NULL)');
    return $db;
}

function ertek(string $kulcs, mixed $alap = null): mixed
{
    $q = adatbazis()->prepare('SELECT ertek FROM ertekek WHERE kulcs = ?');
    $q->execute([$kulcs]);
    $sor = $q->fetchColumn();
    return $sor === false ? $alap : json_decode((string)$sor, true);
}

function ertek_ir(string $kulcs, mixed $adat): void
{
    $q = adatbazis()->prepare('INSERT INTO ertekek (kulcs, ertek) VALUES (?, ?)
        ON CONFLICT(kulcs) DO UPDATE SET ertek = excluded.ertek');
    $q->execute([$kulcs, json_encode($adat, JSON_UNESCAPED_UNICODE)]);
}

function ma(): string
{
    return date('Y-m-d');
}

function gep(): array
{
    $g = ertek('gep', []);
    $alap = ['aktiv' => false, 'auto' => true, 'cim' => 'Közgáz FM', 'napi' => 3, 'max_perc' => 7,
        'tiltott_telefonok' => [], 'utolso' => 0, 'verzio' => ''];
    return array_merge($alap, is_array($g) ? $g : []);
}

function gep_elerheto(array $g): bool
{
    return time() - (int)$g['utolso'] <= GEP_ELAVULT_MP;
}

function telefon_kulcs(string $eszkoz): string
{
    return substr(hash('sha256', $eszkoz), 0, 32);
}

function szokoz(string $s): string
{
    return trim((string)preg_replace('/\s+/u', ' ', $s));
}

function hossz(string $s): int
{
    return mb_strlen($s, 'UTF-8');
}

function youtube_ellenoriz(string $szoveg): void
{
    $kis = mb_strtolower($szoveg, 'UTF-8');
    $gazda_eleje = false;
    foreach (YOUTUBE_GAZDAK as $g) {
        if (str_starts_with($kis, $g)) {
            $gazda_eleje = true;
        }
    }
    if (!str_contains($szoveg, '://') && !$gazda_eleje) {
        return;
    }
    $cim = str_contains($szoveg, '://') ? $szoveg : 'https://' . $szoveg;
    $reszek = parse_url($cim);
    $sema = strtolower((string)($reszek['scheme'] ?? ''));
    $gazda = strtolower((string)($reszek['host'] ?? ''));
    if (!in_array($sema, ['http', 'https'], true) || !in_array($gazda, YOUTUBE_GAZDAK, true)) {
        throw new KeresHiba(422, 'bad_link', 'Csak YouTube-link vagy a szám címe adható meg.');
    }
}

function lejart_takaritas(): void
{
    $db = adatbazis();
    $db->prepare('DELETE FROM keresek WHERE ido < ?')->execute([time() - MEGORZES_NAP * 86400]);
    $db->prepare('UPDATE keresek SET allapot = \'elutasitva\', allapot_nev = \'Elutasítva\',
        ok = \'A rádió nem tudta feldolgozni, próbáld újra.\'
        WHERE allapot = \'kereses\' AND ido < ?')->execute([time() - ATADATLAN_LEJAR_MP]);
}

function mai_szam(string $eszkoz): int
{
    $q = adatbazis()->prepare('SELECT COUNT(*) FROM keresek WHERE eszkoz = ? AND nap = ?
        AND NOT (allapot = \'elutasitva\' AND ok <> \'\')');
    $q->execute([$eszkoz, ma()]);
    return (int)$q->fetchColumn();
}

function nyilvanos(array $k): array
{
    $nevek = [
        'kereses' => $k['atadva'] ? 'Keresés és ellenőrzés…' : 'Továbbítás a rádiónak…',
        'varakozik' => 'Jóváhagyásra vár',
        'elfogadva' => 'Elfogadva, hamarosan szól',
        'szol' => 'Most szól',
        'elutasitva' => 'Elutasítva',
        'levett' => 'Levették a sorból',
    ];
    return [
        'azon' => $k['azon'],
        'szoveg' => $k['szoveg'],
        'cim' => $k['cim'],
        'allapot' => $k['allapot'],
        'allapot_nev' => $nevek[$k['allapot']] ?? ($k['allapot_nev'] ?: $k['allapot']),
        'ok' => $k['ok'],
        'ido' => date('H:i', (int)$k['ido']),
    ];
}

function diak_allapot(string $eszkoz): array
{
    $g = gep();
    $elerheto = gep_elerheto($g);
    $napi = max(1, (int)$g['napi']);
    $q = adatbazis()->prepare('SELECT * FROM keresek WHERE eszkoz = ? AND nap = ? ORDER BY ido DESC LIMIT 30');
    $q->execute([$eszkoz, ma()]);
    return [
        'aktiv' => $elerheto && (bool)$g['aktiv'],
        'elerheto' => $elerheto,
        'auto' => (bool)$g['auto'],
        'cim' => (string)$g['cim'],
        'napi' => $napi,
        'maradek' => max(0, $napi - mai_szam($eszkoz)),
        'max_perc' => (int)$g['max_perc'],
        'tiltva' => in_array(telefon_kulcs($eszkoz), (array)$g['tiltott_telefonok'], true),
        'sajat' => array_map('nyilvanos', $q->fetchAll()),
    ];
}

function uj_keres(string $eszkoz, string $ip, mixed $szoveg, mixed $nev): void
{
    if (!is_string($szoveg) || !is_string($nev)) {
        throw new KeresHiba(422, 'validation_error', 'Hibás kérés.');
    }
    $g = gep();
    if (!gep_elerheto($g)) {
        throw new KeresHiba(503, 'offline', 'Az iskolarádió most nem elérhető, próbáld később.');
    }
    if (!$g['aktiv']) {
        throw new KeresHiba(409, 'disabled', 'A zenekérés most nincs bekapcsolva.');
    }
    $szoveg = szokoz($szoveg);
    $nev = szokoz($nev);
    if ($szoveg === '') {
        throw new KeresHiba(422, 'validation_error', 'Írd be a szám címét vagy a YouTube-linkjét.');
    }
    if (hossz($szoveg) > MAX_SZOVEG || hossz($nev) > MAX_NEV) {
        throw new KeresHiba(422, 'validation_error',
            'Legfeljebb ' . MAX_SZOVEG . ' karakter lehet a kérés, ' . MAX_NEV . ' a név.');
    }
    youtube_ellenoriz($szoveg);
    if (in_array(telefon_kulcs($eszkoz), (array)$g['tiltott_telefonok'], true)) {
        throw new KeresHiba(403, 'device_blocked', 'Erről a telefonról most nem kérhetsz számot.');
    }
    $db = adatbazis();
    $db->beginTransaction();
    try {
        $napi = max(1, (int)$g['napi']);
        if (mai_szam($eszkoz) >= $napi) {
            throw new KeresHiba(429, 'daily_limit', "Ma már nem kérhetsz több számot (napi $napi).");
        }
        $q = $db->prepare('SELECT COUNT(*) FROM keresek WHERE ip = ? AND ido >= ?');
        $q->execute([$ip, time() - 3600]);
        if ((int)$q->fetchColumn() >= IP_ORANKENT) {
            throw new KeresHiba(429, 'rate_limited', 'Erről a hálózatról most túl sok kérés jött, próbáld később.');
        }
        $q = $db->query('SELECT COUNT(*) FROM keresek WHERE allapot IN (\'kereses\', \'varakozik\')');
        if ((int)$q->fetchColumn() >= MAX_VARAKOZO) {
            throw new KeresHiba(429, 'queue_full', 'Most túl sok kérés vár, próbáld később.');
        }
        $azon = rtrim(strtr(base64_encode(random_bytes(9)), '+/', '-_'), '=');
        $db->prepare('INSERT INTO keresek (azon, szoveg, nev, eszkoz, ip, ido, nap) VALUES (?, ?, ?, ?, ?, ?, ?)')
            ->execute([$azon, $szoveg, $nev, $eszkoz, $ip, time(), ma()]);
        $db->commit();
    } catch (Throwable $e) {
        $db->rollBack();
        throw $e;
    }
}

function gep_szinkron(array $adat): array
{
    $b = $adat['beallitasok'] ?? null;
    if (!is_array($b)) {
        throw new KeresHiba(422, 'validation_error', 'Hiányoznak a beállítások.');
    }
    $tiltott = array_values(array_filter((array)($b['tiltott_telefonok'] ?? []),
        fn($t) => is_string($t) && preg_match('/^[0-9a-f]{32}$/', $t)));
    ertek_ir('gep', [
        'aktiv' => (bool)($b['aktiv'] ?? false),
        'auto' => (bool)($b['auto'] ?? true),
        'cim' => mb_substr(szokoz((string)($b['cim'] ?? 'Közgáz FM')), 0, 60, 'UTF-8'),
        'napi' => max(1, min(20, (int)($b['napi'] ?? 3))),
        'max_perc' => max(1, min(30, (int)($b['max_perc'] ?? 7))),
        'tiltott_telefonok' => array_slice($tiltott, 0, 500),
        'utolso' => time(),
        'verzio' => mb_substr((string)($adat['verzio'] ?? ''), 0, 20, 'UTF-8'),
    ]);
    $db = adatbazis();
    $frissit = $db->prepare('UPDATE keresek SET allapot = ?, allapot_nev = ?, cim = ?, ok = ?, atadva = 1
        WHERE azon = ?');
    $ervenyes = ['kereses', 'varakozik', 'elfogadva', 'szol', 'elutasitva', 'levett'];
    foreach (array_slice((array)($adat['allapotok'] ?? []), 0, 500) as $a) {
        if (!is_array($a) || !is_string($a['azon'] ?? null) || !in_array($a['allapot'] ?? '', $ervenyes, true)) {
            continue;
        }
        $frissit->execute([
            $a['allapot'],
            mb_substr((string)($a['allapot_nev'] ?? ''), 0, 60, 'UTF-8'),
            mb_substr((string)($a['cim'] ?? ''), 0, 200, 'UTF-8'),
            mb_substr((string)($a['ok'] ?? ''), 0, 200, 'UTF-8'),
            $a['azon'],
        ]);
    }
    lejart_takaritas();
    $q = $db->prepare('SELECT azon, szoveg, nev, eszkoz, ip, ido FROM keresek
        WHERE atadva = 0 AND allapot = \'kereses\' ORDER BY ido LIMIT 20');
    $q->execute();
    $uj = array_map(fn($k) => [
        'azon' => $k['azon'],
        'szoveg' => $k['szoveg'],
        'nev' => $k['nev'],
        'eszkoz' => $k['eszkoz'],
        'ip' => $k['ip'],
        'ido' => date('c', (int)$k['ido']),
    ], $q->fetchAll());
    return ['uj' => $uj, 'ido' => date('c')];
}
