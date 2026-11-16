// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for French (`fr`).
class AppLocalizationsFr extends AppLocalizations {
  AppLocalizationsFr([String locale = 'fr']) : super(locale);

  @override
  String get appTitle => 'Administration Frontline CRCON';

  @override
  String get connections => 'Connexions CRCON';

  @override
  String get pairCrcon => 'Associer CRCON';

  @override
  String get pairFirst => 'Associez votre première installation CRCON.';

  @override
  String get incidentNotifications => 'Notifications d’incidents';

  @override
  String get revokeDeviceTitle => 'Révoquer cet appareil ?';

  @override
  String get revokeDeviceBody =>
      'CRCON invalidera immédiatement ses jetons d’accès et de renouvellement.';

  @override
  String get cancel => 'Annuler';

  @override
  String get revoke => 'Révoquer';

  @override
  String get pairInstructions =>
      'Dans CRCON, ouvrez « Configurer les applications », créez un code QR, puis scannez-le ici.';

  @override
  String get compareCode => 'Comparez ce code avec CRCON';

  @override
  String get approvePhone =>
      'Approuvez le téléphone dans le navigateur CRCON pour terminer l’association.';

  @override
  String get createIncident => 'Créer un incident';

  @override
  String get gameServer => 'Serveur de jeu';

  @override
  String get reason => 'Raison';

  @override
  String get create => 'Créer';

  @override
  String serverNumber(Object number) {
    return 'Serveur $number';
  }

  @override
  String get newIncident => 'Nouvel incident';

  @override
  String get incidentInbox => 'Boîte des incidents';

  @override
  String get noIncidents => 'Pas d\'incident.';

  @override
  String get playerSearch => 'Recherche de joueurs';

  @override
  String get pairConnectionFirst => 'Associez d’abord une connexion CRCON.';

  @override
  String get crconConnection => 'Connexion CRCON';

  @override
  String get nameOrPlayerId => 'Nom ou identifiant du joueur';

  @override
  String get unknown => 'Inconnu';

  @override
  String get playerProfile => 'Profil du joueur';

  @override
  String get unknownPlayer => 'Joueur inconnu';

  @override
  String get offline => 'Hors ligne';

  @override
  String get onlineNow => 'En ligne maintenant';

  @override
  String get sessions => 'Sessions';

  @override
  String get bans => 'Bannissements';

  @override
  String get adminComments => 'Commentaires d’administration';

  @override
  String get flags => 'Drapeaux';

  @override
  String get recentComments => 'Commentaires récents';

  @override
  String get incident => 'Incident';

  @override
  String get incidentUnavailable => 'Incident non disponible';

  @override
  String reporter(String name) {
    return 'Auteur du signalement : $name';
  }

  @override
  String target(String name) {
    return 'Cible : $name';
  }

  @override
  String assigned(String name) {
    return 'Attribué à : $name';
  }

  @override
  String get notSet => 'non défini';

  @override
  String get notLinked => 'non associé';

  @override
  String get nobody => 'personne';

  @override
  String get claim => 'Prendre en charge';

  @override
  String get release => 'Libérer';

  @override
  String get reassign => 'Réattribuer';

  @override
  String get resolve => 'Résoudre';

  @override
  String get dismiss => 'Rejeter';

  @override
  String get reopen => 'Rouvrir';

  @override
  String get addNote => 'Ajouter une note';

  @override
  String get linkPlayer => 'Associer le joueur';

  @override
  String get playerActions => 'Actions du joueur';

  @override
  String get linkPlayerFirst =>
      'Associez un joueur identifié de manière unique dans CRCON avant d’utiliser les actions sur le joueur.';

  @override
  String get message => 'Message';

  @override
  String get punish => 'Sanctionner';

  @override
  String get comment => 'Commentaire';

  @override
  String get kick => 'Expulser';

  @override
  String get tempBan => 'Bannissement temporaire';

  @override
  String get timeline => 'Chronologie';

  @override
  String get addPrivateNote => 'Ajouter une note privée d’administration';

  @override
  String get note => 'Note';

  @override
  String get save => 'Enregistrer';

  @override
  String get linkTargetPlayer => 'Associer le joueur ciblé';

  @override
  String get playerName => 'Nom du joueur';

  @override
  String get playerId => 'Identifiant du joueur';

  @override
  String get link => 'Lien';

  @override
  String get reassignIncident => 'Réattribuer l’incident';

  @override
  String get crconUsername => 'Nom d\'utilisateur CRCON';

  @override
  String get confirm => 'Confirmer';

  @override
  String get adminComment => 'Commentaire d’administration';

  @override
  String get requiredReason => 'Justification requise';

  @override
  String get inbox => 'Boîte de réception';

  @override
  String get players => 'Joueurs';

  @override
  String get connectionsShort => 'Connexions';

  @override
  String get language => 'Langue';

  @override
  String get german => 'Deutsch';

  @override
  String get english => 'Anglais';

  @override
  String get cachedMayBeStale =>
      'En cache — les données peuvent être anciennes';

  @override
  String get manual => 'manuel';

  @override
  String get event => 'événement';

  @override
  String get system => 'système';
}
