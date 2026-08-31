import i18n from "@/i18n";

const resources = {
  de: {
    changeWorkbench: {
      eyebrow: "Karten & Spielbetrieb",
      title: "Karte wechseln",
      subtitle:
        "Prüfe die laufende Runde und löse einen sofortigen Kartenwechsel kontrolliert für den ausgewählten Server aus.",
      liveState: "Aktueller Kartenstatus",
      switchNow: "Jetzt wechseln",
      catalogTitle: "Kartenkatalog",
      catalogDescription: "Suche gezielt nach Karte, Spielmodus oder Umgebung.",
      selectMap: "{{map}} für den sofortigen Kartenwechsel auswählen",
      immediateAction: "Unmittelbare Serveraktion",
      playersAffected: "Betroffene Spieler",
      countdown: "Vorlauf",
      seconds: "{{count}} Sekunden",
      targetServer: "Zielserver",
      confirmSwitch: "Kartenwechsel starten",
    },
    rotationWorkbench: {
      eyebrow: "Karten & Spielbetrieb",
      subtitle:
        "Stelle Rotation und feste Kartenfolge als prüfbaren Entwurf zusammen und veröffentliche Änderungen bewusst.",
      navigation: "Bereiche der Kartenrotation",
      builderTabDescription: "Rotation zusammenstellen",
      sequenceTabDescription: "Feste Reihenfolge planen",
      settingsTabDescription: "Ausspielung prüfen",
      filters: "Karten filtern",
      searchLabel: "Karte oder Karten-ID",
      resetFilters: "Zurücksetzen",
      results: "{{count}} Ergebnisse",
      catalogTab: "Katalog",
      draftTab: "Entwurf",
      catalogTitle: "Kartenkatalog",
      catalogDescription: "Varianten suchen, filtern und dem Entwurf hinzufügen.",
      draftTitle: "Unveröffentlichter Entwurf",
      draftDescription:
        "Die Reihenfolge wird erst nach dem Speichern auf dem Server aktiv.",
      draftState: "{{count}} Karten sind im aktuellen Entwurf enthalten.",
      duplicateNotice:
        "{{count}} doppelte Einträge sind als bewusste Gewichtung im Entwurf enthalten.",
      emptyDraftNotice:
        "Der Entwurf ist leer. Speichern würde die bestehende Kartenliste auf dem Server vollständig leeren.",
      unsavedChanges: "Ungespeicherter Entwurf",
      changesPending: "Reihenfolge wurde verändert",
      saved: "Entwurf entspricht dem Serverstand",
      publish: "Entwurf veröffentlichen",
      orderHint:
        "Per Ziehen oder mit den Pfeiltasten anordnen. Doppelte Karten bleiben möglich.",
      dragHint: "Ziehen oder mit der Tastatur verschieben",
      moveMap: "{{map}} verschieben",
      moveUp: "Eine Position nach oben",
      moveDown: "Eine Position nach unten",
      moveUpNamed: "{{map}} eine Position nach oben verschieben",
      moveDownNamed: "{{map}} eine Position nach unten verschieben",
      addNamed: "{{map}} zum Entwurf hinzufügen",
      rotationSaved: "Kartenrotation gespeichert.",
      rotationDraftTitle: "Rotationsentwurf",
      rotationDraftDescription:
        "Diese Reihenfolge läuft zyklisch und kann Karten mehrfach enthalten.",
      publishRotation: "Rotation veröffentlichen",
      sequenceDraftDescription:
        "Diese feste Kartenfolge wird vor der normalen Rotation abgearbeitet.",
      publishSequence: "Kartenfolge veröffentlichen",
      behaviorEyebrow: "Ausspielung",
      behaviorTitle: "Verhalten der Rotation",
      behaviorDescription:
        "Lege fest, ob der Server die veröffentlichte Reihenfolge beibehält oder pro Durchlauf mischt.",
      shuffleActive: "Bei jedem Durchlauf zufällig mischen",
      shuffleInactive: "Veröffentlichte Reihenfolge beibehalten",
      mode: "Modus",
      random: "Zufällig",
      fixed: "Feste Reihenfolge",
      modeDetail: "Wirkt ab dem nächsten Rotationsdurchlauf",
      rotationSize: "Rotation",
      mapsCount: "{{count}} Karten",
      rotationSizeDetail: "Aktuell veröffentlichter Serverstand",
      preview: "Vorschau",
      previewDetail: "Erste Einträge der Rotation",
      nextFiveTitle: "Vorschau der nächsten fünf Karten",
      nextFiveDescription:
        "Bei fester Reihenfolge zeigt die Vorschau den Beginn der veröffentlichten Rotation.",
      nextFiveShuffleDescription:
        "Bei aktiver Mischung ist dies eine Orientierung; die tatsächliche Reihenfolge wird vom Server zufällig bestimmt.",
      noPreview: "Veröffentliche zuerst mindestens eine Karte in der Rotation.",
      settingsChangesPending: "Ausspielung wurde verändert",
      settingsSaved: "Ausspielung entspricht dem Serverstand",
      settingsStateDescription:
        "Änderungen werden erst nach dem Speichern für den nächsten Rotationsdurchlauf wirksam.",
      saveSettings: "Ausspielung speichern",
    },
  },
  en: {
    changeWorkbench: {
      eyebrow: "Maps & game operations",
      title: "Change map",
      subtitle:
        "Review the live round and trigger an immediate map change on the selected server with clear impact context.",
      liveState: "Current map state",
      switchNow: "Switch now",
      catalogTitle: "Map catalog",
      catalogDescription: "Find a map by name, game mode, or environment.",
      selectMap: "Select {{map}} for an immediate map change",
      immediateAction: "Immediate server action",
      playersAffected: "Players affected",
      countdown: "Lead time",
      seconds: "{{count}} seconds",
      targetServer: "Target server",
      confirmSwitch: "Start map change",
    },
    rotationWorkbench: {
      eyebrow: "Maps & game operations",
      subtitle:
        "Build the rotation and fixed sequence as a reviewable draft, then publish changes deliberately.",
      navigation: "Map rotation sections",
      builderTabDescription: "Build the rotation",
      sequenceTabDescription: "Plan a fixed sequence",
      settingsTabDescription: "Review playback",
      filters: "Filter maps",
      searchLabel: "Map or map ID",
      resetFilters: "Reset",
      results: "{{count}} results",
      catalogTab: "Catalog",
      draftTab: "Draft",
      catalogTitle: "Map catalog",
      catalogDescription: "Search, filter, and add variants to the draft.",
      draftTitle: "Unpublished draft",
      draftDescription: "The order becomes active on the server only after saving.",
      draftState: "The current draft contains {{count}} maps.",
      duplicateNotice:
        "{{count}} duplicate entries remain in the draft as intentional weighting.",
      emptyDraftNotice:
        "The draft is empty. Saving would remove the entire existing map list from the server.",
      unsavedChanges: "Unpublished draft",
      changesPending: "The order has changed",
      saved: "Draft matches the server",
      publish: "Publish draft",
      orderHint:
        "Reorder by dragging or with the arrow controls. Duplicate maps remain supported.",
      dragHint: "Drag or move with the keyboard",
      moveMap: "Move {{map}}",
      moveUp: "Move up one position",
      moveDown: "Move down one position",
      moveUpNamed: "Move {{map}} up one position",
      moveDownNamed: "Move {{map}} down one position",
      addNamed: "Add {{map}} to the draft",
      rotationSaved: "Map rotation saved.",
      rotationDraftTitle: "Rotation draft",
      rotationDraftDescription:
        "This order repeats cyclically and may contain a map more than once.",
      publishRotation: "Publish rotation",
      sequenceDraftDescription:
        "This fixed sequence is played before the regular rotation resumes.",
      publishSequence: "Publish sequence",
      behaviorEyebrow: "Playback",
      behaviorTitle: "Rotation behavior",
      behaviorDescription:
        "Choose whether the server keeps the published order or shuffles each cycle.",
      shuffleActive: "Shuffle randomly on every cycle",
      shuffleInactive: "Keep the published order",
      mode: "Mode",
      random: "Random",
      fixed: "Fixed order",
      modeDetail: "Takes effect on the next rotation cycle",
      rotationSize: "Rotation",
      mapsCount: "{{count}} maps",
      rotationSizeDetail: "Currently published server state",
      preview: "Preview",
      previewDetail: "First entries in the rotation",
      nextFiveTitle: "Preview the next five maps",
      nextFiveDescription:
        "With a fixed order, this previews the start of the published rotation.",
      nextFiveShuffleDescription:
        "With shuffle enabled this is only a guide; the server determines the actual order at random.",
      noPreview: "Publish at least one map in the rotation first.",
      settingsChangesPending: "Playback has changed",
      settingsSaved: "Playback matches the server",
      settingsStateDescription:
        "Changes take effect for the next rotation cycle only after saving.",
      saveSettings: "Save playback",
    },
  },
};

for (const [language, maps] of Object.entries(resources)) {
  i18n.addResourceBundle(language, "translation", { maps }, true, true);
}
