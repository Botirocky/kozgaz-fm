<?php

declare(strict_types=1);

namespace KozgazFM;

use DateTimeImmutable;

final class Esemeny
{
    public const JELZO = 'jelző';
    public const BECSENGO = 'becsengő';
    public const KICSENGO = 'kicsengő';
    public const ZENE_INDUL = 'zene indul';
    public const ZENE_LEALL = 'zene leáll';
    public const BEMONDAS = 'bemondás';
    public const RENDKIVULI = 'rendkívüli csengetés';
    public const RIADO = 'riadó';
    public const RIADO_VEGE = 'riadó vége';
    public const CSEND = 'csendes időszak';
    public const CSEND_VEGE = 'csendes időszak vége';

    public const CSENGOK = [self::JELZO, self::BECSENGO, self::KICSENGO];
    public const KULONLEGES = [self::RENDKIVULI, self::RIADO, self::CSEND];

    public const NEVEK = [
        self::JELZO => 'jelzo', self::BECSENGO => 'becsengo', self::KICSENGO => 'kicsengo',
        self::ZENE_INDUL => 'zene_indul', self::ZENE_LEALL => 'zene_leall', self::BEMONDAS => 'bemondas',
        self::RENDKIVULI => 'rendkivuli', self::RIADO => 'riado', self::RIADO_VEGE => 'riado_vege',
        self::CSEND => 'csend', self::CSEND_VEGE => 'csend_vege',
    ];

    private const SORREND = [
        self::ZENE_LEALL, self::CSEND, self::KICSENGO, self::JELZO, self::BECSENGO, self::RENDKIVULI,
        self::RIADO_VEGE, self::RIADO, self::BEMONDAS, self::CSEND_VEGE, self::ZENE_INDUL,
    ];

    public function __construct(
        public readonly DateTimeImmutable $ido,
        public readonly string $tipus,
        public readonly int $ora = 0,
        public readonly ?array $bemondas = null,
        public readonly ?array $rendkivuli = null,
        public readonly ?int $hangero = null,
    ) {
    }

    public function halkan(int $hangero): self
    {
        return new self($this->ido, $this->tipus, $this->ora, $this->bemondas, $this->rendkivuli, $hangero);
    }

    public function csengo(): bool
    {
        return in_array($this->tipus, self::CSENGOK, true);
    }

    public function nev(): string
    {
        return self::NEVEK[$this->tipus];
    }

    public function leiras(): string
    {
        if ($this->tipus === self::BEMONDAS && $this->bemondas) {
            return 'Bemondás: ' . $this->bemondas['nev'];
        }
        if ($this->rendkivuli) {
            if ($this->tipus === self::RIADO_VEGE || $this->tipus === self::CSEND_VEGE) {
                return $this->rendkivuli['nev'] . ' – vége';
            }
            return $this->rendkivuli['nev'];
        }
        if ($this->csengo()) {
            return "{$this->ora}. óra – {$this->tipus}" . ($this->hangero ? ' (halkan)' : '');
        }
        return mb_strtoupper(mb_substr($this->tipus, 0, 1)) . mb_substr($this->tipus, 1);
    }

    public function sorrend(): int
    {
        return (int)array_search($this->tipus, self::SORREND, true);
    }

    public function kulcs(): string
    {
        return $this->ido->format('Y-m-d H:i:s') . '|' . $this->tipus . '|' . $this->ora . '|'
            . ($this->rendkivuli['nev'] ?? '') . '|' . ($this->bemondas['nev'] ?? '');
    }
}
