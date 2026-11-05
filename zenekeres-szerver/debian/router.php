<?php
$ut = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
if (preg_match('#^/[A-Za-z0-9._-]+\.(css|js|png)$#', $ut) && is_file(__DIR__ . '/public' . $ut)) {
    return false;
}
require __DIR__ . '/public/index.php';
