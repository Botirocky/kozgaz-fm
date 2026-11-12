<?php

declare(strict_types=1);

date_default_timezone_set('Europe/Budapest');
mb_internal_encoding('UTF-8');

spl_autoload_register(static function (string $osztaly): void {
    $elotag = 'KozgazFM\\';
    if (!str_starts_with($osztaly, $elotag)) {
        return;
    }
    $ut = __DIR__ . '/' . str_replace('\\', '/', substr($osztaly, strlen($elotag))) . '.php';
    if (is_file($ut)) {
        require $ut;
    }
});

const KFM_VERZIO = '1.19.2';
