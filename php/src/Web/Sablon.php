<?php

declare(strict_types=1);

namespace KozgazFM\Web;

final class Sablon
{
    public static function e(mixed $s): string
    {
        return htmlspecialchars((string)$s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    }

    public static function ikon(string $nev): string
    {
        $utak = [
            'pult' => '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
            'riasztas' => '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
            'csengo' => '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
            'zene' => '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
            'naptar' => '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
            'bemondas' => '<path d="m3 11 18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/>',
            'naplo' => '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/>',
            'grafikon' => '<path d="M3 3v18h18"/><path d="M18 17V9M13 17V5M8 17v-3"/>',
            'beallitas' => '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
            'sugo' => '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3M12 17h.01"/>',
            'lakat' => '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
            'kijelzo' => '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>',
            'ki' => '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
        ];
        return '<svg class="ikon" viewBox="0 0 24 24" aria-hidden="true">' . ($utak[$nev] ?? '') . '</svg>';
    }

    public static function fej(string $cim, array $tobb = []): string
    {
        $osztaly = self::e($tobb['osztaly'] ?? '');
        return '<!doctype html><html lang="hu"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            . '<title>' . self::e($cim) . ' – Közgáz FM</title><link rel="icon" href="/statikus/logo.png">'
            . '<link rel="stylesheet" href="/statikus/app.css?v=' . KFM_VERZIO . '"></head><body class="' . $osztaly . '">';
    }

    public static function keret(Alkalmazas $app, string $ut, string $tartalom, array $adat = []): string
    {
        [$cim] = Alkalmazas::OLDALAK[$ut];
        $nav = '';
        foreach (Alkalmazas::OLDALAK as $u => [$nev, $ikon, $vedett]) {
            if (isset(Alkalmazas::CSOPORTOK[$u])) {
                $nav .= '<div class="nav-cim">' . self::e(Alkalmazas::CSOPORTOK[$u]) . '</div>';
            }
            $nav .= '<a class="nav' . ($u === $ut ? ' aktiv' : '') . ($u === '/riasztas' ? ' nav-riaszt' : '') . '" href="' . $u . '"'
                . ($vedett && $app->pinKell() ? ' title="PIN-kóddal védett oldal"' : '') . '>' . self::ikon($ikon) . '<span>' . self::e($nev) . '</span></a>';
        }
        $zarGomb = $app->pinKell() ? '<button class="gomb sav" data-muvelet="zarolas">' . self::ikon('lakat') . 'Beállítások zárolása</button>' : '';
        $adat += ['oldal' => $ut, 'pin' => $app->pinKell(), 'feloldva' => $app->feloldva(), 'vedett' => $app->vedett($ut)];
        return self::fej($cim, ['osztaly' => 'alkalmazas']) . '<div class="elrendezes"><nav class="oldalsav" aria-label="Oldalak">'
            . '<a class="logo" href="/"><img src="/statikus/logo.png" alt="Közgáz FM"></a>' . $nav . '<div class="sav-alja">' . $zarGomb
            . '<a class="gomb sav" href="/kijelzo" target="_blank" rel="noopener">' . self::ikon('kijelzo') . 'Folyosói kijelző</a>'
            . '<button class="gomb sav" data-muvelet="kilepes">' . self::ikon('ki') . 'Kilépés</button></div></nav>'
            . '<div class="fo"><header class="fejlec"><button class="menu-gomb" data-muvelet="menu" aria-label="Menü">☰</button>'
            . '<div><div class="fejlec-cim">' . self::e($cim) . '</div><div class="fejlec-szakasz" id="fej-szakasz"></div></div>'
            . '<div class="elo" id="elo" hidden></div><div class="fejlec-jobb"><div class="ora" id="ora"></div><div class="fej-hatra" id="fej-hatra"></div></div></header>'
            . '<main id="tartalom" class="tartalom" data-oldal="' . self::e($ut) . '">' . $tartalom . '</main>'
            . '<footer class="allapotsor"><span id="as-automatika"></span><span id="as-kimenet"></span><span id="as-tartalek"></span><span class="verzio">Közgáz FM ' . self::e(KFM_VERZIO) . '</span></footer>'
            . '</div></div><div id="uzenetek" class="uzenetek" aria-live="polite"></div>'
            . '<script type="application/json" id="oldal-adat">' . json_encode($adat, JSON_UNESCAPED_UNICODE | JSON_HEX_TAG | JSON_HEX_AMP) . '</script>'
            . '<script src="/statikus/app.js?v=' . KFM_VERZIO . '"></script></body></html>';
    }

    public static function hibaOldal(string $uzenet): string
    {
        return self::fej('Hiba') . '<main class="kozepre"><div class="kartya kicsi"><h1>Hiba</h1><p>' . self::e($uzenet)
            . '</p><p><a class="gomb" href="/">Vissza a Vezérlőpultra</a></p></div></main></body></html>';
    }

    public static function belepes(bool $elso, string $hiba = ''): string
    {
        $szoveg = $elso
            ? '<h1>Első indítás</h1><p class="halvany">Adj meg egy legalább 8 karakteres jelszót a kezelőfelülethez. Ezzel lehet majd belépni böngészőből (telefonról is).</p>'
            : '<h1>Belépés</h1><p class="halvany">A Közgáz FM kezelőfelülete.</p>';
        $mezok = '<label>Jelszó<input type="password" name="jelszo" autocomplete="' . ($elso ? 'new-password' : 'current-password') . '" required minlength="' . ($elso ? 8 : 1) . '" autofocus></label>'
            . ($elso ? '<label>Jelszó még egyszer<input type="password" name="jelszo2" autocomplete="new-password" required minlength="8"></label>' : '');
        return self::fej($elso ? 'Első indítás' : 'Belépés', ['osztaly' => 'belepes-oldal']) . '<main class="kozepre"><form class="kartya kicsi" id="belepes" data-elso="' . ($elso ? '1' : '0') . '">'
            . '<img class="belepes-logo" src="/statikus/logo.png" alt="">' . $szoveg . $mezok . '<p class="hiba-szoveg" id="belepes-hiba">' . self::e($hiba) . '</p>'
            . '<button class="gomb fo" type="submit">' . ($elso ? 'Jelszó beállítása' : 'Belépés') . '</button></form></main><script src="/statikus/belepes.js?v=' . KFM_VERZIO . '"></script></body></html>';
    }
}
