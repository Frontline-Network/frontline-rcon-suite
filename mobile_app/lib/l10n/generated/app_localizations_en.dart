// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'Frontline CRCON Admin';

  @override
  String get connections => 'CRCON connections';

  @override
  String get pairCrcon => 'Pair CRCON';

  @override
  String get pairFirst => 'Pair your first CRCON installation.';

  @override
  String get incidentNotifications => 'Incident notifications';

  @override
  String get revokeDeviceTitle => 'Revoke this device?';

  @override
  String get revokeDeviceBody =>
      'CRCON will invalidate its access and refresh tokens immediately.';

  @override
  String get cancel => 'Cancel';

  @override
  String get revoke => 'Revoke';

  @override
  String get pairInstructions =>
      'Open “Set up apps” in CRCON, create a QR code, then scan it here.';

  @override
  String get compareCode => 'Compare this code with CRCON';

  @override
  String get approvePhone =>
      'Approve the phone in the CRCON browser to finish pairing.';

  @override
  String get createIncident => 'Create incident';

  @override
  String get gameServer => 'Game server';

  @override
  String get reason => 'Reason';

  @override
  String get create => 'Create';

  @override
  String serverNumber(Object number) {
    return 'Server $number';
  }

  @override
  String get newIncident => 'New incident';

  @override
  String get incidentInbox => 'Incident inbox';

  @override
  String get noIncidents => 'No incidents.';

  @override
  String get playerSearch => 'Player search';

  @override
  String get pairConnectionFirst => 'Pair a CRCON connection first.';

  @override
  String get crconConnection => 'CRCON connection';

  @override
  String get nameOrPlayerId => 'Name or player ID';

  @override
  String get unknown => 'Unknown';

  @override
  String get playerProfile => 'Player profile';

  @override
  String get unknownPlayer => 'Unknown player';

  @override
  String get offline => 'Offline';

  @override
  String get onlineNow => 'Online now';

  @override
  String get sessions => 'Sessions';

  @override
  String get bans => 'Bans';

  @override
  String get adminComments => 'Admin comments';

  @override
  String get flags => 'Flags';

  @override
  String get recentComments => 'Recent comments';

  @override
  String get incident => 'Incident';

  @override
  String get incidentUnavailable => 'Incident unavailable';

  @override
  String reporter(String name) {
    return 'Reporter: $name';
  }

  @override
  String target(String name) {
    return 'Target: $name';
  }

  @override
  String assigned(String name) {
    return 'Assigned: $name';
  }

  @override
  String get notSet => 'not set';

  @override
  String get notLinked => 'not linked';

  @override
  String get nobody => 'nobody';

  @override
  String get claim => 'Claim';

  @override
  String get release => 'Release';

  @override
  String get reassign => 'Reassign';

  @override
  String get resolve => 'Resolve';

  @override
  String get dismiss => 'Dismiss';

  @override
  String get reopen => 'Reopen';

  @override
  String get addNote => 'Add note';

  @override
  String get linkPlayer => 'Link player';

  @override
  String get playerActions => 'Player actions';

  @override
  String get linkPlayerFirst =>
      'Link a unique player in CRCON before using player actions.';

  @override
  String get message => 'Message';

  @override
  String get punish => 'Punish';

  @override
  String get comment => 'Comment';

  @override
  String get kick => 'Kick';

  @override
  String get tempBan => 'Temporary ban';

  @override
  String get timeline => 'Timeline';

  @override
  String get addPrivateNote => 'Add private admin note';

  @override
  String get note => 'Note';

  @override
  String get save => 'Save';

  @override
  String get linkTargetPlayer => 'Link target player';

  @override
  String get playerName => 'Player name';

  @override
  String get playerId => 'Player ID';

  @override
  String get link => 'Link';

  @override
  String get reassignIncident => 'Reassign incident';

  @override
  String get crconUsername => 'CRCON username';

  @override
  String get confirm => 'Confirm';

  @override
  String get adminComment => 'Admin comment';

  @override
  String get requiredReason => 'Required reason';

  @override
  String get inbox => 'Inbox';

  @override
  String get players => 'Players';

  @override
  String get connectionsShort => 'Connections';

  @override
  String get language => 'Language';

  @override
  String get german => 'Deutsch';

  @override
  String get english => 'English';

  @override
  String get cachedMayBeStale => 'Cached — may be stale';

  @override
  String get manual => 'manual';

  @override
  String get event => 'event';

  @override
  String get system => 'system';
}
