<?php

declare(strict_types=1);

namespace KozgazFM;

final class Mpv
{
    private $folyamat = null;
    private $csatlakozas = null;
    private string $puffer = '';
    private int $keresSzam = 0;
    private array $esemenyek = [];
    private float $hangeroErtek = -1;
    public float $pozicio = 0.0;
    public float $hossz = 0.0;
    public bool $szol = false;
    public bool $szunetel = false;
    public ?string $fajl = null;
    private string $socket;
    private bool $inditasraVar = false;

    public function __construct(public readonly string $nev, public readonly string $eszkoz = '')
    {
        $this->socket = Utvonalak::futas() . '/mpv-' . preg_replace('/[^a-z0-9_-]/i', '_', $nev) . '.sock';
    }

    public function indit(): bool
    {
        if ($this->el()) {
            return true;
        }
        $this->leall();
        @unlink($this->socket);
        $parancs = ['mpv', '--idle=yes', '--no-video', '--no-terminal', '--really-quiet', '--no-config',
            '--input-ipc-server=' . $this->socket, '--volume=0', '--volume-max=100', '--keep-open=no',
            '--audio-client-name=KozgazFM-' . $this->nev, '--audio-buffer=0.3', '--cache=no'];
        if ($this->eszkoz !== '') {
            $parancs[] = '--audio-device=pulse/' . $this->eszkoz;
        }
        $this->folyamat = proc_open($parancs, [0 => ['file', '/dev/null', 'r'], 1 => ['file', '/dev/null', 'w'],
            2 => ['file', '/dev/null', 'w']], $csovek);
        if (!is_resource($this->folyamat)) {
            $this->folyamat = null;
            return false;
        }
        for ($i = 0; $i < 60 && !file_exists($this->socket); $i++) {
            usleep(50000);
        }
        $this->csatlakozas = @stream_socket_client('unix://' . $this->socket, $hibakod, $hiba, 2);
        if (!$this->csatlakozas) {
            $this->leall();
            return false;
        }
        stream_set_blocking($this->csatlakozas, false);
        $this->hangeroErtek = -1;
        $this->kuld(['observe_property', 1, 'time-pos']);
        $this->kuld(['observe_property', 2, 'duration']);
        $this->kuld(['observe_property', 3, 'pause']);
        $this->kuld(['observe_property', 4, 'idle-active']);
        return true;
    }

    public function el(): bool
    {
        if (!is_resource($this->folyamat) || !$this->csatlakozas) {
            return false;
        }
        return proc_get_status($this->folyamat)['running'];
    }

    public function leall(): void
    {
        if ($this->csatlakozas) {
            @fwrite($this->csatlakozas, json_encode(['command' => ['quit']]) . "\n");
            @fclose($this->csatlakozas);
        }
        $this->csatlakozas = null;
        if (is_resource($this->folyamat)) {
            for ($i = 0; $i < 10 && proc_get_status($this->folyamat)['running']; $i++) {
                usleep(30000);
            }
            proc_terminate($this->folyamat, 9);
            proc_close($this->folyamat);
        }
        $this->folyamat = null;
        $this->szol = false;
        $this->fajl = null;
    }

    private function kuld(array $parancs): void
    {
        if (!$this->csatlakozas && !$this->indit()) {
            return;
        }
        $sor = json_encode(['command' => $parancs, 'request_id' => ++$this->keresSzam], JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . "\n";
        if (@fwrite($this->csatlakozas, $sor) === false) {
            $this->leall();
        }
    }

    public function betolt(string $ut, bool $ismetles = false, float $kezdoHangero = 0.0): bool
    {
        if (!$this->indit()) {
            return false;
        }
        $this->hangero($kezdoHangero);
        $this->kuld(['set_property', 'loop-file', $ismetles ? 'inf' : 'no']);
        $this->kuld(['set_property', 'pause', false]);
        $this->inditasraVar = true;
        $this->kuld(['loadfile', $ut, 'replace']);
        $this->fajl = $ut;
        $this->szol = true;
        $this->szunetel = false;
        $this->pozicio = 0.0;
        $this->hossz = 0.0;
        return true;
    }

    public function allj(): void
    {
        if ($this->csatlakozas) {
            $this->kuld(['stop']);
        }
        $this->szol = false;
        $this->fajl = null;
        $this->pozicio = 0.0;
        $this->inditasraVar = false;
    }

    public function szunet(bool $be): void
    {
        $this->kuld(['set_property', 'pause', $be]);
        $this->szunetel = $be;
    }

    public static function mpvHangero(float $amplitudo): float
    {
        return round(100 * (max(0.0, min(1.0, $amplitudo)) ** (1 / 3)), 2);
    }

    public function hangero(float $amplitudo): void
    {
        $v = self::mpvHangero($amplitudo);
        if (abs($v - $this->hangeroErtek) < 0.05) {
            return;
        }
        $this->hangeroErtek = $v;
        $this->kuld(['set_property', 'volume', $v]);
    }

    public function esemenyek(): array
    {
        if (!$this->csatlakozas) {
            return [];
        }
        $adat = @fread($this->csatlakozas, 65536);
        if ($adat === false || (feof($this->csatlakozas) && $adat === '')) {
            $this->leall();
            return [['event' => 'end-file', 'reason' => 'error', 'file_error' => 'az mpv leállt']];
        }
        $this->puffer .= $adat;
        $kesz = [];
        while (($poz = strpos($this->puffer, "\n")) !== false) {
            $sor = substr($this->puffer, 0, $poz);
            $this->puffer = substr($this->puffer, $poz + 1);
            $e = json_decode($sor, true);
            if (!is_array($e) || !isset($e['event'])) {
                continue;
            }
            if ($e['event'] === 'property-change') {
                match ($e['name'] ?? '') {
                    'time-pos' => $this->pozicio = (float)($e['data'] ?? 0),
                    'duration' => $this->hossz = (float)($e['data'] ?? 0),
                    'pause' => $this->szunetel = (bool)($e['data'] ?? false),
                    default => null,
                };
                continue;
            }
            if ($e['event'] === 'start-file') {
                $this->inditasraVar = false;
                continue;
            }
            if ($e['event'] === 'end-file') {
                if ($this->inditasraVar || ($e['reason'] ?? '') === 'stop' || ($e['reason'] ?? '') === 'redirect') {
                    continue;
                }
                $this->szol = false;
            }
            $kesz[] = $e;
        }
        return $kesz;
    }
}
