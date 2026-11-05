<?php

declare(strict_types=1);

namespace KozgazFM;

final class Spotify
{
    public const ATIRANYITAS = 'http://127.0.0.1:8898/callback';
    public const JOGOK = 'user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private playlist-read-collaborative';
    private const API = 'https://api.spotify.com/v1';
    private const TOKEN_URL = 'https://accounts.spotify.com/api/token';
    private const URI_MINTA = '#(?:open\.spotify\.com/(?:intl-[a-z-]+/)?|spotify:)(playlist|album|track|artist|show)[/:]([A-Za-z0-9]{10,})#';

    private array $token = [];

    public function __construct(public readonly string $clientId)
    {
        $adat = json_decode((string)@file_get_contents(self::tokenFajl()), true);
        $this->token = is_array($adat) ? $adat : [];
    }

    public static function tokenFajl(): string
    {
        return Utvonalak::adat() . '/spotify_token.json';
    }

    public static function uri(string $cim): ?string
    {
        return preg_match(self::URI_MINTA, trim($cim), $m) ? "spotify:{$m[1]}:{$m[2]}" : null;
    }

    public function bejelentkezve(): bool
    {
        return !empty($this->token['refresh_token']) && $this->clientId !== '';
    }

    public static function kijelentkezes(): void
    {
        @unlink(self::tokenFajl());
    }

    public static function bejelentkezesCim(string $clientId, string $allapot, string $ellenorzo): string
    {
        $kihivas = rtrim(strtr(base64_encode(hash('sha256', $ellenorzo, true)), '+/', '-_'), '=');
        return 'https://accounts.spotify.com/authorize?' . http_build_query([
            'client_id' => $clientId, 'response_type' => 'code', 'redirect_uri' => self::ATIRANYITAS,
            'code_challenge_method' => 'S256', 'code_challenge' => $kihivas, 'scope' => self::JOGOK, 'state' => $allapot,
        ]);
    }

    public function kodCsere(string $kod, string $ellenorzo): void
    {
        $this->tokenKeres(['grant_type' => 'authorization_code', 'code' => $kod, 'redirect_uri' => self::ATIRANYITAS,
            'client_id' => $this->clientId, 'code_verifier' => $ellenorzo]);
    }

    private function tokenKeres(array $adat): void
    {
        [$kod, $valasz, $hiba] = Http::keres('POST', self::TOKEN_URL, http_build_query($adat),
            ['Content-Type: application/x-www-form-urlencoded'], 15);
        if ($kod === 0) {
            throw new Hiba('Nem érhető el a Spotify (nincs internet?).');
        }
        if ($kod === 400 || $kod === 401) {
            self::kijelentkezes();
            throw new Hiba('A Spotify-bejelentkezés lejárt, jelentkezz be újra.');
        }
        if ($kod !== 200) {
            throw new Hiba("Spotify tokenhiba ({$kod})");
        }
        $uj = json_decode($valasz, true) ?: [];
        $uj['lejar'] = time() + (int)($uj['expires_in'] ?? 3600) - 60;
        $uj['refresh_token'] ??= $this->token['refresh_token'] ?? null;
        $this->token = $uj;
        file_put_contents(self::tokenFajl(), json_encode($uj));
        @chmod(self::tokenFajl(), 0600);
    }

    private function hozzaferes(): string
    {
        if (!$this->bejelentkezve()) {
            throw new Hiba('Nincs Spotify-bejelentkezés.');
        }
        if (time() >= (int)($this->token['lejar'] ?? 0)) {
            $this->tokenKeres(['grant_type' => 'refresh_token', 'refresh_token' => $this->token['refresh_token'], 'client_id' => $this->clientId]);
        }
        return (string)$this->token['access_token'];
    }

    private function keres(string $metodus, string $ut, array $parameterek = [], ?array $torzs = null): mixed
    {
        $url = self::API . $ut;
        $parameterek = array_filter($parameterek, static fn($v) => $v !== null && $v !== '');
        if ($parameterek) {
            $url .= '?' . http_build_query($parameterek);
        }
        $adat = $torzs !== null ? json_encode($torzs) : (in_array($metodus, ['PUT', 'POST'], true) ? '' : null);
        $fejlecek = ['Authorization: Bearer ' . $this->hozzaferes(), 'Content-Type: application/json'];
        if ($adat === '') {
            $fejlecek[] = 'Content-Length: 0';
        }
        [$kod, $valasz] = Http::keres($metodus, $url, $adat, $fejlecek, 15);
        if ($kod === 0) {
            throw new Hiba('Nem érhető el a Spotify (nincs internet?).');
        }
        if ($kod >= 400) {
            throw new Hiba(self::hibaSzoveg($kod, (string)$valasz));
        }
        return $valasz !== '' ? json_decode($valasz, true) : null;
    }

