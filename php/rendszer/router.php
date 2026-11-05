<?php

declare(strict_types=1);

$ut = (string)parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);
if (str_starts_with($ut, '/statikus/')) {
    $fajl = realpath(__DIR__ . '/../public' . $ut);
    $gyoker = realpath(__DIR__ . '/../public/statikus');
    if ($fajl === false || $gyoker === false || !str_starts_with($fajl, $gyoker . '/') || !is_file($fajl)) {
        http_response_code(404);
        return true;
    }
    $tipusok = ['css' => 'text/css; charset=utf-8', 'js' => 'text/javascript; charset=utf-8', 'png' => 'image/png',
        'svg' => 'image/svg+xml', 'html' => 'text/html; charset=utf-8', 'json' => 'application/json', 'ico' => 'image/x-icon',
        'woff2' => 'font/woff2', 'mp3' => 'audio/mpeg', 'webmanifest' => 'application/manifest+json'];
    header('Content-Type: ' . ($tipusok[strtolower(pathinfo($fajl, PATHINFO_EXTENSION))] ?? 'application/octet-stream'));
    header('Cache-Control: public, max-age=86400');
    header('X-Content-Type-Options: nosniff');
    header('Content-Length: ' . filesize($fajl));
    readfile($fajl);
    return true;
}
require __DIR__ . '/../public/index.php';
