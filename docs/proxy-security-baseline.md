# Reverse-Proxy-Sicherheitsbasis

`rcongui/nginx.conf` ist die HTTPS-Grenze der Admin- und der öffentlichen
CRCON-Oberfläche. Die Konfiguration lässt ausschließlich TLS 1.2 und TLS 1.3
zu. TLS 1.0 und TLS 1.1 werden nicht mehr angeboten.

## Response-Header

Die beiden HTTPS-Server liefern folgende Basis auf dynamischen und statischen
Antworten aus:

| Header | Wert | Zweck |
| --- | --- | --- |
| `Strict-Transport-Security` | `max-age=31536000` (nur HTTPS) | Browser verwenden die bekannte Domain anschließend nur per HTTPS. |
| `X-Content-Type-Options` | `nosniff` | Verhindert MIME-Type-Sniffing. |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Beschränkt beim Verlassen der Seite übertragene URL-Details. |
| `X-Frame-Options` | `SAMEORIGIN` | Verhindert Einbettung durch fremde Domains. |
| `Content-Security-Policy` | `base-uri 'self'; frame-ancestors 'self'; object-src 'none'` | Sperrt Plugin-Inhalte, fremde Basis-URLs und fremde Frames, ohne bestehende Skript-, API- oder WebSocket-Verbindungen einzuengen. |

Nginx vererbt `add_header` nicht in Locations, die selbst einen Header für
Caching setzen. Deshalb ist die Basis dort bewusst wiederholt. Der dazugehörige
Regressionstest schützt diese leicht zu übersehende Nginx-Eigenheit.

## Zertifikate und Prüfung nach dem Rollout

Die Zertifikatspfade (`/certs/cert.crt` und `/certs/key.key`), der HTTP-Listener
auf Port 80 und die Proxy-Routen bleiben unverändert. HTTP-01-Erneuerungen
bleiben dadurch möglich; HSTS wird nur über TLS gesendet.

Nach dem Rollout gegen jede öffentliche RCON-Domain prüfen:

```bash
# Erwartet: TLS 1.0 und TLS 1.1 scheitern, 1.2 und 1.3 verbinden sich.
openssl s_client -connect rcon.example.gg:443 -tls1
openssl s_client -connect rcon.example.gg:443 -tls1_1
openssl s_client -connect rcon.example.gg:443 -tls1_2
openssl s_client -connect rcon.example.gg:443 -tls1_3

# Erwartet: die fünf Response-Header sind vorhanden.
curl -sSI https://rcon.example.gg/ | \
  grep -Ei 'strict-transport|x-content-type|referrer-policy|x-frame-options|content-security-policy'
```

`nginx -t` ist zusätzlich vor einem Container-Neustart auszuführen. Ein
konkreter Zertifikatserneuerungslauf bleibt Verantwortung des jeweiligen
Hostings, da die Zertifikate als Deployment-Secret eingebunden werden.
