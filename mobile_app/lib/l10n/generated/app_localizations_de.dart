// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for German (`de`).
class AppLocalizationsDe extends AppLocalizations {
  AppLocalizationsDe([String locale = 'de']) : super(locale);

  @override
  String get appTitle => 'Frontline CRCON Administration';

  @override
  String get connections => 'CRCON-Verbindungen';

  @override
  String get pairCrcon => 'CRCON koppeln';

  @override
  String get pairFirst => 'Kopple zuerst eine CRCON-Installation.';

  @override
  String get incidentNotifications => 'Vorfallbenachrichtigungen';

  @override
  String get revokeDeviceTitle => 'Dieses Gerät widerrufen?';

  @override
  String get revokeDeviceBody =>
      'CRCON macht Zugriffs- und Aktualisierungstoken sofort ungültig.';

  @override
  String get cancel => 'Abbrechen';

  @override
  String get revoke => 'Widerrufen';

  @override
  String get pairInstructions =>
      'Öffne in CRCON „Apps einrichten“, erstelle einen QR-Code und scanne ihn hier.';

  @override
  String get compareCode => 'Vergleiche diesen Code mit CRCON';

  @override
  String get approvePhone =>
      'Bestätige das Smartphone im CRCON-Browser, um die Kopplung abzuschließen.';

  @override
  String get createIncident => 'Vorfall erstellen';

  @override
  String get gameServer => 'Gameserver';

  @override
  String get reason => 'Grund';

  @override
  String get create => 'Erstellen';

  @override
  String serverNumber(Object number) {
    return 'Server $number';
  }

  @override
  String get newIncident => 'Neuer Vorfall';

  @override
  String get incidentInbox => 'Vorfall-Inbox';

  @override
  String get noIncidents => 'Keine Vorfälle.';

  @override
  String get playerSearch => 'Spielersuche';

  @override
  String get pairConnectionFirst => 'Kopple zuerst eine CRCON-Verbindung.';

  @override
  String get crconConnection => 'CRCON-Verbindung';

  @override
  String get nameOrPlayerId => 'Name oder Spieler-ID';

  @override
  String get unknown => 'Unbekannt';

  @override
  String get playerProfile => 'Spielerprofil';

  @override
  String get unknownPlayer => 'Unbekannter Spieler';

  @override
  String get offline => 'Offline';

  @override
  String get onlineNow => 'Jetzt online';

  @override
  String get sessions => 'Sitzungen';

  @override
  String get bans => 'Sperren';

  @override
  String get adminComments => 'Admin-Kommentare';

  @override
  String get flags => 'Markierungen';

  @override
  String get recentComments => 'Letzte Kommentare';

  @override
  String get incident => 'Vorfall';

  @override
  String get incidentUnavailable => 'Vorfall nicht verfügbar';

  @override
  String reporter(String name) {
    return 'Gemeldet von: $name';
  }

  @override
  String target(String name) {
    return 'Ziel: $name';
  }

  @override
  String assigned(String name) {
    return 'Zugewiesen: $name';
  }

  @override
  String get notSet => 'nicht angegeben';

  @override
  String get notLinked => 'nicht verknüpft';

  @override
  String get nobody => 'niemandem';

  @override
  String get claim => 'Übernehmen';

  @override
  String get release => 'Freigeben';

  @override
  String get reassign => 'Neu zuweisen';

  @override
  String get resolve => 'Lösen';

  @override
  String get dismiss => 'Verwerfen';

  @override
  String get reopen => 'Wieder öffnen';

  @override
  String get addNote => 'Notiz hinzufügen';

  @override
  String get linkPlayer => 'Spieler verknüpfen';

  @override
  String get playerActions => 'Spieleraktionen';

  @override
  String get linkPlayerFirst =>
      'Verknüpfe zuerst einen eindeutigen CRCON-Spieler, um Aktionen auszuführen.';

  @override
  String get message => 'Nachricht';

  @override
  String get punish => 'Bestrafen';

  @override
  String get comment => 'Kommentar';

  @override
  String get kick => 'Kicken';

  @override
  String get tempBan => 'Temporär sperren';

  @override
  String get timeline => 'Verlauf';

  @override
  String get addPrivateNote => 'Private Admin-Notiz hinzufügen';

  @override
  String get note => 'Notiz';

  @override
  String get save => 'Speichern';

  @override
  String get linkTargetPlayer => 'Zielspieler verknüpfen';

  @override
  String get playerName => 'Spielername';

  @override
  String get playerId => 'Spieler-ID';

  @override
  String get link => 'Verknüpfen';

  @override
  String get reassignIncident => 'Vorfall neu zuweisen';

  @override
  String get crconUsername => 'CRCON-Benutzername';

  @override
  String get confirm => 'Bestätigen';

  @override
  String get adminComment => 'Admin-Kommentar';

  @override
  String get requiredReason => 'Erforderlicher Grund';

  @override
  String get inbox => 'Inbox';

  @override
  String get players => 'Spieler';

  @override
  String get connectionsShort => 'Verbindungen';

  @override
  String get language => 'Sprache';

  @override
  String get german => 'Deutsch';

  @override
  String get english => 'English';

  @override
  String get cachedMayBeStale =>
      'Zwischengespeichert — möglicherweise veraltet';

  @override
  String get manual => 'manuell';

  @override
  String get event => 'Ereignis';

  @override
  String get system => 'System';
}
