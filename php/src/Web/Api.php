<?php

declare(strict_types=1);

namespace KozgazFM\Web;

use DateInterval;
use DateTimeImmutable;
use KozgazFM\Adatbazis;
use KozgazFM\Beallitasok;
use KozgazFM\Bemondo;
use KozgazFM\Hiba;
use KozgazFM\Kghsz;
use KozgazFM\NaptarImport;
use KozgazFM\Naplo;
use KozgazFM\Orarend;
use KozgazFM\Qr;
use KozgazFM\SajatHangok;
use KozgazFM\Spotify;
use KozgazFM\Statisztika;
use KozgazFM\Tartalek;
use KozgazFM\Unnepek;
use KozgazFM\Utvonalak;
use KozgazFM\YouTube;
use KozgazFM\Zar;
use KozgazFM\Zenekeres;
use KozgazFM\ZenekeresSzerver;

final class Api
{
    public const MAX_BEMONDAS = 500;
    public const MAX_SABLON = 30;
    public const CSEND_PERC = [5, 240];

    private const PUBLIKUS = [
        'GET /api/v1/zenekeres' => 'zenekeresAllapot',
        'POST /api/v1/zenekeres' => 'zenekeresKuldes',
        'GET /api/v1/kijelzo' => 'kijelzo',
        'GET /api/v1/qr' => 'qr',
        'POST /api/v1/belepes' => 'belepes',
        'POST /api/v1/elso-jelszo' => 'elsoJelszo',
    ];

    private const KULCSOS = [
        'GET /api/v1/tartalek/eletjel' => 'tartalekEletjel',
        'GET /api/v1/tartalek/beallitasok' => 'tartalekBeallitasok',
    ];

    private const UTVONALAK = [
        'GET /api/v1/allapot' => ['allapot', false],
        'GET /api/v1/statisztika' => ['statisztika', false],
        'POST /api/v1/csengetes' => ['csengetes', false],
        'POST /api/v1/zene/inditas' => ['parancs:zene_inditas', false],
        'POST /api/v1/zene/leallitas' => ['parancs:zene_leallitas', false],
        'POST /api/v1/zene/kovetkezo' => ['parancs:zene_kovetkezo', false],
        'POST /api/v1/zene/elozo' => ['parancs:zene_elozo', false],
        'PATCH /api/v1/zene' => ['zeneAllitas', false],
        'POST /api/v1/zene/ugras' => ['zeneUgras', false],
        'POST /api/v1/zene/keveres' => ['zeneKeveres', false],
        'POST /api/v1/bemondas' => ['bemondas', false],
        'DELETE /api/v1/bemondas' => ['parancs:bemondas_leallitas', false],
        'PUT /api/v1/bemondas/sablonok' => ['sablonokMentese', false],
        'POST /api/v1/csend' => ['csendInditas', false],
        'DELETE /api/v1/csend' => ['parancs:csend_leallitas', false],
        'POST /api/v1/riasztas' => ['parancs:riasztas_inditas', true],
        'DELETE /api/v1/riasztas' => ['parancs:riasztas_leallitas', true],
        'PATCH /api/v1/ma' => ['maAllitas', false],
        'POST /api/v1/zenekeres/dontes' => ['zenekeresDontes', false],
        'POST /api/v1/zenekeres/levetel' => ['azonParancs:zenekeres_levetel', false],
        'POST /api/v1/zenekeres/szam-tiltas' => ['azonParancs:zenekeres_szam_tiltas', false],
        'POST /api/v1/zenekeres/telefon-tiltas' => ['azonParancs:zenekeres_telefon_tiltas', false],
        'DELETE /api/v1/zenekeres/telefon-tiltas' => ['telefonFeloldas', false],
        'POST /api/v1/zene/tiltas' => ['parancs:zene_tiltas', false],
        'DELETE /api/v1/zene/tiltas' => ['azonParancs:zene_tiltas_feloldas', false],
        'POST /api/v1/kilepes' => ['kilepes', false],
        'POST /api/v1/feloldas' => ['feloldas', false],
        'POST /api/v1/zarolas' => ['zarolas', false],
        'GET /api/v1/naplo' => ['naplo', true],
        'GET /api/v1/beallitasok' => ['beallitasok', true],
        'PATCH /api/v1/beallitasok' => ['beallitasMentes', true],
        'POST /api/v1/jelszo' => ['jelszoCsere', true],
        'POST /api/v1/pin' => ['pinAllitas', true],
        'GET /api/v1/hangok' => ['hangLista', false],
        'POST /api/v1/hangok' => ['hangFeltoltes', true],
        'PATCH /api/v1/hangok' => ['hangAtnevezes', true],
        'DELETE /api/v1/hangok' => ['hangTorles', true],
        'POST /api/v1/hang-proba' => ['hangProba', false],
        'POST /api/v1/zona-proba' => ['zonaProba', true],
        'POST /api/v1/rend-generalas' => ['rendGeneralas', true],
        'POST /api/v1/unnepek' => ['unnepek', true],
        'POST /api/v1/import/ics' => ['icsImport', true],
        'POST /api/v1/import/kghsz' => ['kghszImport', true],
        'POST /api/v1/import/alkalmaz' => ['importAlkalmaz', true],
        'GET /api/v1/export' => ['export', true],
        'POST /api/v1/import/beallitasok' => ['beallitasImport', true],
        'GET /api/v1/spotify/eszkozok' => ['spotifyEszkozok', true],
        'POST /api/v1/spotify/kijelentkezes' => ['spotifyKijelentkezes', true],
        'POST /api/v1/gyorsitotar-urites' => ['parancs:gyorsitotar_urites', true],
        'POST /api/v1/forras-ujratoltes' => ['parancs:forras_ujratoltes', true],
        'POST /api/v1/zene-szinkron' => ['parancs:zene_szinkron_most', true],
        'DELETE /api/v1/zene-szinkron' => ['parancs:zene_szinkron_leallit', true],
        'POST /api/v1/ertesites-proba' => ['parancs:ertesites_proba', true],
        'POST /api/v1/tartalek-kulcs' => ['tartalekKulcs', true],
        'GET /api/v1/rendszer' => ['rendszer', false],
    ];

