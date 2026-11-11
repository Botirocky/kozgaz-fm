<?php

declare(strict_types=1);

namespace KozgazFM;

final class ZeneLejatszo
{
    public const LISTA_MEGORZES_MP = 4 * 3600;
    public const SPOTIFY_MAX_KIHAGYAS = 8;
    private const KESO_MERES_MP = 8;

    private Csoport $fo;
    private Csoport $kifuto;
    private Animacio $animacio;
    private Animacio $kifutoAnimacio;
    private float $erosites = 1.0;
    private float $kifutoAlap = 0.0;
    private float $foAlap = 0.0;
    private string $gorbe = '';
    private array $csendProbalt = [];

    public ?array $forras = null;
    public array $szamok = [];
    private array $fuggoKert = [];
    public int $index = 0;
    public bool $keveres = true;
    public bool $gyorsitotar = true;
    public int $hangeroErtek = 60;
    public float $elhalkitasMp = 3.0;
    public float $atusztatasMp = 5.0;
    public bool $atusztatasBe = true;
    public string $spotifyEszkoz = '';
    public ?string $spotifyClientId = null;
    private bool $halkitva = false;
    private bool $szol = false;
    private bool $betoltesAlatt = false;
    private bool $inditBetoltesUtan = false;
    private int $hibasorozat = 0;
    private array $letoltesAlatt = [];
    private ?array $varakozo = null;
    private int $generacio = 0;
    public string $mostCim = '';
    public ?Szuro $szuro = null;
    public bool $korhatarTiltas = false;
    private array $korhatarosak = [];
    private array $tragarak = [];
    private array $tiltottYtok = [];
    private array $tiltottKulcsok = [];
    private string $spotifyFelirat = '';
    private array $tarolt = [];
    private int $spotifyKihagyas = 0;
    private float $spotifyKovetkezoFrissites = 0.0;
    private ?float $kesleltetettLepes = null;

    public ?\Closure $szamValtozott = null;
    public ?\Closure $kertSzol = null;
    public ?\Closure $allapotValtozott = null;
    public ?\Closure $hibaJelzes = null;
    public ?\Closure $listaValtozott = null;
    public ?\Closure $kiszurve = null;
    public ?\Closure $spotifySzoveg = null;

    public function __construct(private readonly Hatter $hatter, public readonly Kiegyenlito $kiegyenlito)
    {
        $this->fo = new Csoport('zene-a');
        $this->kifuto = new Csoport('zene-b');
        $this->fo->aktival('zene');
        $this->kifuto->aktival('zene');
        $this->animacio = new Animacio(fn(float $v) => $this->foSzint($v));
        $this->kifutoAnimacio = new Animacio(fn(float $v) => $this->kifutoSzint($v));
    }

    private function foSzint(float $v): void
    {
        $this->fo->hangero(match ($this->gorbe) {
            'be' => self::szint($this->celHangero(), $this->erosites) * Atuszas::gorbeBe($v),
            'ki' => $this->foAlap * Atuszas::gorbeKi($v),
            default => self::szint($v, $this->erosites),
        });
    }

    private function kifutoSzint(float $v): void
    {
        $this->kifuto->hangero($this->kifutoAlap * Atuszas::gorbeKi($v));
    }

    private function csendMp(?string $ut): array
    {
        return $this->atusztatasBe ? Atuszas::csendMp($ut) : [0.0, 0.0];
    }

    private function csendElore(): void
    {
        if (!$this->atusztatasBe || !$this->szamok) {
            return;
        }
        for ($i = 0; $i < 3; $i++) {
            $ut = $this->szamok[($this->index + $i) % count($this->szamok)]->helyi;
            if ($ut === null || isset($this->csendProbalt[$ut]) || Atuszas::keres($ut) !== null) {
                continue;
            }
            $this->csendProbalt[$ut] = true;
            $this->hatter->futtat('csend', ['ut' => $ut], null, null, 'csend', 300);
        }
    }

    private function kifutoHalkit(float $mp): void
    {
        if (!$this->kifuto->szol()) {
            return;
        }
        $this->kifutoAlap = $this->kifuto->amplitudo();
        $this->kifutoAnimacio->indit(0.0, 1.0, $mp, function (): void {
            $this->kifuto->allj();
        });
    }

    private function atuszasIndit(float $mp): void
    {
        [$this->fo, $this->kifuto] = [$this->kifuto, $this->fo];
        [$this->animacio, $this->kifutoAnimacio] = [
            new Animacio(fn(float $v) => $this->foSzint($v)),
            new Animacio(fn(float $v) => $this->kifutoSzint($v)),
        ];
        $this->kifutoHalkit($mp);
    }

    private function keziAtuszasMp(): float
    {
        $mp = min(Atuszas::hossz($this->atusztatasBe, $this->atusztatasMp), Atuszas::KEZI_ATUSZTATAS_MP);
        if ($mp <= 0 || !$this->szol || $this->halkitva || $this->spotifyMod() || !$this->fo->szol() || $this->fo->szunetel()) {
            return 0.0;
        }
        return $mp;
    }

    public static function szint(float $szazalek, float $erosites): float
    {
        return min(1.0, (max(0.0, min(100.0, $szazalek)) / 100) ** 2 * $erosites);
    }

