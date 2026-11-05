<?php

declare(strict_types=1);

namespace KozgazFM;

final class SajatHangok
{
    public const ELOTAG = 'sajat:';
    public const HANGFAJLOK = ['mp3', 'm4a', 'aac', 'ogg', 'oga', 'opus', 'flac', 'wav', 'wma', 'webm'];
    public const MAX_MERET = 30 * 1024 * 1024;

    public static function biztonsagosNev(string $nev): string
    {
        $alap = trim(\Normalizer::normalize($nev, \Normalizer::FORM_KC) ?: $nev);
        $alap = (string)preg_replace('/[<>:"\/\\\\|?*\x00-\x1f]/u', '', $alap);
        $alap = trim((string)preg_replace('/\s+/u', ' ', $alap), ' .');
        return mb_substr($alap, 0, 80) ?: 'Saját hang';
    }

    public static function sajat(string $ertek): bool
    {
        return str_starts_with($ertek, self::ELOTAG);
    }

    public static function ut(string $ertek): ?string
    {
        if (!self::sajat($ertek)) {
            return null;
        }
        $fajlnev = substr($ertek, strlen(self::ELOTAG));
        if ($fajlnev === '' || basename($fajlnev) !== $fajlnev) {
            return null;
        }
        $cel = Utvonalak::sajatHangok() . '/' . $fajlnev;
        return is_file($cel) ? $cel : null;
    }

    public static function nev(string $ertek): string
    {
        return self::sajat($ertek) ? pathinfo(substr($ertek, strlen(self::ELOTAG)), PATHINFO_FILENAME) : '';
    }

    public static function lista(): array
    {
        $lista = [];
        foreach (scandir(Utvonalak::sajatHangok()) ?: [] as $f) {
            $ut = Utvonalak::sajatHangok() . '/' . $f;
            if (is_file($ut) && in_array(strtolower(pathinfo($f, PATHINFO_EXTENSION)), self::HANGFAJLOK, true)) {
                $lista[] = ['ertek' => self::ELOTAG . $f, 'nev' => pathinfo($f, PATHINFO_FILENAME), 'ut' => $ut];
            }
        }
        usort($lista, static fn($a, $b) => strcasecmp($a['nev'], $b['nev']));
        return $lista;
    }

    private static function szabadUt(string $tiszta, string $kiterjesztes, ?string $kiveve = null): string
    {
        $mappa = Utvonalak::sajatHangok();
        $cel = "{$mappa}/{$tiszta}.{$kiterjesztes}";
        $sorszam = 2;
        while (file_exists($cel) && $cel !== $kiveve) {
            $cel = "{$mappa}/{$tiszta} ({$sorszam}).{$kiterjesztes}";
            $sorszam++;
        }
        return $cel;
    }

    public static function hozzaad(string $forras, string $eredetiNev, ?string $ujNev = null): array
    {
        $kiterjesztes = strtolower(pathinfo($eredetiNev, PATHINFO_EXTENSION));
        if (!in_array($kiterjesztes, self::HANGFAJLOK, true)) {
            throw new Hiba("Ez nem támogatott hangfájl: {$eredetiNev}", 'validation_error', 422);
        }
        $meret = @filesize($forras);
        if (!$meret) {
            throw new Hiba("A fájl üres vagy nem olvasható: {$eredetiNev}", 'validation_error', 422);
        }
        if ($meret > self::MAX_MERET) {
            throw new Hiba('A fájl túl nagy (legfeljebb ' . intdiv(self::MAX_MERET, 1048576) . " MB): {$eredetiNev}", 'validation_error', 422);
        }
        $cel = self::szabadUt(self::biztonsagosNev($ujNev ?: pathinfo($eredetiNev, PATHINFO_FILENAME)), $kiterjesztes);
        if (!(is_uploaded_file($forras) ? move_uploaded_file($forras, $cel) : copy($forras, $cel))) {
            throw new Hiba('Nem sikerült bemásolni a hangfájlt.');
        }
        @chmod($cel, 0664);
        return ['ertek' => self::ELOTAG . basename($cel), 'nev' => pathinfo($cel, PATHINFO_FILENAME), 'ut' => $cel];
    }

    public static function atnevez(string $ertek, string $ujNev): array
    {
        $regi = self::ut($ertek);
        if ($regi === null) {
            throw new Hiba('A hang már nem található.', 'not_found', 404);
        }
        $cel = self::szabadUt(self::biztonsagosNev($ujNev), strtolower(pathinfo($regi, PATHINFO_EXTENSION)), $regi);
        if ($cel !== $regi && !rename($regi, $cel)) {
            throw new Hiba('Nem sikerült átnevezni.');
        }
        return ['ertek' => self::ELOTAG . basename($cel), 'nev' => pathinfo($cel, PATHINFO_FILENAME), 'ut' => $cel];
    }

    public static function torol(string $ertek): void
    {
        $hely = self::ut($ertek);
        if ($hely !== null && !@unlink($hely)) {
            throw new Hiba('Nem sikerült törölni.');
        }
    }

    public static function hangUt(string $ertek): ?string
    {
        if (str_starts_with($ertek, 'beepitett:')) {
            $nev = substr($ertek, 10);
            $nev = isset(Beallitasok::BEEPITETT_HANGOK[$nev]) ? $nev : (Beallitasok::REGI_HANGOK[$nev] ?? '');
            return isset(Beallitasok::BEEPITETT_HANGOK[$nev]) ? Utvonalak::beepitettHang($nev) : null;
        }
        if (self::sajat($ertek)) {
            return self::ut($ertek);
        }
        return is_file($ertek) ? $ertek : null;
    }

    public static function hangNev(string $ertek): string
    {
        if (str_starts_with($ertek, 'beepitett:')) {
            $nev = substr($ertek, 10);
            return Beallitasok::BEEPITETT_HANGOK[$nev] ?? Beallitasok::BEEPITETT_HANGOK[Beallitasok::REGI_HANGOK[$nev] ?? ''] ?? 'Ismeretlen';
        }
        if (self::sajat($ertek)) {
            return self::nev($ertek);
        }
        return basename($ertek);
    }

    public static function osszes(): array
    {
        $lista = [];
        foreach (Beallitasok::BEEPITETT_HANGOK as $azon => $nev) {
            $lista[] = ['ertek' => "beepitett:{$azon}", 'nev' => $nev, 'beepitett' => true];
        }
        foreach (self::lista() as $h) {
            $lista[] = ['ertek' => $h['ertek'], 'nev' => $h['nev'], 'beepitett' => false];
        }
        return $lista;
    }
}
