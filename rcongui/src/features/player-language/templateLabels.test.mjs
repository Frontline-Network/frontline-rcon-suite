import test from 'node:test';
import assert from 'node:assert/strict';
import { templateLabel, templateSection, translationStatus } from './templateLabels.js';
import { workbenchDE, workbenchEN, workbenchFR } from '../../i18n/locales/player-language-workbench.js';

const automod = {
  no_leader: ['warning','punish','kick'], solo_tank: ['warning','punish','kick'],
  level: ['warning','punish','kick','force_kick','min_level','max_level','violation','announcement'],
  seeding: ['warning','punish','kick','announcement','disallowed_roles.violation','disallowed_weapons.violation','enforce_cap_fight.violation'],
  name: ['kick'], vac: ['reason'], teamkill: ['reason'], windows_store: ['reason'],
};
for (const [language, copy] of Object.entries({de:workbenchDE,en:workbenchEN,fr:workbenchFR})) {
  const t = (key, options) => key.replace(/^playerLanguages\./,'').split('.').reduce((value,part)=>value?.[part],copy) ?? options?.defaultValue ?? key;
  test(`every existing automated template has a readable ${language} name`, () => {
    const templates=Object.entries(automod).flatMap(([module,actions])=>actions.map(action=>({key:`automod.${module}.${action}`,group:'automod'})));
    templates.push(...Object.keys(workbenchEN.balanceLabels).map(key=>({key:'autobalancer.'+key,group:'autobalancer'})),
      ...['message_header','message_footer'].map(key=>({key:'messages.'+key,group:'moderation'})));
    for (const item of templates) {
      const label=templateLabel(item,t);
      assert.ok(label.length>3,item.key);
      assert.ok(!label.includes('playerLanguages.') && !label.includes(item.key),item.key);
      assert.notEqual(label,copy.unnamedTemplate,item.key);
      assert.ok(!templateSection(item,t).includes('playerLanguages.'),item.key);
    }
    assert.equal(templateLabel({key:'manual:55',title:'Community rule'},t),'Community rule');
    assert.equal(templateLabel({key:'unknown:100'},t),copy.unnamedTemplate);
  });
}
test('review status takes priority over complete stale translations',()=>{
  const complete={source:'Original',translations:{de:'DE',en:'EN',fr:'FR'}};
  assert.equal(translationStatus(complete),'ready');
  assert.equal(translationStatus({...complete,needs_review:true}),'needsReview');
  assert.equal(translationStatus({source:'Original',translations:{de:'DE',en:'  '}}),'incomplete');
  assert.equal(translationStatus({source:'',translations:{}}),'unused');
});