    private function jel(?\Closure $fv, mixed ...$argumentumok): void
    {
        if ($fv) {
            $fv(...$argumentumok);
        }
    }

    public function szol(): bool
    {
        return $this->szol;
    }

    public function spotifyMod(): bool
    {
        return $this->forras !== null && $this->forras['tipus'] === 'spotify';
    }

    public function zonak(array $lista): void
    {
        if (!$this->fo->ujraepitendo($lista)) {
            $this->fo->zonak($lista);
            $this->kifuto->zonak($lista);
            $this->fo->aktival('zene');
            $this->kifuto->aktival('zene');
            return;
        }
        $folyt = $this->szol && !$this->spotifyMod();
        if ($folyt) {
            $this->megallit(false, false);
        }
        foreach ([$this->fo, $this->kifuto] as $cs) {
            $cs->zonak($lista);
            $cs->aktival('zene');
        }
        if ($folyt) {
            $this->indit();
        }
    }

    public function aktivZonak(): bool
    {
        return (bool)$this->fo->aktivZonak('zene');
    }

    private function forrasNev(): string
    {
        return $this->forras['nev'] ?? '';
    }

    private function szuroOk(Szam $szam): ?string
    {
        if ($szam->yt !== '' && isset($this->korhatarosak[$szam->yt])) {
            return 'korhatáros';
        }
        if (isset($this->tragarak[$szam->cim])) {
            return 'trágár szöveg';
        }
        if ($this->tiltottE($szam->yt, $szam->cim)) {
            return 'letiltott szám';
        }
        if (!$this->szuro) {
            return null;
        }
        $mappa = $szam->helyi && $szam->yt === '' ? basename(dirname($szam->helyi)) : '';
        $t = $this->szuro->talalat($szam->cim, $mappa);
        return $t !== null ? "tiltott szó: {$t}" : null;
    }

    private function szurt(array $szamok): array
    {
        $maradt = array_values(array_filter($szamok, fn(Szam $s) => $s->kert || $this->szuroOk($s) === null));
        return [$maradt, count($szamok) - count($maradt)];
    }

    public function szuroBeallitas(?Szuro $szuro, bool $korhatarTiltas): void
    {
        $regi = $this->szuro?->kulcs();
        if ($regi === $szuro?->kulcs() && $korhatarTiltas === $this->korhatarTiltas) {
            return;
        }
        $this->szuro = $szuro;
        $this->korhatarTiltas = $korhatarTiltas;
        if (!$korhatarTiltas) {
            $this->korhatarosak = [];
        }
        $this->tarolt = [];
        if (!$this->szamok) {
            return;
        }
        $regiLista = $this->szamok;
        $horgony = $regiLista[$this->index] ?? null;
        $maradt = array_values(array_filter($regiLista, fn(Szam $s) => ($s === $horgony && $this->szol) || $s->kert || $this->szuroOk($s) === null));
        $kiszurt = count($regiLista) - count($maradt);
        if (!$kiszurt) {
            return;
        }
        $elotte = count(array_filter(array_slice($regiLista, 0, $this->index), static fn($s) => in_array($s, $maradt, true)));
        $this->szamok = $maradt;
        $this->index = $maradt ? $elotte % count($maradt) : 0;
        $this->jel($this->listaValtozott);
        $this->jel($this->kiszurve, "A szűrő {$kiszurt} számot kivett a lejátszási sorból");
    }

    public function vizsgalando(): array
    {
        if ($this->spotifyMod() || !$this->szamok) {
            return [];
        }
        $hossz = count($this->szamok);
        $lista = [];
        for ($i = 0; $i < $hossz; $i++) {
            $s = $this->szamok[($this->index + $i) % $hossz];
            if (!$s->kert && !$s->keresbol) {
                $lista[] = $s;
            }
        }
        return $lista;
    }

    public function tragarakTorlese(): void
    {
        $this->tragarak = [];
        $this->tarolt = [];
    }

    public function tragaratKivesz(Szam $szam, string $reszlet): void
    {
        $this->tragarak[$szam->cim] = true;
        $this->tarolt = [];
        if ($szam->kert || $szam->keresbol || !in_array($szam, $this->szamok, true)) {
            return;
        }
        $this->jel($this->kiszurve, "Trágár szövegű szám kihagyva: {$szam->cim} ({$reszlet})");
        $this->sorbolKivesz($szam);
    }

    public function tiltottE(string $yt, string $cim): bool
    {
        if ($yt !== '' && isset($this->tiltottYtok[$yt])) {
            return true;
        }
        return $this->tiltottKulcsok && isset($this->tiltottKulcsok[Dalszoveg::kulcs($cim)]);
    }

    public function tiltottBeallitas(array $ytok, array $cimek): void
    {
        $this->tiltottYtok = array_fill_keys(array_filter($ytok), true);
        $kulcsok = [];
        foreach ($cimek as $c) {
            $k = Dalszoveg::kulcs($c);
            if (trim($k, ' |') !== '') {
                $kulcsok[$k] = true;
            }
        }
        $this->tiltottKulcsok = $kulcsok;
        $this->tarolt = [];
    }