    public function __construct(private readonly Alkalmazas $app)
    {
    }

    public function kezel(): void
    {
        $kulcs = $this->app->metodus . ' ' . $this->app->ut;
        if (isset(self::KULCSOS[$kulcs])) {
            $this->kulcsEllenoriz();
            $this->ok($this->{self::KULCSOS[$kulcs]}());
            return;
        }
        if (isset(self::PUBLIKUS[$kulcs])) {
            if ($this->app->metodus !== 'GET') {
                $this->app->csrfEllenoriz();
            }
            $this->ok($this->{self::PUBLIKUS[$kulcs]}($this->app->metodus === 'GET' ? $_GET : $this->app->torzs()));
            return;
        }
        if (!isset(self::UTVONALAK[$kulcs])) {
            $letezik = false;
            foreach (array_merge(array_keys(self::UTVONALAK), array_keys(self::PUBLIKUS), array_keys(self::KULCSOS)) as $u) {
                if (explode(' ', $u)[1] === $this->app->ut) {
                    $letezik = true;
                }
            }
            throw $letezik ? new Hiba('Ez a művelet itt nem engedélyezett.', 'method_not_allowed', 405) : new Hiba('Nincs ilyen végpont.', 'not_found', 404);
        }
        if (!$this->app->bejelentkezve()) {
            throw new Hiba('Jelentkezz be.', 'unauthorized', 401);
        }
        $this->app->csrfEllenoriz();
        [$kezelo, $vedett] = self::UTVONALAK[$kulcs];
        if ($vedett && !$this->app->feloldva()) {
            throw new Hiba('Ehhez a művelethez add meg a PIN-kódot.', 'pin_required', 423);
        }
        $adat = $this->app->metodus === 'GET' ? $_GET : $this->app->torzs();
        if (str_starts_with($kezelo, 'parancs:')) {
            $this->ok($this->parancs(substr($kezelo, 8), $adat));
            return;
        }
        if (str_starts_with($kezelo, 'azonParancs:')) {
            $this->ok($this->parancs(substr($kezelo, 12), ['azon' => $this->szoveg($adat, 'azon')]));
            return;
        }
        $this->ok($this->{$kezelo}($adat));
    }

    private function ok(mixed $adat): void
    {
        $this->app->json(['data' => $adat]);
    }

    private function parancs(string $muvelet, array $adat = []): mixed
    {
        $eredmeny = Adatbazis::parancs($muvelet, $adat + ['ki' => $this->app->ki()]);
        $this->app->b = Beallitasok::betolt();
        return in_array($muvelet, ['zenekeres_uj', 'csend_inditas', 'zenekeres_dontes'], true) ? $eredmeny : Allapot::teljes($this->app->b);
    }

