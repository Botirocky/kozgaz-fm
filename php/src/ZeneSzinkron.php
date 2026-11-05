<?php

declare(strict_types=1);

namespace KozgazFM;

final class ZeneSzinkron
{
    public const LISTA_FAJL = '.kozgaz-fm-szinkron.json';
    public const RESZ = '.resz';
    public const IDOKORLAT_MP = 30;
    public const DARAB = 256 * 1024;
    public const ELSO_KOR_MP = 20;
    public const KOR_PERC = 30;
    public const FORRAS_NEV = 'Zenék a szerverről';

    public string $hiba = '';
    public ?int $utolso = null;
    public ?array $eredmeny = null;
    public string $allapot = '';
    public bool $fut = false;
    private float $kovetkezo;
    private bool $voltBe = true;

    public function __construct(private readonly Hatter $hatter, private readonly Vezerlo $v)
    {
        $this->kovetkezo = microtime(true) + self::ELSO_KOR_MP;
    }

    public static function alapMappa(): string
    {
        return Utvonalak::adat() . '/szerver-zenek';
    }

    public static function haladasFajl(): string
    {
        return Utvonalak::futas() . '/zene-szinkron.json';
    }

    public static function leallFajl(): string
    {
        return Utvonalak::futas() . '/zene-szinkron.leall';
    }

    public function mappa(): string
    {
        $m = trim($this->v->b['zene_szinkron_mappa']);
        return $m !== '' ? rtrim($m, '/') : self::alapMappa();
    }

    public function beallitva(): bool
    {
        $b = $this->v->b;
        return $b['zene_szinkron'] && trim($b['zenekeres_szerver']) !== '' && trim($b['zenekeres_szerver_kulcs']) !== '';
    }

    public function leallit(): void
    {
        if ($this->fut) {
            @touch(self::leallFajl());
        }
    }

    public function indit(): void
    {
        if ($this->fut) {
            return;
        }
        $this->kovetkezo = microtime(true) + self::KOR_PERC * 60;
        if (!$this->beallitva()) {
            return;
        }
        try {
            $cim = ZenekeresSzerver::szerverCim($this->v->b['zenekeres_szerver']);
        } catch (Hiba $e) {
            $this->hibas($e->getMessage());
            return;
        }
        @unlink(self::leallFajl());
        @unlink(self::haladasFajl());
        $this->fut = true;
        $this->allapot = 'A zenék listájának lekérése…';
        $mappa = $this->mappa();
        $this->hatter->futtat('zene_szinkron', ['cim' => $cim, 'kulcs' => trim($this->v->b['zenekeres_szerver_kulcs']),
            'mappa' => $mappa, 'kbps' => (int)$this->v->b['zene_szinkron_kbps']],
            fn(?array $e) => $this->kesz($e ?? [], $mappa), fn(string $h) => $this->hibas($h), 'szinkron', 6 * 3600);
    }

    public function tick(): void
    {
        $be = $this->beallitva();
        if ($be && !$this->voltBe) {
            $this->kovetkezo = min($this->kovetkezo, microtime(true) + 1);
        }
        if (!$be && $this->fut) {
            $this->leallit();
        }
        $this->voltBe = $be;
        if ($this->fut) {
            $adat = json_decode((string)@file_get_contents(self::haladasFajl()), true);
            if (is_array($adat) && isset($adat['i'], $adat['osszes'], $adat['ut'])) {
                $this->allapot = "Letöltés: {$adat['i']}/{$adat['osszes']} – " . basename((string)$adat['ut']);
            }
            return;
        }
        if (microtime(true) >= $this->kovetkezo) {
            $this->indit();
        }
    }

    public function allapotAdat(): array
    {
        $b = $this->v->b;
        return ['be' => (bool)$b['zene_szinkron'], 'beallitva' => $this->beallitva(),
            'szerver' => trim($b['zenekeres_szerver']) !== '' && trim($b['zenekeres_szerver_kulcs']) !== '',
            'fut' => $this->fut, 'allapot' => $this->allapot, 'hiba' => $this->hiba, 'utolso' => $this->utolso,
            'eredmeny' => $this->eredmeny, 'mappa' => $this->mappa()];
    }

    private function hibas(string $uzenet): void
    {
        $this->fut = false;
        if ($uzenet !== $this->hiba) {
            $this->v->log("Zenék a szerverről: {$uzenet}");
        }
        $this->hiba = $uzenet;
        $this->allapot = '';
    }

