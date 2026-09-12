// Deterministic, fake-mode-only example for the live log repetition controls.
export function createLogStackDemo(size = 5) {
  const count = Math.max(2, Math.min(Number.parseInt(size, 10) || 5, 500));
  const stepMs = count > 60 ? 100 : 1000;
  const body =
    "Dein Squad hat keinen Offizier. Squads ohne Squadleader sind nicht erlaubt.";
  const makeMessage = (index, text = body) => ({
    action: "MESSAGE",
    timestamp_ms: Date.parse("2026-09-12T19:23:45Z") - index * stepMs,
    player_name_1: `Demo-Spieler ${index + 1}`,
    player_id_1: String(76561198000000001n + BigInt(index)),
    message: `Demo-Spieler ${index + 1}(${
      76561198000000001n + BigInt(index)
    }): ${text}`,
    sub_content: text,
  });
  return [
    ...Array.from({ length: count }, (_, index) => makeMessage(index)),
    makeMessage(count, "Bitte beachte die Serverregeln."),
    {
      ...makeMessage(count + 1, "Hallo Squad!"),
      action: "CHAT[Team][Allies]",
      team: "Allies",
    },
    makeMessage(count + 2),
    ...Array.from({ length: 102 }, (_, index) =>
      makeMessage(index + count + 3, `Einzelmeldung ${index + 1}`)
    ),
  ];
}