    private function szoveg(array $adat, string $mezo, int $max = 200): string
    {
        $ertek = $adat[$mezo] ?? null;
        if (!is_string($ertek) || trim($ertek) === '' || mb_strlen($ertek) > $max) {
            throw new Hiba("Hiányzó vagy hibás mező: {$mezo}", 'validation_error', 422);
        }
        return trim($ertek);
    }

    private function egesz(array $adat, string $mezo, int $min, int $max, ?int $alap = null): int
    {
        $ertek = $adat[$mezo] ?? $alap;
        if (!is_int($ertek) && !(is_string($ertek) && ctype_digit($ertek))) {
            throw new Hiba("Hiányzó vagy hibás szám: {$mezo}", 'validation_error', 422);
        }
        $ertek = (int)$ertek;
        if ($ertek < $min || $ertek > $max) {
            throw new Hiba("A(z) {$mezo} {$min} és {$max} között legyen.", 'validation_error', 422);
        }
        return $ertek;
    }

    private function kulcsEllenoriz(): void
    {
        $kulcs = (string)($_SERVER['HTTP_X_KOZGAZ_FM_KULCS'] ?? '');
        $b = $this->app->b;
        if ($b['tartalek_mod'] === '' || $b['tartalek_kulcs'] === '' || !hash_equals($b['tartalek_kulcs'], $kulcs)) {
            throw new Hiba('Hibás kulcs.', 'unauthorized', 401);
        }
    }

    private function allapot(): array
    {
        return Allapot::teljes($this->app->b);
    }

    private function rendszer(): array
    {
        $d = Allapot::demon();
        $spotify = trim($this->app->b['spotify_client_id']) !== '' && (new Spotify(trim($this->app->b['spotify_client_id'])))->bejelentkezve();
        return ['demon' => $d['el'], 'tartalek' => $d['tartalek'] ?? null, 'keres_szerver' => $d['keres_szerver'] ?? null,
            'kimenetek' => $d['kimenetek'] ?? [], 'kimenet_nev' => $d['kimenet_nev'] ?? null, 'hianyzo_zonak' => $d['hianyzo_zonak'] ?? [],
            'kiegyenlito' => $d['kiegyenlito'] ?? null, 'letoltes' => $d['letoltes'] ?? 0, 'tts' => $d['tts'] ?? false,
            'tts_hangok' => Bemondo::hangok(), 'spotify' => $spotify, 'pin' => $this->app->pinKell(), 'feloldva' => $this->app->feloldva(),
            'gyorsitotar_mb' => round(YouTube::meret(Utvonalak::mappa('gyorsitotar/youtube')) / 1048576, 1),
            'szabad_gb' => round(((float)@disk_free_space(Utvonalak::adat())) / 1e9, 1), 'zene_gyoker' => Utvonalak::zeneGyoker(),
            'zene_mappak' => array_values(array_filter(glob(Utvonalak::zeneGyoker() . '/*', GLOB_ONLYDIR) ?: [])),
            'verzio' => KFM_VERZIO, 'gep' => gethostname()];
    }

    private function statisztika(array $adat): array
    {
        $ma = new DateTimeImmutable('today');
        $nap = max(1, min(400, (int)($adat['nap'] ?? 7)));
        $tol = isset($adat['tol']) && preg_match('/^\d{4}-\d{2}-\d{2}$/', (string)$adat['tol']) ? new DateTimeImmutable($adat['tol']) : $ma->sub(new DateInterval('P' . ($nap - 1) . 'D'));
        $ig = isset($adat['ig']) && preg_match('/^\d{4}-\d{2}-\d{2}$/', (string)$adat['ig']) ? new DateTimeImmutable($adat['ig']) : $ma;
        if ($ig < $tol || $tol->diff($ig)->days > 400) {
            throw new Hiba('Hibás időszak.', 'validation_error', 422);
        }
        if (($adat['csv'] ?? '') === '1') {
            header('Content-Type: text/csv; charset=utf-8');
            header('Content-Disposition: attachment; filename="kozgaz-fm-lejatszasok-' . $tol->format('Y-m-d') . '.csv"');
            echo (new Statisztika())->csv($tol, $ig);
            exit;
        }
        return (new Statisztika())->osszegzes($tol, $ig, (int)($adat['top'] ?? 10));
    }

