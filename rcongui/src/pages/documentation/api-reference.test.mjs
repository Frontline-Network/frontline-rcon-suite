import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  normalizeApiDocumentation,
  filterApiDocumentation,
  localizeApiDocumentation,
  apiEndpointPath,
} from "./api-reference.mjs";

const snapshot = JSON.parse(
  readFileSync(
    new URL("../../mirage/data/api-documentation.json", import.meta.url),
    "utf8"
  )
);

test("handles the actual backend introspection format, including methods and conjunctive permissions", () => {
  const docs = normalizeApiDocumentation(snapshot);
  assert.equal(docs.length, snapshot.length);
  const bans = docs.find((item) => item.endpoint === "get_bans");
  assert.deepEqual(bans.permissions.sort(), [
    "api.can_view_perma_bans",
    "api.can_view_temp_bans",
  ]);
  const message = docs.find((item) => item.endpoint === "message_player");
  assert.deepEqual(message.methods, ["POST"]);
  assert.equal(
    message.arguments.find((arg) => arg.name === "player_id").default,
    null
  );
  // The string 'None' is a Python default, not an absent default.
  assert.equal(
    message.arguments.find((arg) => arg.name === "player_name").default,
    "None"
  );
});

test("searches endpoint, parameter and permission names together, with an independent method filter", () => {
  const docs = normalizeApiDocumentation(snapshot);
  const result = filterApiDocumentation(
    docs,
    "MESSAGE_PLAYER can_message_players player_id",
    "POST"
  );
  assert(result.some((item) => item.endpoint === "message_player"));
  assert(
    !filterApiDocumentation(docs, "message_player", "GET").some(
      (item) => item.endpoint === "message_player"
    )
  );
  assert.equal(
    filterApiDocumentation(docs, "this_endpoint_does_not_exist", "").length,
    0
  );
});

test("rejects a failed or malformed payload instead of presenting it as an empty API", () => {
  assert.throws(() =>
    normalizeApiDocumentation({ failed: true, error: "Unavailable" })
  );
  assert.throws(() => normalizeApiDocumentation([null, { endpoint: 42 }]));
  assert.deepEqual(normalizeApiDocumentation([]), []);
});

test("older partial entries remain readable without inventing permissions or argument defaults", () => {
  const [entry] = normalizeApiDocumentation([
    {
      endpoint: "legacy",
      doc_string: null,
      arguments: { value: null },
      allowed_http_methods: [null, "get"],
      permissions_required: "not an array",
    },
  ]);
  assert.deepEqual(entry.methods, ["GET"]);
  assert.deepEqual(entry.permissions, []);
  assert.deepEqual(entry.arguments, [
    { name: "value", type: "", default: null },
  ]);
});

test("language changes localize the same catalog without losing technical notes or metadata", () => {
  const docs = normalizeApiDocumentation(snapshot);
  const german = localizeApiDocumentation(docs, "de-DE");
  const english = localizeApiDocumentation(docs, "en");
  const index = docs.findIndex((item) => item.endpoint === "get_bans");
  assert.equal(
    german[index].description,
    snapshot.find((item) => item.endpoint === "get_bans")
      .description_translations.de
  );
  assert.equal(
    english[index].description,
    docs[index].descriptionTranslations.en
  );
  assert.notEqual(german[index].description, english[index].description);
  assert.deepEqual(german[index].permissions, docs[index].permissions);
  const source = german.find((item) => item.endpoint === "clear_cache");
  assert.equal(
    source.technicalDescription,
    docs.find((item) => item.endpoint === "clear_cache").description
  );
  assert(german.every((item) => item.description));
});

test("German purpose searches and original technical searches both find the endpoint", () => {
  const docs = localizeApiDocumentation(
    normalizeApiDocumentation(snapshot),
    "de"
  );
  assert(
    filterApiDocumentation(docs, "Teamwechsel", "POST").some(
      (item) => item.endpoint === "switch_player_now"
    )
  );
  assert(
    filterApiDocumentation(docs, "excessively polling", "").some(
      (item) => item.endpoint === "clear_cache"
    )
  );
});

test("missing or malformed translations retain original documentation", () => {
  const docs = normalizeApiDocumentation([
    {
      endpoint: "legacy",
      doc_string: "Original",
      description_translations: { de: {}, en: null },
    },
    {
      endpoint: "partial",
      doc_string: "Technical notes",
      description_translations: { de: " ", en: "English explanation" },
    },
  ]);
  const [legacy, partial] = localizeApiDocumentation(docs, "de");
  assert.equal(legacy.description, "Original");
  assert.equal(legacy.technicalDescription, "");
  assert.equal(partial.description, "English explanation");
  assert.equal(partial.technicalDescription, "Technical notes");
  assert.equal(docs[1].description, "Technical notes");
});

test("WebSocket routes use their registered root rather than the HTTP API prefix", () => {
  const docs = normalizeApiDocumentation(snapshot);
  assert.equal(
    apiEndpointPath(
      docs.find((item) => item.endpoint === "ws/mobile/v1/incidents")
    ),
    "/ws/mobile/v1/incidents"
  );
  assert.equal(
    apiEndpointPath(docs.find((item) => item.endpoint === "get_status")),
    "/api/get_status"
  );
});
