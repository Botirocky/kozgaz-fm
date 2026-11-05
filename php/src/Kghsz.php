<?php

declare(strict_types=1);

namespace KozgazFM;

use DateInterval;
use DateTimeImmutable;
use DateTimeZone;

final class Kghsz
{
    public const ALAP_CIM = 'https://kghsz.hu';
    public const OLDAL_CSENGETES = '/rolunk/nyitvatartas';
    public const OLDAL_HAZIREND = '/szakmai-dokumentumok/hazirend';
    public const OLDAL_TANEV = '/tanuloinknak/tanev-rendje';
    public const OLDAL_ESEMENYEK = '/tanuloinknak/esemenyek';
    private const HONAPOK = ['január' => 1, 'február' => 2, 'március' => 3, 'április' => 4, 'május' => 5, 'június' => 6,
        'július' => 7, 'augusztus' => 8, 'szeptember' => 9, 'október' => 10, 'november' => 11, 'december' => 12];
    private const ORA_SOR = '/(\d{1,2})\.(?:\s*óra)?\s*\|\s*(\d{1,2}:\d{2})\s*(?:-|–|\|)\s*(\d{1,2}:\d{2})/u';
    private const BLOKKOK = ['p', 'br', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'table'];

    private static function datumMinta(): string
    {
        return '(\d{4})\.\s*(' . implode('|', array_keys(self::HONAPOK)) . ')\s+(\d{1,2})\.';
    }

    private static function tiszta(string $s): string
    {
        return trim((string)preg_replace('/\s+/u', ' ', str_replace("\u{a0}", ' ', $s)));
    }

    public static function sorok(string $html): array
    {
        if (trim($html) === '') {
            return [];
        }
        $dom = new \DOMDocument();
        libxml_use_internal_errors(true);
        $dom->loadHTML('<?xml encoding="utf-8"?><div>' . $html . '</div>', LIBXML_NOERROR | LIBXML_NOWARNING);
        libxml_clear_errors();
        $sorok = [];
        $kint = '';
        $lezar = static function () use (&$kint, &$sorok): void {
            $s = self::tiszta($kint);
            if ($s !== '') {
                $sorok[] = $s;
            }
            $kint = '';
        };
        $cellaSzoveg = static function (\DOMNode $n) use (&$cellaSzoveg): string {
            $szoveg = '';
            foreach ($n->childNodes as $c) {
                if ($c instanceof \DOMText) {
                    $szoveg .= $c->nodeValue;
                } elseif ($c instanceof \DOMElement) {
                    if (in_array(strtolower($c->tagName), ['p', 'br', 'div', 'li'], true)) {
                        $szoveg .= ' ';
                    }
                    $szoveg .= $cellaSzoveg($c);
                }
            }
            return $szoveg;
        };
        $bejar = static function (\DOMNode $n) use (&$bejar, &$kint, &$sorok, $lezar, $cellaSzoveg): void {
            foreach ($n->childNodes as $c) {
                if ($c instanceof \DOMText) {
                    $kint .= $c->nodeValue;
                    continue;
                }
                if (!$c instanceof \DOMElement) {
                    continue;
                }
                $tag = strtolower($c->tagName);
                if ($tag === 'tr') {
                    $lezar();
                    $cellak = [];
                    foreach ($c->childNodes as $cella) {
                        if ($cella instanceof \DOMElement && in_array(strtolower($cella->tagName), ['td', 'th'], true)) {
                            $t = self::tiszta($cellaSzoveg($cella));
                            if ($t !== '') {
                                $cellak[] = $t;
                            }
                        }
                    }
                    if ($cellak) {
                        $sorok[] = implode(' | ', $cellak);
                    }
                    continue;
                }
                $blokk = in_array($tag, self::BLOKKOK, true);
                if ($blokk) {
                    $lezar();
                }
                $bejar($c);
                if ($blokk && $tag !== 'br') {
                    $lezar();
                }
            }
        };
        $bejar($dom->getElementsByTagName('div')->item(0));
        $lezar();
        return $sorok;
    }

    public static function oldalAdat(string $html): array
    {
        if (!preg_match('/<script id="__NEXT_DATA__"[^>]*>(.*?)<\/script>/s', $html, $m)) {
            throw new Hiba('Az iskola honlapjának szerkezete megváltozott (nincs adatblokk).');
        }
        $adat = json_decode($m[1], true)['props']['pageProps'] ?? null;
        if (!is_array($adat)) {
            throw new Hiba('Az iskola honlapjának adatai nem értelmezhetők.');
        }
        return $adat;
    }

    private static function ido(string $s): string
    {
        [$o, $p] = explode(':', $s);
        return sprintf('%02d:%s', (int)$o, $p);
    }

