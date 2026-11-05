<?php

declare(strict_types=1);

namespace KozgazFM;

final class Http
{
    public static function keres(string $metodus, string $url, ?string $torzs = null, array $fejlecek = [], float $idokorlat = 15,
                                 int $maxMeret = 4 * 1024 * 1024, bool $proxyNelkul = false): array
    {
        $opciok = [
            'http' => [
                'method' => $metodus,
                'header' => implode("\r\n", $fejlecek),
                'timeout' => $idokorlat,
                'ignore_errors' => true,
                'follow_location' => 1,
                'max_redirects' => 5,
            ],
            'ssl' => ['verify_peer' => true, 'verify_peer_name' => true],
        ];
        if ($torzs !== null) {
            $opciok['http']['content'] = $torzs;
        }
        $kontextus = stream_context_create($opciok);
        $hibaUzenet = '';
        set_error_handler(static function (int $szint, string $uzenet) use (&$hibaUzenet): bool {
            $hibaUzenet = preg_replace('/^.*?: /', '', $uzenet);
            return true;
        });
        try {
            $f = @fopen($url, 'rb', false, $kontextus);
        } finally {
            restore_error_handler();
        }
        if ($f === false) {
            return [0, '', $hibaUzenet ?: 'nem érhető el'];
        }
        $adat = (string)stream_get_contents($f, $maxMeret + 1);
        $meta = stream_get_meta_data($f);
        fclose($f);
        $kod = 0;
        foreach ($meta['wrapper_data'] ?? [] as $sor) {
            if (preg_match('#^HTTP/\S+\s+(\d{3})#', (string)$sor, $m)) {
                $kod = (int)$m[1];
            }
        }
        if (strlen($adat) > $maxMeret) {
            return [0, '', 'túl nagy válasz'];
        }
        return [$kod, $adat, ''];
    }

    public static function json(string $metodus, string $url, ?array $torzs = null, array $fejlecek = [], float $idokorlat = 15): array
    {
        $fejlecek[] = 'Accept: application/json';
        if ($torzs !== null) {
            $fejlecek[] = 'Content-Type: application/json';
        }
        [$kod, $valasz, $hiba] = self::keres($metodus, $url, $torzs !== null ? json_encode($torzs, JSON_UNESCAPED_UNICODE) : null,
            $fejlecek, $idokorlat);
        return [$kod, $valasz !== '' ? json_decode($valasz, true) : null, $hiba];
    }
}
