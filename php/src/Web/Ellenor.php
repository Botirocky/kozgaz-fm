<?php

declare(strict_types=1);

namespace KozgazFM\Web;

use KozgazFM\Beallitasok;
use KozgazFM\Ertesito;
use KozgazFM\Hiba;
use KozgazFM\Szuro;
use KozgazFM\Tartalek;

final class Ellenor
{
    private const IDO = '/^([01]\d|2[0-3]):[0-5]\d$/';
    private const DATUM = '/^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/';

    private static function hiba(string $uzenet): never
    {
        throw new Hiba($uzenet, 'validation_error', 422);
    }

    private static function ido(string $s, string $hol): void
    {
        if (!preg_match(self::IDO, $s)) {
            self::hiba("{$hol}: az időpont ÓÓ:PP alakú legyen (pl. 08:15), ez nem jó: „{$s}”.");
        }
    }

    private static function datum(string $s, string $hol): void
    {
        if (!preg_match(self::DATUM, $s)) {
            self::hiba("{$hol}: a dátum ÉÉÉÉ-HH-NN alakú legyen, ez nem jó: „{$s}”.");
        }
    }

    private static function tartomany(int|float $ertek, int|float $min, int|float $max, string $hol): void
    {
        if ($ertek < $min || $ertek > $max) {
            self::hiba("{$hol}: {$min} és {$max} között legyen.");
        }
    }