    public function mostSzolo(): ?array
    {
        if (!$this->szol) {
            return null;
        }
        if ($this->spotifyMod()) {
            return $this->spotifyFelirat !== '' ? [$this->spotifyFelirat, ''] : null;
        }
        $szam = $this->szamok[$this->index] ?? null;
        return $szam ? [$szam->cim, $szam->yt] : null;
    }

    public function tiltottakatKivesz(): void
    {
        $this->fuggoKert = array_values(array_filter($this->fuggoKert, fn(Szam $s) => !$this->tiltottE($s->yt, $s->cim)));
        if ($this->spotifyMod()) {
            if ($this->szol && $this->tiltottE('', $this->spotifyFelirat)) {
                $this->kovetkezo();
            }
            return;
        }
        $jelenlegi = $this->szamok[$this->index] ?? null;
        $tiltottak = array_values(array_filter($this->szamok, fn(Szam $s) => $this->tiltottE($s->yt, $s->cim)));
        usort($tiltottak, static fn($a, $b) => (int)($a === $jelenlegi) <=> (int)($b === $jelenlegi));
        foreach ($tiltottak as $s) {
            $this->sorbolKivesz($s);
        }
    }

    public function ytKivesz(string $yt): void
    {
        if ($yt === '') {
            return;
        }
        $this->fuggoKert = array_values(array_filter($this->fuggoKert, static fn(Szam $s) => $s->yt !== $yt));
        $jelenlegi = $this->szamok[$this->index] ?? null;
        $talalatok = array_values(array_filter($this->szamok, static fn(Szam $s) => $s->yt === $yt));
        usort($talalatok, static fn($a, $b) => (int)($a === $jelenlegi) <=> (int)($b === $jelenlegi));
        foreach ($talalatok as $s) {
            $this->sorbolKivesz($s);
        }
        $this->tarolt = [];
    }

    private function sorbolKivesz(Szam $szam): void
    {
        $hely = array_search($szam, $this->szamok, true);
        if ($hely === false) {
            return;
        }
        $mostSzol = $hely === $this->index && $this->szol;
        array_splice($this->szamok, $hely, 1);
        if ($hely < $this->index) {
            $this->index--;
        }
        $this->jel($this->listaValtozott);
        if (!$this->szamok) {
            $this->megallit(false);
            $this->jel($this->hibaJelzes, "A(z) „{$this->forrasNev()}” forrásban nincs lejátszható szám.");
        } elseif ($mostSzol) {
            $this->jatszd($this->index);
        } else {
            $this->index %= count($this->szamok);
        }
    }

    private function tarolKulcs(array $forras): string
    {
        return $forras['tipus'] . "\n" . $forras['cim'];
    }

    private function tarol(): void
    {
        if ($this->forras === null || $this->spotifyMod() || !$this->szamok) {
            return;
        }
        $sajat = array_values(array_filter($this->szamok, static fn(Szam $s) => !$s->kert && !$s->keresbol));
        if (!$sajat) {
            return;
        }
        $lejatszott = count(array_filter(array_slice($this->szamok, 0, $this->index + 1), static fn(Szam $s) => !$s->kert && !$s->keresbol));
        $this->tarolt[$this->tarolKulcs($this->forras)] = [$sajat, $lejatszott % count($sajat), microtime(true)];
    }

    private function visszatolt(array $forras): bool
    {
        $kulcs = $this->tarolKulcs($forras);
        $tarolt = $this->tarolt[$kulcs] ?? null;
        unset($this->tarolt[$kulcs]);
        if ($tarolt === null || microtime(true) - $tarolt[2] > self::LISTA_MEGORZES_MP) {
            return false;
        }
        [$szamok, $index] = $tarolt;
        $szamok = array_values(array_filter(array_merge(array_slice($szamok, $index), array_slice($szamok, 0, $index)),
            fn(Szam $s) => $this->szuroOk($s) === null));
        if (!$szamok) {
            return false;
        }
        foreach ($szamok as $s) {
            $this->kiegyenlito->kell($s->helyi);
        }
        $this->szamok = array_merge($this->fuggoKert, $szamok);
        $this->fuggoKert = [];
        $this->index = 0;
        $this->jel($this->listaValtozott);
        $this->eloreLetolt();
        return true;
    }

    public function forrasBeallitas(?array $forras): void
    {
        if ($forras == $this->forras && ($this->szamok || $this->spotifyMod() || $this->betoltesAlatt)) {
            return;
        }
        $folyt = $this->szol;
        if ($folyt) {
            $this->megallit(false);
        }
        $this->tarol();
        $this->forras = $forras;
        $this->fuggoKert = array_merge(array_values(array_filter($this->szamok, static fn(Szam $s) => $s->kert)), $this->fuggoKert);
        $this->szamok = [];
        $this->index = 0;
        $this->generacio++;
        $this->spotifyKihagyas = 0;
        $this->betoltesAlatt = false;
        $this->jel($this->listaValtozott);
        if ($forras === null || $forras['tipus'] === 'spotify') {
            return;
        }
        if ($this->visszatolt($forras)) {
            if ($folyt) {
                $this->indit();
            }
            return;
        }
        $this->betoltes($folyt);
    }

