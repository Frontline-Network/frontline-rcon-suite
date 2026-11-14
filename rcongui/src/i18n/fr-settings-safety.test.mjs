import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const { settings, records, settingEffect } = JSON.parse(readFileSync(new URL("./locales/fr-draft.json", import.meta.url), "utf8"));

test("French settings preserve critical reversibility and automation warnings", () => {
  assert.match(settings.consoleAdmins.undoRemoval, /Annuler la suppression/);
  assert.match(settings.consoleAdmins.confirmSaveHint, /immédiatement/);
  assert.match(settings.discordReports.aiSafety, /peut effectuer des expulsions/);
  assert.match(settings.discordReports.aiSafety, /autorisations appropriées/);
  assert.match(settings.discordReports.activateWithoutTest, /Aucun test n’a encore réussi/);
  assert.match(settings.mobile.pairingWarning, /une seule fois/);
  assert.match(settings.integrations.unsavedConfirmation, /Passer quand même/);
  assert.match(settings.configForms.noLeader.fields.dry_run.help, /ni punition ni expulsion/);
  assert.match(settings.configForms.noSoloTank.fields.number_of_punishments.help, /0.*empêcher l’expulsion/);
  assert.match(settings.configForms.noSoloTank.fields.number_of_punishments.help, /-1.*indéfiniment/);
  assert.match(settings.configForms.tkBans.title, /tirs alliés/);
  assert.match(settings.consoleAdmins.invalidImportRows, /{{count}} lignes seront ignorées/);
  assert.match(settings.consoleAdmins.invalidImportRows, /{{lines}}/);
  assert.match(settings.configForms.vacBans.summary.flags_other, /{{count}} marqueurs protégés/);
  assert.match(settings.configForms.vacBans.sections.exemptions.description, /Marqueurs/);
  assert.match(settings.configForms.noLeader.fields.notes_interval_seconds.help, /Délai entre deux vérifications invisibles/);
  assert.match(settings.configForms.noSoloTank.workbench.detection.skipped, /sans étape de confirmation supplémentaire/);
  assert.match(settingEffect.auditUnavailable, /dernier administrateur et les données de retour arrière/);
});

test("French records explain irreversible actions and moderation events", () => {
  assert.match(records.vips.uploadWarning, /remplace toutes les entrées VIP/);
  assert.match(records.vips.uploadWarning, /sauvegarde/);
  assert.match(records.blacklists.confirmDeleteDescription, /ne pourra pas être restaurée/);
  assert.match(records.blacklists.confirmExpireDescription, /immédiatement/);
  assert.equal(records.gameLogs.timeline.eventLabels.kill, "Élimination");
  assert.equal(records.auditLogs.emptyTitle, "Aucune entrée d’audit trouvée");
});
