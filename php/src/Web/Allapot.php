<?php

declare(strict_types=1);

namespace KozgazFM\Web;

use DateTimeImmutable;
use KozgazFM\Adatbazis;
use KozgazFM\Esemeny;
use KozgazFM\Orarend;
use KozgazFM\SajatHangok;
use KozgazFM\Utvonalak;
use KozgazFM\Zenekeres;

final class Allapot
{
    public const MAI_KERESEK = 30;

    public static function demon(): array
    {
        $adat = json_decode((string)@file_get_contents(Utvonalak::allapotFajl()), true);
        $adat = is_array($adat) ? $adat : [];
        $adat['el'] = isset($adat['ido']) && time() - (int)$adat['ido'] < 10;
        return $adat;
    }

    public static function hangok(array $b): array
    {
        $lista = [['becsengo', 'Becsengő', $b['hang_becsengo']], ['kicsengo', 'Kicsengő', $b['hang_kicsengo']],
            ['jelzo', 'Jelzőcsengő', $b['hang_jelzo']], ['gong', 'Gong', $b['hang_gong']]];
        foreach (SajatHangok::lista() as $h) {
            $lista[] = [$h['ertek'], $h['nev'], $h['ertek']];
        }
        return $lista;
    }

    public static function telefonTiltott(array $b, string $eszkoz): bool
    {
        $ma = date('Y-m-d');
        $kulcs = Zenekeres::telefonKulcs($eszkoz);
        foreach ($b['tiltott_telefonok'] as $t) {
            if ($t['kulcs'] === $kulcs && $t['ig'] >= $ma) {
                return true;
            }
        }
        return false;
    }

    public static function keresek(): Zenekeres
    {
        $k = new Zenekeres();
        try {
            $k->lista = Adatbazis::keresek();
        } catch (\Throwable) {
            $k->lista = [];
        }
        return $k;
    }

