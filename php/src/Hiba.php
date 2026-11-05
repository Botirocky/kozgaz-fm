<?php

declare(strict_types=1);

namespace KozgazFM;

class Hiba extends \RuntimeException
{
    public function __construct(string $uzenet, public readonly string $kod = 'error', public readonly int $statusz = 400)
    {
        parent::__construct($uzenet);
    }
}
