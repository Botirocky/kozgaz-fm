<?php

declare(strict_types=1);

namespace KozgazFM;

final class Csoport
{
    private array $tagok = [];
    private array $zonaLista = [];
    private array $aktiv = [];
    private float $amplitudo = 1.0;
    private bool $teljes = false;
    public string $cel = 'mind';

    public function __construct(public readonly string $szerep, array $zonak = [])
    {
        $this->zonak($zonak ?: [['nev' => 'Alapértelmezett', 'eszkoz' => '', 'csengo' => true, 'zene' => true, 'bemondas' => true, 'szorzo' => 1.0]]);
    }

    public function ujraepitendo(array $zonak): bool
    {
        return array_column($zonak, 'eszkoz') !== array_column($this->zonaLista, 'eszkoz');
    }

    public function zonak(array $zonak): void
    {
        if ($this->ujraepitendo($zonak) || !$this->tagok) {
            foreach ($this->tagok as $m) {
                $m->leall();
            }
            $this->tagok = [];
            foreach (array_values($zonak) as $i => $z) {
                $this->tagok[$i] = new Mpv("{$this->szerep}-{$i}", (string)$z['eszkoz']);
            }
        }
        $this->zonaLista = array_values($zonak);
        $this->aktiv = Kimenetek::celIndexek($this->zonaLista, $this->cel);
    }

    public function aktivZonak(string $cel): array
    {
        return Kimenetek::celIndexek($this->zonaLista, $cel);
    }

    public function aktival(string $cel, bool $teljes = false): bool
    {
        $this->cel = $cel;
        $this->teljes = $teljes;
        $this->aktiv = Kimenetek::celIndexek($this->zonaLista, $cel);
        return (bool)$this->aktiv;
    }

    private function fo(): ?Mpv
    {
        return $this->aktiv ? $this->tagok[$this->aktiv[0]] : null;
    }

    public function betolt(string $ut, bool $ismetles = false): bool
    {
        $siker = false;
        foreach ($this->tagok as $i => $m) {
            if (in_array($i, $this->aktiv, true)) {
                $siker = $m->betolt($ut, $ismetles, $this->zonaAmplitudo($i)) || $siker;
            } elseif ($m->szol) {
                $m->allj();
            }
        }
        return $siker;
    }

    private function zonaAmplitudo(int $i): float
    {
        $szorzo = $this->teljes ? 1.0 : (float)($this->zonaLista[$i]['szorzo'] ?? 1.0);
        return $this->amplitudo * $szorzo;
    }

    public function hangero(float $amplitudo): void
    {
        $this->amplitudo = max(0.0, min(1.0, $amplitudo));
        foreach ($this->aktiv as $i) {
            $this->tagok[$i]->hangero($this->zonaAmplitudo($i));
        }
    }

    public function amplitudo(): float
    {
        return $this->amplitudo;
    }

    public function allj(): void
    {
        foreach ($this->tagok as $m) {
            if ($m->szol || $m->fajl !== null) {
                $m->allj();
            }
        }
    }

    public function szunet(bool $be): void
    {
        foreach ($this->aktiv as $i) {
            $this->tagok[$i]->szunet($be);
        }
    }

    public function szol(): bool
    {
        $fo = $this->fo();
        return $fo !== null && $fo->szol;
    }

    public function szunetel(): bool
    {
        $fo = $this->fo();
        return $fo !== null && $fo->szol && $fo->szunetel;
    }

    public function pozicio(): float
    {
        return $this->fo()?->pozicio ?? 0.0;
    }

    public function hossz(): float
    {
        return $this->fo()?->hossz ?? 0.0;
    }

    public function fajl(): ?string
    {
        return $this->fo()?->fajl;
    }

    public function esemenyek(): array
    {
        $fo = $this->fo();
        $kesz = [];
        foreach ($this->tagok as $m) {
            foreach ($m->esemenyek() as $e) {
                if ($m === $fo && $e['event'] === 'end-file') {
                    $kesz[] = ($e['reason'] ?? '') === 'eof' ? ['vege'] : ['hiba', (string)($e['file_error'] ?? 'lejátszási hiba')];
                }
            }
        }
        return $kesz;
    }

    public function forrasok(): array
    {
        return array_filter(array_map(static fn(Mpv $m) => $m->fajl, $this->tagok));
    }

    public function leall(): void
    {
        foreach ($this->tagok as $m) {
            $m->leall();
        }
    }
}
