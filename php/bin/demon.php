<?php

declare(strict_types=1);

require dirname(__DIR__) . '/src/bootstrap.php';

use KozgazFM\Naplo;
use KozgazFM\Utvonalak;
use KozgazFM\Vezerlo;

$zar = fopen(Utvonalak::adat() . '/demon.lock', 'c');
if (!$zar || !flock($zar, LOCK_EX | LOCK_NB)) {
    fwrite(STDERR, "Már fut egy Közgáz FM démon.\n");
    exit(1);
}

$fut = true;
if (function_exists('pcntl_async_signals')) {
    pcntl_async_signals(true);
    foreach ([SIGTERM, SIGINT] as $jel) {
        pcntl_signal($jel, static function () use (&$fut): void {
            $fut = false;
        });
    }
    pcntl_signal(SIGCHLD, SIG_DFL);
}

Utvonalak::mappa('munkamenetek');
$v = new Vezerlo();
$v->indit();
$utem = 0.1;
while ($fut) {
    $kezdet = microtime(true);
    try {
        $v->tick();
    } catch (Throwable $e) {
        Naplo::ir('HIBA: a démon ütemében: ' . get_class($e) . ': ' . $e->getMessage() . ' (' . basename($e->getFile()) . ':' . $e->getLine() . ')');
        usleep(500000);
    }
    $hatra = $utem - (microtime(true) - $kezdet);
    if ($hatra > 0) {
        usleep((int)($hatra * 1e6));
    }
}
$v->log('A Közgáz FM démon leáll');
$v->leallit();
flock($zar, LOCK_UN);
