<?php

declare(strict_types=1);

namespace KozgazFM;

use DateInterval;
use DateTimeImmutable;

final class Vezerlo
{
    public array $b;
    private int $bIdo = 0;
    public Hatter $hatter;
    public CsengoLejatszo $csengo;
    public CsengoLejatszo $proba;
    public ZeneLejatszo $zene;
    public Kiegyenlito $kiegyenlito;
    public Bemondo $bemondo;
    public ?Statisztika $stat;
    public Ertesito $ertesito;
    public Tartalek $tartalek;
    public ZenekeresSzerver $keresSzerver;
    public ZeneSzinkron $zeneSzinkron;
    public Zenekeres $keresek;
    public Szuro $szuro;
    public bool $riasztas = false;
    private bool $autoRiado = false;
    private bool $autoZene = false;
    private array $sor = [];
    public ?array $musorBlokk = null;
    private bool $musorKezi = false;
    private ?Esemeny $kihagyott = null;
    private array $esemenyek = [];
    private ?string $nap = null;
    private ?DateTimeImmutable $utolso = null;
    private array $uzenetek = [];
    private int $uzenetSzam = 0;
    private bool $kovetkezoKert = false;
    private ?string $reggeliNap = null;
    private array $kimenetek = [];
    private float $kimenetIdo = 0.0;
    private ?string $kimenetJel = null;
    private array $dalszovegNezett = [];
    private bool $dalszovegFut = false;
    private float $dalszovegSzunet = 0.0;
    private float $dalszovegIdo = 0.0;
    private float $allapotIdo = 0.0;
    private float $eletjelIdo = 0.0;
    private float $beallitasEllenorzes = 0.0;
    private float $takaritasIdo = 0.0;
    private bool $keresekValtoztak = false;
    private float $indulas;

    public function __construct()
    {
        $this->indulas = microtime(true);
        $this->b = Beallitasok::betolt();
        $this->bIdo = is_file(Utvonalak::beallitasFajl()) ? (int)filemtime(Utvonalak::beallitasFajl()) : 0;
        $this->hatter = new Hatter();
        $this->kiegyenlito = new Kiegyenlito($this->hatter);
        $this->csengo = new CsengoLejatszo('csengo');
        $this->proba = new CsengoLejatszo('proba');
        $this->zene = new ZeneLejatszo($this->hatter, $this->kiegyenlito);
        $this->bemondo = new Bemondo($this->hatter);
        $this->stat = $this->statisztikaNyit();
        $this->ertesito = new Ertesito(fn() => $this->b, $this->hatter, fn(string $s) => $this->log($s));
        $this->keresek = new Zenekeres();
        $this->szuro = new Szuro($this->b['szuro_szavak'], $this->b['szuro_alap']);
        $this->tartalek = new Tartalek($this->hatter, fn() => $this->b);
        $this->keresSzerver = new ZenekeresSzerver($this->hatter, $this);
        $this->zeneSzinkron = new ZeneSzinkron($this->hatter, $this);
        $this->kotesek();
        $this->beallitasokAlkalmazasa();
    }

    private function kotesek(): void
    {
        $this->csengo->kesz = fn() => $this->kovetkezoFeladat();
        $this->bemondo->kesz = fn() => $this->kovetkezoFeladat();
        $this->bemondo->hangfajlKesz = function (string $ut): void {
            if (!$this->csengo->lejatszas($ut, $this->b['csengo_hangero'], false, 'bemondas')) {
                $this->kovetkezoFeladat();
            }
        };
        $this->kiegyenlito->mert = fn(string $ut) => $this->zene->mertJott($ut);
        $z = $this->zene;
        $z->hibaJelzes = function (string $s): void {
            $this->jelez($s, 'hiba', false);
            $this->ertesito->kuld('hiba', 'Zenehiba', $s, 'figy', Ertesito::ISMETLES_MP, 'zenehiba');
        };
        $z->szamValtozott = function (string $cim, string $forras): void {
            $this->log("Zene: {$cim} ({$forras})");
            $kert = $this->kovetkezoKert;
            $this->kovetkezoKert = false;
            $this->stat?->szamKezd($cim, $forras, $kert);
        };
        $z->allapotValtozott = function (bool $szol): void {
            if (!$szol) {
                $this->stat?->szamVege();
            } elseif ($this->stat && !$this->stat->nyitott() && $this->zene->mostCim !== '') {
                $this->stat->szamKezd($this->zene->mostCim, $this->zene->forras['nev'] ?? '');
            }
        };
        $z->kertSzol = function (string $yt): void {
            $this->kovetkezoKert = true;
            if ($this->keresek->szol($yt)) {
                $this->keresekValtoztak = true;
            }
        };
        $z->kiszurve = fn(string $s) => $this->log($s);
        $z->spotifySzoveg = fn(string $felirat, string $cim) => $this->spotifyDalszoveg($felirat, $cim);
        $this->tartalek->atvetel = function (): void {
            $this->atvetel();
            $this->ertesito->kuld('tartalek', 'A tartalékgép átvette a csengetést', 'A fő gép nem válaszol, ez a gép csenget helyette.', 'hiba', 60);
        };
        $this->tartalek->visszaadas = function (): void {
            $this->visszaadas();
            $this->ertesito->kuld('tartalek', 'A fő gép újra működik', 'A tartalékgép visszaadta a csengetést a fő gépnek.', 'info', 60);
        };
        $this->tartalek->szinkronizalt = function (array $adat): void {
            [$uj, $valtozott] = Tartalek::szinkronAlkalmaz($this->b, $adat);
            if ($valtozott) {
                $this->b = $uj;
                $this->log('Beállítások átvéve a fő gépről (' . count($valtozott) . ' csoport)');
                $this->mentes();
            }
        };
    }

    private function statisztikaNyit(): ?Statisztika
    {
        try {
            $s = new Statisztika();
            $s->takarit();
            return $s;
        } catch (\Throwable $e) {
            Naplo::ir('A statisztika nem nyitható meg: ' . $e->getMessage());
            return null;
        }
    }

    public function log(string $szoveg): void
    {
        Naplo::ir($szoveg);
    }

    private function uzenet(string $szoveg, string $szint): void
    {
        $this->uzenetek[] = ['id' => ++$this->uzenetSzam, 'ido' => time(), 'szoveg' => $szoveg, 'szint' => $szint];
        $this->uzenetek = array_slice($this->uzenetek, -20);
    }

    public function jelez(string $szoveg, string $szint = 'info', bool $ertesit = true): void
    {
        $this->log($szint === 'info' ? $szoveg : "HIBA: {$szoveg}");
        $this->uzenet($szoveg, $szint);
        if ($szint === 'hiba' && $ertesit) {
            $this->ertesito->kuld('hiba', 'Hiba a csengetőn', $szoveg, 'figy');
        }
    }

    private function tiltas(string $szoveg): void
    {
        $this->log($szoveg);
        $this->uzenet($szoveg, 'hiba');
    }

    public function indit(): void
    {
        $this->log('Közgáz FM ' . KFM_VERZIO . ' (PHP) elindult');
        $this->ertesito->kuld('indulas', 'A Közgáz FM elindult', 'Verzió: ' . KFM_VERZIO . '. Ha nem te indítottad újra, lehet, hogy összeomlott vagy áramszünet volt.', 'info', 60);
        $this->leallasAlattKimaradt();
        $this->eletjelIr();
        $this->kimenetFrissit(true);
    }

    public function leallit(): void
    {
        $this->zene->allj();
        $this->stat?->szamVege();
        $this->csengo->leall();
        $this->proba->leall();
        $this->zene->leall();
        $this->hatter->leallit();
        $this->allapotIr(true);
    }

    private function eletjelIr(): void
    {
        @file_put_contents(Utvonalak::eletjelFajl(), date('Y-m-d\TH:i:s'));
    }

