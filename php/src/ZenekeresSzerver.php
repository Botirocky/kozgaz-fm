<?php

declare(strict_types=1);

namespace KozgazFM;

final class ZenekeresSzerver
{
    public const KOR_MP = 4;
    public const HIBA_KOR_MP = 20;
    public const MAX_UJ = 20;

    public string $hiba = '';
    public ?int $utolso = null;
    private array $tavoli = [];
    private array $elkuldott = [];
    private array $kozvetlen = [];
    private bool $fut = false;
    private float $kovetkezo = 1.0;

    public function __construct(private readonly Hatter $hatter, private readonly Vezerlo $v)
    {
        $this->kovetkezo = microtime(true) + 1;
    }

    public static function szerverCim(string $cim): string
    {
        $cim = rtrim(trim($cim), '/');
        if ($cim === '') {
            return '';
        }
        if (!str_contains($cim, '://')) {
            $cim = "https://{$cim}";
        }
        $r = parse_url($cim);
        if (!is_array($r) || !in_array($r['scheme'] ?? '', ['http', 'https'], true) || empty($r['host'])) {
            throw new Hiba('A szerver címe http:// vagy https:// kezdetű webcím legyen.', 'validation_error', 422);
        }
        return "{$r['scheme']}://{$r['host']}" . (isset($r['port']) ? ":{$r['port']}" : '') . rtrim($r['path'] ?? '', '/');
    }

    public function beallitva(): bool
    {
        return trim($this->v->b['zenekeres_szerver']) !== '' && trim($this->v->b['zenekeres_szerver_kulcs']) !== '';
    }

    public function cim(): string
    {
        try {
            return self::szerverCim($this->v->b['zenekeres_szerver']);
        } catch (Hiba) {
            return '';
        }
    }

    public function oldal(): string
    {
        $cim = $this->cim();
        return $cim !== '' && trim($this->v->b['zenekeres_szerver_kulcs']) !== '' ? "{$cim}/" : '';
    }

    public function ujraindit(): void
    {
        $this->hiba = '';
        $this->utolso = null;
        $this->elkuldott = [];
        $this->kovetkezo = microtime(true) + 0.2;
    }

    private function beallitasok(): array
    {
        $b = $this->v->b;
        $ma = date('Y-m-d');
        return ['aktiv' => $b['zenekeres'], 'auto' => $b['zenekeres_auto'], 'cim' => $b['kijelzo_cim'], 'napi' => $b['zenekeres_napi'],
            'max_perc' => $b['zenekeres_max_perc'],
            'tiltott_telefonok' => array_values(array_column(array_filter($b['tiltott_telefonok'], static fn($t) => $t['ig'] >= $ma), 'kulcs'))];
    }

    private function allapotok(): array
    {
        $lista = [];
        foreach ($this->v->keresek->lista as $k) {
            if (isset($this->tavoli[$k['azon']])) {
                $adat = Zenekeres::nyilvanos($k);
                if (($this->elkuldott[$k['azon']] ?? null) !== $adat) {
                    $lista[] = $adat;
                }
            }
        }
        foreach ($this->kozvetlen as $azon => $adat) {
            if (($this->elkuldott[$azon] ?? null) !== $adat) {
                $lista[] = $adat;
            }
        }
        return $lista;
    }

    public function tick(): void
    {
        if ($this->fut || microtime(true) < $this->kovetkezo) {
            return;
        }
        if (!$this->beallitva() || $this->v->tartalek->passziv()) {
            $this->kovetkezo = microtime(true) + self::KOR_MP;
            return;
        }
        $cim = $this->cim();
        if ($cim === '') {
            $this->hibas('A szerver címe hibás.');
            return;
        }
        $allapotok = $this->allapotok();
        $this->fut = true;
        $this->hatter->futtat('zenekeres_szerver', ['cim' => $cim, 'kulcs' => trim($this->v->b['zenekeres_szerver_kulcs']),
            'adat' => ['beallitasok' => $this->beallitasok(), 'allapotok' => $allapotok, 'verzio' => KFM_VERZIO]],
            fn(?array $valasz) => $this->kesz($valasz ?? [], $allapotok), fn(string $h) => $this->hibas($h), 'alap', 20);
    }