    private function kesz(array $e, string $mappa): void
    {
        $this->fut = false;
        $this->hiba = '';
        $this->allapot = '';
        $this->eredmeny = $e;
        $this->utolso = time();
        $uj = (int)($e['uj'] ?? 0);
        $torolt = (int)($e['torolt'] ?? 0);
        if ($uj || $torolt) {
            $this->v->log(sprintf('Zenék a szerverről: %d új, %d törölt szám (%.1f MB)', $uj, $torolt, ($e['bajt'] ?? 0) / 1048576));
        }
        if (!empty($e['hibas'])) {
            $this->v->log("Zenék a szerverről: {$e['hibas']} számot nem sikerült letölteni, a következő körben újra próbálja");
        }
        $this->v->szerverZenekFrissultek($mappa, (bool)($uj || $torolt));
    }

    public static function biztonsagosUt(mixed $ut): ?string
    {
        if (!is_string($ut) || $ut === '' || str_contains($ut, '\\') || str_contains($ut, "\0")) {
            return null;
        }
        foreach (explode('/', $ut) as $r) {
            if ($r === '' || $r === '.' || $r === '..' || str_starts_with($r, '.')) {
                return null;
            }
        }
        return $ut;
    }

    private static function hibaKod(int $kod, string $uzenet): Hiba
    {
        return match (true) {
            $kod === 401 || $kod === 403 => new Hiba('A szerver nem fogadta el a kulcsot.'),
            $kod === 503 => new Hiba('A szerveren nincs meg a zenemappa (nincs bent a pendrive?), a helyi zenék maradnak.'),
            $kod > 0 => new Hiba("A szerver hibát jelzett ({$kod})."),
            default => new Hiba("A szerver nem érhető el ({$uzenet})."),
        };
    }

    private static function fejlecek(string $kulcs): array
    {
        return ["X-Kozgaz-FM-Kulcs: {$kulcs}", 'User-Agent: KozgazFM/' . KFM_VERZIO];
    }

    public static function lista(string $cim, string $kulcs): array
    {
        [$kod, $torzs, $hiba] = Http::keres('GET', "{$cim}/api/zenek", null, self::fejlecek($kulcs), self::IDOKORLAT_MP, 20_000_000);
        if ($kod !== 200) {
            throw self::hibaKod($kod, $hiba);
        }
        $adat = json_decode($torzs, true);
        $elemek = is_array($adat) ? ($adat['data'] ?? null) : null;
        if (!is_array($elemek)) {
            throw new Hiba('A szerver érvénytelen választ küldött.');
        }
        return array_values(array_filter($elemek, static fn($e) => is_array($e) && self::biztonsagosUt($e['ut'] ?? null) !== null
            && is_int($e['meret'] ?? null) && is_int($e['ido'] ?? null)));
    }

    public static function letolt(string $cim, string $kulcs, string $ut, string $cel, int $meret, int $kbps = 0): int
    {
        $ideiglenes = $cel . self::RESZ;
        if (!is_dir(dirname($cel))) {
            @mkdir(dirname($cel), 0775, true);
        }
        $megvan = is_file($ideiglenes) ? (int)filesize($ideiglenes) : 0;
        if ($megvan > $meret) {
            @unlink($ideiglenes);
            $megvan = 0;
        }
        $fejlecek = self::fejlecek($kulcs);
        if ($megvan) {
            $fejlecek[] = "Range: bytes={$megvan}-";
        }
        $kontextus = stream_context_create(['http' => ['method' => 'GET', 'header' => implode("\r\n", $fejlecek),
            'timeout' => self::IDOKORLAT_MP, 'ignore_errors' => true, 'follow_location' => 1],
            'ssl' => ['verify_peer' => true, 'verify_peer_name' => true]]);
        $be = @fopen("{$cim}/api/zenek/fajl?" . http_build_query(['ut' => $ut]), 'rb', false, $kontextus);
        if ($be === false) {
            throw self::hibaKod(0, error_get_last()['message'] ?? 'nem érhető el');
        }
        $kod = 0;
        foreach (stream_get_meta_data($be)['wrapper_data'] ?? [] as $sor) {
            if (preg_match('#^HTTP/\S+\s+(\d{3})#', (string)$sor, $m)) {
                $kod = (int)$m[1];
            }
        }
        if ($kod !== 200 && $kod !== 206) {
            fclose($be);
            throw self::hibaKod($kod, '');
        }
        if ($megvan && $kod !== 206) {
            $megvan = 0;
        }
        $ki = fopen($ideiglenes, $megvan ? 'ab' : 'wb');
        $kezdet = microtime(true);
        $atvitt = 0;
        try {
            while (!feof($be)) {
                $darab = fread($be, self::DARAB);
                if ($darab === false) {
                    break;
                }
                if ($darab === '') {
                    if (stream_get_meta_data($be)['timed_out'] ?? false) {
                        break;
                    }
                    continue;
                }
                fwrite($ki, $darab);
                $atvitt += strlen($darab);
                if ($kbps > 0) {
                    $varni = $atvitt / ($kbps * 1024) - (microtime(true) - $kezdet);
                    if ($varni > 0) {
                        usleep((int)($varni * 1_000_000));
                    }
                }
            }
        } finally {
            fclose($be);
            fclose($ki);
        }
        clearstatcache(true, $ideiglenes);
        if ((int)filesize($ideiglenes) !== $meret) {
            throw new Hiba("Hiányos letöltés: {$ut}");
        }
        rename($ideiglenes, $cel);
        return $atvitt;
    }