    private function csengetes(array $adat): array
    {
        $azon = (string)($adat['hang'] ?? 'becsengo');
        foreach (Allapot::hangok($this->app->b) as [$a, $nev, $ertek]) {
            if ($a === $azon) {
                Naplo::ir("Webpanel ({$this->app->ip}): csengetés – {$nev}");
                return $this->parancs('csengetes', ['hang' => $ertek, 'leiras' => "Webes csengetés ({$nev})"]);
            }
        }
        throw new Hiba('Ismeretlen csengőhang.', 'validation_error', 422);
    }

    private function zeneAllitas(array $adat): array
    {
        if (array_key_exists('hangero', $adat)) {
            $this->parancs('zene_hangero', ['hangero' => $this->egesz($adat, 'hangero', 0, 100)]);
        }
        if (array_key_exists('keveres', $adat)) {
            if (!is_bool($adat['keveres'])) {
                throw new Hiba('Hibás mező: keveres', 'validation_error', 422);
            }
            Naplo::ir("Webpanel ({$this->app->ip}): keverés " . ($adat['keveres'] ? 'be' : 'ki'));
            $this->parancs('keveres_allitas', ['keveres' => $adat['keveres']]);
        }
        if (array_key_exists('forras', $adat)) {
            $this->parancs('forras_valtas', ['index' => $this->egesz($adat, 'forras', 0, 1000)]);
        }
        return Allapot::teljes($this->app->b);
    }

    private function zeneKeveres(array $adat): array
    {
        Naplo::ir("Webpanel ({$this->app->ip}): keverés most");
        return $this->parancs('zene_keveres');
    }

    private function zeneUgras(array $adat): array
    {
        $p = ['index' => $this->egesz($adat, 'index', 0, 100000)];
        if (isset($adat['cim']) && is_string($adat['cim'])) {
            $p['cim'] = $adat['cim'];
        }
        return $this->parancs('zene_ugras', $p);
    }

    private function bemondas(array $adat): array
    {
        $szoveg = $this->szoveg($adat, 'szoveg', self::MAX_BEMONDAS);
        Naplo::ir("Webpanel ({$this->app->ip}): bemondás");
        return $this->parancs('bemondas', ['szoveg' => $szoveg, 'gong' => (bool)($adat['gong'] ?? true)]);
    }

    private function sablonokMentese(array $adat): array
    {
        $lista = $adat['sablonok'] ?? null;
        if (!is_array($lista) || count($lista) > self::MAX_SABLON) {
            throw new Hiba('Legfeljebb ' . self::MAX_SABLON . ' sablon lehet.', 'validation_error', 422);
        }
        $tiszta = [];
        foreach ($lista as $s) {
            if (!is_string($s) || mb_strlen($s) > self::MAX_BEMONDAS) {
                throw new Hiba('Hibás sablon.', 'validation_error', 422);
            }
            if (trim($s) !== '') {
                $tiszta[] = trim($s);
            }
        }
        Adatbazis::parancs('beallitas', ['valtozasok' => ['bemondas_sablonok' => $tiszta], 'naplo' => "Webpanel ({$this->app->ip}): bemondás-sablonok mentve"]);
        $this->app->b = Beallitasok::betolt();
        return Allapot::teljes($this->app->b);
    }

    private function csendInditas(array $adat): array
    {
        $this->parancs('csend_inditas', ['perc' => $this->egesz($adat, 'perc', ...self::CSEND_PERC),
            'hangero' => $this->egesz($adat, 'hangero', 0, 100, 0), 'nev' => mb_substr(trim((string)($adat['nev'] ?? '')) ?: 'Csendes időszak', 0, 60)]);
        $this->app->b = Beallitasok::betolt();
        return Allapot::teljes($this->app->b);
    }

    private function maAllitas(array $adat): array
    {
        if (array_key_exists('csengetes', $adat)) {
            $this->parancs('ma_kapcsolo', ['mezo' => 'ma_nincs_csengetes', 'be' => !$adat['csengetes']]);
        }
        if (array_key_exists('zene', $adat)) {
            $this->parancs('ma_kapcsolo', ['mezo' => 'ma_nincs_zene', 'be' => !$adat['zene']]);
        }
        if (array_key_exists('rend', $adat)) {
            $this->parancs('ma_rend', ['nev' => (string)$adat['rend']]);
        }
        return Allapot::teljes($this->app->b);
    }

    private function zenekeresDontes(array $adat): array
    {
        $this->parancs('zenekeres_dontes', ['azon' => $this->szoveg($adat, 'azon'), 'elfogad' => (bool)($adat['elfogad'] ?? false)]);
        return Allapot::teljes($this->app->b);
    }

