const autobalancerNotes = `
Zweck
Der faire Autobalancer korrigiert ein dauerhaftes Ungleichgewicht der Spielerzahlen.
Er führt keine reinen Stärkewechsel durch, wenn die Spielerzahlen bereits ausgeglichen
sind. Commander sind immer ausgeschlossen. Bestehende Squads werden möglichst geschützt.

Betriebsarten
- disabled: Der Dienst ist ausgeschaltet.
- shadow: Nur beobachten und protokollieren. Keine Nachrichten und keine Teamwechsel.
- manual: Freiwillige werden gesucht. Danach muss ein Admin den Vorschlag freigeben.
- auto: Freiwillige werden gesucht. Danach wird automatisch ein Spieler ausgewählt.
  Der tatsächliche Wechsel erfolgt trotzdem erst nach dessen nächstem Tod.

Wann beginnt ein Vorfall?
Die erlaubte Teamdifferenz muss dauerhaft überschritten sein, die Mindestspielerzahl
muss erreicht sein und die Runde muss außerhalb der Schutzzeit am Kartenanfang und
Kartenende liegen. Ein einzelner Wechsel verändert die Teamdifferenz um zwei Spieler.

Sicherheitsregeln
- Niemals Commander automatisch verschieben.
- Neu verbundene und kürzlich verschobene Spieler schützen.
- Pro Vorfall nur die konfigurierte Höchstzahl an Wechseln.
- Nach jedem Wechsel Teamzahlen und Kandidaten vollständig neu berechnen.
- Der native HLL-Autobalancer bleibt unverändert und sollte eingeschaltet bleiben.

FLN-Pilot
Empfohlen ist zunächst mode = "shadow". history_server_numbers sollte [1, 2] enthalten.
Vorschläge und Blockierungsgründe sind in der Teamansicht sichtbar.
`;

export default autobalancerNotes;