    public function betoltes(bool $inditas = false): void
    {
        $forras = $this->forras;
        if ($forras === null || $forras['tipus'] === 'spotify') {
            return;
        }
        $this->betoltesAlatt = true;
        $this->inditBetoltesUtan = $this->inditBetoltesUtan || $inditas;
        $generacio = $this->generacio;
        $this->hatter->futtat('forras', ['forras' => $forras], function (?array $lista) use ($generacio, $forras): void {
            if ($generacio !== $this->generacio) {
                return;
            }
            $szamok = array_map(static fn($e) => new Szam((string)$e['cim'], $e['helyi'] ?? null, (string)($e['yt'] ?? '')), $lista ?? []);
            [$szamok, $kiszurt] = $this->szurt($szamok);
            if ($kiszurt) {
                $this->jel($this->kiszurve, "A szűrő {$kiszurt} számot kihagyott a(z) „{$forras['nev']}” forrásból");
            }
            $this->betoltesAlatt = false;
            if ($this->keveres) {
                shuffle($szamok);
            }
            $this->szamok = array_merge(array_values(array_filter($this->szamok, static fn(Szam $s) => $s->kert)), $this->fuggoKert, $szamok);
            $this->fuggoKert = [];
            $this->index = 0;
            $this->jel($this->listaValtozott);
            if (!$szamok) {
                $this->jel($this->hibaJelzes, "A(z) „{$forras['nev']}” forrásban nincs lejátszható szám.");
                $this->inditBetoltesUtan = false;
                return;
            }
            $this->eloreLetolt();
            foreach ($szamok as $s) {
                $this->kiegyenlito->kell($s->helyi);
            }
            if ($this->inditBetoltesUtan) {
                $this->inditBetoltesUtan = false;
                $this->indit();
            }
        }, function (string $hiba) use ($generacio, $forras): void {
            if ($generacio !== $this->generacio) {
                return;
            }
            $this->betoltesAlatt = false;
            $this->inditBetoltesUtan = false;
            $this->jel($this->hibaJelzes, "Nem sikerült betölteni: {$forras['nev']} ({$hiba})");
        }, 'alap', 400);
    }

    public function indit(): void
    {
        if ($this->forras === null) {
            $this->jel($this->hibaJelzes, 'Nincs kiválasztott zeneforrás.');
            return;
        }
        if ($this->spotifyMod()) {
            $this->spotifyIndit();
            return;
        }
        if (!$this->aktivZonak()) {
            $this->jel($this->hibaJelzes, 'Egyik hangzónában sincs bekapcsolva a zene (Beállítások → Hangzónák).');
            return;
        }
        if (!$this->szamok) {
            if (!$this->betoltesAlatt) {
                $this->betoltes(true);
            } else {
                $this->inditBetoltesUtan = true;
            }
            return;
        }
        $this->szol = true;
        $this->jel($this->allapotValtozott, true);
        if ($this->fo->szunetel()) {
            $this->beuszas();
            $this->fo->szunet(false);
            return;
        }
        $this->jatszd($this->index);
    }

    private function jatszd(int $index): void
    {
        if (!$this->szamok) {
            return;
        }
        $this->kifutoLeallit();
        $this->index = (($index % count($this->szamok)) + count($this->szamok)) % count($this->szamok);
        $szam = $this->szamok[$this->index];
        $voltKert = $szam->kert;
        if ($szam->kert) {
            $szam->kert = false;
            $this->jel($this->kertSzol, $szam->yt);
        }
        $this->lejatszottKereseketKivesz($szam, $voltKert);
        $this->mostCim = $szam->cim;
        $this->jel($this->szamValtozott, $szam->cim, $this->forrasNev());
        if ($szam->helyi) {
            $mp = $this->keziAtuszasMp();
            if ($mp > 0) {
                $this->atuszasIndit($mp);
            }
            $this->forrastIndit($szam->helyi, $mp > 0 ? $mp : null);
        } else {
            $this->ideiglenesTakaritas($szam->yt);
            $meglevo = YouTube::gyorsitott($szam->yt, $this->ytMappa());
            if ($meglevo) {
                $szam->helyi = $meglevo;
                $this->forrastIndit($meglevo);
            } else {
                $this->fo->allj();
                $this->varakozo = [$szam->yt, $this->generacio, $this->index];
                $this->letolt($szam);
            }
        }
        $this->eloreLetolt();
    }

    private function letolt(Szam $szam): void
    {
        if (isset($this->letoltesAlatt[$szam->yt])) {
            return;
        }
        $this->letoltesAlatt[$szam->yt] = true;
        $this->hatter->futtat('letoltes', ['yt' => $szam->yt, 'mappa' => $this->ytMappa(), 'korhatar' => $this->korhatarTiltas],
            fn(?string $ut) => $this->letoltve($szam, (string)$ut),
            fn(string $hiba, string $kod = '') => $this->letoltesHiba($szam, $hiba, $kod), 'letoltes', 700);
    }

    private function forrastIndit(string $ut, ?float $beuszasMp = null): void
    {
        $this->animacio->allj();
        $this->gorbe = '';
        $this->erosites = $this->kiegyenlito->szorzo($ut);
        $this->fo->hangero(0.0);
        if (!$this->fo->betolt($ut, false, $this->csendMp($ut)[0])) {
            $this->lejatszasiHiba('az mpv nem indult el');
            return;
        }
        if ($this->szol) {
            $this->beuszas($beuszasMp);
        }
    }