    private function leallasAlattKimaradt(): void
    {
        $szoveg = trim((string)@file_get_contents(Utvonalak::eletjelFajl()));
        if ($szoveg === '') {
            return;
        }
        try {
            $utolso = new DateTimeImmutable($szoveg);
        } catch (\Throwable) {
            return;
        }
        $most = new DateTimeImmutable();
        if ($most->getTimestamp() - $utolso->getTimestamp() > 120) {
            $this->kimaradtak($utolso, $most);
        }
    }

    public function zonaKimenetek(): array
    {
        return Kimenetek::zonak($this->b);
    }

    private function kimenetFrissit(bool $kenyszer = false): void
    {
        if (!$kenyszer && microtime(true) - $this->kimenetIdo < 30) {
            return;
        }
        $this->kimenetIdo = microtime(true);
        $this->kimenetek = Kimenetek::lista();
        $jel = json_encode(array_column($this->kimenetek, 'azon'));
        if ($jel !== $this->kimenetJel) {
            $elso = $this->kimenetJel === null;
            $this->kimenetJel = $jel;
            if (!$elso || microtime(true) - $this->indulas > 15) {
                $this->kimenetEllenoriz();
            }
        }
        if ($kenyszer) {
            $this->kimenetEllenoriz();
        }
    }

    private function kimenetEllenoriz(): void
    {
        if (Kimenetek::nev($this->b, $this->kimenetek) !== null) {
            return;
        }
        if (!$this->kimenetek) {
            $szoveg = 'A gépen nincs elérhető hangkimenet, a csengő nem fog szólni. Ellenőrizd a hangkártyát, a HDMI- vagy USB-kábelt (és hogy a démon eléri-e a PipeWire/Pulse socketet).';
        } elseif ($this->b['zonak']) {
            $szoveg = 'Nem érhető el ezeknek a zónáknak a hangkimenete: ' . implode(', ', Kimenetek::hianyzoZonak($this->b, $this->kimenetek)) . '. Ott az alapértelmezett kimenet szól; ellenőrizd a kábeleket és az erősítőket.';
        } else {
            $szoveg = 'A beállított hangkimenet nem érhető el (pl. kihúzták a kábelt), a csengő az alapértelmezett kimeneten szól. Ellenőrizd az erősítő bekötését.';
        }
        $this->log("HIBA: {$szoveg}");
        $this->ertesito->kuld('hangkimenet', 'Hangkimenet-gond', $szoveg, 'hiba');
    }

    private function reggeliOnteszt(DateTimeImmutable $most): void
    {
        $ma = $most->format('Y-m-d');
        if ($this->reggeliNap === $ma || $this->tartalek->passziv() || !$this->ertesito->bekapcsolt('reggel')) {
            return;
        }
        $ido = Orarend::idopont(Orarend::nap($most), $this->b['ertesites_reggel_ido']);
        $elteres = $most->getTimestamp() - $ido->getTimestamp();
        if ($elteres < 0 || $elteres > 3 * 3600) {
            return;
        }
        $this->reggeliNap = $ma;
        $rend = Orarend::napiRend($this->b, $most);
        if ($rend === null) {
            return;
        }
        $csengok = array_values(array_filter($this->esemenyek, static fn(Esemeny $e) => $e->csengo()));
        $forras = $this->aktivForras();
        $tegnap = $this->stat?->osszegzes($most->sub(new DateInterval('P1D')), $most->sub(new DateInterval('P1D')));
        $hatar = $most->sub(new DateInterval('P1D'))->format('Y-m-d H:i:s');
        $hibak = count(array_filter(Naplo::utolso(2000), static fn($s) => substr($s, 0, 19) >= $hatar && str_contains($s, 'HIBA:')));
        $szabad = @disk_free_space(Utvonalak::adat());
        [$cim, $uzenet, $szint] = Ertesito::reggeliJelentes($most, $rend['nev'], $csengok ? $csengok[0]->ido : null, count($csengok),
            Kimenetek::nev($this->b, $this->kimenetek), $forras['nev'] ?? null, count($this->zene->szamok), $tegnap, $hibak,
            $szabad !== false ? $szabad / 1e9 : null);
        $this->log("Reggeli önteszt: {$cim}");
        $this->ertesito->kuld('reggel', $cim, $uzenet, $szint, 0);
    }

    public function beallitasokAlkalmazasa(): void
    {
        $b = $this->b;
        $zonak = $this->zonaKimenetek();
        $this->csengo->zonak($zonak);
        $this->proba->zonak($zonak);
        $this->zene->zonak($zonak);
        $this->zene->keveres = $b['keveres'];
        $this->zene->gyorsitotar = $b['youtube_gyorsitotar'];
        $this->zene->elhalkitasMp = $b['elhalkitas'];
        $this->zene->atusztatasMp = $b['atusztatas'];
        $this->zene->atusztatasBe = $b['atusztatas_be'];
        $this->zene->hangero($b['zene_hangero']);
        $this->zene->spotifyEszkoz = $b['spotify_eszkoz'];
        $this->zene->spotifyClientId = trim($b['spotify_client_id']) ?: null;
        $this->kiegyenlito->bekapcsolva = $b['hangero_kiegyenlites'];
        $this->zene->erositesUjra();
        foreach ($this->zene->szamok as $s) {
            $this->kiegyenlito->kell($s->helyi);
        }
        $this->bemondo->hang = $b['tts_hang'];
        $uj = new Szuro($b['szuro_szavak'], $b['szuro_alap']);
        if ($uj->kulcs() !== $this->szuro->kulcs()) {
            $this->szuro = $uj;
        }
        $this->zene->szuroBeallitas($this->szuro, $b['szuro_korhataros']);
        $this->tiltasFrissit();
        $this->zene->forrasBeallitas($this->jelenlegiForras());
        $this->nap = null;
    }

    private function tartalekHang(string $hang): string
    {
        foreach (Beallitasok::HANG_MEZOK as $mezo => $alap) {
            if ($this->b[$mezo] === $hang) {
                return $alap;
            }
        }
        return Beallitasok::HANG_MEZOK['hang_becsengo'];
    }

    public function mentes(): void
    {
        Beallitasok::ment($this->b);
        clearstatcache(true, Utvonalak::beallitasFajl());
        $this->bIdo = (int)filemtime(Utvonalak::beallitasFajl());
        $this->beallitasokAlkalmazasa();
        $this->szinkron();
    }

    public function aktivForras(): ?array
    {
        $forrasok = $this->b['forrasok'];
        if (!$forrasok) {
            return null;
        }
        $i = $this->b['aktiv_forras'];
        if (isset($forrasok[$i]) && $forrasok[$i]['aktiv']) {
            return $forrasok[$i];
        }
        foreach ($forrasok as $f) {
            if ($f['aktiv']) {
                return $f;
            }
        }
        return null;
    }

    private function blokkForras(int $nap, int $szunet): array
    {
        $blokk = Orarend::musorblokk($this->b, $nap, $szunet);
        if ($blokk !== null) {
            foreach ($this->b['forrasok'] as $f) {
                if ($f['aktiv'] && $f['nev'] === $blokk['forras']) {
                    return [$f, $blokk];
                }
            }
        }
        return [$this->aktivForras(), null];
    }

    public function jelenlegiForras(?DateTimeImmutable $most = null): ?array
    {
        $most ??= new DateTimeImmutable();
        $szunet = $this->b['musorblokkok'] && !$this->musorKezi ? Orarend::zeneSzunet($this->b, $most) : null;
        if ($szunet === null) {
            $this->musorBlokk = null;
            return $this->aktivForras();
        }
        [$forras, $this->musorBlokk] = $this->blokkForras(Orarend::het($most), $szunet);
        return $forras;
    }

