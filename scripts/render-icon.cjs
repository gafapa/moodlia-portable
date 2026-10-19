// Render the workspace's existing vector brand mark for native desktop packaging.
const { chromium } = require('playwright');
const fs = require('node:fs');
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 512, height: 512 } });
    await page.setContent('<style>html,body{margin:0;width:512px;height:512px}svg{display:block;width:512px;height:512px}</style>' +
      fs.readFileSync('desktop/icon.svg', 'utf8'));
    await page.screenshot({ path: 'desktop/icon.png', omitBackground: true });
  } finally { await browser.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
