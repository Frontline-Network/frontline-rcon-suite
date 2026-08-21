# Integrations-Capabilities API v1

`GET /api/v1/capabilities` ist der stabile, anonyme Startpunkt für Bots,
Provisioner und Kundenintegrationen. Er führt weder einen RCON-Befehl noch eine
Spielserver-Abfrage aus. Damit kann ein Client vor der Authentifizierung ohne
Probe-Requests feststellen, welches Spielprofil und welche ausdrücklich
unterstützten Funktionsgruppen die Installation bietet.

## Vertrag

Die Antwort verwendet den normalen CRCON-Response-Umschlag. Der eigentliche
Vertrag steht in `result`:

```json
{
  "result": {
    "schema_version": 1,
    "crcon_version": "0.3.0",
    "game": {
      "id": "hllv",
      "supported_game_modes": ["conquest", "domination", "offensive", "warfare"],
      "timer_controls": {
        "match_timer_modes": ["offensive", "warfare"],
        "warmup_timer_modes": ["warfare"]
      }
    },
    "operations": {
      "player_moderation": {
        "available": true,
        "required_legacy_commands": ["punish", "kick", "temp_ban", "perma_ban"]
      }
    }
  },
  "failed": false
}
```

`operations.<name>.available` darf nur verwendet werden, wenn **alle** dort
genannten Legacy-Befehle in der Installation registriert sind. Der Endpunkt
verspricht bewusst nur die bereits spielübergreifend abgesicherten
Funktionsgruppen. Nicht aufgeführte historische Routen sind keine v1-Zusage.

Für die Argumente, HTTP-Methoden und Berechtigungen der Legacy-Operationen
liefert der in `interfaces.legacy_api.documentation_path` genannte Endpunkt
`/api/get_api_documentation` die maschinenlesbare Bestandsdokumentation.

## Beispielclient

```python
from urllib.request import urlopen
import json

base_url = "https://rcon.example.gg"
with urlopen(f"{base_url}/api/v1/capabilities", timeout=5) as response:
    contract = json.load(response)["result"]

if contract["game"]["id"] != "hllv":
    raise RuntimeError("This integration requires an HLLV installation")
if not contract["operations"]["player_moderation"]["available"]:
    raise RuntimeError("Player moderation is unavailable on this installation")

print(contract["interfaces"]["legacy_api"]["documentation_path"])
```

Die Capability-Abfrage selbst enthält keine Secrets. Authentifizierung und
Berechtigungen werden anschließend weiterhin bei jeder Legacy- oder
Mobile-Operation durch CRCON durchgesetzt.

## Kompatibilitäts- und Deprecation-Regeln

- Die v1-URL und die Bedeutung vorhandener Felder bleiben kompatibel.
- Neue optionale Felder und Funktionsgruppen dürfen additiv erscheinen. Clients
  müssen unbekannte Felder ignorieren.
- Nicht additive Änderungen erhalten eine neue Hauptversion (`/api/v2/...`).
- Eine v1-Operation wird mindestens 90 Tage vor Entfernung als deprecated
  markiert und nennt dann einen Ersatzpfad.
- Unversionierte `/api/*`-Routen bleiben Bestandskompatibilität. Neue Bots
  sollen zuerst diesen Capability-Vertrag lesen und nicht aus 404-Antworten auf
  Funktionen schließen.
