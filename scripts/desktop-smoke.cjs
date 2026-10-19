const { _electron: electron } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const workspace = path.resolve(process.argv[2]);
  const application = await electron.launch({ args: process.argv[3] ? [] : ['.'],
    ...(process.argv[3] ? { executablePath: path.resolve(process.argv[3]) } : {}),
    env: { ...process.env, MOODLIA_WORKSPACE: workspace } });
  try {
    const page = await application.firstWindow();
    await page.waitForURL('http://127.0.0.1:8787/**', { timeout: 600000 });
    await page.context().clearCookies();
    await page.goto('http://127.0.0.1:8787/login/index.php');
    const config = JSON.parse(fs.readFileSync(path.join(workspace, 'data', 'config.json'), 'utf8'));
    page.on('request', request => {
      if (request.method() === 'POST' && new URL(request.url()).pathname === '/login/index.php') {
        const form = new URLSearchParams(request.postData() || '');
        fs.writeFileSync('build/login-request-check.json', JSON.stringify({
          username_matches: form.get('username') === 'teacher',
          password_matches: form.get('password') === config.password,
          login_token_present: Boolean(form.get('logintoken'))
        }, null, 2));
      }
    });
    if (await page.locator('#username').count()) {
      // Moodle replaces the password element when its visibility control finishes rendering.
      await page.locator('.toggle-sensitive-wrapper #password').waitFor({ state: 'attached' });
      await page.locator('#username').fill('teacher');
      await page.locator('#password').fill(config.password);
      await Promise.all([
        page.waitForURL(url => !url.pathname.includes('/login/'), { timeout: 60000 }).catch(async error => {
          fs.writeFileSync('build/login-failure.txt', await page.locator('body').innerText());
          await page.screenshot({ path: 'build/login-failure.png' });
          throw error;
        }),
        page.locator('#loginbtn').click()
      ]);
    }
    if (page.url().includes('/login/')) throw new Error('Teacher login failed');
    const configuration = await application.evaluate(({ BrowserWindow }) => {
      const preferences = BrowserWindow.getAllWindows()[0].webContents.getLastWebPreferences();
      return { sandbox: preferences.sandbox, contextIsolation: preferences.contextIsolation,
        nodeIntegration: preferences.nodeIntegration };
    });
    if (!configuration.sandbox || !configuration.contextIsolation || configuration.nodeIntegration) {
      throw new Error('Unsafe Electron renderer preferences');
    }
    await page.screenshot({ path: 'build/desktop-home.png' });
    fs.writeFileSync('build/desktop-evidence.json', JSON.stringify({
      login: 'passed', url: page.url(), renderer: configuration }, null, 2));
  } finally {
    // Use normal application quit so its backend can stop the database.
    const stopped = new Promise(resolve => application.process().once('exit', resolve));
    await application.evaluate(({ app }) => app.quit());
    await stopped;
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
