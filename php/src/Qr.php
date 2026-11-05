<?php

declare(strict_types=1);

namespace KozgazFM;

final class Qr
{
    public static function matrix(string $szoveg, string $szint = 'H'): array
    {
        $f = proc_open(['qrencode', '-t', 'ASCII', '-m', '0', '-l', $szint, '-o', '-', $szoveg], [1 => ['pipe', 'w'], 2 => ['file', '/dev/null', 'w']], $csovek);
        if (!is_resource($f)) {
            return [];
        }
        $ki = (string)stream_get_contents($csovek[1]);
        fclose($csovek[1]);
        proc_close($f);
        $matrix = [];
        foreach (preg_split('/\R/', rtrim($ki, "\r\n")) ?: [] as $sor) {
            if ($sor === '') {
                continue;
            }
            $matrix[] = array_map(static fn($p) => $p === '##', str_split(str_pad($sor, strlen($sor) + strlen($sor) % 2), 2));
        }
        return $matrix;
    }

    private static function kereso(int $x, int $y, int $n): bool
    {
        return ($x < 7 && $y < 7) || ($x >= $n - 7 && $y < 7) || ($x < 7 && $y >= $n - 7);
    }

    public static function plakatSvg(array $matrix, string $tinta = '#14273D', string $kek = '#4085C0'): string
    {
        $n = count($matrix);
        $utak = '';
        foreach ($matrix as $y => $sor) {
            foreach ($sor as $x => $ertek) {
                if ($ertek && !self::kereso($x, $y, $n)) {
                    $utak .= "M{$x} {$y}h1.03v1.03h-1.03z";
                }
            }
        }
        $keresok = '';
        foreach ([[0, 0], [$n - 7, 0], [0, $n - 7]] as [$kx, $ky]) {
            $keresok .= sprintf('<rect x="%d" y="%d" width="7" height="7" rx="1.8" fill="%s"/>', $kx, $ky, $tinta)
                . sprintf('<rect x="%d" y="%d" width="5" height="5" rx="1.1" fill="#fff"/>', $kx + 1, $ky + 1)
                . sprintf('<rect x="%d" y="%d" width="3" height="3" rx="0.9" fill="%s"/>', $kx + 2, $ky + 2, $kek);
        }
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' . $n . ' ' . $n . '" shape-rendering="geometricPrecision">'
            . '<path fill="' . $tinta . '" d="' . $utak . '"/>' . $keresok . '</svg>';
    }
}
