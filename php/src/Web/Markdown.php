<?php

declare(strict_types=1);

namespace KozgazFM\Web;

final class Markdown
{
    private static function sorKozi(string $s): string
    {
        $s = Sablon::e($s);
        $s = (string)preg_replace('/`([^`]+)`/', '<code>$1</code>', $s);
        $s = (string)preg_replace('/\*\*([^*]+)\*\*/', '<strong>$1</strong>', $s);
        $s = (string)preg_replace('/(?<![\w*])\*([^*\n]+)\*(?![\w*])/u', '<em>$1</em>', $s);
        return (string)preg_replace('/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/', '<a href="$2" target="_blank" rel="noopener">$1</a>', $s);
    }

    public static function html(string $md): string
    {
        $ki = [];
        $bekezdes = [];
        $listak = [];
        $tartalom = [];
        $lezarBekezdes = static function () use (&$bekezdes, &$ki): void {
            if ($bekezdes) {
                $ki[] = '<p>' . self::sorKozi(implode(' ', $bekezdes)) . '</p>';
                $bekezdes = [];
            }
        };
        $lezarListak = static function (int $szint = -1) use (&$listak, &$ki): void {
            while ($listak && end($listak)[0] > $szint) {
                $ki[] = '</li></' . array_pop($listak)[1] . '>';
            }
        };
        foreach (preg_split('/\R/', $md) ?: [] as $sor) {
            if (trim($sor) === '') {
                $lezarBekezdes();
                continue;
            }
            if (preg_match('/^(#{1,4})\s+(.*)$/', $sor, $m)) {
                $lezarBekezdes();
                $lezarListak();
                $szint = strlen($m[1]);
                $azon = trim((string)preg_replace('/[^a-z0-9]+/', '-', strtolower(iconv('UTF-8', 'ASCII//TRANSLIT', $m[2]) ?: $m[2])), '-');
                if ($szint === 2) {
                    $tartalom[] = '<a href="#' . $azon . '">' . Sablon::e($m[2]) . '</a>';
                }
                $ki[] = "<h{$szint} id=\"{$azon}\">" . self::sorKozi($m[2]) . "</h{$szint}>";
                continue;
            }
            if (preg_match('/^(\s*)([-*]|\d+\.)\s+(.*)$/', $sor, $m)) {
                $lezarBekezdes();
                $szint = intdiv(strlen($m[1]), 2);
                $tipus = ctype_digit(rtrim($m[2], '.')) ? 'ol' : 'ul';
                if ($listak && end($listak)[0] === $szint) {
                    $ki[] = '</li>';
                } elseif (!$listak || end($listak)[0] < $szint) {
                    $ki[] = "<{$tipus}>";
                    $listak[] = [$szint, $tipus];
                } else {
                    $lezarListak($szint);
                    $ki[] = '</li>';
                }
                $ki[] = '<li>' . self::sorKozi($m[3]);
                continue;
            }
            if ($listak && preg_match('/^\s{2,}(\S.*)$/', $sor, $m)) {
                $ki[] = ' ' . self::sorKozi($m[1]);
                continue;
            }
            $lezarListak();
            $bekezdes[] = trim($sor);
        }
        $lezarBekezdes();
        $lezarListak();
        return ($tartalom ? '<nav class="sugo-tartalom">' . implode('', $tartalom) . '</nav>' : '') . implode("\n", $ki);
    }
}
