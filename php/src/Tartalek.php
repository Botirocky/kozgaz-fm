<?php

declare(strict_types=1);

namespace KozgazFM;

final class Tartalek
{
    public const FEJLEC = 'X-Kozgaz-FM-Kulcs';
    public const ELETJEL_MP = 5;
    public const KIESES_HATAR = 3;
    public const VISSZA_HATAR = 2;
    public const SZINKRON_MP = 300;
    public const PORT = 8080;
    public const SZEREPEK = ['' => 'Kikapcsolva', 'fo' => 'Ez a fő gép', 'tartalek' => 'Ez a tartalék gép'];
    public const SZINKRON_MEZOK = [
        'rendek', 'het', 'kivetelek', 'szunnapok', 'rendkivuli', 'bemondasok', 'bemondas_sablonok',
        'jelzo', 'jelzo_perc', 'kicsengo', 'zene_szunetben', 'zene_min_szunet', 'zene_kesleltetes',
        'zene_leall_elotte', 'reggeli_zene', 'reggeli_zene_tol', 'zene_kihagyott_szunetek', 'ma_nincs_csengetes', 'ma_nincs_zene',
        'szuro_alap', 'szuro_korhataros', 'szuro_szavak', 'szuro_dalszoveg', 'szuro_erzekenyseg', 'tiltott_szamok',
    ];

    public int $hibasSor = 0;
    public int $sikeresSor = 0;
    public ?bool $el = null;
    public bool $atvett = false;
    public ?int $utolsoJel = null;
    public string $hiba = '';
    public array $partner = [];
    private bool $fut = false;
    private float $kovetkezo = 0.0;
    private ?float $utolsoSzinkron = null;
    private string $regiSzerep = '';
    public ?\Closure $atvetel = null;
    public ?\Closure $visszaadas = null;
    public ?\Closure $szinkronizalt = null;
    public ?\Closure $valtozott = null;

    public function __construct(private readonly Hatter $hatter, private readonly \Closure $beallitasok)
    {
    }

    public static function ujKulcs(): string
    {
        return rtrim(strtr(base64_encode(random_bytes(24)), '+/', '-_'), '=');
    }

    public static function cimNormalizal(string $cim): string
    {
        $cim = trim($cim);
        if ($cim === '') {
            return '';
        }
        if (!str_contains($cim, '://')) {
            $cim = "http://{$cim}";
        }
        $r = parse_url($cim);
        if (!is_array($r) || !in_array($r['scheme'] ?? '', ['http', 'https'], true) || empty($r['host'])
            || !in_array($r['path'] ?? '', ['', '/'], true) || isset($r['query']) || isset($r['user'])) {
            throw new Hiba('A cím formája: 192.168.1.20:8080 vagy http://csengo-gep:8080', 'validation_error', 422);
        }
        $gazda = str_contains($r['host'], ':') && !str_starts_with($r['host'], '[') ? "[{$r['host']}]" : $r['host'];
        return "{$r['scheme']}://{$gazda}:" . ($r['port'] ?? self::PORT);
    }

    public static function szinkronAdat(array $b): array
    {
        return array_intersect_key($b, array_flip(self::SZINKRON_MEZOK));
    }

    public static function szinkronAlkalmaz(array $b, array $adat): array
    {
        $uj = Beallitasok::normalizal(array_merge($b, array_intersect_key($adat, array_flip(self::SZINKRON_MEZOK))));
        $valtozott = [];
        foreach (self::SZINKRON_MEZOK as $mezo) {
            if (array_key_exists($mezo, $adat) && $uj[$mezo] !== $b[$mezo]) {
                $valtozott[] = $mezo;
            }
        }
        return [$uj, $valtozott];
    }

    public static function eletjel(array $b, bool $atvett, bool $riasztas): array
    {
        return ['szerep' => $b['tartalek_mod'], 'verzio' => KFM_VERZIO, 'ido' => date('Y-m-d\TH:i:s'), 'atvett' => $atvett, 'riasztas' => $riasztas];
    }

    public function szerep(): string
    {
        $b = ($this->beallitasok)();
        return $b['tartalek_kulcs'] !== '' && $b['tartalek_cim'] !== '' ? $b['tartalek_mod'] : '';
    }

    public function passziv(): bool
    {
        return $this->szerep() === 'tartalek' && !$this->atvett;
    }

    private function alaphelyzet(): void
    {
        $this->hibasSor = $this->sikeresSor = 0;
        $this->el = null;
        $this->atvett = false;
        $this->utolsoJel = null;
        $this->hiba = '';
        $this->partner = [];
    }