    public function szoloForras(): ?array
    {
        $f = $this->zene->forras;
        return $f !== null && in_array($f, $this->b['forrasok'], false) ? $f : $this->aktivForras();
    }

    public function maiEsemenyek(): array
    {
        $this->frissitNap(new DateTimeImmutable());
        return $this->esemenyek;
    }

    private function frissitNap(DateTimeImmutable $most): void
    {
        $nap = $most->format('Y-m-d');
        if ($this->nap !== $nap) {
            $this->nap = $nap;
            $this->esemenyek = Orarend::napiEsemenyek($this->b, $most);
        }
    }

    public function tick(): void
    {
        $most = new DateTimeImmutable();
        $this->hatter->tick();
        $this->csengo->tick();
        $this->proba->tick();
        $this->zene->tick();
        $this->beallitasFigyeles();
        $this->utemezo($most);
        $this->tartalek->tick();
        $this->keresSzerver->tick();
        if (!$this->tartalek->passziv()) {
            $this->zeneSzinkron->tick();
        }
        $this->dalszovegOr();
        $this->kimenetFrissit();
        $this->parancsok();
        if ($this->keresekValtoztak) {
            $this->keresekValtoztak = false;
            Adatbazis::keresekMent($this->keresek->lista);
        }
        if (microtime(true) - $this->eletjelIdo > 60) {
            $this->eletjelIdo = microtime(true);
            $this->eletjelIr();
        }
        if (microtime(true) - $this->takaritasIdo > 600) {
            $this->takaritasIdo = microtime(true);
            Adatbazis::takarit();
            $this->keresek->takarit();
            $this->keresekValtoztak = true;
        }
        if (microtime(true) - $this->allapotIdo > 0.5) {
            $this->allapotIr();
        }
    }

    private function beallitasFigyeles(): void
    {
        if (microtime(true) - $this->beallitasEllenorzes < 1) {
            return;
        }
        $this->beallitasEllenorzes = microtime(true);
        clearstatcache(true, Utvonalak::beallitasFajl());
        $ido = is_file(Utvonalak::beallitasFajl()) ? (int)filemtime(Utvonalak::beallitasFajl()) : 0;
        if ($ido !== $this->bIdo) {
            $this->bIdo = $ido;
            $this->b = Beallitasok::betolt();
            $this->log('A beállításfájl kívülről megváltozott, újratöltve');
            $this->beallitasokAlkalmazasa();
            $this->szinkron();
        }
    }

    private function utemezo(DateTimeImmutable $most): void
    {
        $elozo = $this->utolso;
        $this->frissitNap($most);
        $this->utolso = $most;
        if ($elozo === null || $most < $elozo || $most->getTimestamp() - $elozo->getTimestamp() > 20) {
            if ($elozo !== null) {
                $this->log('Óraugrás vagy alvás után újraszinkronizálás');
                $this->kimaradtak($elozo, $most);
            }
            $this->szinkron();
            return;
        }
        $this->reggeliOnteszt($most);
        $esemenyek = $elozo->format('Y-m-d') !== $most->format('Y-m-d')
            ? array_merge(Orarend::napiEsemenyek($this->b, $elozo), $this->esemenyek) : $this->esemenyek;
        foreach ($esemenyek as $e) {
            if ($elozo < $e->ido && $e->ido <= $most) {
                $this->kezel($e);
            }
        }
    }

    private function kimaradtak(DateTimeImmutable $elozo, DateTimeImmutable $most): void
    {
        if ($this->tartalek->passziv()) {
            return;
        }
        $napok = array_unique([$elozo->format('Y-m-d'), $most->format('Y-m-d')]);
        sort($napok);
        $esemenyek = [];
        foreach ($napok as $nap) {
            array_push($esemenyek, ...($nap === $this->nap ? $this->esemenyek : Orarend::napiEsemenyek($this->b, new DateTimeImmutable($nap))));
        }
        $kimaradt = Ertesito::kimaradtCsengetesek($esemenyek, $elozo, $most, array_merge(Esemeny::CSENGOK, [Esemeny::RENDKIVULI]));
        if (!$kimaradt) {
            return;
        }
        $lista = implode(', ', array_map(static fn(Esemeny $e) => $e->ido->format('H:i') . ' ' . $e->leiras(), array_slice($kimaradt, 0, 8)));
        $tovabbi = count($kimaradt) > 8 ? ' és még ' . (count($kimaradt) - 8) : '';
        $szoveg = count($kimaradt) . ' csengetés kimaradt (' . $elozo->format('m.d. H:i') . ' és ' . $most->format('m.d. H:i')
            . " között a program nem futott, a gép aludt vagy ugrott az órája): {$lista}{$tovabbi}";
        $this->log("HIBA: {$szoveg}");
        $this->ertesito->kuld('kimaradt', 'Kimaradt csengetés', $szoveg, 'hiba');
    }

    private function szinkron(): void
    {
        $most = new DateTimeImmutable();
        if ($this->riasztas) {
            return;
        }
        if ($this->tartalek->passziv()) {
            if ($this->autoZene && $this->zene->szol()) {
                $this->zene->megallit();
            }
            $this->autoZene = false;
            return;
        }
        $ablak = Orarend::zeneAblakban($this->b, $most);
        if ($ablak && !$this->zene->szol()) {
            $this->autoZene = true;
            $this->zene->forrasBeallitas($this->jelenlegiForras($most));
            $this->zene->indit();
        } elseif (!$ablak && $this->autoZene && $this->zene->szol()) {
            $this->autoZene = false;
            $this->zene->megallit();
        }
    }

    private function kezel(Esemeny $e): void
    {
        if ($this->tartalek->passziv()) {
            if ($e->csengo() || $e->tipus === Esemeny::RENDKIVULI) {
                $this->kihagyott = $e;
            }
            return;
        }
        if ($this->riasztas && !in_array($e->tipus, [Esemeny::ZENE_LEALL, Esemeny::RIADO_VEGE, Esemeny::CSEND, Esemeny::CSEND_VEGE], true)) {
            $this->log('Kihagyva riasztás miatt: ' . $e->leiras());
            return;
        }
        switch ($e->tipus) {
            case Esemeny::RIADO:
                $this->log('Rendkívüli esemény: ' . $e->leiras());
                $this->riasztasIndit();
                $this->autoRiado = true;
                break;
            case Esemeny::RIADO_VEGE:
                if ($this->riasztas && $this->autoRiado) {
                    $this->riasztasLeallit();
                }
                break;
            case Esemeny::CSEND:
            case Esemeny::CSEND_VEGE:
                $this->log('Csendes időszak ' . ($e->tipus === Esemeny::CSEND ? 'kezdődik' : 'véget ért') . ': ' . ($e->rendkivuli['nev'] ?? ''));
                if ($e->tipus === Esemeny::CSEND && $this->zene->szol()) {
                    $this->zeneLeallit();
                }
                break;
            case Esemeny::RENDKIVULI:
                if ($e->rendkivuli) {
                    if ($this->zene->szol()) {
                        $this->autoZene = false;
                        $this->zene->megallit(false, true, true);
                    }
                    $this->csengetes($e->rendkivuli['hang'], $e->leiras(), null, $e->ido, 'rendkivuli');
                }
                break;
            case Esemeny::ZENE_INDUL:
                $this->musorKezi = false;
                [$forras, $this->musorBlokk] = $this->blokkForras(Orarend::het($e->ido), $e->ora);
                if ($forras === null) {
                    return;
                }
                $blokk = $this->musorBlokk ? " – {$this->musorBlokk['nev']} (" . Orarend::szunetNev($e->ora) . ", {$forras['nev']})" : '';
                $this->log("Szünetzene indul{$blokk}");
                $this->autoZene = true;
                $this->zene->forrasBeallitas($forras);
                $this->zene->indit();
                break;
            case Esemeny::ZENE_LEALL:
                if ($this->zene->szol() && $this->autoZene) {
                    $this->log('Szünetzene leáll');
                    $this->zene->megallit();
                }
                $this->autoZene = false;
                break;
            case Esemeny::BEMONDAS:
                if ($e->bemondas) {
                    $this->bemondas($e->bemondas);
                }
                break;
            case Esemeny::JELZO:
            case Esemeny::BECSENGO:
                if ($this->zene->szol()) {
                    $this->autoZene = false;
                    $this->zene->megallit(false, true, true);
                }
                $hang = $e->tipus === Esemeny::JELZO ? $this->b['hang_jelzo'] : $this->b['hang_becsengo'];
                $this->csengetes($hang, $e->leiras(), $e->hangero, $e->ido, $e->nev());
                break;
            case Esemeny::KICSENGO:
                $this->csengetes($this->b['hang_kicsengo'], $e->leiras(), $e->hangero, $e->ido, 'kicsengo');
                break;
        }
    }

