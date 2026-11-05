<?php

declare(strict_types=1);

require dirname(__DIR__) . '/src/bootstrap.php';

use KozgazFM\Beallitasok;
use KozgazFM\Utvonalak;
use KozgazFM\Zar;

function munkamenetek_torlese(): void
{
    foreach (glob(Utvonalak::mappa('munkamenetek') . '/*') ?: [] as $fajl) {
        @unlink($fajl);
    }
}

$parancs = $argv[1] ?? '';
$b = Beallitasok::betolt();
switch ($parancs) {
    case 'pin-torles':
        $b['admin_pin'] = '';
        Beallitasok::ment($b);
        echo "A PIN-kód törölve, a többi beállítás megmaradt.\n";
        exit(0);
    case 'jelszo-torles':
        $b['web_jelszo'] = '';
        Beallitasok::ment($b);
        munkamenetek_torlese();
        echo "A webes jelszó törölve. A következő megnyitáskor új jelszót kell megadni.\n";
        exit(0);
    case 'jelszo':
        $jelszo = trim((string)stream_get_contents(STDIN));
        if (!Zar::jelszoErvenyes($jelszo)) {
            fwrite(STDERR, "A jelszó legalább 8 karakter legyen.\n");
            exit(1);
        }
        $b['web_jelszo'] = Zar::jelszoHash($jelszo);
        Beallitasok::ment($b);
        munkamenetek_torlese();
        exit(0);
    case 'van-jelszo':
        exit($b['web_jelszo'] !== '' ? 0 : 1);
}
fwrite(STDERR, "Használat: php bin/kezelo.php pin-torles|jelszo-torles|jelszo (a jelszó a bemeneten)|van-jelszo\n");
exit(2);
