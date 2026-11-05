<?php

declare(strict_types=1);

namespace KozgazFM;

final class Ertesito
{
    public const ESEMENYEK = [
        'kimaradt' => 'Kimaradt csengetés (pl. alvás vagy óraugrás után)',
        'hiba' => 'Hibák: hiányzó hangfájl, zenehiba, nincs felolvasó hang',
        'hangkimenet' => 'Eltűnt vagy nem elérhető hangkimenet',
        'riasztas' => 'Riasztás indult',
        'tartalek' => 'A tartalékgép átvette vagy visszaadta a csengetést',
        'indulas' => 'A program elindult (pl. összeomlás vagy áramszünet után)',
        'reggel' => 'Reggeli önteszt tanítási napokon',
    ];
    public const SMTP_MODOK = ['starttls' => 'STARTTLS (587)', 'ssl' => 'SSL/TLS (465)', 'nincs' => 'Titkosítás nélkül (csak belső hálón)'];
    public const ISMETLES_MP = 1800;
    private const PRIORITAS = ['info' => 3, 'figy' => 4, 'hiba' => 5];
    private const CIMKE = ['info' => 'white_check_mark', 'figy' => 'warning', 'hiba' => 'rotating_light'];

    private array $legutobb = [];

    public function __construct(private readonly \Closure $beallitasok, private readonly Hatter $hatter, private readonly \Closure $naplo)
    {
    }

    public static function ntfyCel(string $url): array
    {
        $r = parse_url(trim($url));
        if (!is_array($r) || !in_array($r['scheme'] ?? '', ['http', 'https'], true) || empty($r['host'])) {
            throw new Hiba('Az ntfy-cím http:// vagy https:// kezdetű legyen, pl. https://ntfy.sh/kozgaz-fm-xyz');
        }
        $ut = array_values(array_filter(explode('/', $r['path'] ?? ''), 'strlen'));
        $tema = end($ut);
        if (!$ut || !preg_match('/^[-_A-Za-z0-9]{1,64}$/', (string)$tema)) {
            throw new Hiba('Az ntfy-cím végén a téma (topic) neve legyen: betű, szám, - vagy _.');
        }
        $port = isset($r['port']) ? ':' . $r['port'] : '';
        return ["{$r['scheme']}://{$r['host']}{$port}/" . implode('/', array_slice($ut, 0, -1)), (string)$tema];
    }

    public static function ntfyKuld(string $url, string $token, string $cim, string $uzenet, string $szint): void
    {
        [$alap, $tema] = self::ntfyCel($url);
        $fejlec = ['Content-Type: application/json', 'User-Agent: KozgazFM'];
        if (trim($token) !== '') {
            $fejlec[] = 'Authorization: Bearer ' . trim($token);
        }
        [$kod, , $hiba] = Http::keres('POST', $alap, json_encode(['topic' => $tema, 'title' => mb_substr($cim, 0, 250),
            'message' => mb_substr($uzenet, 0, 3500), 'priority' => self::PRIORITAS[$szint] ?? 3, 'tags' => [self::CIMKE[$szint] ?? 'bell']],
            JSON_UNESCAPED_UNICODE), $fejlec, 15);
        if ($kod === 0) {
            throw new Hiba("Az ntfy-szerver nem érhető el: {$hiba}");
        }
        if ($kod >= 400) {
            throw new Hiba("Az ntfy-szerver {$kod}-as hibát adott" . (in_array($kod, [401, 403], true) ? ' (hibás vagy hiányzó token?)' : '') . '.');
        }
    }

    public static function cimzettek(string $szoveg): array
    {
        return array_values(array_filter(array_map('trim', preg_split('/[,;\s]+/', $szoveg) ?: []), static fn($c) => str_contains($c, '@')));
    }

    public static function emailKuld(array $b, string $cim, string $uzenet): void
    {
        $lista = self::cimzettek($b['ertesites_email']);
        if (!$lista || trim($b['smtp_szerver']) === '') {
            throw new Hiba('Add meg a címzettet és az SMTP-szervert.');
        }
        $felado = trim($b['smtp_felado']) ?: (trim($b['smtp_felhasznalo']) ?: $lista[0]);
        (new Smtp(trim($b['smtp_szerver']), (int)$b['smtp_port'], $b['smtp_mod']))->kuld(trim($b['smtp_felhasznalo']),
            $b['smtp_jelszo'], $felado, $lista, 'Közgáz FM: ' . $cim, $uzenet);
    }

    public static function csatornak(array $b): array
    {
        $lista = [];
        if (trim($b['ertesites_ntfy']) !== '') {
            $lista[] = 'ntfy';
        }
        if (trim($b['ertesites_email']) !== '' && trim($b['smtp_szerver']) !== '') {
            $lista[] = 'e-mail';
        }
        return $lista;
    }