    private function telefonFeloldas(array $adat): array
    {
        return $this->parancs('telefon_feloldas', ['kulcs' => $this->szoveg($adat, 'kulcs')]);
    }

    private function kijelzo(): array
    {
        $a = Allapot::teljes($this->app->b, false);
        $oldal = Allapot::demon()['keres_szerver']['oldal'] ?? '';
        $a['keres_cim'] = $this->app->b['zenekeres'] ? (trim($this->app->b['zenekeres_oldal']) ?: ($oldal ?: $this->keresCim())) : '';
        $a['riasztas'] = false;
        unset($a['hangok'], $a['sablonok'], $a['demon']);
        $a['menetrend'] = array_values(array_filter($a['menetrend'], static fn($e) => $e['tipus'] !== 'riado' && $e['tipus'] !== 'riado_vege'));
        return $a;
    }

    public function keresCim(): string
    {
        $sema = !empty($_SERVER['HTTPS']) ? 'https' : 'http';
        return "{$sema}://" . ($_SERVER['HTTP_HOST'] ?? 'localhost') . '/keres';
    }

    private function qr(array $adat): void
    {
        $szoveg = (string)($adat['szoveg'] ?? '');
        if ($szoveg === '' || strlen($szoveg) > 1000) {
            throw new Hiba('Hiányzó szöveg.', 'validation_error', 422);
        }
        if (($adat['stilus'] ?? '') === 'plakat') {
            $matrix = Qr::matrix($szoveg);
            $svg = $matrix ? Qr::plakatSvg($matrix) : '';
        } else {
            $f = proc_open(['qrencode', '-t', 'SVG', '-m', '2', '-l', 'M', '-o', '-', $szoveg], [1 => ['pipe', 'w'], 2 => ['file', '/dev/null', 'w']], $csovek);
            $svg = is_resource($f) ? (string)stream_get_contents($csovek[1]) : '';
            if (is_resource($f)) {
                fclose($csovek[1]);
                proc_close($f);
            }
        }
        if ($svg === '') {
            throw new Hiba('A QR-kód nem készült el (nincs qrencode).', 'unavailable', 503);
        }
        header('Content-Type: image/svg+xml');
        header('Cache-Control: max-age=3600');
        if (($adat['letoltes'] ?? '') === '1') {
            header('Content-Disposition: attachment; filename="kozgaz-fm-qr.svg"');
        }
        echo $svg;
        exit;
    }

    private function belepes(array $adat): array
    {
        try {
            $siker = $this->app->belep((string)($adat['jelszo'] ?? ''));
        } catch (Hiba $e) {
            throw new Hiba($e->getMessage(), 'rate_limited', 429);
        }
        if (!$siker) {
            Naplo::ir("Webpanel: sikertelen belépés ({$this->app->ip})");
            throw new Hiba('Hibás jelszó.', 'unauthorized', 401);
        }
        Naplo::ir("Webpanel: belépés ({$this->app->ip})");
        return ['belepve' => true];
    }

    private function elsoJelszo(array $adat): array
    {
        if ($this->app->b['web_jelszo'] !== '') {
            throw new Hiba('A jelszó már be van állítva.', 'conflict', 409);
        }
        $jelszo = (string)($adat['jelszo'] ?? '');
        $hash = Zar::jelszoHash($jelszo);
        $this->beallitasIras(['web_jelszo' => $hash], "Webpanel: első jelszó beállítva ({$this->app->ip})", true);
        $this->app->b = Beallitasok::betolt();
        $this->app->belep($jelszo);
        return ['belepve' => true];
    }

    private function kilepes(): array
    {
        $this->app->kilep();
        return ['belepve' => false];
    }

    private function feloldas(array $adat): array
    {
        try {
            $ok = $this->app->pinFelold((string)($adat['pin'] ?? ''));
        } catch (Hiba $e) {
            throw new Hiba($e->getMessage(), 'rate_limited', 429);
        }
        if (!$ok) {
            throw new Hiba('Hibás PIN.', 'unauthorized', 401);
        }
        return ['feloldva' => true, 'perc' => $this->app->b['admin_zar_perc']];
    }

    private function zarolas(): array
    {
        $this->app->zarol();
        return ['feloldva' => false];
    }

    private function naplo(array $adat): array
    {
        return Naplo::utolso(max(10, min(5000, (int)($adat['n'] ?? 500))));
    }

    private const TITKOK = ['web_jelszo', 'admin_pin'];
    private const NEM_IRHATO = ['web_jelszo', 'admin_pin', 'tiltott_szamok', 'tiltott_telefonok'];