    private function hibas(string $uzenet): void
    {
        $this->fut = false;
        if ($uzenet !== $this->hiba) {
            $this->v->log("Zenekérés-szerver: {$uzenet}");
        }
        $this->hiba = $uzenet;
        $this->kovetkezo = microtime(true) + self::HIBA_KOR_MP;
    }

    private function kesz(array $valasz, array $elkuldott): void
    {
        $this->fut = false;
        if ($this->hiba !== '') {
            $this->v->log('Zenekérés-szerver: a kapcsolat helyreállt');
        }
        $this->hiba = '';
        $this->utolso = time();
        foreach ($elkuldott as $adat) {
            $this->elkuldott[$adat['azon']] = $adat;
        }
        foreach (array_slice(is_array($valasz['uj'] ?? null) ? $valasz['uj'] : [], 0, self::MAX_UJ) as $elem) {
            if (is_array($elem)) {
                $this->fogad($elem);
            }
        }
        $this->takarit();
        $this->kovetkezo = microtime(true) + ($this->allapotok() ? 0.2 : self::KOR_MP);
    }

    private function fogad(array $elem): void
    {
        [$azon, $szoveg, $nev, $eszkoz, $ip] = array_map(static fn($m) => (string)($elem[$m] ?? ''), ['azon', 'szoveg', 'nev', 'eszkoz', 'ip']);
        if ($azon === '' || $eszkoz === '' || isset($this->tavoli[$azon]) || isset($this->kozvetlen[$azon])) {
            return;
        }
        try {
            $this->v->zenekeresUj($szoveg, $nev, $eszkoz, $ip ?: 'szerver', $azon);
            $this->tavoli[$azon] = true;
        } catch (Hiba $e) {
            $this->kozvetlen[$azon] = ['azon' => $azon, 'szoveg' => mb_substr($szoveg, 0, 150), 'cim' => '', 'allapot' => 'elutasitva',
                'allapot_nev' => 'Elutasítva', 'ok' => $e->getMessage(), 'ido' => date('H:i')];
        }
    }

    private function takarit(): void
    {
        $elok = array_fill_keys(array_column($this->v->keresek->lista, 'azon'), true);
        $this->tavoli = array_intersect_key($this->tavoli, $elok);
        if (count($this->kozvetlen) > 200) {
            $this->kozvetlen = array_slice($this->kozvetlen, -100, null, true);
        }
        foreach (array_keys($this->elkuldott) as $azon) {
            if (!isset($this->tavoli[$azon]) && !isset($this->kozvetlen[$azon])) {
                unset($this->elkuldott[$azon]);
            }
        }
    }

    public static function kuld(string $cim, string $kulcs, array $adat): array
    {
        [$kod, $valasz, $hiba] = Http::keres('POST', "{$cim}/api/gep", json_encode($adat, JSON_UNESCAPED_UNICODE),
            ['Content-Type: application/json', 'X-Kozgaz-FM-Kulcs: ' . $kulcs, 'User-Agent: KozgazFM/' . KFM_VERZIO], 10);
        if ($kod === 0) {
            throw new Hiba("A szerver nem érhető el ({$hiba}).");
        }
        if ($kod === 401 || $kod === 403) {
            throw new Hiba('A szerver nem fogadta el a kulcsot.');
        }
        if ($kod >= 400) {
            throw new Hiba("A szerver hibát jelzett ({$kod}).");
        }
        $tartalom = json_decode($valasz ?: '{}', true);
        if (!is_array($tartalom) || !is_array($tartalom['data'] ?? null)) {
            throw new Hiba('A szerver érvénytelen választ küldött.');
        }
        return $tartalom['data'];
    }
}
