// Synthetic UI fixture only. Never bundle the private repository's real notes
// in frontend assets: production reads its authenticated backend endpoint.
export const updateChannelPreview = {
  status: "ready",
  installed_version: "v0.8.8",
  frontend_version: "v0.8.8",
  preview: true,
  reader_id: "preview-user",
  stale: false,
  checked_at: "2026-10-04T08:00:00Z",
  releases: [
    {
      tag_name: "v0.8.8",
      name: "Beispiel: Ein übersichtlicherer Arbeitsbereich",
      current: true,
      highlights: {
        schema_version: 1,
        title: { de: "Dein RCON. Dein Look.", en: "Your RCON. Your style." },
        description: {
          de: "Mit Aurora und Vanguard passt du deinen Arbeitsbereich an deinen Stil an. Wähle deine Farben und behalte im Spielbetrieb den Überblick.",
          en: "Make your workspace your own with Aurora and Vanguard. Choose your colours and keep match operations in clear view.",
        },
        image: "theme-collection",
        image_alt: {
          de: "Sechs überlappende RCON-Ansichten in unterschiedlichen Farbstilen.",
          en: "Six overlapping RCON dashboards in different colour styles.",
        },
        action: {
          id: "appearance",
          label: { de: "Darstellung öffnen", en: "Open appearance" },
        },
        items: [
          {
            icon: "shortcuts",
            title: {
              de: "Schnellzugriffe nach Maß",
              en: "Shortcuts that suit you",
            },
            description: {
              de: "Deine wichtigsten Seiten sind in Aurora nur einen Klick entfernt.",
              en: "Keep your most-used pages one click away in Aurora.",
            },
          },
          {
            icon: "book",
            title: {
              de: "Hilfe direkt im RCON",
              en: "Help, right in your RCON",
            },
            description: {
              de: "Antworten zur Bedienung und API findest du jetzt an einem Ort.",
              en: "Find guidance on everyday tasks and the API in one place.",
            },
          },
        ],
      },
      prerelease: false,
      published_at: "2026-10-01T21:16:05Z",
      body: "## Was sich verbessert hat\n\nDiese **Beispielnotiz** zeigt, wie ein aufgespieltes Update im RCON erscheint.\n\n- Klar gegliederte Einstellungen erleichtern die Orientierung.\n- Benutzer und Rollen lassen sich in einer gemeinsamen Verwaltung bearbeiten.\n- Hinweise zu Änderungen bleiben direkt im Arbeitsbereich lesbar.\n\n## Für euren Alltag\n\nDie vorhandenen Einstellungen bleiben erhalten. Ihr könnt den Versionsverlauf durchsuchen und später wieder aufrufen.\n\n[Interner Verweis](https://github.com/Frontline-Network/frontline-rcon-suite/pull/1) wird als Text dargestellt, ohne das private Repository zu öffnen.",
    },
    {
      tag_name: "v0.8.7",
      name: "Beispiel: Verbesserungen im Spielbetrieb",
      current: false,
      prerelease: false,
      published_at: "2026-09-20T14:10:06Z",
      body: "## Spielbetrieb\n\nBeispiel für einen älteren Changelog: verständlichere Hinweise bei der Moderation und eine übersichtlichere Statusanzeige.\n\n## Hinweise\n\nDer Versionsverlauf beschreibt frühere Releases. Er ist kein Protokoll darüber, wann diese Installation aktualisiert wurde.",
    },
    {
      tag_name: "v0.8.6",
      name: "Beispiel: Sprache und Bedienung",
      current: false,
      prerelease: false,
      published_at: "2026-09-16T23:28:30Z",
      body: "## Bedienung\n\nBeispiel für ergänzte englische Beschriftungen und vereinheitlichte Hinweise.",
    },
  ],
};
