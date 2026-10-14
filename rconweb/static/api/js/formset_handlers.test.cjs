const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

const source = readFileSync(path.join(__dirname, "formset_handlers.js"), "utf8");

function form({ state = "complete", value = "", field = true, crypto = true } = {}) {
    const input = field ? { value } : null;
    const listeners = new Map();
    const fields = new Map([["id_api_key", input]]);
    let generated = 0;
    const context = {
        document: {
            readyState: state,
            getElementById: (id) => fields.get(id),
            addEventListener: (name, callback) => listeners.set(name, callback),
        },
        window: crypto ? { crypto: { randomUUID: () => {
            generated++;
            return "00000000-0000-4000-8000-000000000001";
        } } } : {},
    };
    // No legacy window.uuidv4 library is present in the current admin template.
    vm.runInNewContext(source, context);
    return { input, fields, listeners, generated: () => generated };
}

test("standalone key field is filled without the removed UUID library", () => {
    const page = form();
    assert.equal(page.generated(), 1);
    assert.equal(page.input.value.length, 36);
});

test("initialization waits for DOMContentLoaded when needed", () => {
    const page = form({ state: "loading" });
    assert.equal(page.generated(), 0);
    page.listeners.get("DOMContentLoaded")();
    assert.equal(page.generated(), 1);
});

test("initialization also works after the DOM is interactive", () => {
    assert.equal(form({ state: "interactive" }).generated(), 1);
});

test("existing or manually entered keys are never overwritten", () => {
    const page = form({ value: "already-entered-key" });
    assert.equal(page.input.value, "already-entered-key");
    assert.equal(page.generated(), 0);
});

test("other admin forms without a key input do not throw", () => {
    assert.equal(form({ field: false }).generated(), 0);
});

test("new user inline gets a key, without replacing a filled inline", () => {
    const page = form({ field: false });
    const input = { value: "" };
    page.fields.set("id_djangoapikey_set-0-api_key", input);
    const event = { detail: { formsetName: "djangoapikey_set" }, target: { id: "djangoapikey_set-0" } };
    page.listeners.get("formset:added")(event);
    assert.equal(input.value.length, 36);
    page.listeners.get("formset:added")(event);
    assert.equal(page.generated(), 1);
});

test("unrelated inlines do not generate keys", () => {
    const page = form({ field: false });
    page.listeners.get("formset:added")({ detail: { formsetName: "steamplayer" } });
    assert.equal(page.generated(), 0);
});

test("missing secure crypto does not fall back to insecure randomness", () => {
    const page = form({ crypto: false });
    assert.equal(page.input.value, "");
    assert.equal(page.generated(), 0);
});
