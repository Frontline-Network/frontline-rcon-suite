// French operator documentation. Keep operational and permission guidance aligned with content.js.
export const frenchHelp = {
  updates: {
    title: "Mises à jour et historique des modifications",
    summary: "Consulter les modifications de la version installée directement dans RCON.",
    body: `### Canal de mise à jour
Ouvrez **Canal de mise à jour** dans le menu du compte ou la navigation pour lire les notes de cette installation. Aurora propose aussi un lien en bas de sa navigation principale. La version actuelle est indiquée et l’historique contient les versions stables précédentes. La recherche porte sur les titres, versions et textes.

### Après le déploiement
Une nouvelle version GitHub n’apparaît que lorsque **le frontend et le backend utilisent la même version publiée**. Un déploiement incomplet, une version de développement ou une version inconnue affiche une explication. Un lien direct ne contourne pas cette vérification. L’historique ne prouve pas la date d’installation des versions précédentes.

### Nouveautés
Certaines versions présentent un aperçu avec une fonction principale et jusqu’à deux améliorations. Il utilise votre thème et votre langue ; **DE / EN / FR** change la langue de l’application. L’aperçu ne s’ouvre pas au-dessus d’un formulaire ou d’une autre boîte de dialogue.

Il apparaît une fois par compte et par version. Cet état est enregistré sur le serveur et partagé entre les appareils. **Plus tard** reporte le rappel de 24 heures, jusqu’à votre prochaine visite de la vue d’ensemble. Rouvrez-le avec **Nouveautés** dans le menu du compte ou le canal de mise à jour. Son état est indépendant de la lecture des notes. Si les textes de présentation requis ne sont pas disponibles, les notes normales restent accessibles.

### État de lecture
**Nouveau pour vous** indique la version actuelle jusqu’à ce que vous la marquiez comme lue. Cet état est mémorisé dans ce navigateur pour votre compte et cette adresse RCON. Lire les notes ne modifie aucun paramètre et n’installe rien.

### Sans compte GitHub
Les notes du dépôt privé sont affichées dans RCON. Votre connexion RCON habituelle suffit. Les liens du dépôt, images externes et identifiants ne sont pas chargés. Les notes conservent la langue de la version publiée.`,
  },
  start: {
    title: "Prise en main et navigation",
    summary: "Choisir un serveur, trouver les vues et appliquer les modifications en toute sécurité.",
    body: `### Choisir le bon serveur
Avant toute action, vérifiez le serveur sélectionné et l’état de la connexion. Les données en direct et les actions concernent le serveur actif. L’administration des utilisateurs et l’apparence personnelle ont leur propre portée.

### Trouver la vue adaptée
- **En direct :** surveillez les joueurs, les événements et la répartition des équipes pendant une manche.
- **Modération :** utilisez les fiches des joueurs et les listes noires pour le suivi et les sanctions.
- **Gestion du jeu :** modifiez les cartes, la rotation, les votes et les paramètres du serveur.
- **Automatisation :** configurez les automods et les règles. L’équilibreur possède également sa propre vue.
- **Historique :** consultez les journaux, les actions exécutées et les manches terminées.

La recherche dans l’en-tête permet de trouver les pages. Dans le thème Aurora, l’icône de menu à gauche ouvre la navigation ; vos raccourcis QuickIcons se trouvent en dessous.

### Appliquer les modifications
Chaque formulaire applique ses modifications avec son bouton d’enregistrement ou d’application. Avant de confirmer, vérifiez la portée affichée, surtout pour les changements de carte, les actions sur les joueurs et les actions groupées. Une notification de réussite confirme l’application ; modifier une valeur ne suffit pas.

### Fonctions absentes
Les actions disponibles dépendent de vos autorisations et des capacités du serveur de jeu. Une action grisée ou une page absente n’indique donc pas nécessairement une erreur d’affichage.`,
  },
  moderation: {
    title: "Opérations en direct et modération",
    summary: "Trouver les joueurs, examiner les incidents et agir de manière adaptée.",
    body: `### Traiter un incident
1. Ouvrez **En direct** et utilisez les filtres pour trouver les joueurs ou événements concernés.
2. Ouvrez la fiche du joueur et vérifiez son nom, son identifiant, son équipe et les journaux pertinents. Des noms similaires ne suffisent pas à confirmer l’identité.
3. Choisissez l’action appropriée selon la situation et vos autorisations : message, punition, expulsion, changement d’équipe ou bannissement.
4. Vérifiez la cible, le motif et, le cas échéant, la durée avant de confirmer.
5. Vérifiez le résultat et consignez les informations utiles dans la fiche du joueur.

### Expulsions, bannissements et listes noires
Une **expulsion** retire un joueur de la session en cours. Un **bannissement temporaire** empêche son retour pendant la durée indiquée ; un **bannissement permanent** dure jusqu’à sa levée. Une **liste noire** gère des entrées et leurs règles dans CRCON. Supprimer une entrée ne lève pas nécessairement un bannissement déjà présent sur le serveur : utilisez l’action de débannissement prévue à cet effet.

### Équilibreur automatique
Consultez son état, la situation des équipes et les actions proposées dans sa vue. Le modèle **Modérateur** permet d’examiner et d’exécuter les propositions. Modifier sa configuration nécessite des autorisations supplémentaires.

### Historique et filtres
Les filtres en direct modifient l’affichage, pas les événements enregistrés. Pour les incidents plus anciens, utilisez les fiches des joueurs et les journaux historiques. Le journal d’audit enregistre les actions administratives qui prennent en charge cette fonction.`,
  },
  maps: {
    title: "Cartes et gestion des manches",
    summary: "Comprendre les changements de carte, la rotation, les votes et les paramètres de jeu.",
    body: `### Carte actuelle et prochaine carte
La carte actuelle correspond à la partie en cours ; la prochaine indique l’étape prévue. Vérifiez si l’action change la carte immédiatement ou prépare un changement ultérieur. Un changement immédiat interrompt la manche.

### Rotation et vote de carte
La **rotation** définit l’ordre des cartes. La **liste blanche** limite les cartes autorisées dans le processus concerné. **Votemap** contrôle le vote de carte et son résultat. L’ordre aléatoire et le vote peuvent modifier la carte suivante.
1. Vérifiez le serveur sélectionné et les cartes disponibles.
2. Modifiez la rotation ou les règles de vote dans la rubrique correspondante.
3. Enregistrez et vérifiez l’état du vote ou la séquence des cartes.

### Objectifs, météo et durées
La disponibilité et l’effet dépendent du jeu et du serveur. Lisez les indications de chaque paramètre. Un réglage enregistré peut ne prendre effet qu’au prochain état de jeu approprié.

### Quel rôle choisir ?
**Gestion des parties** comprend cartes, rotation, votes, objectifs, météo, durées des manches et de l’échauffement, messages de bienvenue et campagnes. Ajoutez **Modérateur** pour les expulsions, bannissements et autres sanctions.`,
  },
  messages: {
    title: "Messages et automatisation",
    summary: "Utiliser les messages de bienvenue, les annonces et les campagnes.",
    body: `### Choisir le type de message
- **Message direct :** envoyé à un joueur sélectionné.
- **Message de bienvenue :** modifie le texte d’accueil du serveur.
- **Annonce :** gère le texte diffusé sur tout le serveur.
- **Campagnes :** envoient des messages selon le public, les horaires et les conditions.

### Préparer une campagne
1. Choisissez le type de campagne et modifiez son texte et ses conditions.
2. Vérifiez les variables disponibles et l’aperçu ; elles diffèrent selon le type de message.
3. Vérifiez le public, les délais et les règles de pause lorsqu’ils sont disponibles.
4. Utilisez les messages de test avec attention : ils sont réellement envoyés au joueur sélectionné.
5. Enregistrez la configuration et vérifiez l’état de l’envoi ou les journaux.

En mode test du **cycle de vie VIP**, les publics et journaux sont créés sans envoi automatique. Un message de test explicitement déclenché reste envoyé.

### Règles automatiques
Les automods et les paramètres automatiques peuvent modifier le déroulement du jeu. Vérifiez leurs conditions, leur activation et les chevauchements éventuels. L’aperçu, la validation et l’enregistrement ont des rôles distincts : une validation réussie n’active pas automatiquement une règle.`,
  },
  roles: {
    title: "Utilisateurs, rôles et autorisations",
    summary: "Configurer des groupes à partir de modèles et comprendre les accès effectifs.",
    body: `### Créer un rôle
1. Ouvrez **Administration → Groupes → Ajouter** et choisissez un nom explicite.
2. Sélectionnez un modèle et lisez sa description. Sa sélection affiche d’abord uniquement un aperçu.
3. Cliquez sur **Appliquer le modèle** : ses autorisations s’ajoutent à la sélection actuelle.
4. Combinez les modèles ou ajustez les autorisations individuelles. Vérifiez puis cliquez sur **Enregistrer**.
5. Ouvrez le compte utilisateur, attribuez-lui le groupe et enregistrez aussi le compte.

### Modèles disponibles
| Modèle | Fonctions |
| --- | --- |
| Lecture seule | Consulter les données en direct, les fiches des joueurs, les listes de bannissement et l’historique. |
| Support | Envoyer aussi des messages, ajouter des commentaires et gérer la liste de surveillance des joueurs. |
| Modérateur | Expulser, punir, bannir temporairement ou définitivement, débannir, agir sur les équipes et escouades et gérer les listes noires et signalements. Examiner et exécuter les propositions de l’équilibreur. |
| Gestion des parties | Contrôler les cartes, la rotation, l’ordre aléatoire, les objectifs, la météo, les durées et le vote de carte. Gérer les messages de bienvenue, les annonces et les campagnes. |

**Modérateur + Gestion des parties** combine les actions sur les joueurs et la gestion du jeu. Ces modèles ne donnent pas accès à l’administration des utilisateurs, à la console RCON brute ou à l’attribution VIP. La configuration de l’équilibreur ne fait pas non plus partie du modèle Modérateur.

Les modèles sont des points de départ. Leur modification ne change pas les groupes déjà enregistrés. Une nouvelle application ajoute des autorisations sans en supprimer.

### Sélection multiple
La sélection générale agit sur toutes les autorisations actuellement filtrées. Chaque catégorie possède aussi sa sélection, même repliée. Une recherche limite les actions groupées aux résultats correspondants ; effacez-la pour modifier toute la sélection. Seul **Enregistrer** applique les modifications.

### Cumul des autorisations
Les droits effectifs d’un compte réunissent ceux de **tous ses groupes et les droits attribués directement**. Retirer un droit direct ne supprime pas celui accordé par un groupe.
- **Compte actif :** autorise la connexion ; un compte inactif ne peut pas se connecter.
- **Accès à l’administration (staff) :** autorise l’entrée dans l’administration, sous réserve des droits de modèle nécessaires. Il n’accorde pas automatiquement tous les droits RCON.
- **Superutilisateur :** possède toutes les autorisations. Ce statut n’est pas nécessaire aux modérateurs ordinaires.

### Mot de passe et récupération
Dans **Menu utilisateur → Modifier le mot de passe**, changez votre propre mot de passe. Le formulaire affiche les règles applicables. Vous restez connecté dans ce navigateur ; les autres sessions deviennent invalides.

Depuis la page de connexion, **Mot de passe oublié ?** permet de demander un lien valable 30 minutes, invalidé après utilisation. Un compte actif disposant d’un mot de passe local et d’une adresse accessible est nécessaire. Vérifiez les courriers indésirables et contactez un administrateur si aucun message n’arrive. La réponse ne révèle pas si une adresse est enregistrée.

Pour les administrateurs : configurez SMTP et activez **CRCON_PASSWORD_RESET_ENABLED**. **CRCON_PUBLIC_URL** fixe l’adresse HTTPS des liens. Les champs SMTP figurent dans **default.env** ; placez les identifiants dans le fichier privé **.env**. Le port 587 utilise généralement TLS et le port 465 SSL. Recréez ensuite les conteneurs backend avec la configuration Compose mise à jour. Tant que la configuration manque, la récupération est indiquée comme indisponible.

### Une action reste indisponible
Vérifiez la description des autorisations et la référence API : certaines actions exigent plusieurs droits simultanément. Vérifiez tous les groupes attribués, enregistrez et rechargez la vue de l’utilisateur concerné.`,
  },
  appearance: {
    title: "Thème, couleurs et QuickIcons",
    summary: "Personnaliser l’interface et les raccourcis.",
    body: `### Modifier le thème et les couleurs
1. Ouvrez **Apparence** dans la navigation ou le menu utilisateur.
2. Choisissez **Aurora** ou **Vanguard**, puis le style de couleur.
3. Aurora propose six styles : rose, bleu glacier, émeraude, ambre, améthyste et ardoise.
4. Choisissez le mode clair, sombre ou système. Vous pouvez aussi adapter les couleurs aux troubles de la vision des couleurs.
5. Vérifiez l’aperçu immédiat puis enregistrez. **Annuler** restaure l’apparence précédente.

L’apparence est liée à votre compte. Si un backend ancien ne peut pas enregistrer ces préférences, la boîte de dialogue précise qu’elles seront stockées localement dans le navigateur.

En mode sombre, l’image de fond statique suit le style choisi et ne contient aucune animation. Le mode clair conserve son fond clair.

### Personnaliser les QuickIcons
Dans Aurora, utilisez le bouton en pointillés **Personnaliser** sous les raccourcis. Recherchez les pages souhaitées, choisissez vos favoris, classez-les avec les flèches et enregistrez.

Les QuickIcons affichent uniquement les destinations accessibles. Si un compte perd une autorisation, le raccourci correspondant est masqué. L’icône de menu au-dessus du séparateur donne toujours accès à toute la navigation.

### Petits écrans
Ouvrez la navigation avec l’icône de menu. Certaines barres du bureau ne sont pas affichées en permanence sur téléphone. La documentation est aussi accessible depuis le menu utilisateur.`,
  },
  troubleshooting: {
    title: "Questions fréquentes et erreurs",
    summary: "Comprendre les droits manquants, les données périmées et les échecs d’enregistrement.",
    body: `### Pourquoi puis-je voir une page sans rien modifier ?
Les autorisations de lecture et de modification sont distinctes. Certaines pages regroupent des fonctions soumises à des droits différents. Voir une page ne garantit pas l’accès à toutes ses actions.

### Pourquoi les données ne sont-elles pas à jour ?
Vérifiez le serveur sélectionné, l’état de la connexion et l’heure de la dernière mise à jour. Une vue déconnectée ou une liste filtrée vide ne signifie pas que le serveur de jeu est vide. Effacez les filtres pour identifier la cause.

### Pourquoi ma modification n’a-t-elle pas été enregistrée ?
Lisez l’erreur et vérifiez les champs obligatoires, les plages de valeurs et vos droits. Une session expirée nécessite une nouvelle connexion. Si le résultat d’une action serveur est incertain, vérifiez d’abord l’état réel avant de la répéter.

### Pourquoi un utilisateur conserve-t-il un droit retiré ?
D’autres groupes ou des droits directs peuvent accorder le même accès. Les superutilisateurs disposent de tous les droits indépendamment de la sélection affichée. Vérifiez le compte dans son ensemble.

### Quelles informations aident au diagnostic ?
Notez la page, le serveur, l’heure, l’erreur exacte et les étapes permettant de reproduire le problème. Précisez si l’erreur survient au chargement, à la validation ou à l’enregistrement. Ne mettez ni clé API ni mot de passe dans les captures d’écran ou rapports.`,
  },
};
