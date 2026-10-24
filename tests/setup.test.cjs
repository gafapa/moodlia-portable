const assert = require('node:assert/strict');
const test = require('node:test');
const { validateSelection } = require('../desktop/setup-model.cjs');
const plugins = require('../plugins.json');
const versions = ['4.5.15', '5.0.8', '5.1.8', '5.2.4', '5.3.0'];

test('setup supports Moodle alone and an independent tabs plugin', () => {
  for (const selection of [
    { version: '5.3.0', moodlia: false, plugins: [] },
    { version: '4.5.15', moodlia: false, plugins: ['format_onetopic'] },
    { version: '5.1.8', moodlia: true, plugins: ['format_onetopic'] },
  ]) assert.deepEqual(validateSelection(selection, versions, plugins), selection);
});

test('setup rejects forged versions, options and unsupported plugin selections', () => {
  for (const selection of [null, {},
    { version: '../other', moodlia: true, plugins: [] },
    { version: '5.3.0', moodlia: true, plugins: ['format_onetopic'] },
    { version: '4.5.15', moodlia: 'false', plugins: [] },
    { version: '4.5.15', moodlia: true, plugins: ['../escape'] },
    { version: '4.5.15', moodlia: true, plugins: ['format_onetopic', 'format_onetopic'] },
  ]) assert.throws(() => validateSelection(selection, versions, plugins));
});