    public function ytMappa(): string
    {
        return Utvonalak::mappa('gyorsitotar/' . ($this->gyorsitotar ? 'youtube' : 'youtube-ideiglenes'));
    }

    private function ideiglenesTakaritas(string $megtart): void
    {
        if ($this->gyorsitotar) {
            return;
        }
        $mappa = Utvonalak::mappa('gyorsitotar/youtube-ideiglenes');
        foreach (glob($mappa . '/*') ?: [] as $f) {
            if (is_file($f) && !str_starts_with(basename($f), $megtart)) {
                @unlink($f);
            }
        }
        foreach ($this->szamok as $s) {
            if ($s->yt !== '' && $s->yt !== $megtart && $s->helyi && dirname($s->helyi) === $mappa) {
                $s->helyi = null;
            }
        }
    }

    private function eloreLetolt(): void
    {
        $this->csendElore();
        if ($this->szamok) {
            for ($e = 3; $e >= 0; $e--) {
                $this->kiegyenlito->kell($this->szamok[($this->index + $e) % count($this->szamok)]->helyi, true);
            }
        }
        if (!$this->gyorsitotar || !$this->szamok) {
            return;
        }
        for ($e = 0; $e < 3; $e++) {
            $szam = $this->szamok[($this->index + $e) % count($this->szamok)];
            if ($szam->yt === '' || $szam->helyi || isset($this->letoltesAlatt[$szam->yt])) {
                continue;
            }
            if (count($this->letoltesAlatt) >= 2) {
                return;
            }
            $this->letolt($szam);
        }
    }

    private function varRa(Szam $szam): bool
    {
        if ($this->varakozo === null || $this->varakozo[0] !== $szam->yt) {
            return false;
        }
        [, $generacio, $index] = $this->varakozo;
        $this->varakozo = null;
        return $generacio === $this->generacio && $index === $this->index && $this->szol;
    }

    private function letoltve(Szam $szam, string $ut): void
    {
        unset($this->letoltesAlatt[$szam->yt]);
        $szam->helyi = $ut;
        if ($this->varRa($szam)) {
            $this->forrastIndit($ut);
        }
        $this->eloreLetolt();
    }

    private function letoltesHiba(Szam $szam, string $hiba, string $kod): void
    {
        unset($this->letoltesAlatt[$szam->yt]);
        if ($kod === 'korhatar') {
            $this->korhatarosatKivesz($szam);
            return;
        }
        if ($this->varRa($szam)) {
            $this->lejatszasiHiba($hiba);
        }
    }

    private function korhatarosatKivesz(Szam $szam): void
    {
        $this->korhatarosak[$szam->yt] = true;
        $this->jel($this->kiszurve, "Korhatáros videó kihagyva: {$szam->cim}");
        $varta = $this->varRa($szam);
        $hely = array_search($szam, $this->szamok, true);
        if ($hely === false) {
            return;
        }
        array_splice($this->szamok, $hely, 1);
        if ($hely < $this->index) {
            $this->index--;
        }
        $this->jel($this->listaValtozott);
        if (!$this->szamok) {
            $this->megallit(false);
            $this->jel($this->hibaJelzes, "A(z) „{$this->forrasNev()}” forrásban nincs lejátszható szám.");
        } elseif ($varta) {
            $this->jatszd($this->index);
        }
    }

    private function beuszas(?float $hosszMp = null): void
    {
        if ($hosszMp !== null) {
            $this->gorbe = 'be';
            $this->animacio->indit(0.0, 1.0, $hosszMp);
            return;
        }
        $this->gorbe = '';
        $this->animacio->indit(0.0, $this->celHangero(), min($this->elhalkitasMp, 2.0));
    }

    private function celHangero(): float
    {
        return $this->hangeroErtek * ($this->halkitva ? 0.25 : 1.0);
    }

    public function erositesUjra(): void
    {
        $uj = $this->kiegyenlito->szorzo($this->fo->fajl());
        if (abs($uj - $this->erosites) < 0.01) {
            return;
        }
        $this->erosites = $uj;
        if ($this->szol && !$this->animacio->fut()) {
            $this->fo->hangero(self::szint($this->celHangero(), $uj));
        }
    }

    public function mertJott(string $ut): void
    {
        if (!$this->szol || $this->spotifyMod() || $this->fo->fajl() !== $ut || $this->fo->pozicio() > self::KESO_MERES_MP) {
            return;
        }
        $regi = $this->erosites;
        $uj = $this->kiegyenlito->szorzo($ut);
        if (abs($uj - $regi) < 0.01) {
            return;
        }
        $this->erosites = $uj;
        if ($this->animacio->fut()) {
            return;
        }
        $cel = $this->celHangero();
        $this->gorbe = '';
        $this->animacio->indit(min(100.0, $cel * sqrt($regi / $uj)), $cel, 1.2);
    }

    private function kifutoLeallit(): void
    {
        $this->kifutoAnimacio->allj();
        if ($this->kifuto->szol()) {
            $this->kifuto->allj();
        }
    }

