import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_de.dart';
import 'app_localizations_en.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'generated/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('de'),
    Locale('en'),
  ];

  /// No description provided for @appTitle.
  ///
  /// In en, this message translates to:
  /// **'Frontline CRCON Admin'**
  String get appTitle;

  /// No description provided for @connections.
  ///
  /// In en, this message translates to:
  /// **'CRCON connections'**
  String get connections;

  /// No description provided for @pairCrcon.
  ///
  /// In en, this message translates to:
  /// **'Pair CRCON'**
  String get pairCrcon;

  /// No description provided for @pairFirst.
  ///
  /// In en, this message translates to:
  /// **'Pair your first CRCON installation.'**
  String get pairFirst;

  /// No description provided for @incidentNotifications.
  ///
  /// In en, this message translates to:
  /// **'Incident notifications'**
  String get incidentNotifications;

  /// No description provided for @revokeDeviceTitle.
  ///
  /// In en, this message translates to:
  /// **'Revoke this device?'**
  String get revokeDeviceTitle;

  /// No description provided for @revokeDeviceBody.
  ///
  /// In en, this message translates to:
  /// **'CRCON will invalidate its access and refresh tokens immediately.'**
  String get revokeDeviceBody;

  /// No description provided for @cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;

  /// No description provided for @revoke.
  ///
  /// In en, this message translates to:
  /// **'Revoke'**
  String get revoke;

  /// No description provided for @pairInstructions.
  ///
  /// In en, this message translates to:
  /// **'Open Mobile App in CRCON, create a QR code, then scan it here.'**
  String get pairInstructions;

  /// No description provided for @compareCode.
  ///
  /// In en, this message translates to:
  /// **'Compare this code with CRCON'**
  String get compareCode;

  /// No description provided for @approvePhone.
  ///
  /// In en, this message translates to:
  /// **'Approve the phone in the CRCON browser to finish pairing.'**
  String get approvePhone;

  /// No description provided for @createIncident.
  ///
  /// In en, this message translates to:
  /// **'Create incident'**
  String get createIncident;

  /// No description provided for @gameServer.
  ///
  /// In en, this message translates to:
  /// **'Game server'**
  String get gameServer;

  /// No description provided for @reason.
  ///
  /// In en, this message translates to:
  /// **'Reason'**
  String get reason;

  /// No description provided for @create.
  ///
  /// In en, this message translates to:
  /// **'Create'**
  String get create;

  /// No description provided for @serverNumber.
  ///
  /// In en, this message translates to:
  /// **'Server {number}'**
  String serverNumber(Object number);

  /// No description provided for @newIncident.
  ///
  /// In en, this message translates to:
  /// **'New incident'**
  String get newIncident;

  /// No description provided for @incidentInbox.
  ///
  /// In en, this message translates to:
  /// **'Incident inbox'**
  String get incidentInbox;

  /// No description provided for @noIncidents.
  ///
  /// In en, this message translates to:
  /// **'No incidents.'**
  String get noIncidents;

  /// No description provided for @playerSearch.
  ///
  /// In en, this message translates to:
  /// **'Player search'**
  String get playerSearch;

  /// No description provided for @pairConnectionFirst.
  ///
  /// In en, this message translates to:
  /// **'Pair a CRCON connection first.'**
  String get pairConnectionFirst;

  /// No description provided for @crconConnection.
  ///
  /// In en, this message translates to:
  /// **'CRCON connection'**
  String get crconConnection;

  /// No description provided for @nameOrPlayerId.
  ///
  /// In en, this message translates to:
  /// **'Name or player ID'**
  String get nameOrPlayerId;

  /// No description provided for @unknown.
  ///
  /// In en, this message translates to:
  /// **'Unknown'**
  String get unknown;

  /// No description provided for @playerProfile.
  ///
  /// In en, this message translates to:
  /// **'Player profile'**
  String get playerProfile;

  /// No description provided for @unknownPlayer.
  ///
  /// In en, this message translates to:
  /// **'Unknown player'**
  String get unknownPlayer;

  /// No description provided for @offline.
  ///
  /// In en, this message translates to:
  /// **'Offline'**
  String get offline;

  /// No description provided for @onlineNow.
  ///
  /// In en, this message translates to:
  /// **'Online now'**
  String get onlineNow;

  /// No description provided for @sessions.
  ///
  /// In en, this message translates to:
  /// **'Sessions'**
  String get sessions;

  /// No description provided for @bans.
  ///
  /// In en, this message translates to:
  /// **'Bans'**
  String get bans;

  /// No description provided for @adminComments.
  ///
  /// In en, this message translates to:
  /// **'Admin comments'**
  String get adminComments;

  /// No description provided for @flags.
  ///
  /// In en, this message translates to:
  /// **'Flags'**
  String get flags;

  /// No description provided for @recentComments.
  ///
  /// In en, this message translates to:
  /// **'Recent comments'**
  String get recentComments;

  /// No description provided for @incident.
  ///
  /// In en, this message translates to:
  /// **'Incident'**
  String get incident;

  /// No description provided for @incidentUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Incident unavailable'**
  String get incidentUnavailable;

  /// No description provided for @reporter.
  ///
  /// In en, this message translates to:
  /// **'Reporter: {name}'**
  String reporter(String name);

  /// No description provided for @target.
  ///
  /// In en, this message translates to:
  /// **'Target: {name}'**
  String target(String name);

  /// No description provided for @assigned.
  ///
  /// In en, this message translates to:
  /// **'Assigned: {name}'**
  String assigned(String name);

  /// No description provided for @notSet.
  ///
  /// In en, this message translates to:
  /// **'not set'**
  String get notSet;

  /// No description provided for @notLinked.
  ///
  /// In en, this message translates to:
  /// **'not linked'**
  String get notLinked;

  /// No description provided for @nobody.
  ///
  /// In en, this message translates to:
  /// **'nobody'**
  String get nobody;

  /// No description provided for @claim.
  ///
  /// In en, this message translates to:
  /// **'Claim'**
  String get claim;

  /// No description provided for @release.
  ///
  /// In en, this message translates to:
  /// **'Release'**
  String get release;

  /// No description provided for @reassign.
  ///
  /// In en, this message translates to:
  /// **'Reassign'**
  String get reassign;

  /// No description provided for @resolve.
  ///
  /// In en, this message translates to:
  /// **'Resolve'**
  String get resolve;

  /// No description provided for @dismiss.
  ///
  /// In en, this message translates to:
  /// **'Dismiss'**
  String get dismiss;

  /// No description provided for @reopen.
  ///
  /// In en, this message translates to:
  /// **'Reopen'**
  String get reopen;

  /// No description provided for @addNote.
  ///
  /// In en, this message translates to:
  /// **'Add note'**
  String get addNote;

  /// No description provided for @linkPlayer.
  ///
  /// In en, this message translates to:
  /// **'Link player'**
  String get linkPlayer;

  /// No description provided for @playerActions.
  ///
  /// In en, this message translates to:
  /// **'Player actions'**
  String get playerActions;

  /// No description provided for @linkPlayerFirst.
  ///
  /// In en, this message translates to:
  /// **'Link a unique player in CRCON before using player actions.'**
  String get linkPlayerFirst;

  /// No description provided for @message.
  ///
  /// In en, this message translates to:
  /// **'Message'**
  String get message;

  /// No description provided for @punish.
  ///
  /// In en, this message translates to:
  /// **'Punish'**
  String get punish;

  /// No description provided for @comment.
  ///
  /// In en, this message translates to:
  /// **'Comment'**
  String get comment;

  /// No description provided for @kick.
  ///
  /// In en, this message translates to:
  /// **'Kick'**
  String get kick;

  /// No description provided for @tempBan.
  ///
  /// In en, this message translates to:
  /// **'Temporary ban'**
  String get tempBan;

  /// No description provided for @timeline.
  ///
  /// In en, this message translates to:
  /// **'Timeline'**
  String get timeline;

  /// No description provided for @addPrivateNote.
  ///
  /// In en, this message translates to:
  /// **'Add private admin note'**
  String get addPrivateNote;

  /// No description provided for @note.
  ///
  /// In en, this message translates to:
  /// **'Note'**
  String get note;

  /// No description provided for @save.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get save;

  /// No description provided for @linkTargetPlayer.
  ///
  /// In en, this message translates to:
  /// **'Link target player'**
  String get linkTargetPlayer;

  /// No description provided for @playerName.
  ///
  /// In en, this message translates to:
  /// **'Player name'**
  String get playerName;

  /// No description provided for @playerId.
  ///
  /// In en, this message translates to:
  /// **'Player ID'**
  String get playerId;

  /// No description provided for @link.
  ///
  /// In en, this message translates to:
  /// **'Link'**
  String get link;

  /// No description provided for @reassignIncident.
  ///
  /// In en, this message translates to:
  /// **'Reassign incident'**
  String get reassignIncident;

  /// No description provided for @crconUsername.
  ///
  /// In en, this message translates to:
  /// **'CRCON username'**
  String get crconUsername;

  /// No description provided for @confirm.
  ///
  /// In en, this message translates to:
  /// **'Confirm'**
  String get confirm;

  /// No description provided for @adminComment.
  ///
  /// In en, this message translates to:
  /// **'Admin comment'**
  String get adminComment;

  /// No description provided for @requiredReason.
  ///
  /// In en, this message translates to:
  /// **'Required reason'**
  String get requiredReason;

  /// No description provided for @inbox.
  ///
  /// In en, this message translates to:
  /// **'Inbox'**
  String get inbox;

  /// No description provided for @players.
  ///
  /// In en, this message translates to:
  /// **'Players'**
  String get players;

  /// No description provided for @connectionsShort.
  ///
  /// In en, this message translates to:
  /// **'Connections'**
  String get connectionsShort;

  /// No description provided for @language.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get language;

  /// No description provided for @german.
  ///
  /// In en, this message translates to:
  /// **'Deutsch'**
  String get german;

  /// No description provided for @english.
  ///
  /// In en, this message translates to:
  /// **'English'**
  String get english;

  /// No description provided for @cachedMayBeStale.
  ///
  /// In en, this message translates to:
  /// **'Cached — may be stale'**
  String get cachedMayBeStale;

  /// No description provided for @manual.
  ///
  /// In en, this message translates to:
  /// **'manual'**
  String get manual;

  /// No description provided for @event.
  ///
  /// In en, this message translates to:
  /// **'event'**
  String get event;

  /// No description provided for @system.
  ///
  /// In en, this message translates to:
  /// **'system'**
  String get system;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['de', 'en'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'de':
      return AppLocalizationsDe();
    case 'en':
      return AppLocalizationsEn();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
