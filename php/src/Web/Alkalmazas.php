<?php

declare(strict_types=1);

namespace KozgazFM\Web;

use KozgazFM\Beallitasok;
use KozgazFM\Hiba;
use KozgazFM\Naplo;
use KozgazFM\Utvonalak;
use KozgazFM\Zar;

final class Alkalmazas
{
    public const SUTI = 'kfm_munkamenet';
    public const ESZKOZ_SUTI = 'kfm_eszkoz';
    public const ELETTARTAM = 12 * 3600;
    public const MAX_TOREK = 64 * 1024;

    public const OLDALAK = [
        '/' => ['Vezérlőpult', 'pult', false],
        '/riasztas' => ['Riasztás', 'riasztas', true],
        '/csengetes' => ['Csengetési rend', 'csengo', true],
        '/zene' => ['Zene', 'zene', true],
        '/naptar' => ['Naptár', 'naptar', true],
        '/bemondasok' => ['Bemondások', 'bemondas', true],
        '/naplo' => ['Napló', 'naplo', true],
        '/statisztika' => ['Statisztika', 'grafikon', false],
        '/beallitasok' => ['Beállítások', 'beallitas', true],
        '/sugo' => ['Súgó', 'sugo', false],
    ];
    public const CSOPORTOK = ['/csengetes' => 'Műsor', '/naplo' => 'Áttekintés', '/beallitasok' => 'Rendszer'];

    public array $b;
    public string $metodus;
    public string $ut;
    public string $ip;

