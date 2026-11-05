<?php

declare(strict_types=1);

namespace KozgazFM;

final class Hatter
{
    private array $futok = [];
    private array $varok = [];
    private int $sorszam = 0;

    public function __construct(private readonly array $korlatok = ['alap' => 4, 'letoltes' => 2, 'meres' => 1, 'dalszoveg' => 1])
    {
    }

    public function futtat(string $feladat, array $adat, ?\Closure $siker = null, ?\Closure $hiba = null, string $csoport = 'alap',
                           int $idokorlat = 600): int
    {
        $id = ++$this->sorszam;
        $this->varok[] = compact('id', 'feladat', 'adat', 'siker', 'hiba', 'csoport', 'idokorlat');
        $this->indit();
        return $id;
    }

    public function fut(string $csoport): int
    {
        return count(array_filter($this->futok, static fn($f) => $f['csoport'] === $csoport));
    }

    public function varakozik(string $csoport): int
    {
        return count(array_filter($this->varok, static fn($f) => $f['csoport'] === $csoport)) + $this->fut($csoport);
    }

    private function indit(): void
    {
        foreach ($this->varok as $i => $f) {
            if ($this->fut($f['csoport']) >= ($this->korlatok[$f['csoport']] ?? 2)) {
                continue;
            }
            unset($this->varok[$i]);
            $leirok = [0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']];
            $folyamat = proc_open([PHP_BINARY, dirname(__DIR__) . '/bin/munka.php', $f['feladat']], $leirok, $csovek);
            if (!is_resource($folyamat)) {
                if ($f['hiba']) {
                    ($f['hiba'])('a háttérfolyamat nem indult el');
                }
                continue;
            }
            fwrite($csovek[0], json_encode($f['adat'], JSON_UNESCAPED_UNICODE));
            fclose($csovek[0]);
            stream_set_blocking($csovek[1], false);
            stream_set_blocking($csovek[2], false);
            $this->futok[$f['id']] = $f + ['folyamat' => $folyamat, 'ki' => $csovek[1], 'hibaki' => $csovek[2],
                'kimenet' => '', 'hibakimenet' => '', 'kezdet' => microtime(true)];
        }
        $this->varok = array_values($this->varok);
    }

    public function tick(): void
    {
        foreach ($this->futok as $id => &$f) {
            $f['kimenet'] .= (string)stream_get_contents($f['ki']);
            $f['hibakimenet'] .= (string)stream_get_contents($f['hibaki']);
            $allapot = proc_get_status($f['folyamat']);
            $lejart = microtime(true) - $f['kezdet'] > $f['idokorlat'];
            if ($allapot['running'] && !$lejart) {
                continue;
            }
            if ($lejart && $allapot['running']) {
                proc_terminate($f['folyamat'], 9);
            }
            $f['kimenet'] .= (string)stream_get_contents($f['ki']);
            fclose($f['ki']);
            fclose($f['hibaki']);
            proc_close($f['folyamat']);
            $feladat = $f;
            unset($this->futok[$id]);
            $valasz = json_decode(trim($feladat['kimenet']), true);
            try {
                if ($lejart) {
                    $feladat['hiba'] && ($feladat['hiba'])('túl sokáig tartott');
                } elseif (is_array($valasz) && ($valasz['ok'] ?? false)) {
                    $feladat['siker'] && ($feladat['siker'])($valasz['eredmeny'] ?? null);
                } else {
                    $uzenet = is_array($valasz) ? (string)($valasz['hiba'] ?? 'ismeretlen hiba')
                        : (trim($feladat['hibakimenet']) ?: 'érvénytelen válasz');
                    $feladat['hiba'] && ($feladat['hiba'])(mb_substr($uzenet, 0, 400), is_array($valasz) ? ($valasz['kod'] ?? '') : '');
                }
            } catch (\Throwable $e) {
                Naplo::ir('HIBA: háttérfeladat visszahívása (' . $feladat['feladat'] . '): ' . $e->getMessage());
            }
        }
        unset($f);
        $this->indit();
    }

    public function leallit(): void
    {
        foreach ($this->futok as $f) {
            proc_terminate($f['folyamat'], 9);
        }
        $this->futok = [];
        $this->varok = [];
    }
}