    private static function jegyzekOlvas(string $mappa): array
    {
        $adat = json_decode((string)@file_get_contents("{$mappa}/" . self::LISTA_FAJL), true);
        if (!is_array($adat)) {
            return [];
        }
        return array_filter($adat, static fn($v) => is_array($v) && count($v) === 2);
    }

    private static function jegyzekIr(string $mappa, array $jegyzek): void
    {
        $ut = "{$mappa}/" . self::LISTA_FAJL;
        file_put_contents("{$ut}.tmp", json_encode($jegyzek, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
        rename("{$ut}.tmp", $ut);
    }

    private static function uresMappakTorlese(string $mappa): void
    {
        $mappak = [];
        $it = new \RecursiveIteratorIterator(new \RecursiveDirectoryIterator($mappa, \FilesystemIterator::SKIP_DOTS),
            \RecursiveIteratorIterator::CHILD_FIRST);
        foreach ($it as $f) {
            if ($f->isDir()) {
                $mappak[] = $f->getPathname();
            }
        }
        foreach ($mappak as $m) {
            @rmdir($m);
        }
    }

    public static function szinkron(string $cim, string $kulcs, string $mappa, int $kbps = 0, ?\Closure $jelez = null,
                                    ?\Closure $megszakit = null): array
    {
        $tavoli = self::lista($cim, $kulcs);
        if (!is_dir($mappa)) {
            @mkdir($mappa, 0775, true);
        }
        $jegyzek = self::jegyzekOlvas($mappa);
        if (!$tavoli) {
            throw new Hiba('A szerver üres zenelistát adott (ki van húzva a pendrive?) – a helyi zenékhez nem nyúlok.');
        }
        $e = ['osszes' => count($tavoli), 'uj' => 0, 'torolt' => 0, 'hibas' => 0, 'bajt' => 0];
        $meglevo = [];
        $megszakadt = false;
        foreach ($tavoli as $i => $elem) {
            if ($megszakit && $megszakit()) {
                $megszakadt = true;
                break;
            }
            $ut = $elem['ut'];
            $meglevo[$ut] = true;
            $cel = "{$mappa}/{$ut}";
            $jo = is_file($cel) && filesize($cel) === $elem['meret'];
            if (($jegyzek[$ut] ?? null) === [$elem['meret'], $elem['ido']] && $jo) {
                continue;
            }
            if (!isset($jegyzek[$ut]) && $jo) {
                $jegyzek[$ut] = [$elem['meret'], $elem['ido']];
                self::jegyzekIr($mappa, $jegyzek);
                continue;
            }
            if ($jelez) {
                $jelez($i + 1, count($tavoli), $ut);
            }
            try {
                $e['bajt'] += self::letolt($cim, $kulcs, $ut, $cel, $elem['meret'], $kbps);
            } catch (Hiba) {
                $e['hibas']++;
                continue;
            }
            @touch($cel, $elem['ido']);
            $jegyzek[$ut] = [$elem['meret'], $elem['ido']];
            self::jegyzekIr($mappa, $jegyzek);
            $e['uj']++;
        }
        if (!$megszakadt) {
            foreach (array_keys($jegyzek) as $ut) {
                if (isset($meglevo[$ut])) {
                    continue;
                }
                if (self::biztonsagosUt($ut) !== null) {
                    if (is_file("{$mappa}/{$ut}") && !@unlink("{$mappa}/{$ut}")) {
                        continue;
                    }
                    $e['torolt']++;
                }
                unset($jegyzek[$ut]);
            }
            if ($e['torolt']) {
                self::jegyzekIr($mappa, $jegyzek);
                self::uresMappakTorlese($mappa);
            }
        }
        return $e;
    }
}
