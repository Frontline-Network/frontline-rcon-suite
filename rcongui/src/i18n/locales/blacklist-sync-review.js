export const blacklistSyncReviewCopy = {
  de: {
    title: "Sperrlisten-Synchronisation: Prüfung erforderlich",
    help: "Diese Änderung konnte auf diesem Spielserver nicht eindeutig bestätigt werden. Prüfe den tatsächlichen Sperrstatus und die aktuellen Sperrlisten und korrigiere den Spielserver bei Bedarf. Weitere Änderungen für diesen Server warten bis zur Bestätigung.",
    refresh: "Aktualisieren", empty: "Keine offenen Prüfungen.", operation: "Vorgang", details: "Einzelheiten", confirm: "Als geprüft markieren",
    overlap: "Mehrere Änderungen überschneiden sich.", uncertain: "Der Spielserver hat die Ausführung nicht eindeutig bestätigt.",
    confirmPrompt: "Hast du den Sperrstatus auf dem Spielserver und die aktuellen Sperrlisten geprüft? Die Bestätigung führt die Änderung nicht erneut aus und gibt nachfolgende Änderungen frei.",
    loadError: "Synchronisationsprüfungen konnten nicht geladen werden.", saveError: "Prüfung konnte nicht bestätigt werden.", more: "Weitere offene Prüfungen: {{count}}",
  },
  en: {
    title: "Blacklist synchronization: review required",
    help: "This change could not be confirmed on this game server. Check the actual ban status and current blacklists, and correct the game server if necessary. Later changes for this server wait until it is acknowledged.",
    refresh: "Refresh", empty: "No outstanding reviews.", operation: "Operation", details: "Details", confirm: "Mark as reviewed",
    overlap: "Several changes overlap.", uncertain: "The game server did not clearly confirm the action.",
    confirmPrompt: "Have you checked the ban status on the game server and the current blacklists? Acknowledging does not repeat this change and releases later changes.",
    loadError: "Could not load synchronization reviews.", saveError: "Could not acknowledge this review.", more: "More outstanding reviews: {{count}}",
  },
  fr: {
    title: "Synchronisation des listes noires : vérification requise",
    help: "Cette modification n’a pas pu être confirmée sur ce serveur de jeu. Vérifiez le statut réel du bannissement et les listes noires actuelles, puis corrigez le serveur de jeu si nécessaire. Les modifications suivantes attendent la confirmation.",
    refresh: "Actualiser", empty: "Aucune vérification en attente.", operation: "Opération", details: "Détails", confirm: "Marquer comme vérifié",
    overlap: "Plusieurs modifications se chevauchent.", uncertain: "Le serveur de jeu n’a pas confirmé clairement l’action.",
    confirmPrompt: "Avez-vous vérifié le statut du bannissement sur le serveur de jeu et les listes noires actuelles ? La confirmation ne répète pas cette modification et libère les suivantes.",
    loadError: "Impossible de charger les vérifications de synchronisation.", saveError: "Impossible de confirmer cette vérification.", more: "Autres vérifications en attente : {{count}}",
  },
};