    private function foglalt(): bool
    {
        if ($this->csengo->szol()) {
            $this->csengo->megallit();
            return true;
        }
        if ($this->bemondo->beszel()) {
            $this->bemondo->megallit();
            return true;
        }
        return false;
    }

    public function csengetes(string $hang, string $leiras = 'Kézi csengetés', ?int $hangero = null, ?DateTimeImmutable $tervezett = null, string $tipus = 'kezi'): void
    {
        if ($this->riasztas) {
            $this->tiltas('Riasztás közben nincs csengetés.');
            return;
        }
        $this->log("Csengetés: {$leiras}" . ($hangero !== null ? " (halkan, {$hangero}%)" : ''));
        $this->stat?->csengetes($tipus, $leiras, $tervezett);
        array_unshift($this->sor, ['tipus' => 'hang', 'ertek' => $hang, 'ismetles' => false, 'tartalek' => $this->tartalekHang($hang), 'hangero' => $hangero, 'cel' => 'csengo']);
        if (!$this->foglalt()) {
            $this->kovetkezoFeladat();
        }
    }

    public function bemondas(array $bem): void
    {
        if ($this->riasztas) {
            $this->tiltas('Riasztás közben nincs bemondás.');
            return;
        }
        $this->log('Bemondás: ' . $bem['nev']);
        if ($bem['gong']) {
            $this->sor[] = ['tipus' => 'hang', 'ertek' => $this->b['hang_gong'], 'ismetles' => false, 'tartalek' => Beallitasok::HANG_MEZOK['hang_gong'], 'hangero' => null, 'cel' => 'bemondas'];
        }
        $this->sor[] = ['tipus' => $bem['tipus'] === 'szoveg' ? 'szoveg' : 'fajl', 'ertek' => $bem['tartalom'], 'ismetles' => false, 'tartalek' => '', 'hangero' => null, 'cel' => 'bemondas'];
        if (!$this->csengo->szol() && !$this->bemondo->beszel()) {
            $this->kovetkezoFeladat();
        }
    }

    public function gyorsBemondas(string $szoveg, bool $gong = true): void
    {
        $this->bemondas(['nev' => 'Gyors bemondás', 'ido' => '00:00', 'tipus' => 'szoveg', 'tartalom' => $szoveg, 'gong' => $gong]);
    }

    public function bemondasLeallit(): void
    {
        $this->sor = array_values(array_filter($this->sor, fn($f) => $f['tipus'] === 'hang' && $f['ertek'] !== $this->b['hang_gong']));
        if ($this->bemondo->beszel()) {
            $this->bemondo->megallit();
        } elseif ($this->csengo->szol() && !$this->riasztas) {
            $this->csengo->megallit();
        }
    }

    private function kovetkezoFeladat(): void
    {
        $this->proba->megallit();
        while ($this->sor) {
            $f = array_shift($this->sor);
            $this->zene->halkit(true);
            if ($f['tipus'] === 'szoveg') {
                if (Bemondo::elerheto() && $this->bemondo->mond($f['ertek'])) {
                    return;
                }
                $this->jelez('A gépen nincs elérhető felolvasó hang (TTS).', 'hiba');
                continue;
            }
            $hangero = $f['ismetles'] ? 100 : ($f['hangero'] ?: $this->b['csengo_hangero']);
            if ($this->csengo->lejatszas($f['ertek'], $hangero, $f['ismetles'], $f['cel'])) {
                return;
            }
            if ($f['tartalek'] !== '' && $f['tartalek'] !== $f['ertek']) {
                $this->jelez('A beállított csengőhang nem található, a beépített hang szól helyette.', 'hiba');
                if ($this->csengo->lejatszas($f['tartalek'], $hangero, $f['ismetles'], $f['cel'])) {
                    return;
                }
            }
            $this->jelez("A hangfájl nem található: {$f['ertek']}", 'hiba');
        }
        if (!$this->riasztas) {
            $this->zene->halkit(false);
        }
    }

    public function riasztasIndit(): void
    {
        if ($this->riasztas) {
            return;
        }
        $this->riasztas = true;
        $this->autoRiado = false;
        $this->autoZene = false;
        $this->zene->megallit(false, true, true);
        $this->log('RIASZTÁS ELINDÍTVA');
        $this->ertesito->kuld('riasztas', 'Riasztás indult', date('H:i') . '-kor elindult a riasztás a Közgáz FM-en.', 'hiba', 60);
        $this->sor = [['tipus' => 'hang', 'ertek' => $this->b['hang_riasztas'], 'ismetles' => true, 'tartalek' => Beallitasok::HANG_MEZOK['hang_riasztas'], 'hangero' => null, 'cel' => 'mind']];
        if (!$this->foglalt()) {
            $this->kovetkezoFeladat();
        }
        $this->uzenet('RIASZTÁS folyamatban – a Riasztás oldalon állítható le.', 'hiba');
    }

    public function riasztasLeallit(): void
    {
        if (!$this->riasztas) {
            return;
        }
        $this->riasztas = false;
        $this->autoRiado = false;
        $this->sor = [];
        $this->log('Riasztás leállítva');
        if (!$this->foglalt()) {
            $this->zene->halkit(false);
        }
    }

    public function zeneIndit(): void
    {
        $this->autoZene = false;
        $this->zene->indit();
    }

    public function zeneLeallit(): void
    {
        $this->autoZene = false;
        $this->zene->megallit();
    }

    public function forrasValtas(int $index): void
    {
        $this->b['aktiv_forras'] = $index;
        Beallitasok::ment($this->b);
        $this->bIdo = (int)filemtime(Utvonalak::beallitasFajl());
        $this->musorKezi = $this->musorBlokk !== null;
        $this->musorBlokk = null;
        $this->zene->forrasBeallitas($this->aktivForras());
    }

    public function maKapcsolo(string $mezo, bool $be): void
    {
        $this->b[$mezo] = $be ? date('Y-m-d') : '';
        $this->mentes();
        if ($mezo === 'ma_nincs_zene' && $be && $this->autoZene) {
            $this->zeneLeallit();
        }
        $this->log(($mezo === 'ma_nincs_csengetes' ? 'Ma nincs csengetés' : 'Ma nincs szünetzene') . ($be ? ' – bekapcsolva' : ' – kikapcsolva'));
    }

    public function maRend(string $nev): void
    {
        $ma = date('Y-m-d');
        if ($nev !== '') {
            $this->b['kivetelek'][$ma] = $nev;
        } else {
            unset($this->b['kivetelek'][$ma]);
        }
        $this->mentes();
        $this->log('Mai csengetési rend: ' . ($nev ?: 'alapértelmezett'));
    }

