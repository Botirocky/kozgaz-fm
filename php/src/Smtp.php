<?php

declare(strict_types=1);

namespace KozgazFM;

final class Smtp
{
    private $kapcsolat = null;

    public function __construct(private readonly string $szerver, private readonly int $port, private readonly string $mod)
    {
    }

    private function sor(): string
    {
        $valasz = '';
        while (($sor = fgets($this->kapcsolat, 1024)) !== false) {
            $valasz .= $sor;
            if (strlen($sor) < 4 || $sor[3] === ' ') {
                break;
            }
        }
        return $valasz;
    }

    private function parancs(string $szoveg, array $vart): string
    {
        fwrite($this->kapcsolat, $szoveg . "\r\n");
        $valasz = $this->sor();
        if (!in_array((int)substr($valasz, 0, 3), $vart, true)) {
            if (str_starts_with($szoveg, 'AUTH') || (int)substr($valasz, 0, 3) === 535) {
                throw new Hiba('Az SMTP-szerver nem fogadta el a felhasználónevet vagy a jelszót.');
            }
            throw new Hiba('Az e-mail nem ment el: ' . trim($valasz));
        }
        return $valasz;
    }

    public function kuld(string $felhasznalo, string $jelszo, string $felado, array $cimzettek, string $targy, string $szoveg): void
    {
        $cel = ($this->mod === 'ssl' ? 'ssl://' : 'tcp://') . $this->szerver . ':' . $this->port;
        $this->kapcsolat = @stream_socket_client($cel, $hibakod, $hiba, 15, STREAM_CLIENT_CONNECT,
            stream_context_create(['ssl' => ['verify_peer' => true, 'verify_peer_name' => true]]));
        if (!$this->kapcsolat) {
            throw new Hiba("Az e-mail nem ment el: {$hiba}");
        }
        stream_set_timeout($this->kapcsolat, 15);
        try {
            $this->sor();
            $nev = gethostname() ?: 'kozgaz-fm';
            $this->parancs("EHLO {$nev}", [250]);
            if ($this->mod === 'starttls') {
                $this->parancs('STARTTLS', [220]);
                if (!stream_socket_enable_crypto($this->kapcsolat, true, STREAM_CRYPTO_METHOD_TLS_CLIENT)) {
                    throw new Hiba('Az e-mail nem ment el: a TLS nem jött létre.');
                }
                $this->parancs("EHLO {$nev}", [250]);
            }
            if ($felhasznalo !== '') {
                $this->parancs('AUTH PLAIN ' . base64_encode("\0{$felhasznalo}\0{$jelszo}"), [235]);
            }
            $this->parancs("MAIL FROM:<{$felado}>", [250]);
            foreach ($cimzettek as $c) {
                $this->parancs("RCPT TO:<{$c}>", [250, 251]);
            }
            $this->parancs('DATA', [354]);
            $fej = [
                'From: ' . $felado, 'To: ' . implode(', ', $cimzettek),
                'Subject: =?UTF-8?B?' . base64_encode($targy) . '?=', 'Date: ' . date('r'),
                'Message-ID: <' . bin2hex(random_bytes(8)) . '@kozgaz-fm>', 'MIME-Version: 1.0',
                'Content-Type: text/plain; charset=utf-8', 'Content-Transfer-Encoding: base64',
            ];
            $torzs = implode("\r\n", $fej) . "\r\n\r\n" . chunk_split(base64_encode($szoveg)) . "\r\n.";
            $this->parancs($torzs, [250]);
            $this->parancs('QUIT', [221, 250]);
        } finally {
            fclose($this->kapcsolat);
        }
    }
}
