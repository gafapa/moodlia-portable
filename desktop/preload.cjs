const { contextBridge, ipcRenderer } = require('electron');

if (location.protocol === 'file:' && location.pathname.endsWith('/setup.html')) {
  contextBridge.exposeInMainWorld('portableSetup', {
    catalog: () => ipcRenderer.invoke('portable:catalog'),
    start: selection => ipcRenderer.invoke('portable:start', selection),
    cancel: () => ipcRenderer.invoke('portable:cancel'),
  });
}