    public function leiras(): array
    {
        $szerep = $this->szerep();
        $b = ($this->beallitasok)();
        if ($szerep === '') {
            return $b['tartalek_mod'] !== '' ? ['Add meg a közös kulcsot és a másik gép címét.', 'figyelem'] : ['', ''];
        }
        $jel = $this->utolsoJel ? ' (utolsó jel: ' . date('H:i:s', $this->utolsoJel) . ')' : '';
        if ($szerep === 'fo') {
            return match ($this->el) {
                true => ["A tartalék gép készenlétben{$jel}", 'szol'],
                false => ["A tartalék gép {$this->hiba}", 'figyelem'],
                default => ['Kapcsolódás a tartalék géphez…', 'halvany'],
            };
        }
        if ($this->atvett) {
            return ["A fő gép {$this->hiba} – ez a gép csenget helyette", 'hiba'];
        }
        if ($this->hibasSor) {
            return ["A fő gép {$this->hiba} ({$this->hibasSor}/" . self::KIESES_HATAR . '. próba)', 'figyelem'];
        }
        return $this->el ? ["A fő gép működik, ez a gép készenlétben vár{$jel}", 'kek'] : ['Kapcsolódás a fő géphez…', 'halvany'];
    }

    public function tick(): void
    {
        $szerep = $this->szerep();
        if ($szerep !== $this->regiSzerep) {
            $atvett = $this->atvett;
            $this->alaphelyzet();
            $this->regiSzerep = $szerep;
            $this->kovetkezo = microtime(true) + 0.5;
            if ($atvett && $this->visszaadas) {
                ($this->visszaadas)();
            }
            $this->valtozott && ($this->valtozott)();
        }
        if ($szerep === '' || $this->fut || microtime(true) < $this->kovetkezo) {
            return;
        }
        $this->kovetkezo = microtime(true) + self::ELETJEL_MP;
        $this->fut = true;
        $b = ($this->beallitasok)();
        $this->hatter->futtat('tartalek', ['cim' => $b['tartalek_cim'], 'ut' => 'eletjel', 'kulcs' => $b['tartalek_kulcs']],
            fn(?array $adat) => $this->jelJott($adat ?? []), fn(string $h) => $this->jelHiba($h), 'alap', 15);
    }

    private function jelJott(array $adat): void
    {
        $this->fut = false;
        $this->partner = $adat;
        $this->hibasSor = 0;
        $this->sikeresSor++;
        $this->utolsoJel = time();
        $this->hiba = '';
        $this->el = true;
        if ($this->atvett && $this->sikeresSor >= self::VISSZA_HATAR) {
            $this->atvett = false;
            $this->visszaadas && ($this->visszaadas)();
        }
        $this->valtozott && ($this->valtozott)();
        if ($this->szerep() === 'tartalek' && ($this->partner['szerep'] ?? '') === 'fo'
            && ($this->utolsoSzinkron === null || microtime(true) - $this->utolsoSzinkron >= self::SZINKRON_MP)) {
            $this->szinkron();
        }
    }

    private function jelHiba(string $hiba): void
    {
        $this->fut = false;
        $this->sikeresSor = 0;
        $this->hibasSor++;
        $this->hiba = $hiba;
        if ($this->hibasSor >= self::KIESES_HATAR) {
            $this->el = false;
            if (!$this->atvett) {
                $this->atvett = true;
                if ($this->szerep() === 'tartalek' && $this->atvetel) {
                    ($this->atvetel)();
                }
            }
        }
        $this->valtozott && ($this->valtozott)();
    }

    public function szinkron(): void
    {
        if ($this->szerep() !== 'tartalek') {
            return;
        }
        $this->utolsoSzinkron = microtime(true);
        $b = ($this->beallitasok)();
        $this->hatter->futtat('tartalek', ['cim' => $b['tartalek_cim'], 'ut' => 'beallitasok', 'kulcs' => $b['tartalek_kulcs']],
            fn(?array $adat) => $this->szinkronizalt && ($this->szinkronizalt)($adat ?? []),
            function (string $h): void {
                $this->hiba = "Szinkron: {$h}";
            }, 'alap', 20);
    }

    public static function lekeres(string $alap, string $ut, string $kulcs): array
    {
        [$kod, $valasz, $hiba] = Http::keres('GET', rtrim($alap, '/') . "/api/v1/tartalek/{$ut}", null,
            [self::FEJLEC . ': ' . $kulcs, 'X-Kozgaz-FM: 1', 'Accept: application/json'], 8);
        if ($kod === 0) {
            throw new Hiba(str_contains($hiba, 'timed out') ? 'nem válaszolt időben' : 'nem érhető el a hálózaton');
        }
        if ($kod === 401) {
            throw new Hiba('nem fogadta el a kulcsot');
        }
        if ($kod !== 200) {
            throw new Hiba("hibát jelzett ({$kod})");
        }
        $adat = json_decode($valasz, true);
        if (!is_array($adat) || !is_array($adat['data'] ?? null)) {
            throw new Hiba('érthetetlen választ adott');
        }
        return $adat['data'];
    }
}