    private static function hibaSzoveg(int $kod, string $valasz): string
    {
        $reszlet = json_decode($valasz, true)['error'] ?? [];
        $ok = is_array($reszlet) ? (string)($reszlet['reason'] ?? '') : '';
        $uzenet = is_array($reszlet) ? (string)($reszlet['message'] ?? '') : (string)$reszlet;
        return match (true) {
            $ok === 'PREMIUM_REQUIRED' || ($kod === 403 && str_contains(strtolower($uzenet), 'premium')) => 'A Spotify vezérléséhez Premium-előfizetés kell.',
            $ok === 'NO_ACTIVE_DEVICE' || $kod === 404 => 'Nincs aktív Spotify-eszköz. Indítsd el a Spotify alkalmazást.',
            $kod === 401 => 'A Spotify-bejelentkezés érvénytelen, jelentkezz be újra.',
            $kod === 429 => 'Túl sok Spotify-kérés, várj egy kicsit.',
            $kod === 403 && str_contains(strtolower($uzenet), 'restriction') => 'A Spotify ezt most nem engedi (már szünetel, vagy nem vezérelhető).',
            default => "Spotify-hiba ({$kod}): " . ($uzenet ?: 'ismeretlen'),
        };
    }

    public function eszkozok(): array
    {
        return ($this->keres('GET', '/me/player/devices') ?? [])['devices'] ?? [];
    }

    private function eszkoz(string $kert): string
    {
        $eszkozok = $this->eszkozok();
        if (!$eszkozok) {
            throw new Hiba('Nincs elérhető Spotify-eszköz. Indítsd el a Spotify alkalmazást a hangosító gépen.');
        }
        foreach ($eszkozok as $e) {
            if ($kert !== '' && in_array($kert, [$e['id'] ?? '', $e['name'] ?? ''], true)) {
                return $e['id'];
            }
        }
        foreach ($eszkozok as $e) {
            if (!empty($e['is_active'])) {
                return $e['id'];
            }
        }
        return $eszkozok[0]['id'];
    }

    public function lejatszas(string $uri, string $eszkoz = '', bool $keveres = true, ?int $hangero = null): void
    {
        $azon = $this->eszkoz($eszkoz);
        if ($hangero !== null) {
            $this->hangero($hangero, $azon);
        }
        $torzs = str_starts_with($uri, 'spotify:track:') ? ['uris' => [$uri]] : ['context_uri' => $uri];
        $this->keres('PUT', '/me/player/play', ['device_id' => $azon], $torzs);
        try {
            $this->keres('PUT', '/me/player/shuffle', ['state' => $keveres ? 'true' : 'false', 'device_id' => $azon]);
        } catch (Hiba) {
        }
    }

    public function szunet(): void
    {
        try {
            $this->keres('PUT', '/me/player/pause');
        } catch (Hiba $e) {
            $kis = mb_strtolower($e->getMessage());
            if (!str_contains($kis, 'nincs aktív') && !str_contains($kis, 'már szünetel')) {
                throw $e;
            }
        }
    }

    public function hangero(int $szazalek, ?string $eszkozId = null): void
    {
        $this->keres('PUT', '/me/player/volume', ['volume_percent' => max(0, min(100, $szazalek)), 'device_id' => $eszkozId]);
    }

    public function elhalkit(int $honnan, float $mp, int $lepes = 6): void
    {
        for ($i = 1; $i <= $lepes; $i++) {
            $this->hangero((int)round($honnan * (1 - $i / $lepes)));
            usleep((int)($mp / $lepes * 1e6));
        }
    }

    public function kovetkezo(): void
    {
        $this->keres('POST', '/me/player/next');
    }

    public function elozo(): void
    {
        $this->keres('POST', '/me/player/previous');
    }

    public function mostSzol(): ?array
    {
        $adat = $this->keres('GET', '/me/player/currently-playing');
        if (!$adat || empty($adat['item'])) {
            return null;
        }
        $elem = $adat['item'];
        return ['cim' => (string)($elem['name'] ?? ''), 'eloado' => implode(', ', array_column($elem['artists'] ?? [], 'name')),
            'szol' => !empty($adat['is_playing']), 'explicit' => !empty($elem['explicit']),
            'hossz' => ($elem['duration_ms'] ?? 0) / 1000, 'pozicio' => ($adat['progress_ms'] ?? 0) / 1000];
    }
}
