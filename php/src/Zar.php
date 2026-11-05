<?php

declare(strict_types=1);

namespace KozgazFM;

final class Zar
{
    public const ALGORITMUS = 'pbkdf2_sha256';
    public const KOROK = 200000;
    public const MIN_HOSSZ = 4;
    public const MAX_HOSSZ = 8;
    public const MAX_HIBA = 5;
    public const TILTAS_MP = 60;
    public const JELSZO_MIN = 8;
    public const JELSZO_MAX = 128;

    public static function pinErvenyes(string $pin): bool
    {
        return strlen($pin) >= self::MIN_HOSSZ && strlen($pin) <= self::MAX_HOSSZ && ctype_digit($pin);
    }

    public static function jelszoErvenyes(string $jelszo): bool
    {
        $hossz = mb_strlen($jelszo);
        return $hossz >= self::JELSZO_MIN && $hossz <= self::JELSZO_MAX && $jelszo === trim($jelszo);
    }

    private static function kivonat(string $titok, int $kor): string
    {
        $so = random_bytes(16);
        $kivonat = hash_pbkdf2('sha256', $titok, $so, $kor, 32, true);
        return self::ALGORITMUS . '$' . $kor . '$' . bin2hex($so) . '$' . bin2hex($kivonat);
    }

    public static function pinHash(string $pin, int $kor = self::KOROK): string
    {
        if (!self::pinErvenyes($pin)) {
            throw new Hiba('A PIN ' . self::MIN_HOSSZ . '–' . self::MAX_HOSSZ . ' számjegyből álljon.');
        }
        return self::kivonat($pin, $kor);
    }

    public static function jelszoHash(string $jelszo, int $kor = self::KOROK): string
    {
        if (!self::jelszoErvenyes($jelszo)) {
            throw new Hiba('A jelszó legalább ' . self::JELSZO_MIN . ' karakter legyen, szóköz nélkül az elején és a végén.');
        }
        return self::kivonat($jelszo, $kor);
    }

    public static function ellenoriz(string $titok, string $tarolt): bool
    {
        $reszek = explode('$', $tarolt);
        if (count($reszek) !== 4 || $reszek[0] !== self::ALGORITMUS || !ctype_digit($reszek[1])
            || !ctype_xdigit($reszek[2]) || !ctype_xdigit($reszek[3])) {
            return false;
        }
        $vart = hex2bin($reszek[3]);
        $szamolt = hash_pbkdf2('sha256', $titok, (string)hex2bin($reszek[2]), (int)$reszek[1], strlen((string)$vart), true);
        return hash_equals((string)$vart, $szamolt);
    }

    public static function probal(string $kulcs, string $titok, string $tarolt): bool
    {
        $fajl = Utvonalak::mappa('munkamenetek') . '/zar-' . hash('sha256', $kulcs) . '.json';
        $adat = is_file($fajl) ? (json_decode((string)file_get_contents($fajl), true) ?: []) : [];
        $hibak = (int)($adat['hibak'] ?? 0);
        $tiltasVege = (float)($adat['tiltas'] ?? 0);
        $hatra = (int)ceil($tiltasVege - microtime(true));
        if ($hatra > 0) {
            throw new Hiba("Túl sok hibás próbálkozás, várj még {$hatra} másodpercet.");
        }
        if (self::ellenoriz($titok, $tarolt)) {
            @unlink($fajl);
            return true;
        }
        $hibak++;
        if ($hibak >= self::MAX_HIBA) {
            $adat = ['hibak' => 0, 'tiltas' => microtime(true) + self::TILTAS_MP];
        } else {
            $adat = ['hibak' => $hibak, 'tiltas' => 0];
        }
        file_put_contents($fajl, json_encode($adat));
        return false;
    }
}
