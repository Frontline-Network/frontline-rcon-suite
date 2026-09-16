import assert from "node:assert/strict";
import test from "node:test";
import i18next from "i18next";
import { translateOperatorMessage } from "./operator-messages.js";
import { operatorMessageEntries, operatorMessagesDe, operatorMessagesEn } from "./locales/operator-messages.js";

async function translator(language) {
  const instance = i18next.createInstance();
  await instance.init({ lng: language, fallbackLng: false, resources: { de: { translation: { operatorMessages: operatorMessagesDe } }, en: { translation: { operatorMessages: operatorMessagesEn } } }, interpolation: { escapeValue: false } });
  return instance.t.bind(instance);
}

test("every fixed backend message has English and German presentation", async () => {
  const en = await translator("en"), de = await translator("de");
  for (const [key, source, english] of operatorMessageEntries) {
    if (source.includes("{{")) continue;
    assert.equal(translateOperatorMessage(source, en), english, key);
    assert.equal(translateOperatorMessage(source, de), source, key);
  }
  assert.equal(new Set(operatorMessageEntries.map(([key]) => key)).size, operatorMessageEntries.length);
});

test("parameterized messages preserve player names, squads and technical details", async () => {
  const en = await translator("en");
  const cases = [
    ["Müller: Test; <Player>: Drei-Karten-Schutzfrist", "Müller: Test; <Player>: three-map protection period"],
    ["Müller: Squad Äpfel soll zusammenbleiben", "Müller: squad Äpfel should stay together"],
    ["Squad Süd hat sich seit dem Vorschlag verändert", "Squad Süd has changed since the proposal"],
    ["freiwillig; keinem Squad zugewiesen", "volunteer; not assigned to a squad"],
    ["freiwillig; Squad Leader", "volunteer; Squad Leader"],
    ["Rolle mortarobserver wurde fälschlich als unbekannt statt infantry klassifiziert", "Role mortarobserver was incorrectly classified as unknown instead of infantry"],
    ["Müller: Squad unbekannt soll zusammenbleiben", "Müller: squad unbekannt should stay together"],
    ["Interner Fehler: socket timeout; trace-id=17", "Internal error: socket timeout; trace-id=17"],
    ["Spielerdaten sind unvollständig; Mindestspielerzahl ist nicht erreicht", "Player data is incomplete; The minimum player count has not been reached"],
    ["Führungsrolle mortarobserver wurde nicht als Leader erkannt", "Leadership role mortarobserver was not recognized as a leader"],
  ];
  for (const [source, expected] of cases) assert.equal(translateOperatorMessage(source, en), expected);
});

test("unknown messages and user content are not heuristically rewritten", async () => {
  const en = await translator("en");
  for (const source of ["!admin der Commander redet nicht", "Müller", "Kein eigener Text wird übersetzt", "User comment; Autobalancer ist deaktiviert", "freiwillig; mein eigener Grund", "", null, undefined]) {
    assert.equal(translateOperatorMessage(source, en), source);
  }
});

test("backend evidence context and legacy English API failures follow UI language", async () => {
  const en = await translator("en"), de = await translator("de");
  assert.equal(translateOperatorMessage("Kein Nachweis für Streamsniping oder Ghosting.", en), "This is not evidence of stream sniping or ghosting.");
  assert.equal(translateOperatorMessage("Proposal is no longer eligible for approval", de), "Der Vorschlag kann nicht mehr freigegeben werden");
  assert.equal(translateOperatorMessage("Incident is no longer active", en), "The incident is no longer active");
});
