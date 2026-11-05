<?php

declare(strict_types=1);

namespace KozgazFM;

final class Kimenetek
{
    public const CELOK = ['csengo', 'zene', 'bemondas'];

    public static function lista(): array
    {
        $alap = trim((string)shell_exec('pactl get-default-sink 2>/dev/null'));
        $f = proc_open(['pactl', '-f', 'json', 'list', 'sinks'], [1 => ['pipe', 'w'], 2 => ['file', '/dev/null', 'w']], $csovek);
        if (!is_resource($f)) {
            return [];
        }
        $ki = (string)stream_get_contents($csovek[1]);
        fclose($csovek[1]);
        proc_close($f);
        $adat = json_decode($ki, true);
        $lista = [];
        foreach (is_array($adat) ? $adat : [] as $s) {
            if (!empty($s['name'])) {
                $nev = (string)$s['name'];
                foreach ([$s['description'] ?? null, $s['properties']['device.description'] ?? null, $s['properties']['node.description'] ?? null] as $jelolt) {
                    if (is_string($jelolt) && $jelolt !== '' && $jelolt !== '(null)') {
                        $nev = $jelolt;
                        break;
                    }
                }
                $lista[] = ['azon' => (string)$s['name'], 'nev' => $nev, 'alap' => $s['name'] === $alap];
            }
        }
        return $lista;
    }

    public static function zonak(array $b): array
    {
        if (!$b['zonak']) {
            return [['nev' => 'Alapértelmezett', 'eszkoz' => $b['kimenet'], 'csengo' => true, 'zene' => true, 'bemondas' => true, 'szorzo' => 1.0]];
        }
        $lista = [];
        foreach ($b['zonak'] as $i => $z) {
            $lista[] = ['nev' => $z['nev'] ?: ($i + 1) . '. zóna', 'eszkoz' => $z['kimenet'], 'csengo' => $z['csengo'],
                'zene' => $z['zene'], 'bemondas' => $z['bemondas'], 'szorzo' => max(0, min(100, $z['hangero'])) / 100];
        }
        return $lista;
    }

    public static function celIndexek(array $zonak, string $cel): array
    {
        if ($cel === 'mind') {
            return array_keys($zonak);
        }
        if ($cel === 'elso') {
            return $zonak ? [0] : [];
        }
        if (str_starts_with($cel, 'zona:')) {
            $i = ctype_digit(substr($cel, 5)) ? (int)substr($cel, 5) : -1;
            return isset($zonak[$i]) ? [$i] : [];
        }
        return array_keys(array_filter($zonak, static fn($z) => !empty($z[$cel])));
    }

    public static function nev(array $b, ?array $elerheto = null): ?string
    {
        $elerheto ??= self::lista();
        if (!$elerheto) {
            return null;
        }
        $nevek = array_column($elerheto, 'nev', 'azon');
        if ($b['zonak']) {
            $reszek = [];
            foreach ($b['zonak'] as $z) {
                if ($z['kimenet'] !== '' && !isset($nevek[$z['kimenet']])) {
                    return null;
                }
                $reszek[] = ($z['nev'] ?: 'zóna') . ': ' . ($nevek[$z['kimenet']] ?? 'alapértelmezett');
            }
            return implode(', ', $reszek);
        }
        if ($b['kimenet'] !== '') {
            return $nevek[$b['kimenet']] ?? null;
        }
        foreach ($elerheto as $k) {
            if (!empty($k['alap'])) {
                return "Alapértelmezett ({$k['nev']})";
            }
        }
        return 'Alapértelmezett (' . $elerheto[0]['nev'] . ')';
    }

    public static function hianyzoZonak(array $b, ?array $elerheto = null): array
    {
        $azonok = array_column($elerheto ?? self::lista(), 'azon');
        $hianyzo = [];
        foreach ($b['zonak'] as $z) {
            if ($z['kimenet'] !== '' && !in_array($z['kimenet'], $azonok, true)) {
                $hianyzo[] = $z['nev'] ?: 'névtelen';
            }
        }
        return $hianyzo;
    }
}
