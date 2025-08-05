const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // Model management
  downloadModel: (modelId) => ipcRenderer.invoke('download-model', modelId),
  getInstalledModels: () => ipcRenderer.invoke('get-installed-models'),
  runModel: (modelId, prompt) => ipcRenderer.invoke('run-model', modelId, prompt),
  deleteModel: (modelId) => ipcRenderer.invoke('delete-model', modelId),
  
  // System info
  getSystemInfo: () => ipcRenderer.invoke('get-system-info'),
  
  // Connection
  connectToServer: (url) => ipcRenderer.invoke('connect-to-server', url),
  getConnectionStatus: () => ipcRenderer.invoke('get-connection-status'),
  
  // Settings
  getSetting: (key) => ipcRenderer.invoke('get-setting', key),
  setSetting: (key, value) => ipcRenderer.invoke('set-setting', key, value),
  
  // Window controls
  minimizeWindow: () => ipcRenderer.invoke('minimize-window'),
  maximizeWindow: () => ipcRenderer.invoke('maximize-window'),
  closeWindow: () => ipcRenderer.invoke('close-window'),
  
  // Events
  onModelDownloadProgress: (callback) => {
    ipcRenderer.on('model-download-progress', callback);
  },
  onConnectionStatusChange: (callback) => {
    ipcRenderer.on('connection-status-change', callback);
  }
});