import assert from 'node:assert/strict';
import { mkdir, readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium } from 'playwright';

const require = createRequire(import.meta.url);
const { validateSelection } = require('../desktop/setup-model.cjs');
const plugins = JSON.parse(await readFile(new URL('../plugins.json', import.meta.url), 'utf8'));
const catalog = { versions: ['4.5.15', '5.0.8', '5.1.8', '5.2.4', '5.3.0'], plugins };
const output = resolve('node_modules/setup-ui-evidence');
await mkdir(output, { recursive: true });
const browser = await chromium.launch();
try {
  for (const [locale, viewport] of [['en-US', { width: 1280, height: 900 }],
    ['es-ES', { width: 800, height: 600 }]]) {
    const context = await browser.newContext({ locale, viewport });
    const errors = [];
    const selections = [];
    await context.exposeBinding('captureSetup', (_source, selection) => {
      selections.push(validateSelection(selection, catalog.versions, plugins));
      return { accepted: true };
    });
    await context.addInitScript(value => {
      window.portableSetup = { catalog: async () => value,
        start: selection => window.captureSetup(selection), cancel: async () => {} };
    }, catalog);
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(pathToFileURL(resolve('desktop/setup.html')).href);
    await page.locator('#install').waitFor({ state: 'visible' });
    await page.waitForFunction(() => !document.querySelector('#install').disabled);
    assert.equal(await page.locator('#moodlia-plugin').isChecked(), true);
    assert.equal(await page.locator('#format_onetopic').isChecked(), false);
    await page.locator('#format_onetopic').check();
    await page.locator('#moodle-version').selectOption('5.3.0');
    assert.equal(await page.locator('#format_onetopic').isDisabled(), true);
    assert.equal(await page.locator('#format_onetopic').isChecked(), false);
    await page.screenshot({ path: resolve(output, `${locale}-incompatible.png`), fullPage: true });
    await page.locator('#moodle-version').selectOption('4.5.15');
    await page.locator('#format_onetopic').check();
    await page.locator('#moodlia-plugin').uncheck();
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    assert.equal(await page.locator('html').getAttribute('lang'), locale.startsWith('es') ? 'es' : 'en');
    await page.screenshot({ path: resolve(output, `${locale}-selected.png`), fullPage: true });
    await page.locator('#install').click();
    await page.waitForFunction(() => document.querySelector('#install').disabled);
    assert.deepEqual(selections, [{ version: '4.5.15', moodlia: false, plugins: ['format_onetopic'] }]);
    assert.deepEqual(errors, []);
    await context.close();
  }
  console.log('PASS: English/Spanish setup, version changes, compatibility, independent plugins and validated submission.');
  console.log('Scope: real Chromium UI with a synthetic desktop bridge; no Moodle installation or workspace mutation.');
} finally {
  await browser.close();
}
