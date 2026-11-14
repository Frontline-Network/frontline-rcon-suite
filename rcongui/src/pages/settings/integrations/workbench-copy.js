const copy = {
  de: {
    filterLabel: "Kommunikationsmodule filtern",
    removeNamedEntry: (name) => `Eintrag ${name} entfernen`,
    keyLabel: "Name",
    newKeyLabel: "Neue Einstellung",
    newKeyHelp: "Technischen Namen ohne JSON-Syntax eingeben.",
    keyRequired: "Gib einen Namen für die Einstellung ein.",
    keyExists: "Diese Einstellung ist bereits vorhanden.",
    addSetting: "Einstellung hinzufügen",
    additionalSettingsLabel: "Weitere Einträge (Kompatibilität)",
  },
  en: {
    filterLabel: "Filter communication modules",
    removeNamedEntry: (name) => `Remove ${name}`,
    keyLabel: "Name",
    newKeyLabel: "New setting",
    newKeyHelp: "Enter the technical name without JSON syntax.",
    keyRequired: "Enter a name for the setting.",
    keyExists: "This setting already exists.",
    addSetting: "Add setting",
    additionalSettingsLabel: "Additional entries (compatibility)",
  },
  fr: {
    filterLabel: "Filtrer les modules de communication",
    removeNamedEntry: (name) => `Supprimer ${name}`,
    keyLabel: "Nom",
    newKeyLabel: "Nouveau paramètre",
    newKeyHelp: "Saisissez le nom technique sans syntaxe JSON.",
    keyRequired: "Saisissez un nom pour le paramètre.",
    keyExists: "Ce paramètre existe déjà.",
    addSetting: "Ajouter un paramètre",
    additionalSettingsLabel: "Entrées supplémentaires (compatibilité)",
  },
};

export const getIntegrationWorkbenchCopy = (language) => {
  const code = String(language || "en").toLowerCase().split("-")[0];
  return copy[code] || copy.en;
};