    private function atvetel(): void
    {
        $this->jelez('A fő gép nem válaszol – a tartalék gép átvette a csengetést.', 'hiba', false);
        $e = $this->kihagyott;
        $this->kihagyott = null;
        if ($e !== null) {
            $kulonbseg = time() - $e->ido->getTimestamp();
            if ($kulonbseg >= 0 && $kulonbseg <= 60) {
                $this->log('Kimaradt csengetés pótlása: ' . $e->leiras());
                $this->kezel($e);
            }
        }
        $this->szinkron();
    }

    private function visszaadas(): void
    {
        $this->log('A fő gép újra elérhető – a tartalék gép visszaállt készenlétbe');
        $this->kihagyott = null;
        $this->szinkron();
    }

    public function telefonTiltott(string $eszkoz): bool
    {
        $ma = date('Y-m-d');
        $kulcs = Zenekeres::telefonKulcs($eszkoz);
        foreach ($this->b['tiltott_telefonok'] as $t) {
            if ($t['kulcs'] === $kulcs && $t['ig'] >= $ma) {
                return true;
            }
        }
        return false;
    }

    public function zenekeresUj(string $szoveg, string $nev, string $eszkoz, string $ip, string $azon = ''): array
    {
        if (!$this->b['zenekeres']) {
            throw new Hiba('A zenekérés most nincs bekapcsolva.', 'disabled', 503);
        }
        if ($this->telefonTiltott($eszkoz)) {
            throw new Hiba('Erről a telefonról most nem kérhetsz számot.', 'device_blocked', 403);
        }
        $k = $this->keresek->uj($szoveg, $nev, $eszkoz, $ip, $this->b['zenekeres_napi'], $this->b['zenekeres_tiltott'], $this->szuro, $azon);
        $this->keresekValtoztak = true;
        $this->log("Zenekérés érkezett ({$ip}): {$k['szoveg']}");
        $this->stat?->keres('erkezett');
        $azon = $k['azon'];
        $cel = Zenekeres::youtubeCel($k['szoveg']);
        $tobblet = str_starts_with($cel, 'ytsearch') ? $k['szoveg'] : '';
        $this->hatter->futtat('zenekeres', ['cel' => $cel, 'max_mp' => $this->b['zenekeres_max_perc'] * 60, 'tobblet' => $tobblet,
            'dalszoveg' => $this->b['szuro_dalszoveg']], function (?array $eredmeny) use ($azon): void {
            $this->zenekeresKesz($azon, $eredmeny ?? []);
        }, function () use ($azon): void {
            try {
                $this->keresek->nemTalalt($azon, 'A keresés nem sikerült, próbáld újra később.');
            } catch (Hiba) {
            }
            $this->keresekValtoztak = true;
        }, 'alap', 240);
        return Zenekeres::nyilvanos($k);
    }

    private function zenekeresKesz(string $azon, array $eredmeny): void
    {
        $this->keresekValtoztak = true;
        $talalat = $eredmeny['talalat'] ?? null;
        $szoveg = $eredmeny['szoveg'] ?? null;
        $radio = $eredmeny['radio'] ?? '';
        try {
            if ($radio !== '' && $talalat) {
                $this->log("Zenekérés: hosszú szám ({$radio}), helyette a rádiós változat: {$talalat['cim']}");
            }
            if (!$talalat) {
                $this->keresek->nemTalalt($azon, 'Nem található ilyen szám a YouTube-on.');
                return;
            }
            $tragar = Dalszoveg::tragar($szoveg, $this->b['szuro_erzekenyseg']);
            $k = $this->keresek->talalat($azon, $talalat['yt'], $talalat['cim'], $talalat['hossz'], $this->b['zenekeres_max_perc'],
                $this->b['zenekeres_tiltott'], $talalat['korhatar'], $this->szuro, $this->b['szuro_korhataros'], $tragar,
                $this->zene->tiltottE($talalat['yt'], $talalat['cim']));
            if ($tragar) {
                $this->log("Zenekérés elutasítva, trágár szöveg: {$talalat['cim']} (" . Szuro::ertekelesSzoveg($szoveg['ertekeles']) . ')');
            }
            if ($radio !== '') {
                $this->keresek->megjegyzes($azon, 'Rádiós változat (radio edit), mert az eredeti túl hosszú.');
            }
            if ($k['allapot'] === 'varakozik') {
                $this->kertSzamKesz($azon, $szoveg, $this->b['szuro_dalszoveg'], $radio !== '');
            }
        } catch (Hiba) {
        }
    }

    private function kertSzamKesz(string $azon, ?array $szoveg, bool $szovegKell, bool $radio): void
    {
        $megjegyzes = null;
        if ($szovegKell && ($szoveg === null || !$szoveg['talalt'])) {
            $megjegyzes = $szoveg === null ? 'A dalszöveg-szolgáltatás nem érhető el, kézzel ellenőrizd.' : 'Nincs meg a dalszövege, kézzel ellenőrizd.';
        } elseif ($szoveg !== null && !$radio) {
            $megjegyzes = $szoveg['instrumental'] ? 'Instrumentális' : 'Dalszöveg: ' . Szuro::ertekelesSzoveg($szoveg['ertekeles']);
        }
        if ($megjegyzes !== null) {
            $this->keresek->megjegyzes($azon, $megjegyzes);
        }
        $ellenorzott = !$szovegKell || ($szoveg !== null && $szoveg['talalt']);
        $k = $this->keresek->keres($azon);
        if ($this->b['zenekeres_auto'] && $ellenorzott && $this->keresek->automatikusHelye()) {
            try {
                $this->zenekeresDontes($azon, true, 'automatikus');
                $this->uzenet("Kért szám a sorban: {$k['cim']}", 'info');
                return;
            } catch (Hiba $e) {
                $this->keresek->megjegyzes($azon, $e->getMessage());
            }
        }
        $this->uzenet("Új zenekérés: {$k['cim']}", 'info');
    }

    public function zenekeresDontes(string $azon, bool $elfogad, string $ki = ''): array
    {
        $k = $this->keresek->keres($azon);
        if ($elfogad && $k['allapot'] === 'varakozik' && !$this->zene->beszur(new Szam($k['cim'], null, $k['yt']))) {
            throw new Hiba('A kért szám csak mappa, MP3 vagy YouTube forrás mellett játszható (Spotify mellett nem).', 'no_source', 409);
        }
        $k = $this->keresek->dont($azon, $elfogad);
        $this->keresekValtoztak = true;
        if ($elfogad && $k['yt'] !== '' && $this->b['zenekeres_mp3']) {
            $mappa = trim($this->b['zenekeres_mp3_mappa']) ?: Utvonalak::adat() . '/kert-szamok';
            $cim = $k['cim'];
            $this->hatter->futtat('kert_mp3', ['yt' => $k['yt'], 'cim' => $cim, 'mappa' => $mappa],
                fn(?string $ut) => $ut && $this->log("Kért szám elmentve MP3-ként: {$ut}"),
                fn(string $h) => $this->log("HIBA: a kért szám MP3-mentése nem sikerült ({$cim}): {$h}"), 'letoltes', 900);
        }
        $this->log('Zenekérés ' . ($elfogad ? 'elfogadva' : 'elutasítva') . ($ki ? " ({$ki})" : '') . ": {$k['cim']}");
        $this->stat?->keres($elfogad ? 'elfogadva' : 'elutasitva');
        return $k;
    }

    private function tiltasFrissit(): void
    {
        $t = $this->b['tiltott_szamok'];
        $this->zene->tiltottBeallitas(array_column($t, 'yt'), array_column($t, 'cim'));
    }

    private function szamTiltas(string $cim, string $yt, string $ki): void
    {
        if (!$this->zene->tiltottE($yt, $cim)) {
            $this->b['tiltott_szamok'][] = ['azon' => bin2hex(random_bytes(6)), 'cim' => $cim, 'yt' => $yt, 'ido' => date('Y-m-d')];
            $this->tiltasFrissit();
            $this->mentes();
        }
        $this->log('Szám letiltva' . ($ki ? " ({$ki})" : '') . ": {$cim}");
        $this->zene->tiltottakatKivesz();
        if ($yt !== '') {
            foreach ($this->keresek->lista as $k) {
                if ($k['yt'] === $yt) {
                    $this->keresek->levesz($k['azon']);
                }
            }
        }
        $this->keresekValtoztak = true;
    }

