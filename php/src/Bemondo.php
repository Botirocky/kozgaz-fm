<?php

declare(strict_types=1);

namespace KozgazFM;

final class Bemondo
{
    private bool $beszel = false;
    private int $generacio = 0;
    public ?\Closure $hangfajlKesz = null;
    public ?\Closure $kesz = null;
    public string $hang = '';

    public function __construct(private readonly Hatter $hatter)
    {
    }

    public function beszel(): bool
    {
        return $this->beszel;
    }

    private static ?bool $van = null;

    public static function elerheto(): bool
    {
        return self::$van ??= trim((string)shell_exec('command -v espeak-ng 2>/dev/null')) !== '';
    }

    public static function hangok(): array
    {
        $ki = (string)shell_exec('espeak-ng --voices=hu 2>/dev/null');
        $lista = [];
        foreach (array_slice(explode("\n", trim($ki)), 1) as $sor) {
            $reszek = preg_split('/\s+/', trim($sor));
            if (count($reszek) >= 5) {
                $lista[] = $reszek[4];
            }
        }
        return array_values(array_unique(array_merge(['hu'], $lista)));
    }

    public function mond(string $szoveg): bool
    {
        if (trim($szoveg) === '') {
            return false;
        }
        $generacio = ++$this->generacio;
        $this->beszel = true;
        $this->hatter->futtat('tts', ['szoveg' => $szoveg, 'hang' => $this->hang ?: 'hu'], function (?string $ut) use ($generacio): void {
            if ($generacio !== $this->generacio || !$this->beszel) {
                return;
            }
            $this->beszel = false;
            $this->hangfajlKesz && ($this->hangfajlKesz)((string)$ut);
        }, function (string $hiba) use ($generacio): void {
            if ($generacio !== $this->generacio) {
                return;
            }
            Naplo::ir("HIBA: a bemondás hangfájlja nem készült el: {$hiba}");
            $this->beszel = false;
            $this->kesz && ($this->kesz)();
        }, 'alap', 90);
        return true;
    }

    public function megallit(): void
    {
        $this->generacio++;
        if (!$this->beszel) {
            return;
        }
        $this->beszel = false;
        $this->kesz && ($this->kesz)();
    }

    public static function wav(string $szoveg, string $hang = 'hu'): string
    {
        $mappa = Utvonalak::mappa('gyorsitotar/bemondas');
        $regiek = glob($mappa . '/*.wav') ?: [];
        sort($regiek);
        foreach (array_slice($regiek, 0, -4) as $r) {
            @unlink($r);
        }
        $ut = $mappa . '/bemondas-' . hrtime(true) . '.wav';
        $f = proc_open(['espeak-ng', '-v', preg_replace('/[^a-zA-Z0-9+_-]/', '', $hang) ?: 'hu', '-s', '150', '-w', $ut, '--', $szoveg],
            [1 => ['file', '/dev/null', 'w'], 2 => ['pipe', 'w']], $csovek);
        if (!is_resource($f)) {
            throw new Hiba('nincs espeak-ng');
        }
        $hiba = (string)stream_get_contents($csovek[2]);
        fclose($csovek[2]);
        if (proc_close($f) !== 0 || !is_file($ut) || filesize($ut) < 100) {
            throw new Hiba(mb_substr(trim($hiba), 0, 200) ?: 'az espeak-ng nem készített hangot');
        }
        return $ut;
    }
}
