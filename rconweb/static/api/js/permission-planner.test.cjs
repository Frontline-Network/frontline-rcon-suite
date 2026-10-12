const test = require('node:test');
const assert = require('node:assert/strict');
const {matches, bundleState, changes, wizardPlan} = require('./permission-planner.js');

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

const workflows = [
  {id:'console', title:'Console', bundles:[
    {id:'console:0', permissions:['menu','list','roles']},
    {id:'console:1', permissions:['menu','list','roles','assign']},
    {id:'console:2', permissions:['menu','list','roles','remove']},
  ]},
  {id:'other', title:'Other view', bundles:[{id:'other:0', permissions:['list','other']} ]},
];
const available = new Set(['menu','list','roles','assign','remove','internal','other']);

test('wizard draft preserves every assignment with no answer or unchanged', () => {
  const own = new Set(['assign','internal']);
  assert.deepEqual(wizardPlan(workflows, {}, own, available).next, own);
  assert.deepEqual(wizardPlan(workflows, {console:{mode:'keep'}}, own, available).next, own);
});
test('view-only both completes read prerequisites and revokes actions, never internal rights', () => {
  const own = new Set(['menu','assign','remove','internal']);
  const plan = wizardPlan(workflows, {console:{mode:'read'}}, own, available);
  assert.deepEqual(plan.next, new Set(['menu','internal','list','roles']));
  assert.deepEqual(new Set(plan.removed), new Set(['assign','remove']));
  assert.deepEqual(own, new Set(['menu','assign','remove','internal']));
});
test('no-access revokes read and action rights of the answered area only', () => {
  const own = new Set(['menu','list','roles','assign','remove','internal']);
  assert.deepEqual(wizardPlan(workflows, {console:{mode:'none'}}, own, available).next, new Set(['internal']));
});
test('selected actions include prerequisites but never unchecked actions', () => {
  const plan = wizardPlan(workflows, {console:{mode:'custom',actions:['console:1']}}, new Set(['remove']), available);
  assert.deepEqual(plan.next, new Set(['menu','list','roles','assign']));
});
test('contradictory answers expose shared-permission conflicts', () => {
  const plan = wizardPlan(workflows, {console:{mode:'none'},other:{mode:'read'}}, new Set(), available);
  assert.deepEqual(plan.conflicts, [{id:'list',allow:['Other view'],deny:['Console']}]);
});
test('shared changes to skipped areas are visible for review', () => {
  const plan = wizardPlan(workflows, {console:{mode:'none'}}, new Set(['list','other']), available);
  assert.deepEqual(plan.affected, [{id:'other',title:'Other view',permissions:['list']}]);
});
test('unknown actions and unavailable required rights block the draft', () => {
  assert.deepEqual(wizardPlan(workflows, {console:{mode:'custom',actions:['evil']}}, new Set(), available).invalid, ['console']);
  assert.deepEqual(wizardPlan(workflows, {console:{mode:'read'}}, new Set(), new Set(['menu','roles'])).unavailable, ['list']);
  const partial = [{id:'missing',title:'Missing',bundles:[{id:'missing:0',permissions:['menu'],unavailable:['missing_code']}]}];
  assert.deepEqual(wizardPlan(partial, {missing:{mode:'read'}}, new Set(), available).unavailable, ['missing_code']);
});
test('revising a draft recomputes from the current selection without residual grants', () => {
  const own = new Set(['internal']);
  wizardPlan(workflows, {console:{mode:'custom',actions:['console:1']}}, own, available);
  assert.deepEqual(wizardPlan(workflows, {console:{mode:'keep'}}, own, available).next, own);
  assert.deepEqual(wizardPlan(workflows, {console:{mode:'read'}}, own, available).next, new Set(['internal','menu','list','roles']));
});