    public function megallit(bool $elhalkitas = true, bool $kovetkezore = true, bool $gyors = false): void
    {
        if (!$this->szol) {
            return;
        }
        $this->szol = false;
        $this->kesleltetettLepes = null;
        $this->jel($this->allapotValtozott, false);
        $halkul = $elhalkitas || $gyors;
        $mp = $gyors ? Atuszas::CSENGO_ELHALKITAS_MP : $this->elhalkitasMp;
        if ($halkul && !$this->spotifyMod()) {
            $this->kifutoHalkit($mp);
        } else {
            $this->kifutoLeallit();
        }
        if ($this->spotifyMod()) {
            $this->spotifyMegallit($elhalkitas);
            return;
        }
        $vege = function () use ($kovetkezore): void {
            if ($this->szol) {
                return;
            }
            if ($kovetkezore && $this->szamok) {
                $this->fo->allj();
                $this->index = ($this->index + 1) % count($this->szamok);
            } else {
                $this->fo->szunet(true);
            }
        };
        if ($halkul && $this->fo->szol() && !$this->fo->szunetel()) {
            $this->gorbe = 'ki';
            $this->foAlap = $this->fo->amplitudo();
            $this->animacio->indit(0.0, 1.0, $mp, $vege);
        } else {
            $this->animacio->allj();
            $vege();
        }
    }

    public function valt(): void
    {
        $this->szol ? $this->megallit(true, false) : $this->indit();
    }

    public function kovetkezo(): void
    {
        if ($this->spotifyMod()) {
            $this->spotifyHivas('kovetkezo');
            $this->spotifyKovetkezoFrissites = microtime(true) + 1.2;
            return;
        }
        if ($this->szamok) {
            $this->szol = true;
            $this->jel($this->allapotValtozott, true);
            $this->jatszd($this->index + 1);
        }
    }

    public function elozo(): void
    {
        if ($this->spotifyMod()) {
            $this->spotifyHivas('elozo');
            $this->spotifyKovetkezoFrissites = microtime(true) + 1.2;
            return;
        }
        if ($this->szamok) {
            $this->szol = true;
            $this->jel($this->allapotValtozott, true);
            $this->jatszd($this->index - 1);
        }
    }

    public function beszur(Szam $szam): bool
    {
        if ($this->spotifyMod() || $this->forras === null) {
            return false;
        }
        $szam->kert = true;
        $szam->keresbol = true;
        if (!$this->szamok) {
            $this->fuggoKert[] = $szam;
            return true;
        }
        $megallitva = !$this->szol && !$this->fo->szol();
        $hely = $megallitva ? $this->index : $this->index + 1;
        while ($hely < count($this->szamok) && $this->szamok[$hely]->kert) {
            $hely++;
        }
        array_splice($this->szamok, $hely, 0, [$szam]);
        $this->jel($this->listaValtozott);
        $this->eloreLetolt();
        return true;
    }

    private function lejatszottKereseketKivesz(Szam $most, bool $voltKert = false): void
    {
        $marad = array_values(array_filter($this->szamok, static fn(Szam $s) => $s === $most || !($s->keresbol && !$s->kert)));
        if (count($marad) === count($this->szamok)) {
            if ($voltKert) {
                $this->jel($this->listaValtozott);
            }
            return;
        }
        $this->szamok = $marad;
        $this->index = (int)array_search($most, $this->szamok, true);
        $this->jel($this->listaValtozott);
    }

    public function kertSor(): array
    {
        if ($this->spotifyMod() || !$this->szamok) {
            return [];
        }
        $hossz = count($this->szamok);
        $lista = [];
        for ($i = 0; $i < $hossz; $i++) {
            $j = ($this->index + $i) % $hossz;
            if ($this->szamok[$j]->kert) {
                $lista[] = [$j, $this->szamok[$j]];
            }
        }
        return $lista;
    }

    public function kertRendez(array $pontok): void
    {
        if ($this->spotifyMod()) {
            return;
        }
        $helyek = [];
        $valtozott = false;
        foreach ($this->szamok as $i => $s) {
            if ($s->kert && $i !== $this->index) {
                $uj = $s->yt !== '' ? (int)($pontok[$s->yt] ?? 0) : 0;
                $valtozott = $valtozott || $uj !== $s->szavazat;
                $s->szavazat = $uj;
                $helyek[] = $i;
            }
        }
        $regi = array_map(fn(int $i) => $this->szamok[$i], $helyek);
        $uj = $regi;
        usort($uj, static fn(Szam $a, Szam $b) => $b->szavazat <=> $a->szavazat);
        if ($uj !== $regi) {
            foreach ($helyek as $n => $i) {
                $this->szamok[$i] = $uj[$n];
            }
            $this->eloreLetolt();
            $valtozott = true;
        }
        if ($valtozott) {
            $this->jel($this->listaValtozott);
        }
    }

    public function alapLista(): array
    {
        if ($this->spotifyMod()) {
            return [];
        }
        $lista = [];
        foreach ($this->szamok as $i => $s) {
            if (!$s->kert && !$s->keresbol) {
                $lista[] = [$i, $s];
            }
        }
        return $lista;
    }

