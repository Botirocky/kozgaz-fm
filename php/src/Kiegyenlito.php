<?php

declare(strict_types=1);

namespace KozgazFM;

final class Kiegyenlito
{
    public bool $bekapcsolva = true;
    private array $sor = [];
    private array $hibas = [];
    private ?string $fut = null;
    public ?\Closure $mert = null;

    public function __construct(private readonly Hatter $hatter)
    {
    }

    public function szorzo(?string $ut): float
    {
        return Hangossag::erosites($ut, $this->bekapcsolva);
    }

    public function kell(?string $ut, bool $elore = false): void
    {
        if (!$this->bekapcsolva || $ut === null || isset($this->hibas[$ut]) || $ut === $this->fut || Hangossag::keres($ut) !== null) {
            return;
        }
        $hely = array_search($ut, $this->sor, true);
        if ($hely !== false) {
            if (!$elore) {
                return;
            }
            unset($this->sor[$hely]);
        }
        $elore ? array_unshift($this->sor, $ut) : $this->sor[] = $ut;
        $this->sor = array_values($this->sor);
        $this->kovetkezo();
    }

    public function varakozik(): int
    {
        return count($this->sor) + ($this->fut ? 1 : 0);
    }

    private function kovetkezo(): void
    {
        if ($this->fut !== null || !$this->sor) {
            return;
        }
        $ut = array_shift($this->sor);
        $this->fut = $ut;
        $this->hatter->futtat('meres', ['ut' => $ut], function () use ($ut): void {
            $this->fut = null;
            $this->mert && ($this->mert)($ut);
            $this->kovetkezo();
        }, function () use ($ut): void {
            $this->fut = null;
            $this->hibas[$ut] = true;
            $this->kovetkezo();
        }, 'meres', 300);
    }
}