    private function beallitasok(): array
    {
        $b = $this->app->b;
        foreach (self::TITKOK as $t) {
            $b[$t] = $b[$t] !== '';
        }
        return ['beallitasok' => $b, 'alapok' => Beallitasok::alapok(), 'hangok' => SajatHangok::osszes()];
    }

    private function beallitasIras(array $valtozasok, string $naplo, bool $titok = false): void
    {
        Adatbazis::parancs('beallitas', ['valtozasok' => $valtozasok, 'naplo' => $naplo,
            'szerver_ujra' => (bool)array_intersect_key($valtozasok, array_flip(['zenekeres_szerver', 'zenekeres_szerver_kulcs']))]);
    }

    private function beallitasMentes(array $adat): array
    {
        $valtozasok = $adat['valtozasok'] ?? $adat;
        if (!is_array($valtozasok) || !$valtozasok) {
            throw new Hiba('Nincs mit menteni.', 'validation_error', 422);
        }
        $alapok = Beallitasok::alapok();
        foreach (array_keys($valtozasok) as $k) {
            if (!array_key_exists($k, $alapok) || in_array($k, self::NEM_IRHATO, true)) {
                throw new Hiba("Ez a beállítás nem írható: {$k}", 'validation_error', 422);
            }
        }
        $uj = Beallitasok::normalizal(array_merge($this->app->b, $valtozasok));
        Ellenor::ellenoriz($uj, array_keys($valtozasok));
        if (isset($valtozasok['tartalek_cim'])) {
            $valtozasok['tartalek_cim'] = Tartalek::cimNormalizal((string)$valtozasok['tartalek_cim']);
        }
        if (isset($valtozasok['zenekeres_szerver'])) {
            $valtozasok['zenekeres_szerver'] = ZenekeresSzerver::szerverCim((string)$valtozasok['zenekeres_szerver']);
        }
        $this->beallitasIras($valtozasok, "Beállítások mentve ({$this->app->ip}): " . implode(', ', array_keys($valtozasok)));
        $this->app->b = Beallitasok::betolt();
        return $this->beallitasok();
    }

    private function jelszoCsere(array $adat): array
    {
        if (!Zar::ellenoriz((string)($adat['regi'] ?? ''), $this->app->b['web_jelszo'])) {
            throw new Hiba('A jelenlegi jelszó nem stimmel.', 'unauthorized', 401);
        }
        $hash = Zar::jelszoHash((string)($adat['uj'] ?? ''));
        $this->beallitasIras(['web_jelszo' => $hash], "Webes jelszó megváltoztatva ({$this->app->ip})", true);
        $this->app->b = Beallitasok::betolt();
        $this->app->belep((string)$adat['uj']);
        return ['ok' => true];
    }

    private function pinAllitas(array $adat): array
    {
        $pin = (string)($adat['pin'] ?? '');
        $hash = $pin === '' ? '' : Zar::pinHash($pin);
        $this->beallitasIras(['admin_pin' => $hash], $pin === '' ? 'PIN-kód törölve' : 'PIN-kód beállítva', true);
        $this->app->b = Beallitasok::betolt();
        if ($pin !== '') {
            $this->app->pinFelold($pin);
        }
        return ['pin' => $pin !== ''];
    }

    private function hangLista(): array
    {
        return SajatHangok::osszes();
    }

    private function hangFeltoltes(): array
    {
        $f = $_FILES['fajl'] ?? null;
        if (!is_array($f) || ($f['error'] ?? 1) !== UPLOAD_ERR_OK) {
            throw new Hiba('A feltöltés nem sikerült (legfeljebb 30 MB).', 'validation_error', 422);
        }
        $h = SajatHangok::hozzaad($f['tmp_name'], (string)$f['name'], trim((string)($_POST['nev'] ?? '')) ?: null);
        Naplo::ir("Saját hang hozzáadva: {$h['nev']}");
        return SajatHangok::osszes();
    }

    private function hangAtnevezes(array $adat): array
    {
        $ertek = $this->szoveg($adat, 'ertek');
        Adatbazis::parancs('hang_elenged', ['ertek' => $ertek]);
        $h = SajatHangok::atnevez($ertek, $this->szoveg($adat, 'nev', 80));
        Adatbazis::parancs('hangok_valtoztak', ['csere' => [$ertek => $h['ertek']]]);
        return SajatHangok::osszes();
    }

