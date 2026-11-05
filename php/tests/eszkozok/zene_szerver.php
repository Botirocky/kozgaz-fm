<?php

declare(strict_types=1);

$gyoker = getenv('KFM_TESZT_ZENE');
$ut = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
if (($_SERVER['HTTP_X_KOZGAZ_FM_KULCS'] ?? '') !== 'jo-kulcs') {
    http_response_code(401);
    exit;
}
if ($ut === '/api/zenek') {
    $lista = [];
    $it = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($gyoker, FilesystemIterator::SKIP_DOTS));
    foreach ($it as $f) {
        $lista[] = ['ut' => substr($f->getPathname(), strlen($gyoker) + 1), 'meret' => $f->getSize(), 'ido' => $f->getMTime()];
    }
    header('Content-Type: application/json');
    echo json_encode(['data' => $lista]);
    exit;
}
if ($ut === '/api/zenek/fajl') {
    $fajl = $gyoker . '/' . ($_GET['ut'] ?? '');
    $adat = (string)file_get_contents($fajl);
    if (preg_match('/bytes=(\d+)-/', $_SERVER['HTTP_RANGE'] ?? '', $m)) {
        http_response_code(206);
        $adat = substr($adat, (int)$m[1]);
    }
    echo $adat;
    exit;
}
http_response_code(404);
