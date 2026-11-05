<?php

declare(strict_types=1);

namespace KozgazFM\Web;

use KozgazFM\Hiba;
use KozgazFM\Naplo;
use KozgazFM\Spotify;

final class Oldalak
{
    public function __construct(private readonly Alkalmazas $app)
    {
    }

    public function kezel(): void
    {
        $ut = $this->app->ut;
        switch ($ut) {
            case '/keres':
                header('Content-Type: text/html; charset=utf-8');
                $this->app->eszkoz();
                echo $this->statikus('keres.html');
                return;
            case '/kijelzo':
                echo $this->statikus('kijelzo.html');
                return;
            case '/callback':
                $this->spotifyVisszateres();
                return;
        }
        if (!$this->app->bejelentkezve()) {
            if ($ut !== '/belepes') {
                header('Location: /belepes');
                http_response_code(303);
                return;
            }
            echo Sablon::belepes($this->app->b['web_jelszo'] === '');
            return;
        }
        if ($ut === '/belepes') {
            header('Location: /');
            http_response_code(303);
            return;
        }
        if ($ut === '/spotify/belepes') {
            $this->spotifyBelepes();
            return;
        }
        if ($ut === '/plakat') {
            echo $this->statikus('plakat.html');
            return;
        }
        if (!isset(Alkalmazas::OLDALAK[$ut])) {
            throw new Hiba('Nincs ilyen oldal.', 'not_found', 404);
        }
        $adat = [];
        if ($ut === '/sugo') {
            $adat['sugo'] = Markdown::html((string)file_get_contents(dirname(__DIR__, 2) . '/eroforrasok/sugo.md'));
        }
        header('Content-Type: text/html; charset=utf-8');
        echo Sablon::keret($this->app, $ut, '<div class="betoltes">Betöltés…</div>', $adat);
    }

    private function statikus(string $nev): string
    {
        return (string)file_get_contents(dirname(__DIR__, 2) . '/public/statikus/' . $nev);
    }

    private function spotifyBelepes(): void
    {
        $id = trim($this->app->b['spotify_client_id']);
        if ($id === '') {
            throw new Hiba('Előbb add meg a Spotify Client ID-t a Zene oldalon.', 'validation_error', 422);
        }
        $gazda = (string)($_SERVER['HTTP_HOST'] ?? '');
        if ($gazda !== '127.0.0.1:8898') {
            header('Content-Type: text/html; charset=utf-8');
            echo Sablon::hibaOldal('A Spotify a bejelentkezés után a http://127.0.0.1:8898/callback címre tér vissza (ezt kell megadni a Spotify-alkalmazásnál is). '
                . 'Ezért a bejelentkezést azon a gépen indítsd, ahol a Közgáz FM fut, ezen a címen: http://127.0.0.1:8898/zene');
            return;
        }
        $allapot = bin2hex(random_bytes(16));
        $ellenorzo = rtrim(strtr(base64_encode(random_bytes(48)), '+/', '-_'), '=');
        $_SESSION['spotify'] = ['allapot' => $allapot, 'ellenorzo' => $ellenorzo, 'ido' => time()];
        header('Location: ' . Spotify::bejelentkezesCim($id, $allapot, $ellenorzo));
        http_response_code(303);
    }

    private function spotifyVisszateres(): void
    {
        $this->app->munkamenet();
        $vart = $_SESSION['spotify'] ?? null;
        unset($_SESSION['spotify']);
        header('Content-Type: text/html; charset=utf-8');
        if (!$vart || ($vart['allapot'] ?? '') !== ($_GET['state'] ?? '') || time() - (int)$vart['ido'] > 600 || empty($_GET['code'])) {
            echo Sablon::hibaOldal('A Spotify-bejelentkezés nem sikerült' . (!empty($_GET['error']) ? ': ' . $_GET['error'] : '') . '. Próbáld újra a Zene oldalon.');
            return;
        }
        (new Spotify(trim($this->app->b['spotify_client_id'])))->kodCsere((string)$_GET['code'], $vart['ellenorzo']);
        Naplo::ir('Spotify: sikeres bejelentkezés');
        header('Location: /zene#spotify');
        http_response_code(303);
    }
}