    public function mostSzoloTiltasa(string $ki = ''): void
    {
        $szam = $this->zene->mostSzolo();
        if ($szam === null) {
            throw new Hiba('Most nem szól zene.', 'conflict', 409);
        }
        $this->szamTiltas($szam[0], $szam[1], $ki);
    }

    public function zenekeresSzamTiltas(string $azon, string $ki = ''): void
    {
        $k = $this->keresek->keres($azon);
        if ($k['yt'] === '') {
            throw new Hiba('Ehhez a kéréshez még nincs talált szám.', 'conflict', 409);
        }
        $this->szamTiltas($k['cim'], $k['yt'], $ki);
    }

    public function szamFeloldas(string $azon, string $ki = ''): void
    {
        foreach ($this->b['tiltott_szamok'] as $i => $t) {
            if ($t['azon'] === $azon) {
                array_splice($this->b['tiltott_szamok'], $i, 1);
                $this->tiltasFrissit();
                $this->log('Szám tiltása feloldva' . ($ki ? " ({$ki})" : '') . ": {$t['cim']}");
                $this->mentes();
                return;
            }
        }
        throw new Hiba('Nincs ilyen letiltott szám.', 'not_found', 404);
    }

    public function zenekeresLevesz(string $azon, string $ki = ''): void
    {
        $k = $this->keresek->keres($azon);
        if (!in_array($k['allapot'], ['elfogadva', 'szol'], true)) {
            throw new Hiba('Ez a kérés már nincs a sorban.', 'conflict', 409);
        }
        $this->zene->ytKivesz($k['yt']);
        $this->keresek->levesz($azon);
        $this->keresekValtoztak = true;
        $this->log('Kért szám levéve a sorból' . ($ki ? " ({$ki})" : '') . ": {$k['cim']}");
    }

    public function zenekeresTelefonTiltas(string $azon, string $ki = ''): void
    {
        $k = $this->keresek->keres($azon);
        $kulcs = Zenekeres::telefonKulcs($k['eszkoz']);
        $ig = (new DateTimeImmutable())->add(new DateInterval('P' . Zenekeres::TELEFON_TILTAS_NAP . 'D'))->format('Y-m-d');
        $ma = date('Y-m-d');
        $this->b['tiltott_telefonok'] = array_values(array_filter($this->b['tiltott_telefonok'], static fn($t) => $t['kulcs'] !== $kulcs && $t['ig'] >= $ma));
        $this->b['tiltott_telefonok'][] = ['kulcs' => $kulcs, 'nev' => $k['nev'], 'ig' => $ig];
        foreach ($this->keresek->lista as $m) {
            if ($m['eszkoz'] === $k['eszkoz']) {
                if (in_array($m['allapot'], ['elfogadva', 'szol'], true)) {
                    $this->zene->ytKivesz($m['yt']);
                }
                $this->keresek->levesz($m['azon']);
            }
        }
        $this->log("Telefon letiltva {$ig}-ig" . ($ki ? " ({$ki})" : '') . ": {$k['ip']}");
        $this->keresekValtoztak = true;
        $this->mentes();
    }

    public function telefonFeloldas(string $kulcs, string $ki = ''): void
    {
        $elotte = count($this->b['tiltott_telefonok']);
        $this->b['tiltott_telefonok'] = array_values(array_filter($this->b['tiltott_telefonok'], static fn($t) => $t['kulcs'] !== $kulcs));
        if (count($this->b['tiltott_telefonok']) === $elotte) {
            throw new Hiba('Nincs ilyen letiltott telefon.', 'not_found', 404);
        }
        $this->log('Telefon tiltása feloldva' . ($ki ? " ({$ki})" : ''));
        $this->mentes();
    }

    public function aktivCsend(?DateTimeImmutable $most = null): ?array
    {
        $most ??= new DateTimeImmutable();
        return Orarend::csendben(Orarend::csendesIdoszakok($this->b, Orarend::nap($most)), $most);
    }

    public function csendMost(int $perc, int $hangero = 0, string $nev = 'Csendes időszak'): array
    {
        $most = new DateTimeImmutable();
        $kezdet = $most->setTime((int)$most->format('H'), (int)$most->format('i'));
        $vege = min($kezdet->add(new DateInterval("PT{$perc}M")), $most->setTime(23, 59));
        if ($vege <= $most) {
            throw new Hiba('A nap végéig már nem fér bele csendes időszak.', 'validation_error', 422);
        }
        $r = ['nev' => $nev, 'datum' => $most->format('Y-m-d'), 'tol' => $kezdet->format('H:i'), 'tipus' => 'csend', 'ig' => $vege->format('H:i'),
            'hang' => 'beepitett:csengo', 'riado_perc' => 3, 'csengo_hangero' => $hangero, 'aktiv' => true];
        $this->b['rendkivuli'][] = $r;
        $this->log("Csendes időszak kezdődik: {$nev} ({$r['tol']}–{$r['ig']})");
        if ($this->zene->szol()) {
            $this->zeneLeallit();
        }
        $this->mentes();
        return $r;
    }

    public function csendVege(): bool
    {
        $most = new DateTimeImmutable();
        $r = $this->aktivCsend($most);
        if ($r === null) {
            return false;
        }
        foreach ($this->b['rendkivuli'] as $i => $x) {
            if ($x == $r) {
                $ig = $most->format('H:i');
                if ($ig <= $x['tol']) {
                    array_splice($this->b['rendkivuli'], $i, 1);
                } else {
                    $this->b['rendkivuli'][$i]['ig'] = $ig;
                }
                break;
            }
        }
        $this->log("Csendes időszak befejezve: {$r['nev']}");
        $this->mentes();
        return true;
    }

    public function hangProba(string $ertek): bool
    {
        if ($this->proba->szol()) {
            $this->proba->megallit();
            return true;
        }
        if ($this->riasztas || $this->csengo->szol()) {
            throw new Hiba('Csengetés vagy riasztás közben nincs meghallgatás.', 'conflict', 409);
        }
        return $this->proba->lejatszas($ertek, $this->b['csengo_hangero'], false, 'elso');
    }

    public function zonaProba(int $index): bool
    {
        if ($this->riasztas || $this->csengo->szol()) {
            throw new Hiba('Csengetés vagy riasztás közben nincs próbahang.', 'conflict', 409);
        }
        $this->proba->zonak($this->zonaKimenetek());
        return $this->proba->lejatszas($this->b['hang_gong'], $this->b['csengo_hangero'], false, "zona:{$index}");
    }

    private function dalszovegOr(): void
    {
        if (!$this->b['szuro_dalszoveg'] || $this->dalszovegFut || microtime(true) < $this->dalszovegSzunet || microtime(true) - $this->dalszovegIdo < 2) {
            return;
        }
        $this->dalszovegIdo = microtime(true);
        foreach ($this->zene->vizsgalando() as $szam) {
            if (isset($this->dalszovegNezett[$szam->cim])) {
                continue;
            }
            $ismert = Dalszoveg::tarKeres($szam->cim);
            if ($ismert === null) {
                $mappa = $szam->helyi && $szam->yt === '' ? basename(dirname($szam->helyi)) : '';
                $this->dalszovegLekerdez($szam->cim, $mappa, fn(array $e) => $this->dalszovegItel($szam, $e));
                return;
            }
            $this->dalszovegItel($szam, $ismert);
        }
    }