    public static function teljes(array $b, bool $admin = true): array
    {
        $most = new DateTimeImmutable();
        $d = self::demon();
        $a = Orarend::allapot($b, $most);
        $hatra = Orarend::hatralevo($a, $most);
        $mire = match ($a['szakasz']) {
            Orarend::SZ_ORA => 'kicsengetésig',
            Orarend::SZ_SZUNET, Orarend::SZ_REGGEL => 'becsengetésig',
            default => '',
        };
        $kovetkezo = null;
        if ($a['kovetkezo']) {
            $k = $a['kovetkezo'];
            $kovetkezo = ['ido' => $k->ido->format('H:i'), 'nap' => $k->ido->format('Y-m-d') === $most->format('Y-m-d') ? 'ma' : $k->ido->format('m.d.'),
                'nap_szoveg' => Orarend::napSzoveg($k->ido, $most), 'leiras' => $k->leiras()];
        }
        $menetrend = [];
        foreach (Orarend::napiEsemenyek($b, $most) as $e) {
            if ($e->csengo() || in_array($e->tipus, Esemeny::KULONLEGES, true) || in_array($e->tipus, [Esemeny::BEMONDAS, Esemeny::ZENE_INDUL], true)) {
                $menetrend[] = ['ido' => $e->ido->format('H:i'), 'leiras' => $e->tipus === Esemeny::ZENE_INDUL ? 'Szünetzene' : $e->leiras(),
                    'tipus' => $e->csengo() ? 'csengo' : $e->nev(), 'mult' => $e->ido <= $most];
            }
        }
        $ma = $most->format('Y-m-d');
        $csend = Orarend::csendben(Orarend::csendesIdoszakok($b, Orarend::nap($most)), $most);
        $zene = $d['zene'] ?? [];
        $forrasok = [];
        foreach ($b['forrasok'] as $i => $f) {
            if ($f['aktiv']) {
                $forrasok[] = ['index' => $i, 'nev' => $f['nev'], 'tipus' => $f['tipus']];
            }
        }
        $orak = Orarend::napiOrak($b, $most);
        $allapot = [
            'ido' => $most->format('Y-m-d\TH:i:s'),
            'verzio' => KFM_VERZIO,
            'cim' => $b['kijelzo_cim'],
            'szakasz' => Orarend::allapotCim($a),
            'szakasz_tipus' => $a['szakasz'],
            'csend' => $csend ? ['nev' => $csend['nev'], 'ig' => $csend['ig'], 'halk' => $csend['csengo_hangero'] > 0] : null,
            'hatra_mp' => $hatra !== null && $mire ? $hatra : null,
            'hatra_mire' => $mire,
            'hossz_mp' => $mire && $a['kezdet'] && $a['vege'] ? $a['vege']->getTimestamp() - $a['kezdet']->getTimestamp() : null,
            'kovetkezo' => $kovetkezo,
            'riasztas' => (bool)($d['riasztas'] ?? false),
            'csengo_szol' => (bool)($d['csengo_szol'] ?? false),
            'bemondas_szol' => (bool)($d['bemondas_szol'] ?? false),
            'zene' => [
                'szol' => (bool)($zene['szol'] ?? false),
                'cim' => (string)($zene['cim'] ?? ''),
                'forras' => $zene['forras'] ?? null,
                'forrasok' => $forrasok,
                'hangero' => $b['zene_hangero'],
                'blokk' => (string)($zene['blokk'] ?? ''),
                'sor' => $zene['sor'] ?? [],
                'keveres' => (bool)$b['keveres'],
                'most_kert' => (bool)($zene['most_kert'] ?? false),
                'kert_db' => count($zene['kertek'] ?? []),
                'kertek' => $zene['kertek'] ?? [],
                'alap' => isset($zene['alap']) ? ['hely' => $zene['alap']['hely'], 'osszes' => $zene['alap']['osszes']] : null,
                'alap_lista' => $zene['alap']['lista'] ?? [],
            ],
            'ma' => ['csengetes' => $b['ma_nincs_csengetes'] !== $ma, 'zene' => $b['ma_nincs_zene'] !== $ma,
                'rend' => $b['kivetelek'][$ma] ?? '', 'rendek' => array_column($b['rendek'], 'nev')],
            'hangok' => array_map(static fn($h) => ['azonosito' => $h[0], 'nev' => $h[1]], self::hangok($b)),
            'menetrend' => $menetrend,
            'idovonal' => array_map(static fn($p) => [$p[0]->format('H:i'), $p[1]->format('H:i')], $orak),
            'sablonok' => $b['bemondas_sablonok'],
            'demon' => ['el' => $d['el'], 'pid' => $d['pid'] ?? null, 'uzenetek' => $d['uzenetek'] ?? []],
        ];
        if ($admin) {
            $keresek = self::keresek();
            $allapot['zenekeres'] = [
                'aktiv' => $b['zenekeres'], 'auto' => $b['zenekeres_auto'],
                'keresek' => array_map([Zenekeres::class, 'admin'], $keresek->fuggo()),
                'mai' => array_map(static fn($k) => Zenekeres::admin($k) + ['telefon_tiltva' => self::telefonTiltott($b, $k['eszkoz'])],
                    array_slice($keresek->mai(), 0, self::MAI_KERESEK)),
                'tiltott_szamok' => array_map(static fn($t) => ['azon' => $t['azon'], 'cim' => $t['cim'], 'ido' => $t['ido']], $b['tiltott_szamok']),
                'tiltott_telefonok' => array_values(array_map(static fn($t) => ['kulcs' => $t['kulcs'], 'nev' => $t['nev'], 'ig' => $t['ig']],
                    array_filter($b['tiltott_telefonok'], static fn($t) => $t['ig'] >= $ma))),
            ];
            $allapot['rendszer'] = [
                'tartalek' => $d['tartalek'] ?? null,
                'keres_szerver' => $d['keres_szerver'] ?? null,
                'zene_szinkron' => $d['zene_szinkron'] ?? null,
                'kimenetek' => $d['kimenetek'] ?? [],
                'kimenet_nev' => $d['kimenet_nev'] ?? null,
                'hianyzo_zonak' => $d['hianyzo_zonak'] ?? [],
                'kiegyenlito' => $d['kiegyenlito'] ?? null,
                'letoltes' => $d['letoltes'] ?? 0,
                'zene_szamok' => $zene['szamok'] ?? 0,
                'tts' => $d['tts'] ?? false,
                'proba_szol' => $d['proba_szol'] ?? false,
            ];
        }
        return $allapot;
    }
}