    public function __construct()
    {
        $this->b = Beallitasok::betolt();
        $this->metodus = strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET');
        $this->ut = '/' . trim(rawurldecode((string)parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH)), '/');
        $this->ip = (string)($_SERVER['REMOTE_ADDR'] ?? '');
    }

    public function futtat(): void
    {
        $this->fejlecek();
        try {
            if (str_starts_with($this->ut, '/api/v1/')) {
                (new Api($this))->kezel();
                return;
            }
            (new Oldalak($this))->kezel();
        } catch (Hiba $e) {
            if (str_starts_with($this->ut, '/api/')) {
                $this->json(['error' => ['code' => $e->kod, 'message' => $e->getMessage()]], $e->statusz ?: 400);
                return;
            }
            http_response_code($e->statusz ?: 400);
            echo Sablon::hibaOldal($e->getMessage());
        } catch (\Throwable $e) {
            Naplo::ir('HIBA (web): ' . get_class($e) . ': ' . $e->getMessage() . ' (' . basename($e->getFile()) . ':' . $e->getLine() . ')');
            if (str_starts_with($this->ut, '/api/')) {
                $this->json(['error' => ['code' => 'internal', 'message' => 'Belső hiba, részletek a naplóban.']], 500);
                return;
            }
            http_response_code(500);
            echo Sablon::hibaOldal('Belső hiba történt, a részletek a naplóban vannak.');
        }
    }

    private function fejlecek(): void
    {
        header("Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'");
        header('X-Content-Type-Options: nosniff');
        header('X-Frame-Options: DENY');
        header('Referrer-Policy: no-referrer');
        header('Cache-Control: no-store');
    }

    public function json(mixed $adat, int $statusz = 200, array $fejlecek = []): void
    {
        http_response_code($statusz);
        header('Content-Type: application/json; charset=utf-8');
        foreach ($fejlecek as $k => $v) {
            header("{$k}: {$v}");
        }
        echo json_encode($adat, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    }

    public function torzs(): array
    {
        $tipus = (string)($_SERVER['CONTENT_TYPE'] ?? '');
        if (str_starts_with($tipus, 'multipart/form-data') || str_starts_with($tipus, 'application/x-www-form-urlencoded')) {
            return $_POST;
        }
        $nyers = (string)file_get_contents('php://input', false, null, 0, self::MAX_TOREK * 16 + 1);
        if (strlen($nyers) > self::MAX_TOREK * 16) {
            throw new Hiba('Túl nagy kérés.', 'bad_request', 413);
        }
        if (trim($nyers) === '') {
            return [];
        }
        $adat = json_decode($nyers, true);
        if (!is_array($adat)) {
            throw new Hiba('Hibás JSON-kérés.', 'bad_request', 400);
        }
        return $adat;
    }

    public function munkamenet(): void
    {
        if (session_status() === PHP_SESSION_ACTIVE) {
            return;
        }
        Utvonalak::mappa('munkamenetek');
        session_name(self::SUTI);
        session_set_cookie_params(['lifetime' => 0, 'path' => '/', 'httponly' => true, 'samesite' => 'Strict',
            'secure' => !empty($_SERVER['HTTPS'])]);
        session_start();
        if (isset($_SESSION['ig']) && $_SESSION['ig'] < time()) {
            $_SESSION = [];
        }
    }

    public function bejelentkezve(): bool
    {
        $this->munkamenet();
        return !empty($_SESSION['belepve']) && ($_SESSION['jelszo'] ?? '') === hash('sha256', $this->b['web_jelszo']);
    }

    public function belep(string $jelszo): bool
    {
        if ($this->b['web_jelszo'] === '') {
            return false;
        }
        if (!Zar::probal('web:' . $this->ip, $jelszo, $this->b['web_jelszo'])) {
            return false;
        }
        $this->munkamenet();
        session_regenerate_id(true);
        $_SESSION['belepve'] = true;
        $_SESSION['jelszo'] = hash('sha256', $this->b['web_jelszo']);
        $_SESSION['ig'] = time() + self::ELETTARTAM;
        $_SESSION['csrf'] = bin2hex(random_bytes(16));
        return true;
    }

    public function kilep(): void
    {
        $this->munkamenet();
        $_SESSION = [];
        session_destroy();
    }

    public function pinKell(): bool
    {
        return $this->b['admin_pin'] !== '';
    }

    public function feloldva(): bool
    {
        if (!$this->pinKell()) {
            return true;
        }
        $this->munkamenet();
        $ig = (int)($_SESSION['pin_ig'] ?? 0);
        if ($ig <= time()) {
            return false;
        }
        $_SESSION['pin_ig'] = time() + max(1, $this->b['admin_zar_perc']) * 60;
        return true;
    }

    public function pinFelold(string $pin): bool
    {
        if (!$this->pinKell()) {
            return true;
        }
        if (!Zar::probal('pin:' . $this->ip, $pin, $this->b['admin_pin'])) {
            return false;
        }
        $this->munkamenet();
        $_SESSION['pin_ig'] = time() + max(1, $this->b['admin_zar_perc']) * 60;
        return true;
    }

    public function zarol(): void
    {
        $this->munkamenet();
        unset($_SESSION['pin_ig']);
    }

    public function csrfEllenoriz(): void
    {
        if (in_array($this->metodus, ['GET', 'HEAD'], true)) {
            return;
        }
        if (($_SERVER['HTTP_X_KOZGAZ_FM'] ?? '') !== '1') {
            throw new Hiba('Hiányzó biztonsági fejléc.', 'forbidden', 403);
        }
        $origin = (string)($_SERVER['HTTP_ORIGIN'] ?? '');
        if ($origin !== '') {
            $gazda = (string)($_SERVER['HTTP_HOST'] ?? '');
            if (parse_url($origin, PHP_URL_HOST) . (parse_url($origin, PHP_URL_PORT) ? ':' . parse_url($origin, PHP_URL_PORT) : '') !== $gazda) {
                throw new Hiba('Idegen oldalról érkező kérés.', 'forbidden', 403);
            }
        }
    }

    public function ki(): string
    {
        return 'webpanel, ' . $this->ip;
    }

    public function eszkoz(): string
    {
        $eszkoz = (string)($_COOKIE[self::ESZKOZ_SUTI] ?? '');
        if (!preg_match('/^[A-Za-z0-9_-]{16,64}$/', $eszkoz)) {
            $eszkoz = rtrim(strtr(base64_encode(random_bytes(24)), '+/', '-_'), '=');
            setcookie(self::ESZKOZ_SUTI, $eszkoz, ['expires' => time() + 400 * 86400, 'path' => '/', 'httponly' => true,
                'samesite' => 'Lax', 'secure' => !empty($_SERVER['HTTPS'])]);
            $_COOKIE[self::ESZKOZ_SUTI] = $eszkoz;
        }
        return $eszkoz;
    }

    public function vedett(string $ut): bool
    {
        return self::OLDALAK[$ut][2] ?? false;
    }
}