    public function alapPozicio(): ?int
    {
        if ($this->spotifyMod() || !$this->szamok) {
            return null;
        }
        $hossz = count($this->szamok);
        for ($lepes = 0; $lepes < $hossz; $lepes++) {
            $j = ((($this->index - $lepes) % $hossz) + $hossz) % $hossz;
            $s = $this->szamok[$j];
            if (!$s->kert && !$s->keresbol) {
                return $j;
            }
        }
        return null;
    }

    public function mostKert(): bool
    {
        return $this->szol && !$this->spotifyMod() && isset($this->szamok[$this->index]) && $this->szamok[$this->index]->keresbol;
    }

    public function ujrakever(): bool
    {
        if ($this->spotifyMod() || count($this->szamok) < 3) {
            return false;
        }
        $eleje = array_slice($this->szamok, 0, $this->index + 1);
        $hatra = array_slice($this->szamok, $this->index + 1);
        $kertek = array_values(array_filter($hatra, static fn(Szam $s) => $s->kert || $s->keresbol));
        $tobbi = array_values(array_filter($hatra, static fn(Szam $s) => !$s->kert && !$s->keresbol));
        shuffle($tobbi);
        $this->szamok = array_merge($eleje, $kertek, $tobbi);
        $this->jel($this->listaValtozott);
        $this->eloreLetolt();
        return true;
    }

    public function kovetkezok(int $darab = 5): array
    {
        if ($this->spotifyMod() || !$this->szamok) {
            return [];
        }
        $hossz = count($this->szamok);
        $lista = [];
        for ($i = 1; $i <= min($darab, $hossz - 1); $i++) {
            $j = ($this->index + $i) % $hossz;
            $lista[] = [$j, $this->szamok[$j]->cim];
        }
        return $lista;
    }

    public function ugras(int $index): void
    {
        if ($this->szamok) {
            $this->szol = true;
            $this->jel($this->allapotValtozott, true);
            $this->jatszd($index);
        }
    }

    public function hangero(int $szazalek): void
    {
        $this->hangeroErtek = $szazalek;
        if ($this->spotifyMod()) {
            if ($this->szol) {
                $this->spotifyHivas('hangero', ['szazalek' => (int)round($this->celHangero())]);
            }
            return;
        }
        if (!$this->animacio->fut()) {
            $this->fo->hangero(self::szint($this->celHangero(), $this->erosites));
        }
    }

    public function halkit(bool $halkitva): void
    {
        if ($this->halkitva === $halkitva) {
            return;
        }
        $this->halkitva = $halkitva;
        if ($halkitva) {
            $this->kifutoHalkit(0.6);
        }
        if (!$this->szol) {
            return;
        }
        if ($this->spotifyMod()) {
            $this->spotifyHivas('hangero', ['szazalek' => (int)round($this->celHangero())]);
            return;
        }
        $this->gorbe = '';
        $this->animacio->indit($this->hangeroErtek * ($halkitva ? 1.0 : 0.25), $this->celHangero(), 0.6);
    }

    private function lejatszasiHiba(string $szoveg): void
    {
        Naplo::ir("Lejátszási hiba ({$this->mostCim}): {$szoveg}");
        if (!$this->szol || !$this->szamok) {
            return;
        }
        $this->hibasorozat++;
        if ($this->hibasorozat >= min(count($this->szamok), 5)) {
            $this->hibasorozat = 0;
            $this->megallit(false);
            $this->jel($this->hibaJelzes, "A zene nem játszható le: {$szoveg}");
            return;
        }
        $hibas = $this->szamok[$this->index];
        if ($hibas->yt !== '' && $hibas->helyi) {
            @unlink($hibas->helyi);
            $hibas->helyi = null;
        }
        $this->kesleltetettLepes = microtime(true) + 0.8;
    }

    public function tick(): void
    {
        $this->animacio->tick();
        $this->kifutoAnimacio->tick();
        foreach ($this->kifuto->esemenyek() as $e) {
            $this->kifutoAnimacio->allj();
        }
        foreach ($this->fo->esemenyek() as $e) {
            if ($e[0] === 'vege' && $this->szol) {
                $this->hibasorozat = 0;
                $this->jatszd($this->index + 1);
            } elseif ($e[0] === 'hiba') {
                $this->lejatszasiHiba($e[1] ?? 'lejátszási hiba');
            }
        }
        if ($this->kesleltetettLepes !== null && microtime(true) >= $this->kesleltetettLepes) {
            $this->kesleltetettLepes = null;
            if ($this->szol) {
                $this->jatszd($this->index + 1);
            }
        }
        $this->atusztatasEllenoriz();
        if ($this->spotifyMod() && $this->szol && microtime(true) >= $this->spotifyKovetkezoFrissites) {
            $this->spotifyKovetkezoFrissites = microtime(true) + 5.0;
            $this->spotifyFrissit();
        }
    }