    public static function ervenyesOrak(array $orak): bool
    {
        if (!$orak) {
            return false;
        }
        $idopontok = [];
        foreach ($orak as $o) {
            $idopontok[] = $o['kezdet'];
            $idopontok[] = $o['vege'];
        }
        $rendezett = $idopontok;
        sort($rendezett);
        foreach ($idopontok as $i) {
            if (!preg_match('/^([01]\d|2[0-3]):[0-5]\d$/', $i)) {
                return false;
            }
        }
        return $idopontok === $rendezett;
    }

    public static function orakSorokbol(array $sorok): array
    {
        $orak = [];
        foreach ($sorok as $s) {
            if (preg_match(self::ORA_SOR, $s, $t)) {
                $orak[] = [(int)$t[1], ['kezdet' => self::ido($t[2]), 'vege' => self::ido($t[3])]];
            }
        }
        usort($orak, static fn($a, $b) => $a[0] <=> $b[0]);
        return array_column($orak, 1);
    }

    public static function csengetesiRend(string $csengetesHtml, ?string $hazirendHtml): array
    {
        $adat = self::oldalAdat($csengetesHtml)['data'] ?? [];
        $normal = self::orakSorokbol(self::sorok((string)($adat['ringNormal'] ?? '')));
        $rovid = self::orakSorokbol(self::sorok((string)($adat['ringShort'] ?? '')));
        $valodiRovid = self::ervenyesOrak($rovid) && $rovid !== $normal ? $rovid : null;
        if ($hazirendHtml) {
            $reszlet = self::sorok((string)((self::oldalAdat($hazirendHtml)['data'] ?? [])['info'] ?? ''));
            foreach ($reszlet as $i => $s) {
                if (str_contains($s, 'Csengetési órarend') && !str_contains($s, '|')) {
                    $hazirendi = self::orakSorokbol(array_filter(array_slice($reszlet, $i + 1, 15), static fn($s) => preg_match(self::ORA_SOR, $s)));
                    if (self::ervenyesOrak($hazirendi)) {
                        $normal = $hazirendi;
                    }
                    break;
                }
            }
        }
        if (!self::ervenyesOrak($normal)) {
            throw new Hiba('A csengetési rend nem olvasható ki az iskola honlapjáról.');
        }
        return [$normal, $valodiRovid];
    }

    private static function datum(array $t, int $eltolas = 1): DateTimeImmutable
    {
        return new DateTimeImmutable(sprintf('%04d-%02d-%02d', (int)$t[$eltolas], self::HONAPOK[$t[$eltolas + 1]], (int)$t[$eltolas + 2]));
    }

    public static function tanevEsemenyek(string $html): array
    {
        $sorok = self::sorok((string)((self::oldalAdat($html)['data'] ?? [])['currentInfo'] ?? ''));
        $dm = self::datumMinta();
        $esemenyek = [];
        $szunet = null;
        $szakasz = '';
        foreach ($sorok as $sor) {
            if (preg_match('/^(Őszi|Téli|Tavaszi) szünet\b/u', $sor, $nev)) {
                $szunet = $nev[0];
                continue;
            }
            if (str_starts_with($sor, 'Tanításmentes munkanapok')) {
                $szakasz = 'mentes';
                continue;
            }
            if (str_starts_with($sor, 'Érettségi vizsganapok')) {
                $szakasz = '';
                continue;
            }
            $elozo = preg_match("/előtti utolsó tanítási nap\s+{$dm}/u", $sor, $e1);
            $utani = preg_match("/utáni első tanítási nap\s+{$dm}/u", $sor, $e2);
            if ($szunet && $elozo && $utani) {
                $tol = self::datum($e1)->add(new DateInterval('P1D'));
                $ig = self::datum($e2)->sub(new DateInterval('P1D'));
                if ($tol <= $ig && $ig <= $tol->add(new DateInterval('P60D'))) {
                    $esemenyek[] = NaptarImport::esemeny($szunet, $tol, $ig);
                }
                $szunet = null;
                continue;
            }
            if (preg_match("/^Utolsó tanítási nap\s*\|\s*{$dm}/u", $sor, $u)) {
                $nap = self::datum($u);
                $vege = new DateTimeImmutable($nap->format('Y') . '-08-31');
                if ($nap < $vege) {
                    $esemenyek[] = NaptarImport::esemeny('Nyári szünet', $nap->add(new DateInterval('P1D')), $vege);
                }
                continue;
            }
            if ($szakasz === 'mentes' && preg_match("/^\d+\.\s*\|\s*{$dm}\s*\|\s*(.+)/u", $sor, $m)) {
                $nap = self::datum($m);
                $esemenyek[] = NaptarImport::esemeny("Tanításmentes munkanap: {$m[4]}", $nap, $nap);
            }
        }
        $vanSzunet = false;
        foreach ($esemenyek as $e) {
            if (str_ends_with($e['nev'], 'szünet')) {
                $vanSzunet = true;
            }
        }
        if (!$vanSzunet) {
            throw new Hiba('A tanév rendje nem olvasható ki az iskola honlapjáról.');
        }
        return $esemenyek;
    }