    private function dalszovegLekerdez(string $cim, string $tobblet, \Closure $kesz): void
    {
        $this->dalszovegFut = true;
        $this->hatter->futtat('dalszoveg', ['cim' => $cim, 'hossz' => 0, 'tobblet' => $tobblet], function (?array $e) use ($kesz): void {
            $this->dalszovegFut = false;
            $e && $kesz($e);
        }, function (): void {
            $this->dalszovegFut = false;
            $this->dalszovegSzunet = microtime(true) + 120;
        }, 'dalszoveg', 90);
    }

    private function dalszovegItel(Szam $szam, array $e): void
    {
        $this->dalszovegNezett[$szam->cim] = true;
        if (Dalszoveg::tragar($e, $this->b['szuro_erzekenyseg'])) {
            $this->zene->tragaratKivesz($szam, Szuro::ertekelesSzoveg($e['ertekeles']));
        }
    }

    private function spotifyDalszoveg(string $felirat, string $cim): void
    {
        if (!$this->b['szuro_dalszoveg'] || $this->dalszovegFut) {
            return;
        }
        $itel = function (array $e) use ($cim): void {
            if (Dalszoveg::tragar($e, $this->b['szuro_erzekenyseg'])) {
                $this->zene->spotifyTragar($cim);
            }
        };
        $ismert = Dalszoveg::tarKeres($felirat);
        $ismert !== null ? $itel($ismert) : $this->dalszovegLekerdez($felirat, '', $itel);
    }

    private function parancsok(): void
    {
        foreach (Adatbazis::uj() as $p) {
            if (microtime(true) - $p['ido'] > 30) {
                Adatbazis::valasz($p['id'], false, ['uzenet' => 'A parancs elavult.', 'kod' => 'timeout', 'statusz' => 504]);
                continue;
            }
            try {
                $eredmeny = $this->vegrehajt($p['muvelet'], $p['adat']);
                Adatbazis::valasz($p['id'], true, $eredmeny);
            } catch (Hiba $e) {
                Adatbazis::valasz($p['id'], false, ['uzenet' => $e->getMessage(), 'kod' => $e->kod, 'statusz' => $e->statusz]);
            } catch (\Throwable $e) {
                $this->log("HIBA: parancs ({$p['muvelet']}): " . $e->getMessage());
                Adatbazis::valasz($p['id'], false, ['uzenet' => 'Belső hiba: ' . $e->getMessage(), 'kod' => 'internal', 'statusz' => 500]);
            }
            $this->allapotIr(true);
        }
    }

    private function riasztasKozben(): void
    {
        if ($this->riasztas) {
            throw new Hiba('Riasztás közben ez nem lehetséges.', 'alarm_active', 409);
        }
    }

    private function vegrehajt(string $muvelet, array $a): mixed
    {
        $ki = (string)($a['ki'] ?? '');
        switch ($muvelet) {
            case 'csengetes':
                $this->riasztasKozben();
                $this->csengetes((string)$a['hang'], (string)($a['leiras'] ?? 'Kézi csengetés'));
                return true;
            case 'hang_proba':
                return $this->hangProba((string)$a['ertek']);
            case 'zona_proba':
                return $this->zonaProba((int)$a['index']);
            case 'zene_inditas':
                $this->riasztasKozben();
                if ($this->aktivForras() === null) {
                    throw new Hiba('Nincs kiválasztott zeneforrás.', 'no_source', 409);
                }
                $this->zeneIndit();
                return true;
            case 'zene_leallitas':
                $this->zeneLeallit();
                return true;
            case 'zene_valt':
                $this->zene->szol() ? $this->zeneLeallit() : $this->zeneIndit();
                return true;
            case 'zene_kovetkezo':
                $this->riasztasKozben();
                $this->zene->kovetkezo();
                return true;
            case 'zene_elozo':
                $this->riasztasKozben();
                $this->zene->elozo();
                return true;
            case 'zene_ugras':
                $this->riasztasKozben();
                $index = (int)$a['index'];
                if (isset($a['cim']) && ($this->zene->szamok[$index]->cim ?? null) !== $a['cim']) {
                    throw new Hiba('Közben változott a lejátszási sor, frissíts.', 'conflict', 409);
                }
                $this->zene->ugras($index);
                return true;
            case 'zene_keveres':
                if (!$this->zene->ujrakever()) {
                    throw new Hiba('Most nincs mit összekeverni (Spotify vagy túl rövid a sor).', 'cannot_shuffle', 409);
                }
                $this->log('Lejátszási sor újrakeverve');
                return true;
            case 'keveres_allitas':
                $this->b['keveres'] = (bool)$a['keveres'];
                Beallitasok::ment($this->b);
                $this->bIdo = (int)filemtime(Utvonalak::beallitasFajl());
                $this->zene->keveres = $this->b['keveres'];
                return true;
            case 'zene_hangero':
                $this->b['zene_hangero'] = max(0, min(100, (int)$a['hangero']));
                Beallitasok::ment($this->b);
                $this->bIdo = (int)filemtime(Utvonalak::beallitasFajl());
                $this->zene->hangero($this->b['zene_hangero']);
                return true;
            case 'forras_valtas':
                if (!isset($this->b['forrasok'][(int)$a['index']]) || !$this->b['forrasok'][(int)$a['index']]['aktiv']) {
                    throw new Hiba('Nincs ilyen zeneforrás.', 'validation_error', 422);
                }
                $this->forrasValtas((int)$a['index']);
                return true;
            case 'bemondas':
                $this->riasztasKozben();
                $this->gyorsBemondas((string)$a['szoveg'], (bool)($a['gong'] ?? true));
                return true;
            case 'bemondas_inditas':
                $this->riasztasKozben();
                $this->bemondas((array)$a['bemondas']);
                return true;
            case 'bemondas_leallitas':
                $this->bemondasLeallit();
                return true;
            case 'riasztas_inditas':
                $this->log('Riasztás indítása' . ($ki ? " ({$ki})" : ''));
                $this->riasztasIndit();
                return true;
            case 'riasztas_leallitas':
                $this->log('Riasztás leállítása' . ($ki ? " ({$ki})" : ''));
                $this->riasztasLeallit();
                return true;
            case 'csend_inditas':
                $this->riasztasKozben();
                return $this->csendMost((int)$a['perc'], (int)($a['hangero'] ?? 0), (string)($a['nev'] ?? 'Csendes időszak'));
            case 'csend_leallitas':
                if (!$this->csendVege()) {
                    throw new Hiba('Most nincs csendes időszak.', 'conflict', 409);
                }
                return true;
            case 'ma_kapcsolo':
                $mezo = (string)$a['mezo'];
                if (!in_array($mezo, ['ma_nincs_csengetes', 'ma_nincs_zene'], true)) {
                    throw new Hiba('Ismeretlen kapcsoló.', 'validation_error', 422);
                }
                $this->maKapcsolo($mezo, (bool)$a['be']);
                return true;
            case 'ma_rend':
                $nev = (string)$a['nev'];
                if ($nev !== '' && Beallitasok::rend($this->b, $nev) === null) {
                    throw new Hiba('Nincs ilyen csengetési rend.', 'validation_error', 422);
                }
                $this->maRend($nev);
                return true;
            case 'beallitas':
                $this->b = Beallitasok::normalizal(array_merge($this->b, (array)$a['valtozasok']));
                if (!empty($a['naplo'])) {
                    $this->log((string)$a['naplo']);
                }
                $this->mentes();
                if (!empty($a['szerver_ujra'])) {
                    $this->keresSzerver->ujraindit();
                }
                return true;
            case 'beallitas_csere':
                $this->b = Beallitasok::normalizal((array)$a['beallitasok']);
                $this->log((string)($a['naplo'] ?? 'Beállítások cseréje'));
                $this->mentes();
                return true;
            case 'zenekeres_uj':
                return $this->zenekeresUj((string)$a['szoveg'], (string)($a['nev'] ?? ''), (string)$a['eszkoz'], (string)$a['ip']);
            case 'zenekeres_dontes':
                return Zenekeres::admin($this->zenekeresDontes((string)$a['azon'], (bool)$a['elfogad'], $ki));
            case 'zenekeres_levetel':
                $this->zenekeresLevesz((string)$a['azon'], $ki);
                return true;
            case 'zenekeres_szam_tiltas':
                $this->zenekeresSzamTiltas((string)$a['azon'], $ki);
                return true;
            case 'zenekeres_telefon_tiltas':
                $this->zenekeresTelefonTiltas((string)$a['azon'], $ki);
                return true;
            case 'telefon_feloldas':
                $this->telefonFeloldas((string)$a['kulcs'], $ki);
                return true;
            case 'zene_tiltas':
                $this->mostSzoloTiltasa($ki);
                return true;
            case 'zene_tiltas_feloldas':
                $this->szamFeloldas((string)$a['azon'], $ki);
                return true;
            case 'hangok_valtoztak':
                foreach ((array)($a['csere'] ?? []) as $regi => $uj) {
                    foreach (array_keys(Beallitasok::HANG_MEZOK) as $mezo) {
                        if ($this->b[$mezo] === $regi) {
                            $this->b[$mezo] = $uj !== '' ? $uj : Beallitasok::HANG_MEZOK[$mezo];
                        }
                    }
                }
                $this->mentes();
                return true;
            case 'hang_elenged':
                $ut = SajatHangok::ut((string)$a['ertek']);
                $this->proba->megallit();
                if ($ut !== null && in_array($ut, $this->csengo->forrasok(), true) && $this->csengo->szol()) {
                    throw new Hiba('Ez a hang most szól. Várd meg, amíg elhallgat, és próbáld újra.', 'conflict', 409);
                }
                return true;
            case 'gyorsitotar_urites':
                YouTube::urites($this->zene->ytMappa());
                return true;
            case 'zene_szinkron_most':
                if (!$this->zeneSzinkron->beallitva()) {
                    throw new Hiba('Előbb kapcsold be, és add meg a zenekérő szerver címét és kulcsát.', 'validation_error', 422);
                }
                $this->zeneSzinkron->indit();
                return true;
            case 'zene_szinkron_leallit':
                $this->zeneSzinkron->leallit();
                return true;
            case 'forras_ujratoltes':
                $this->zene->forras = null;
                $this->zene->forrasBeallitas($this->jelenlegiForras());
                return true;
            case 'ertesites_proba':
                if (!Ertesito::csatornak($this->b)) {
                    throw new Hiba('Nincs beállítva sem ntfy-cím, sem e-mail.', 'validation_error', 422);
                }
                $this->hatter->futtat('ertesites', ['cim' => 'Próbaértesítés', 'uzenet' => 'Ha ezt látod, a Közgáz FM értesítései működnek.', 'szint' => 'info'],
                    function (?array $hibak): void {
                        $hibak ? $this->jelez('Próbaértesítés: ' . implode('; ', $hibak), 'hiba', false) : $this->uzenet('A próbaértesítés elment.', 'info');
                    });
                return true;
            case 'naplo':
                $this->log((string)$a['szoveg']);
                return true;
            case 'allapot':
                return true;
        }
        throw new Hiba("Ismeretlen művelet: {$muvelet}", 'not_found', 404);
    }