    private function atusztatasEllenoriz(): void
    {
        $atusztatas = Atuszas::hossz($this->atusztatasBe, $this->atusztatasMp);
        if (!$this->szol || $this->halkitva || $atusztatas <= 0 || count($this->szamok) < 2 || !$this->fo->szol()) {
            return;
        }
        $hossz = $this->fo->hossz();
        $pozicio = $this->fo->pozicio();
        if ($hossz < $atusztatas * 3 || $this->kifuto->szol()) {
            return;
        }
        $vegeCsend = $this->csendMp($this->szamok[$this->index % count($this->szamok)]->helyi)[1];
        if ($pozicio < Atuszas::kezdetMp($hossz, $vegeCsend, $atusztatas)) {
            return;
        }
        $kovetkezo = ($this->index + 1) % count($this->szamok);
        $szam = $this->szamok[$kovetkezo];
        if (!$szam->helyi) {
            return;
        }
        $this->atuszasIndit($atusztatas);
        $this->index = $kovetkezo;
        $voltKert = $szam->kert;
        if ($szam->kert) {
            $szam->kert = false;
            $this->jel($this->kertSzol, $szam->yt);
        }
        $this->lejatszottKereseketKivesz($szam, $voltKert);
        $this->mostCim = $szam->cim;
        $this->jel($this->szamValtozott, $szam->cim, $this->forrasNev());
        $this->forrastIndit($szam->helyi, $atusztatas);
        $this->eloreLetolt();
    }

    private function spotifyHivas(string $muvelet, array $adat = [], ?\Closure $siker = null): void
    {
        if (!$this->spotifyClientId) {
            $this->jel($this->hibaJelzes, 'A Spotify nincs összekapcsolva (Zene → Spotify).');
            return;
        }
        $this->hatter->futtat('spotify', ['client_id' => $this->spotifyClientId, 'muvelet' => $muvelet] + $adat, $siker,
            fn(string $hiba) => $this->jel($this->hibaJelzes, $hiba), 'alap', 60);
    }

    private function spotifyIndit(): void
    {
        $uri = Spotify::uri((string)($this->forras['cim'] ?? ''));
        if (!$uri) {
            $this->jel($this->hibaJelzes, 'Érvénytelen Spotify-link.');
            return;
        }
        $this->szol = true;
        $this->jel($this->allapotValtozott, true);
        $this->spotifyHivas('lejatszas', ['uri' => $uri, 'eszkoz' => $this->spotifyEszkoz, 'keveres' => $this->keveres,
            'hangero' => (int)round($this->celHangero())]);
        $this->spotifyKovetkezoFrissites = microtime(true) + 1.0;
    }

    private function spotifyMegallit(bool $elhalkitas): void
    {
        $this->spotifyHivas('megallit', ['elhalkitas' => $elhalkitas, 'honnan' => (int)round($this->celHangero()),
            'mp' => $this->elhalkitasMp, 'vissza' => $this->hangeroErtek]);
    }

    private function spotifyFrissit(): void
    {
        $this->spotifyHivas('most_szol', [], function (?array $adat): void {
            if (!$adat || $adat['cim'] === $this->mostCim || !$this->spotifyMod()) {
                return;
            }
            if ($this->spotifySzurt($adat)) {
                return;
            }
            $this->mostCim = $adat['cim'];
            $this->spotifyFelirat = $adat['eloado'] ? "{$adat['eloado']} - {$adat['cim']}" : $adat['cim'];
            $this->jel($this->szamValtozott, $adat['eloado'] ? "{$adat['eloado']} – {$adat['cim']}" : $adat['cim'],
                $this->forrasNev() ?: 'Spotify');
            $this->jel($this->spotifySzoveg, $this->spotifyFelirat, $adat['cim']);
        });
    }

    private function spotifySzurt(array $adat): bool
    {
        $ok = $this->szuro?->talalat($adat['cim'], $adat['eloado']);
        if ($ok === null && $this->szuro && $this->szuro->alap && !empty($adat['explicit'])) {
            $ok = 'explicit jelölés';
        }
        if ($ok === null && $this->tiltottE('', $adat['eloado'] ? "{$adat['eloado']} - {$adat['cim']}" : $adat['cim'])) {
            $ok = 'letiltott szám';
        }
        if ($ok === null) {
            $this->spotifyKihagyas = 0;
            return false;
        }
        return $this->spotifyAtugrik($adat, $ok);
    }

    public function spotifyTragar(string $cim): void
    {
        if ($this->spotifyMod() && $this->mostCim === $cim) {
            $this->spotifyAtugrik(['cim' => $cim], 'trágár szöveg');
        }
    }

    private function spotifyAtugrik(array $adat, string $ok): bool
    {
        $this->spotifyKihagyas++;
        $this->jel($this->kiszurve, "Spotify-szám átugorva ({$ok}): {$adat['cim']}");
        if ($this->spotifyKihagyas > self::SPOTIFY_MAX_KIHAGYAS) {
            $this->spotifyKihagyas = 0;
            $this->megallit(false);
            $this->jel($this->hibaJelzes, 'A Spotify-listában egymás után túl sok szám akadt fenn a szűrőn, a zene leállt.');
            return true;
        }
        $this->mostCim = $adat['cim'];
        $this->spotifyHivas('kovetkezo');
        $this->spotifyKovetkezoFrissites = microtime(true) + 1.5;
        return true;
    }

    public function allj(): void
    {
        $this->generacio++;
        $this->animacio->allj();
        $this->kifutoLeallit();
        $this->fo->allj();
    }

    public function leall(): void
    {
        $this->fo->leall();
        $this->kifuto->leall();
    }
}
