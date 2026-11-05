<?php

declare(strict_types=1);

require __DIR__ . '/../src/bootstrap.php';

final class TesztHiba extends RuntimeException
{
}

final class TesztKihagyva extends RuntimeException
{
}

function minta(string $nev): string
{
    $ut = is_file(__DIR__ . '/minta/' . $nev) ? __DIR__ . '/minta/' . $nev : __DIR__ . '/adat/' . $nev;
    if (!is_file($ut)) {
        throw new TesztKihagyva("nincs meg a tests/adat/{$nev} mintafájl");
    }
    return $ut;
}

function egyezik(mixed $vart, mixed $kapott, string $uzenet = ''): void
{
    if ($vart !== $kapott) {
        throw new TesztHiba(($uzenet ? $uzenet . ': ' : '') . 'várt ' . var_export($vart, true) . ', kapott ' . var_export($kapott, true));
    }
}

function igaz(bool $feltetel, string $uzenet = 'feltétel nem teljesült'): void
{
    if (!$feltetel) {
        throw new TesztHiba($uzenet);
    }
}

function dobja(callable $fv, string $osztaly, string $uzenet = ''): void
{
    try {
        $fv();
    } catch (Throwable $e) {
        if ($e instanceof $osztaly) {
            return;
        }
        throw new TesztHiba("{$osztaly} helyett " . get_class($e) . ': ' . $e->getMessage());
    }
    throw new TesztHiba($uzenet ?: "{$osztaly} kivételt vártunk");
}

$szuro = $argv[1] ?? '';
$ideiglenes = sys_get_temp_dir() . '/kfm-teszt-' . getmypid();
@mkdir($ideiglenes, 0700, true);
putenv("KOZGAZ_FM_ADAT={$ideiglenes}");

foreach (glob(__DIR__ . '/*Teszt.php') as $fajl) {
    require $fajl;
}

$sikeres = 0;
$hibak = [];
$kihagyott = [];
foreach (get_defined_functions()['user'] as $fv) {
    if (!str_starts_with($fv, 'teszt_') || ($szuro && !str_contains($fv, $szuro))) {
        continue;
    }
    try {
        $fv();
        $sikeres++;
        echo '.';
    } catch (TesztKihagyva $e) {
        $kihagyott[] = "{$fv}: " . $e->getMessage();
        echo 'S';
    } catch (Throwable $e) {
        $hibak[] = "{$fv}: " . $e->getMessage() . ' (' . basename($e->getFile()) . ':' . $e->getLine() . ')';
        echo 'F';
    }
}
echo "\n";
foreach ($hibak as $h) {
    echo "HIBA {$h}\n";
}
foreach ($kihagyott as $k) {
    echo "KIHAGYVA {$k}\n";
}
echo $sikeres . ' sikeres, ' . count($hibak) . ' hibás, ' . count($kihagyott) . " kihagyva\n";
exec('rm -rf ' . escapeshellarg($ideiglenes));
exit($hibak ? 1 : 0);
