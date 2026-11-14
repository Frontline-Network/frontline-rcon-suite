const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

test('French permission controls cover every static translated label', () => {
  const context = {window: {}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, 'permission-fr.js'), 'utf8'), context);
  const catalog = context.window.CRCONPermissionFrench;
  const picker = fs.readFileSync(path.join(__dirname, 'permission-picker.js'), 'utf8');
  const wizard = fs.readFileSync(path.join(__dirname, 'permission-wizard.js'), 'utf8');
  const patterns = [
    [picker, /\bt\("[^"\n]*",\s*"([^"\n]*)"\)/g],
    [wizard, /\bt\(\s*'([^'\n]*)',\s*'([^'\n]*)'\)/g],
  ];
  let count = 0;
  for (const [source, pattern] of patterns) {
    for (const match of source.matchAll(pattern)) {
      const english = match[match.length - 1];
      assert.ok(catalog[english], `Missing French permission text: ${english}`);
      count++;
    }
  }
  assert.ok(count > 80, `Expected meaningful coverage, found ${count}`);
});
