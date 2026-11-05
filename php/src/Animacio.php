<?php

declare(strict_types=1);

namespace KozgazFM;

final class Animacio
{
    private ?float $kezdet = null;
    private float $tol = 0.0;
    private float $ig = 0.0;
    private float $hossz = 0.0;
    private array $vege = [];

    public function __construct(private readonly \Closure $alkalmaz)
    {
    }

    public function indit(float $tol, float $ig, float $hosszMp, ?\Closure $vege = null): void
    {
        $this->tol = $tol;
        $this->ig = $ig;
        $this->hossz = max(0.001, $hosszMp);
        $this->kezdet = microtime(true);
        $this->vege = $vege ? [$vege] : [];
        ($this->alkalmaz)($tol);
    }

    public function fut(): bool
    {
        return $this->kezdet !== null;
    }

    public function allj(): void
    {
        $this->kezdet = null;
        $this->vege = [];
    }

    public function tick(): void
    {
        if ($this->kezdet === null) {
            return;
        }
        $arany = min(1.0, (microtime(true) - $this->kezdet) / $this->hossz);
        ($this->alkalmaz)($this->tol + ($this->ig - $this->tol) * $arany);
        if ($arany >= 1.0) {
            $this->kezdet = null;
            $teendok = $this->vege;
            $this->vege = [];
            foreach ($teendok as $t) {
                $t();
            }
        }
    }
}