    private function hangTorles(array $adat): array
    {
        $ertek = $this->szoveg($adat, 'ertek');
        Adatbazis::parancs('hang_elenged', ['ertek' => $ertek]);
        SajatHangok::torol($ertek);
        Adatbazis::parancs('hangok_valtoztak', ['csere' => [$ertek => '']]);
        Naplo::ir('Saját hang törölve: ' . SajatHangok::nev($ertek));
        return SajatHangok::osszes();
    }

    private function hangProba(array $adat): array
    {
        $ertek = $this->szoveg($adat, 'ertek');
        if (SajatHangok::hangUt($ertek) === null) {
            throw new Hiba('A hangfájl nem található.', 'not_found', 404);
        }
        return ['szol' => Adatbazis::parancs('hang_proba', ['ertek' => $ertek])];
    }

    private function zonaProba(array $adat): array
    {
        return ['szol' => Adatbazis::parancs('zona_proba', ['index' => $this->egesz($adat, 'index', 0, 50)])];
    }

    private function rendGeneralas(array $adat): array
    {
        $elso = (string)($adat['elso'] ?? '08:00');
        if (!preg_match('/^([01]\d|2[0-3]):[0-5]\d$/', $elso)) {
            throw new Hiba('Az első óra kezdete ÓÓ:PP legyen.', 'validation_error', 422);
        }
        return Beallitasok::orak(Orarend::rendGeneralas($elso, $this->egesz($adat, 'darab', 1, 15), $this->egesz($adat, 'ora_hossz', 10, 120),
            $this->egesz($adat, 'szunet', 0, 60), $this->egesz($adat, 'nagyszunet_utan', 0, 15), $this->egesz($adat, 'nagyszunet', 0, 90)));
    }

    private function unnepek(array $adat): array
    {
        $ev = $this->egesz($adat, 'ev', 2000, 2100);
        $b = $this->app->b;
        $meglevo = array_column($b['szunnapok'], 'tol');
        $uj = 0;
        foreach (Unnepek::unnepnapok($ev) as [$nap, $nev]) {
            $iso = $nap->format('Y-m-d');
            if (!in_array($iso, $meglevo, true)) {
                $b['szunnapok'][] = ['tol' => $iso, 'ig' => $iso, 'nev' => $nev];
                $uj++;
            }
        }
        usort($b['szunnapok'], static fn($x, $y) => strcmp($x['tol'], $y['tol']));
        $this->beallitasIras(['szunnapok' => $b['szunnapok']], "Ünnepnapok betöltve ({$ev}): {$uj} új");
        $this->app->b = Beallitasok::betolt();
        return ['uj' => $uj];
    }

    private function icsImport(array $adat): array
    {
        if (isset($_FILES['fajl']) && ($_FILES['fajl']['error'] ?? 1) === UPLOAD_ERR_OK) {
            if ($_FILES['fajl']['size'] > NaptarImport::MAX_MERET) {
                throw new Hiba('A naptár túl nagy (2 MB fölött).', 'validation_error', 422);
            }
            $szoveg = (string)file_get_contents($_FILES['fajl']['tmp_name']);
        } else {
            $szoveg = NaptarImport::letoltes($this->szoveg($adat, 'url', 2000));
        }
        return ['javaslatok' => NaptarImport::javaslatok(NaptarImport::icsBeolvas($szoveg), $this->app->b), 'muveletek' => NaptarImport::MUVELET_NEV];
    }

    private function kghszImport(): array
    {
        $adatok = Kghsz::letoltes($this->app->b);
        return ['normal' => $adatok['normal'], 'rovid' => $adatok['rovid'], 'normal_szoveg' => Kghsz::orakSzoveg($adatok['normal']),
            'rovid_szoveg' => $adatok['rovid'] ? Kghsz::orakSzoveg($adatok['rovid']) : null,
            'valtozott' => Kghsz::rendAtvetel($this->app->b, $adatok),
            'javaslatok' => NaptarImport::javaslatok($adatok['esemenyek'], $this->app->b), 'muveletek' => NaptarImport::MUVELET_NEV];
    }

