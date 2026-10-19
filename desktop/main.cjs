const { app, BrowserWindow, dialog, Menu, shell } = require('electron');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

let window;
let backend;
let stopping = false;
let backendStopped = false;
app.setPath('userData', path.join(app.getPath('appData'), 'MoodlIA'));
const root = app.isPackaged ? path.join(process.resourcesPath, 'portable') : path.join(__dirname, '..', 'build', 'portable');
// Course data survives application updates and uninstallation.
const workspace = process.env.MOODLIA_WORKSPACE || path.join(app.getPath('userData'), 'workspace');
const home = 'http://127.0.0.1:8787';

const ownsLock = app.requestSingleInstanceLock();
if (!ownsLock) app.quit();
app.on('second-instance', () => { if (window) { window.restore(); window.focus(); } });

async function start() {
  window = new BrowserWindow({ width: 1280, height: 900, minWidth: 800, minHeight: 600,
    title: 'MoodlIA', webPreferences: { nodeIntegration: false, contextIsolation: true, sandbox: true } });
  await window.loadFile(path.join(__dirname, 'loading.html'));
  const menu = Menu.buildFromTemplate([
    { label: 'MoodlIA', submenu: [
      { label: 'Moodle home', click: () => window.loadURL(home) },
      { label: 'Connection files', click: () => shell.openPath(path.join(workspace, 'connection')) },
      { label: 'Course exports', click: () => shell.openPath(path.join(workspace, 'exports')) },
      { label: 'Workspace folder', click: () => shell.openPath(workspace) },
      { label: 'Basic instructions', click: () => shell.openPath(path.join(root, 'docs', 'QUICKSTART.md')) },
      { type: 'separator' }, { role: 'quit' }
    ] },
    { label: 'Edit', submenu: [{ role: 'undo' }, { role: 'redo' }, { type: 'separator' },
      { role: 'cut' }, { role: 'copy' }, { role: 'paste' }, { role: 'selectAll' }] },
    { label: 'View', submenu: [{ role: 'reload' }, { role: 'resetZoom' }, { role: 'zoomIn' }, { role: 'zoomOut' }, { role: 'togglefullscreen' }] }
  ]);
  Menu.setApplicationMenu(menu);
  const arguments = ['--desktop', '--workspace', workspace];
  if (!fs.existsSync(path.join(workspace, 'data', 'config.json'))) {
    const versions = JSON.parse(fs.readFileSync(path.join(root, 'versions.json'), 'utf8'));
    const selection = await dialog.showMessageBox(window, {
      type: 'question', title: 'Create your local Moodle',
      message: 'Choose a Moodle version',
      detail: 'Use a version compatible with your destination Moodle. Your only account will be teacher, with administrator permissions. This choice applies to this workspace.',
      buttons: [...versions.map(version => 'Moodle ' + version), 'Cancel'],
      defaultId: 0, cancelId: versions.length,
      checkboxLabel: 'Install MoodlIA plugin', checkboxChecked: true
    });
    if (selection.response === versions.length) { app.quit(); return; }
    arguments.push('--moodle-version', versions[selection.response]);
    if (!selection.checkboxChecked) arguments.push('--without-plugin');
  }
  const executable = path.join(root, 'moodlia-backend' + (process.platform === 'win32' ? '.exe' : ''));
  backend = spawn(executable, arguments, { cwd: root, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
  let output = '';
  let ready = false;
  backend.stdout.on('data', chunk => {
    output = (output + chunk.toString()).slice(-32000);
    if (!ready && output.includes('Ready: ' + home)) {
      ready = true;
      if (!stopping) window.loadURL(home);
    }
  });
  // Errors are deliberately not sent to Moodle's renderer or remote pages.
  backend.stderr.on('data', () => {});
  backend.on('error', error => {
    backendStopped = true;
    dialog.showErrorBox('MoodlIA could not start', 'The bundled backend could not be launched. ' + error.code);
    app.quit();
  });
  backend.on('exit', code => {
    backendStopped = true;
    if (!stopping && code !== 0) {
      dialog.showErrorBox('MoodlIA could not start',
        'Your files have been preserved. Check data/logs in your workspace. Another application may be using port 8787.\n\nWorkspace: ' + workspace);
    }
    app.quit();
  });
  function localUrl(url) {
    try { return new URL(url).origin === home; } catch { return false; }
  }
  function openExternal(url) {
    try { if (['https:', 'http:'].includes(new URL(url).protocol)) shell.openExternal(url); } catch {}
  }
  window.webContents.on('will-navigate', (event, url) => {
    if (!localUrl(url)) { event.preventDefault(); openExternal(url); }
  });
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (localUrl(url)) window.loadURL(url); else openExternal(url);
    return { action: 'deny' };
  });
  window.webContents.session.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
  // Save course backups through the ordinary native save dialog.
  window.webContents.session.on('will-download', (_event, item) => {
    item.setSaveDialogOptions({ defaultPath: path.join(workspace, 'exports', path.basename(item.getFilename())) });
  });
}

app.on('before-quit', event => {
  if (backend && !backendStopped) {
    event.preventDefault();
    if (!stopping) {
      stopping = true;
      if (window && !window.isDestroyed()) window.setTitle('MoodlIA — saving and stopping…');
      backend.stdin.write('stop\n');
      backend.stdin.end();
    }
  }
});
app.on('window-all-closed', () => app.quit());
app.whenReady().then(() => { if (ownsLock) return start(); }).catch(error => {
  dialog.showErrorBox('MoodlIA setup failed', error.message);
  app.quit();
});