    public static function kikuld(array $b, string $cim, string $uzenet, string $szint): array
    {
        $hibak = [];
        $teljes = $uzenet . "\n\n– " . gethostname() . ', ' . date('Y.m.d. H:i');
        if (trim($b['ertesites_ntfy']) !== '') {
            try {
                self::ntfyKuld($b['ertesites_ntfy'], $b['ertesites_ntfy_token'], $cim, $teljes, $szint);
            } catch (\Throwable $e) {
                $hibak[] = 'ntfy: ' . $e->getMessage();
            }
        }
        if (trim($b['ertesites_email']) !== '' && trim($b['smtp_szerver']) !== '') {
            try {
                self::emailKuld($b, $cim, $teljes);
            } catch (\Throwable $e) {
                $hibak[] = 'e-mail: ' . $e->getMessage();
            }
        }
        return $hibak;
    }

    public function bekapcsolt(string $esemeny): bool
    {
        $b = ($this->beallitasok)();
        return self::csatornak($b) && in_array($esemeny, $b['ertesites_esemenyek'], true);
    }

    public function kuld(string $esemeny, string $cim, string $uzenet, string $szint = 'figy', float $ismetlesMp = self::ISMETLES_MP, ?string $kulcsSzoveg = null): bool
    {
        if (!$this->bekapcsolt($esemeny)) {
            return false;
        }
        $kulcs = $esemeny . "\n" . ($kulcsSzoveg ?? "{$cim}\n{$uzenet}");
        $most = microtime(true);
        if ($most - ($this->legutobb[$kulcs] ?? -1e9) < $ismetlesMp) {
            return false;
        }
        $this->legutobb[$kulcs] = $most;
        $this->legutobb = array_filter($this->legutobb, static fn($v) => $most - $v < self::ISMETLES_MP * 4);
        $this->hatter->futtat('ertesites', ['cim' => $cim, 'uzenet' => $uzenet, 'szint' => $szint], function (?array $hibak): void {
            foreach ($hibak ?? [] as $h) {
                ($this->naplo)("Értesítés nem ment el – {$h}");
            }
        }, fn(string $h) => ($this->naplo)("Értesítés nem ment el – váratlan hiba: {$h}"));
        return true;
    }

    public static function kimaradtCsengetesek(array $esemenyek, \DateTimeImmutable $elozo, \DateTimeImmutable $most, array $tipusok): array
    {
        if ($most <= $elozo || $most->getTimestamp() - $elozo->getTimestamp() > 36 * 3600) {
            return [];
        }
        return array_values(array_filter($esemenyek, static fn(Esemeny $e) => $elozo < $e->ido && $e->ido <= $most && in_array($e->tipus, $tipusok, true)));
    }

    public static function reggeliJelentes(\DateTimeImmutable $nap, ?string $rend, ?\DateTimeImmutable $elso, int $csengetesek, ?string $kimenet,
                                           ?string $forras, int $szamok, ?array $tegnap, int $hibak, ?float $szabadGb): array
    {
        $gondok = [];
        $sorok = [];
        if ($rend === null) {
            $sorok[] = 'Ma nincs csengetés.';
        } else {
            $sorok[] = "Mai rend: {$rend}, {$csengetesek} csengetés" . ($elso ? ', az első ' . $elso->format('H:i') . '-kor.' : '.');
        }
        if ($kimenet) {
            $sorok[] = "Hangkimenet: {$kimenet}.";
        } else {
            $sorok[] = 'Hangkimenet: NEM TALÁLHATÓ.';
            $gondok[] = 'nincs hangkimenet';
        }
        $sorok[] = $forras ? "Szünetzene: {$forras}" . ($szamok ? " ({$szamok} szám)." : '.') : 'Szünetzene: nincs kiválasztott forrás.';
        if ($tegnap) {
            $c = $tegnap['csengetes'];
            $pontossag = $c['atlag_keses_ms'] !== null ? ', átlagos eltérés ' . str_replace('.', ',', sprintf('%.1f', $c['atlag_keses_ms'] / 1000)) . ' mp' : '';
            $sorok[] = "Tegnap: {$tegnap['zene']['perc']} perc zene, {$c['darab']} csengetés{$pontossag}.";
            if ($c['kesett']) {
                $gondok[] = "tegnap {$c['kesett']} csengetés késett";
            }
        }
        if ($hibak) {
            $sorok[] = "Az elmúlt 24 órában {$hibak} hiba került a naplóba.";
            $gondok[] = "{$hibak} hiba";
        }
        if ($szabadGb !== null && $szabadGb < 2) {
            $sorok[] = 'Kevés a szabad hely: ' . str_replace('.', ',', sprintf('%.1f', $szabadGb)) . ' GB.';
            $gondok[] = 'kevés hely';
        }
        $cim = 'Reggeli önteszt (' . $nap->format('m.d.') . ')' . ($gondok ? ': ' . implode(', ', $gondok) : ': minden rendben');
        return [$cim, implode("\n", $sorok), $gondok ? 'figy' : 'info'];
    }
}
