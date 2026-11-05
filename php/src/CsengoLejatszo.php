<?php

declare(strict_types=1);

namespace KozgazFM;

final class CsengoLejatszo
{
    public Csoport $csoport;
    private bool $aktiv = false;
    private bool $keszJelzes = false;
    private ?array $fuggoZonak = null;
    public ?\Closure $kesz = null;

    public function __construct(string $szerep)
    {
        $this->csoport = new Csoport($szerep);
    }

    public function szol(): bool
    {
        return $this->aktiv;
    }

    public function zonak(array $lista): void
    {
        if (!$this->aktiv || !$this->csoport->ujraepitendo($lista)) {
            $this->fuggoZonak = null;
            $this->csoport->zonak($lista);
        } else {
            $this->fuggoZonak = $lista;
        }
    }

    public function lejatszas(string $ertek, int $hangero, bool $ismetles = false, string $cel = 'csengo'): bool
    {
        $ut = is_file($ertek) && !str_starts_with($ertek, 'beepitett:') && !str_starts_with($ertek, 'sajat:') ? $ertek : SajatHangok::hangUt($ertek);
        if ($ut === null || !is_file($ut)) {
            return false;
        }
        $this->keszJelzes = false;
        $this->csoport->allj();
        if (!$this->csoport->aktival($cel, $cel === 'mind' && $ismetles)) {
            Naplo::ir("Nincs zóna ehhez: {$cel}");
            $this->aktiv = true;
            $this->vege();
            return true;
        }
        $this->csoport->hangero((max(0, min(100, $hangero)) / 100) ** 2);
        if (!$this->csoport->betolt($ut, $ismetles)) {
            return false;
        }
        $this->aktiv = true;
        return true;
    }

    public function megallit(): void
    {
        if ($this->aktiv) {
            $this->csoport->allj();
            $this->vege();
        }
    }

    private function vege(): void
    {
        if ($this->aktiv) {
            $this->aktiv = false;
            $this->keszJelzes = true;
        }
    }

    public function tick(): void
    {
        foreach ($this->csoport->esemenyek() as $e) {
            if ($e[0] === 'hiba') {
                Naplo::ir('Csengőhang-hiba: ' . ($e[1] ?? ''));
            }
            $this->vege();
        }
        if ($this->keszJelzes && !$this->aktiv) {
            $this->keszJelzes = false;
            if ($this->fuggoZonak !== null) {
                $this->csoport->zonak($this->fuggoZonak);
                $this->fuggoZonak = null;
            }
            $this->kesz && ($this->kesz)();
        }
    }

    public function forrasok(): array
    {
        return $this->csoport->forrasok();
    }

    public function leall(): void
    {
        $this->csoport->leall();
    }
}