    public static function ellenoriz(array $b, array $kulcsok): void
    {
        $k = array_flip($kulcsok);
        if (isset($k['rendek'])) {
            $nevek = [];
            foreach ($b['rendek'] as $r) {
                $nev = trim($r['nev']);
                if ($nev === '') {
                    self::hiba('Minden csengetési rendnek legyen neve.');
                }
                if (isset($nevek[$nev])) {
                    self::hiba("Két csengetési rend neve is „{$nev}”.");
                }
                $nevek[$nev] = true;
                foreach ($r['orak'] as $i => $o) {
                    self::ido($o['kezdet'], "{$nev}, " . ($i + 1) . '. óra kezdete');
                    self::ido($o['vege'], "{$nev}, " . ($i + 1) . '. óra vége');
                    if ($o['vege'] <= $o['kezdet']) {
                        self::hiba("{$nev}, " . ($i + 1) . '. óra: a vége a kezdete után legyen.');
                    }
                }
            }
        }
        $rendNevek = array_column($b['rendek'], 'nev');
        if (isset($k['het']) || isset($k['rendek'])) {
            foreach ($b['het'] as $i => $n) {
                if ($n !== '' && !in_array($n, $rendNevek, true)) {
                    self::hiba(Beallitasok::NAPOK[$i] . ": nincs „{$n}” nevű csengetési rend.");
                }
            }
        }
        if (isset($k['kivetelek'])) {
            foreach ($b['kivetelek'] as $nap => $n) {
                self::datum((string)$nap, 'Kivételnap');
                if (!in_array($n, $rendNevek, true)) {
                    self::hiba("{$nap}: nincs „{$n}” nevű csengetési rend.");
                }
            }
        }
        if (isset($k['szunnapok'])) {
            foreach ($b['szunnapok'] as $s) {
                self::datum($s['tol'], 'Szünnap kezdete');
                self::datum($s['ig'] ?: $s['tol'], 'Szünnap vége');
                if (($s['ig'] ?: $s['tol']) < $s['tol']) {
                    self::hiba("Szünnap ({$s['nev']}): a vége ne legyen a kezdete előtt.");
                }
            }
        }
        if (isset($k['bemondasok'])) {
            foreach ($b['bemondasok'] as $bem) {
                $hol = 'Bemondás (' . ($bem['nev'] ?: 'névtelen') . ')';
                self::ido($bem['ido'], $hol);
                if ($bem['datum'] !== '') {
                    self::datum($bem['datum'], $hol);
                }
                if (!in_array($bem['tipus'], ['szoveg', 'fajl'], true)) {
                    self::hiba("{$hol}: a típus szöveg vagy fájl legyen.");
                }
                if (trim($bem['tartalom']) === '') {
                    self::hiba("{$hol}: üres a tartalma.");
                }
                foreach ($bem['napok'] as $n) {
                    self::tartomany($n, 0, 6, "{$hol}, nap");
                }
            }
        }
        if (isset($k['rendkivuli'])) {
            foreach ($b['rendkivuli'] as $r) {
                $hol = 'Rendkívüli esemény (' . ($r['nev'] ?: 'névtelen') . ')';
                if (!isset(Beallitasok::RENDKIVULI_TIPUSOK[$r['tipus']])) {
                    self::hiba("{$hol}: ismeretlen típus.");
                }
                self::datum($r['datum'], $hol);
                self::ido($r['tol'], $hol);
                if ($r['tipus'] === 'csend') {
                    self::ido($r['ig'], "{$hol}, vége");
                    if ($r['ig'] <= $r['tol']) {
                        self::hiba("{$hol}: a vége a kezdete után legyen.");
                    }
                }
                self::tartomany($r['riado_perc'], 0, 60, "{$hol}, riasztás hossza");
                self::tartomany($r['csengo_hangero'], 0, 100, "{$hol}, csengő hangereje");
            }
        }
        if (isset($k['forrasok'])) {
            foreach ($b['forrasok'] as $f) {
                if (!isset(Beallitasok::FORRAS_TIPUSOK[$f['tipus']])) {
                    self::hiba('Ismeretlen zeneforrás-típus: ' . $f['tipus']);
                }
                if (trim($f['nev']) === '' || trim($f['cim']) === '') {
                    self::hiba('Minden zeneforrásnak legyen neve és címe/útvonala.');
                }
            }
            $nevek = array_column($b['forrasok'], 'nev');
            if (count($nevek) !== count(array_unique($nevek))) {
                self::hiba('Két zeneforrásnak nem lehet ugyanaz a neve (a műsorblokkok név szerint hivatkoznak rájuk).');
            }
        }
        if (isset($k['musorblokkok'])) {
            foreach ($b['musorblokkok'] as $m) {
                if (trim($m['nev']) === '') {
                    self::hiba('Minden műsorblokknak legyen neve.');
                }
                foreach ($m['szunetek'] as $sz) {
                    self::tartomany($sz, 0, 20, "{$m['nev']}, szünet");
                }
            }
        }
        if (isset($k['zene_kihagyott_szunetek'])) {
            foreach ($b['zene_kihagyott_szunetek'] as $sz) {
                self::tartomany($sz, 0, 20, 'Zene nélküli szünet');
            }
        }
        if (isset($k['zenekeres_oldal']) && trim($b['zenekeres_oldal']) !== '' && !preg_match('#^https?://#', trim($b['zenekeres_oldal']))) {
            self::hiba('A kérő oldal címe http:// vagy https:// kezdetű legyen.');
        }
        if (isset($k['zonak'])) {
            foreach ($b['zonak'] as $z) {
                self::tartomany($z['hangero'], 0, 100, 'Zóna hangereje');
            }
        }
        foreach (['reggeli_zene_tol', 'ertesites_reggel_ido'] as $m) {
            if (isset($k[$m])) {
                self::ido($b[$m], $m === 'reggeli_zene_tol' ? 'Reggeli zene' : 'Reggeli önteszt');
            }
        }
        $tartomanyok = [
            'jelzo_perc' => [0, 15, 'Jelzőcsengő'], 'csengo_hangero' => [0, 100, 'Csengő hangereje'], 'zene_hangero' => [0, 100, 'Zene hangereje'],
            'zene_min_szunet' => [0, 60, 'Legrövidebb zenés szünet'], 'zene_kesleltetes' => [0, 600, 'Zene késleltetése'],
            'zene_leall_elotte' => [0, 600, 'Zene leállása'], 'elhalkitas' => [0, 15, 'Elhalkítás'], 'atusztatas' => [0, 12, 'Átúsztatás'],
            'zenekeres_napi' => [1, 50, 'Napi kérés'], 'zenekeres_max_perc' => [1, 60, 'Leghosszabb kért szám'],
            'admin_zar_perc' => [1, 240, 'Automatikus zárolás'], 'smtp_port' => [1, 65535, 'SMTP-port'], 'web_port' => [1, 65535, 'Port'],
        ];
        foreach ($tartomanyok as $m => [$min, $max, $hol]) {
            if (isset($k[$m])) {
                self::tartomany($b[$m], $min, $max, $hol);
            }
        }
        foreach (Beallitasok::HANG_MEZOK as $m => $alap) {
            if (isset($k[$m]) && !str_starts_with($b[$m], 'beepitett:') && !str_starts_with($b[$m], 'sajat:')) {
                self::hiba('Csak beépített vagy feltöltött saját hang választható.');
            }
        }
        if (isset($k['szuro_erzekenyseg']) && !isset(Szuro::ERZEKENYSEGEK[$b['szuro_erzekenyseg']])) {
            self::hiba('Ismeretlen szűrő-érzékenység.');
        }
        if (isset($k['smtp_mod']) && !isset(Ertesito::SMTP_MODOK[$b['smtp_mod']])) {
            self::hiba('Ismeretlen SMTP-mód.');
        }
        if (isset($k['tartalek_mod']) && !isset(Tartalek::SZEREPEK[$b['tartalek_mod']])) {
            self::hiba('Ismeretlen tartalékgép-szerep.');
        }
        if (isset($k['ertesites_ntfy']) && trim($b['ertesites_ntfy']) !== '') {
            Ertesito::ntfyCel($b['ertesites_ntfy']);
        }
        if (isset($k['ertesites_esemenyek'])) {
            foreach ($b['ertesites_esemenyek'] as $e) {
                if (!isset(Ertesito::ESEMENYEK[$e])) {
                    self::hiba("Ismeretlen értesítési esemény: {$e}");
                }
            }
        }
    }
}