    public function szerverZenekFrissultek(string $mappa, bool $valtozott): void
    {
        foreach ($this->b['forrasok'] as $f) {
            if ($f['tipus'] === 'mappa' && rtrim($f['cim'], '/') === $mappa) {
                $megvan = true;
                break;
            }
        }
        if (empty($megvan)) {
            $this->b['forrasok'][] = ['tipus' => 'mappa', 'nev' => ZeneSzinkron::FORRAS_NEV, 'cim' => $mappa, 'aktiv' => true];
            Beallitasok::ment($this->b);
            $this->bIdo = (int)filemtime(Utvonalak::beallitasFajl());
            $this->log('Új zeneforrás: „' . ZeneSzinkron::FORRAS_NEV . "” ({$mappa})");
        }
        $f = $this->zene->forras;
        if ($valtozott && $f !== null && $f['tipus'] === 'mappa' && rtrim($f['cim'], '/') === $mappa && !$this->zene->szol()) {
            $this->zene->forras = null;
            $this->zene->forrasBeallitas($this->jelenlegiForras());
        }
    }

    private function alapHely(): ?array
    {
        $alap = $this->zene->alapLista();
        if (!$alap) {
            return null;
        }
        $poz = $this->zene->alapPozicio();
        $hely = null;
        foreach ($alap as $n => [$i]) {
            if ($i === $poz) {
                $hely = $n + 1;
                break;
            }
        }
        return ['hely' => $hely, 'osszes' => count($alap),
            'lista' => array_map(static fn($p) => ['index' => $p[0], 'cim' => $p[1]->cim], $alap)];
    }

    public function allapotIr(bool $kenyszer = false): void
    {
        $this->allapotIdo = microtime(true);
        $z = $this->zene;
        $aktiv = $this->szoloForras();
        [$tartalekSzoveg, $tartalekSzint] = $this->tartalek->leiras();
        $allapot = [
            'ido' => time(),
            'pid' => getmypid(),
            'verzio' => KFM_VERZIO,
            'riasztas' => $this->riasztas,
            'csengo_szol' => $this->csengo->szol(),
            'bemondas_szol' => $this->bemondo->beszel(),
            'proba_szol' => $this->proba->szol(),
            'zene' => [
                'szol' => $z->szol(),
                'cim' => $z->szol() ? $z->mostCim : '',
                'forras' => $aktiv !== null ? array_search($aktiv, $this->b['forrasok'], false) : null,
                'blokk' => $this->musorBlokk['nev'] ?? '',
                'sor' => $z->szol() ? array_map(fn($p) => ['index' => $p[0], 'cim' => $p[1], 'kert' => $z->szamok[$p[0]]->kert],
                    $z->kovetkezok(max(8, count($z->kertSor()) + 2))) : [],
                'most_kert' => $z->mostKert(),
                'kertek' => array_map(static fn($p) => ['index' => $p[0], 'cim' => $p[1]->cim, 'szavazat' => $p[1]->szavazat], $z->kertSor()),
                'alap' => $this->alapHely(),
                'szamok' => count($z->szamok),
                'spotify' => $z->spotifyMod(),
            ],
            'tartalek' => ['szerep' => $this->tartalek->szerep(), 'passziv' => $this->tartalek->passziv(), 'atvett' => $this->tartalek->atvett,
                'szoveg' => $tartalekSzoveg, 'szint' => $tartalekSzint, 'partner' => $this->tartalek->partner],
            'keres_szerver' => ['beallitva' => $this->keresSzerver->beallitva(), 'hiba' => $this->keresSzerver->hiba,
                'utolso' => $this->keresSzerver->utolso, 'oldal' => $this->keresSzerver->oldal()],
            'zene_szinkron' => $this->zeneSzinkron->allapotAdat(),
            'kimenetek' => $this->kimenetek,
            'kimenet_nev' => Kimenetek::nev($this->b, $this->kimenetek),
            'hianyzo_zonak' => Kimenetek::hianyzoZonak($this->b, $this->kimenetek),
            'kiegyenlito' => ['ismert' => Hangossag::darab(), 'varakozik' => $this->kiegyenlito->varakozik()],
            'letoltes' => $this->hatter->varakozik('letoltes'),
            'uzenetek' => $this->uzenetek,
            'tts' => Bemondo::elerheto(),
        ];
        $json = json_encode($allapot, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PARTIAL_OUTPUT_ON_ERROR);
        $fajl = Utvonalak::allapotFajl();
        @file_put_contents($fajl . '.tmp', $json);
        @rename($fajl . '.tmp', $fajl);
    }
}