    private static function helyiNap(string $ertek): DateTimeImmutable
    {
        return (new DateTimeImmutable(str_replace('Z', '+00:00', $ertek)))->setTimezone(new DateTimeZone(date_default_timezone_get()))->setTime(0, 0);
    }

    public static function honlapiEsemenyek(string $html, DateTimeImmutable $tol): array
    {
        $lista = self::oldalAdat($html)['events'] ?? null;
        if (!is_array($lista)) {
            throw new Hiba('Az iskola eseménynaptára nem értelmezhető.');
        }
        $esemenyek = [];
        foreach ($lista as $e) {
            try {
                $kezdet = self::helyiNap((string)$e['startDate']);
                $veg = !empty($e['endDate']) ? self::helyiNap((string)$e['endDate']) : $kezdet;
                $nev = mb_substr(self::tiszta((string)$e['title']), 0, 120);
            } catch (\Throwable) {
                continue;
            }
            if ($nev !== '' && $kezdet <= $veg && $veg <= $kezdet->add(new DateInterval('P120D')) && $veg >= $tol) {
                $esemenyek[] = NaptarImport::esemeny($nev, $kezdet, $veg);
            }
        }
        return $esemenyek;
    }

    public static function osszevon(array $tanev, array $honlapi, array $b): array
    {
        $foglalt = [];
        foreach ($tanev as $e) {
            foreach (NaptarImport::napok($e) as $n) {
                $foglalt[$n->format('Y-m-d')] = true;
            }
        }
        $pluszok = array_filter($honlapi, static function ($e) use ($foglalt, $b): bool {
            if (NaptarImport::besorol($e, $b)['muvelet'] !== NaptarImport::SZUNNAP) {
                return true;
            }
            foreach (NaptarImport::napok($e) as $n) {
                if (isset($foglalt[$n->format('Y-m-d')])) {
                    return false;
                }
            }
            return true;
        });
        $osszes = array_merge($tanev, array_values($pluszok));
        usort($osszes, static fn($a, $c) => [$a['tol'], $a['ig'], $a['nev']] <=> [$c['tol'], $c['ig'], $c['nev']]);
        return $osszes;
    }

    private static function letolt(string $oldal): string
    {
        [$kod, $adat, $hiba] = Http::keres('GET', self::ALAP_CIM . $oldal, null, ['User-Agent: Mozilla/5.0 (KozgazFM)'], 20, NaptarImport::MAX_MERET);
        if ($kod !== 200) {
            throw new Hiba('Az iskola honlapja nem érhető el: ' . ($hiba ?: "HTTP {$kod}"));
        }
        return $adat;
    }

    public static function letoltes(array $b, ?DateTimeImmutable $ma = null): array
    {
        $ma ??= new DateTimeImmutable('today');
        try {
            $hazirend = self::letolt(self::OLDAL_HAZIREND);
        } catch (Hiba) {
            $hazirend = null;
        }
        [$normal, $rovid] = self::csengetesiRend(self::letolt(self::OLDAL_CSENGETES), $hazirend);
        $tanev = self::tanevEsemenyek(self::letolt(self::OLDAL_TANEV));
        try {
            $honlapi = self::honlapiEsemenyek(self::letolt(self::OLDAL_ESEMENYEK), $ma);
        } catch (Hiba) {
            $honlapi = [];
        }
        return ['normal' => $normal, 'rovid' => $rovid, 'esemenyek' => self::osszevon($tanev, $honlapi, $b)];
    }

    public static function orakSzoveg(array $orak): string
    {
        return $orak ? count($orak) . ' óra, ' . $orak[0]['kezdet'] . '–' . $orak[count($orak) - 1]['vege'] : 'nincs megadva';
    }

    public static function rendAtvetel(array $b, array $adatok): array
    {
        $valtozott = [];
        foreach (['Normál' => $adatok['normal'], 'Rövidített' => $adatok['rovid']] as $nev => $orak) {
            if ($orak === null) {
                continue;
            }
            $rend = Beallitasok::rend($b, $nev);
            if ($rend === null || $rend['orak'] !== $orak) {
                $valtozott[] = $nev;
            }
        }
        return $valtozott;
    }

    public static function rendAlkalmaz(array $b, array $adatok): array
    {
        $valtozott = self::rendAtvetel($b, $adatok);
        foreach (['Normál' => $adatok['normal'], 'Rövidített' => $adatok['rovid']] as $nev => $orak) {
            if ($orak === null || !in_array($nev, $valtozott, true)) {
                continue;
            }
            $megvan = false;
            foreach ($b['rendek'] as &$r) {
                if ($r['nev'] === $nev) {
                    $r['orak'] = $orak;
                    $megvan = true;
                }
            }
            unset($r);
            if (!$megvan) {
                $b['rendek'][] = ['nev' => $nev, 'orak' => $orak];
            }
        }
        return [$b, $valtozott];
    }
}
