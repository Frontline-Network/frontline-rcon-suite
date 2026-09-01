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
};

export const getIntegrationWorkbenchCopy = (language) =>
  copy[String(language || "en").toLowerCase().startsWith("de") ? "de" : "en"];
