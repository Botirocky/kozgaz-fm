<?php

declare(strict_types=1);

namespace KozgazFM;

final class Szam
{
    public function __construct(
        public string $cim,
        public ?string $helyi = null,
        public string $yt = '',
        public bool $kert = false,
        public bool $keresbol = false,
    ) {
    }
}
