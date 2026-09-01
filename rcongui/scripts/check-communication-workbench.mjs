import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) =>
  fs.readFileSync(path.join(root, relativePath), "utf8");

const editor = read(
  "src/pages/settings/integrations/IntegrationConfigEditor.jsx"
);
const hub = read("src/pages/settings/integrations/IntegrationsHub.jsx");
const registry = read("src/pages/settings/integrations/registry.jsx");
const detail = read("src/pages/settings/[configs]/detail.jsx");
const welcome = read(
  "src/pages/settings/welcome-message/WelcomeMessageWorkbench.jsx"
);
const campaigns = read(
  "src/pages/settings/broadcast-message/BroadcastCampaignWorkbench.jsx"
);

const requireText = (source, expected, message) => {
  if (!source.includes(expected)) throw new Error(message);
};

const rejectText = (source, rejected, message) => {
  if (source.includes(rejected)) throw new Error(message);
};

requireText(
  editor,
  "function KeyValueObjectField",
  "Dynamic integration objects must use guided key/value controls."
);
requireText(
  editor,
  '{ type: "object", additionalProperties: true }',
  "Complex legacy integration values must remain editable through nested guided controls."
);
requireText(
  editor,
  "const additionalValue = Object.fromEntries",
  "Schema-defined fields and additional compatibility entries must be separated."
);
requireText(
  editor,
  "workbenchCopy.additionalSettingsLabel",
  "Additional compatibility entries need a clear end-user label."
);
rejectText(
  editor,
  "function JsonObjectField",
  "The end-user integration workbench must not expose a JSON editor."
);
rejectText(
  editor,
  "JSON.parse(draft",
  "The end-user integration workbench must not parse hand-written JSON."
);
requireText(
  hub,
  'xs: "repeat(2, minmax(0, 1fr))"',
  "Mobile integration filters must remain fully visible in a two-column grid."
);
requireText(
  hub,
  'role="group"',
  "Integration filters must expose a labelled control group."
);
requireText(
  detail,
  "mergeConfigWithSchema",
  "Guided integration edits must retain unknown server fields."
);
requireText(
  detail,
  "<IntegrationConfigEditor",
  "Integration routes must use the shared connector editor."
);
requireText(
  welcome,
  "<SeedingWorkbenchLayout",
  "Welcome messages must use the shared communication workbench."
);
requireText(
  welcome,
  "<Preview message={message}",
  "Welcome messages must retain an in-game preview task."
);
requireText(
  campaigns,
  "<SeedingWorkbenchLayout",
  "Campaigns must use the shared communication workbench."
);
requireText(
  campaigns,
  "<ActivityPanel deliveryStatus={deliveryStatus}",
  "Campaigns must keep delivery activity visible."
);

const moduleCount = (registry.match(/\bslug:\s*"/g) || []).length;
if (moduleCount !== 11) {
  throw new Error(
    `Expected 11 communication modules in the compatibility registry, found ${moduleCount}.`
  );
}

console.log(
  "Communication workbench contract passed: guided dynamic settings, mobile filters, legacy preservation, previews and 11 integration routes stay connected."
);