    private function importAlkalmaz(array $adat): array
    {
        $b = $this->app->b;
        $valtozott = [];
        if (!empty($adat['rend']) && is_array($adat['rend'])) {
            [$b, $valtozott] = Kghsz::rendAlkalmaz($b, ['normal' => $adat['rend']['normal'] ?? null, 'rovid' => $adat['rend']['rovid'] ?? null]);
        }
        $javaslatok = array_values(array_filter((array)($adat['javaslatok'] ?? []), static fn($j) => is_array($j) && isset($j['esemeny']['tol'], $j['esemeny']['ig'], $j['muvelet'])));
        [$b, $sz, $k, $m] = NaptarImport::alkalmaz($b, $javaslatok);
        $this->beallitasIras(['szunnapok' => $b['szunnapok'], 'kivetelek' => $b['kivetelek'], 'rendek' => $b['rendek']],
            "Tanév rendje importálva: {$sz} szünnap, {$k} kivételnap" . ($valtozott ? ', rend: ' . implode(', ', $valtozott) : ''));
        $this->app->b = Beallitasok::betolt();
        return ['szunnapok' => $sz, 'kivetelek' => $k, 'megtartott' => $m, 'rendek' => $valtozott];
    }

    private function export(): void
    {
        header('Content-Type: application/json; charset=utf-8');
        header('Content-Disposition: attachment; filename="kozgaz-fm-beallitasok-' . date('Y-m-d') . '.json"');
        echo json_encode(Beallitasok::export($this->app->b), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        exit;
    }

    private function beallitasImport(): array
    {
        $f = $_FILES['fajl'] ?? null;
        if (!is_array($f) || ($f['error'] ?? 1) !== UPLOAD_ERR_OK) {
            throw new Hiba('Válassz egy beállításfájlt (.json).', 'validation_error', 422);
        }
        $adat = json_decode((string)file_get_contents($f['tmp_name']), true);
        if (!is_array($adat)) {
            throw new Hiba('Ez nem Közgáz FM beállításfájl.', 'validation_error', 422);
        }
        $uj = Beallitasok::import($this->app->b, $adat);
        Ellenor::ellenoriz($uj, array_keys($adat));
        Adatbazis::parancs('beallitas_csere', ['beallitasok' => $uj, 'naplo' => "Beállítások importálva ({$this->app->ip})"]);
        $this->app->b = Beallitasok::betolt();
        return $this->beallitasok();
    }

    private function spotifyEszkozok(): array
    {
        $id = trim($this->app->b['spotify_client_id']);
        if ($id === '') {
            throw new Hiba('Előbb add meg a Spotify Client ID-t.', 'validation_error', 422);
        }
        return (new Spotify($id))->eszkozok();
    }

    private function spotifyKijelentkezes(): array
    {
        Spotify::kijelentkezes();
        Naplo::ir('Spotify: kijelentkezve');
        return ['ok' => true];
    }

    private function tartalekKulcs(): array
    {
        return ['kulcs' => Tartalek::ujKulcs()];
    }

    private function tartalekEletjel(): array
    {
        $d = Allapot::demon();
        return Tartalek::eletjel($this->app->b, (bool)($d['tartalek']['atvett'] ?? false), (bool)($d['riasztas'] ?? false));
    }

    private function tartalekBeallitasok(): array
    {
        if ($this->app->b['tartalek_mod'] !== 'fo') {
            throw new Hiba('Ez nem a fő gép.', 'conflict', 409);
        }
        return Tartalek::szinkronAdat($this->app->b);
    }

    private function zenekeresAllapot(): array
    {
        $b = $this->app->b;
        $eszkoz = $this->app->eszkoz();
        $k = Allapot::keresek();
        $d = Allapot::demon();
        $szol = $d['zene']['szol'] ?? false;
        return ['aktiv' => $b['zenekeres'] && ($d['el'] ?? false), 'cim' => $b['kijelzo_cim'],
            'maradek' => $k->maradek($eszkoz, $b['zenekeres_napi']), 'napi' => $b['zenekeres_napi'], 'max_perc' => $b['zenekeres_max_perc'],
            'auto' => $b['zenekeres_auto'], 'tiltva' => Allapot::telefonTiltott($b, $eszkoz),
            'most' => $szol ? (string)($d['zene']['cim'] ?? '') : '',
            'keresek' => array_map([Zenekeres::class, 'nyilvanos'], $k->sajat($eszkoz))];
    }

    private function zenekeresKuldes(array $adat): array
    {
        $eszkoz = $this->app->eszkoz();
        $szoveg = (string)($adat['szoveg'] ?? '');
        $nev = (string)($adat['nev'] ?? '');
        $this->parancs('zenekeres_uj', ['szoveg' => $szoveg, 'nev' => $nev, 'eszkoz' => $eszkoz, 'ip' => $this->app->ip]);
        return $this->zenekeresAllapot();
    }
}
