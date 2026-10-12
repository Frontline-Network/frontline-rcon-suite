const test = require('node:test');
const assert = require('node:assert/strict');
const {matches, bundleState, changes} = require('./permission-planner.js');

test('search matches multiple terms independent of order, accents and case', () => {
  assert.ok(matches('Konsolen-Admins: Liste und Spieler-IDs anzeigen', 'ANZEIGEN konsolen'));
  assert.ok(matches('Temporäre Sperre Größe', 'temporare grosse'));
  assert.ok(matches('Console admins Kennungen', 'kennungen console'));
  assert.ok(matches('anything', '  '));
  assert.equal(matches('Console admins', 'kick'), false);
});
test('bundle recognizes permissions combined from multiple groups and direct access', () => {
  const own = new Set(['menu']);
  const inherited = new Map([['list', ['support']], ['roles', ['junior']]]);
  const plan = bundleState({permissions:['menu','list','roles']}, own, inherited, new Set(['menu','list','roles']));
  assert.deepEqual(plan, {missing:[], unavailable:[], complete:true});
  assert.deepEqual([...own], ['menu']);
});
test('view bundle reports exactly the missing read permission, never action access', () => {
  const available = new Set(['menu','list','roles','kick']);
  const plan = bundleState({permissions:['menu','list','roles']}, new Set(['menu','roles']), new Map(), available);
  assert.deepEqual(plan.missing, ['list']);
  assert.equal(plan.complete, false);
});
test('partial catalogs do not silently offer incomplete bundles', () => {
  const plan = bundleState({permissions:['menu'], unavailable:['can_view_admin_ids']}, new Set(['menu']), new Map(), new Set(['menu']));
  assert.equal(plan.complete, false);
  assert.deepEqual(plan.unavailable, ['can_view_admin_ids']);
});
test('unavailable IDs are rejected even when present in the bundle payload', () => {
  assert.deepEqual(bundleState({permissions:['bad']}, new Set(), new Map(), new Set()).unavailable, ['bad']);
});
test('superusers require no additional direct grants', () => {
  const own = new Set();
  assert.equal(bundleState({permissions:['read']}, own, new Map(), new Set(['read']), true).complete, true);
  assert.equal(own.size, 0);
});
test('change review tracks added and removed rights without touching the baseline', () => {
  const initial = new Set(['read', 'internal']);
  assert.deepEqual(changes(initial, new Set(['read','write'])), {added:['write'], removed:['internal']});
  assert.deepEqual([...initial], ['read','internal']);
  assert.deepEqual(changes(initial, new Set(initial)), {added:[], removed:[]});
});
