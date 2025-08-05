const { app, BrowserWindow, ipcMain, dialog, shell, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const WebSocket = require('ws');
const Store = require('electron-store');
const ModelManager = require('./model-manager');

// Initialize electron store for settings
const store = new Store();

class NeuroLMDesktop {
  constructor() {
    this.mainWindow = null;
    this.webSocket = null;
    this.isConnected = false;
    this.userId = null;
    this.serverUrl = store.get('serverUrl', 'ws://localhost:5000');
    this.installedModels = store.get('installedModels', []);
    this.modelManager = new ModelManager();
    this.isOfflineMode = store.get('offlineMode', true);
  }

  createWindow() {
    this.mainWindow = new BrowserWindow({
      width: 1200,
      height: 800,
      minWidth: 800,
      minHeight: 600,
      icon: path.join(__dirname, '../assets/icon.png'),
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        enableRemoteModule: false,
        preload: path.join(__dirname, 'preload.js')
      },
      titleBarStyle: 'default',
      show: false,
      title: 'NeuroLM Desktop - Personal AI Assistant'
    });

    // Set up application menu
    this.createApplicationMenu();

    // Load the main interface
    this.mainWindow.loadFile(path.join(__dirname, 'index.html'));

    // Show window when ready
    this.mainWindow.once('ready-to-show', () => {
      this.mainWindow.show();
      this.detectHardware();
      this.initializeLocalModels();
    });

    // Handle window closed
    this.mainWindow.on('closed', () => {
      this.mainWindow = null;
      if (this.webSocket) {
        this.webSocket.close();
      }
      if (this.modelManager) {
        this.modelManager.stopOllama();
      }
    });

    // Development tools in dev mode
    if (process.argv.includes('--dev')) {
      this.mainWindow.webContents.openDevTools();
    }
  }

  async detectHardware() {
    const os = require('os');
    
    const hardwareInfo = {
      platform: os.platform(),
      arch: os.arch(),
      totalMemory: Math.round(os.totalmem() / (1024 * 1024 * 1024)), // GB
      cpus: os.cpus().length,
      cpuModel: os.cpus()[0]?.model || 'Unknown'
    };

    // Try to detect GPU (basic detection)
    try {
      const { execSync } = require('child_process');
      if (os.platform() === 'win32') {
        const gpuInfo = execSync('wmic path win32_VideoController get name', { encoding: 'utf8' });
        hardwareInfo.gpu = gpuInfo.split('\n')[1]?.trim() || 'Unknown';
      } else if (os.platform() === 'darwin') {
        const gpuInfo = execSync('system_profiler SPDisplaysDataType | grep "Chipset Model"', { encoding: 'utf8' });
        hardwareInfo.gpu = gpuInfo.split(':')[1]?.trim() || 'Unknown';
      } else {
        hardwareInfo.gpu = 'Detection not available';
      }
    } catch (error) {
      hardwareInfo.gpu = 'Detection failed';
    }

    // Send hardware info to renderer
    this.mainWindow.webContents.send('hardware-detected', hardwareInfo);
    
    // Store hardware info
    store.set('hardwareInfo', hardwareInfo);
  }

  async connectToServer() {
    return new Promise((resolve, reject) => {
      try {
        this.webSocket = new WebSocket(`${this.serverUrl}/ws/desktop`);
        
        this.webSocket.on('open', () => {
          this.isConnected = true;
          this.mainWindow.webContents.send('connection-status', { connected: true });
          
          // Send registration data
          const registrationData = {
            type: 'register',
            data: {
              app_version: app.getVersion(),
              os_info: `${process.platform} ${process.arch}`,
              hardware_info: store.get('hardwareInfo', {}),
              local_models: this.installedModels
            }
          };
          
          this.webSocket.send(JSON.stringify(registrationData));
          resolve();
        });

        this.webSocket.on('message', (data) => {
          try {
            const message = JSON.parse(data.toString());
            this.handleServerMessage(message);
          } catch (error) {
            console.error('Error parsing message:', error);
          }
        });

        this.webSocket.on('close', () => {
          this.isConnected = false;
          this.mainWindow.webContents.send('connection-status', { connected: false });
        });

        this.webSocket.on('error', (error) => {
          console.error('WebSocket error:', error);
          this.isConnected = false;
          this.mainWindow.webContents.send('connection-status', { connected: false });
          reject(error);
        });

      } catch (error) {
        reject(error);
      }
    });
  }

  handleServerMessage(message) {
    switch (message.type) {
      case 'model_download_request':
        this.handleModelDownload(message.data);
        break;
      case 'chat_request':
        this.handleChatRequest(message.data);
        break;
      case 'model_list_request':
        this.sendInstalledModels();
        break;
      default:
        console.log('Unknown message type:', message.type);
    }
  }

  async handleModelDownload(data) {
    const { modelId, modelConfig } = data;
    
    // Send download progress to renderer
    this.mainWindow.webContents.send('model-download-start', { modelId, config: modelConfig });
    
    try {
      // Simulate model download (replace with actual implementation)
      await this.downloadModel(modelId, modelConfig);
      
      // Add to installed models
      this.installedModels.push({
        id: modelId,
        config: modelConfig,
        installedAt: new Date().toISOString()
      });
      
      store.set('installedModels', this.installedModels);
      
      // Notify renderer and server
      this.mainWindow.webContents.send('model-download-complete', { modelId });
      
      if (this.webSocket && this.isConnected) {
        this.webSocket.send(JSON.stringify({
          type: 'model_installed',
          data: { modelId, success: true }
        }));
      }
      
    } catch (error) {
      console.error('Model download failed:', error);
      this.mainWindow.webContents.send('model-download-error', { modelId, error: error.message });
      
      if (this.webSocket && this.isConnected) {
        this.webSocket.send(JSON.stringify({
          type: 'model_installed',
          data: { modelId, success: false, error: error.message }
        }));
      }
    }
  }

  async downloadModel(modelId, modelConfig) {
    // This is a placeholder for actual model download implementation
    // In a real implementation, this would:
    // 1. Download model files from the specified URL
    // 2. Set up local inference engine (like Ollama)
    // 3. Install and configure the model
    
    return new Promise((resolve, reject) => {
      // Simulate download progress
      let progress = 0;
      const progressInterval = setInterval(() => {
        progress += Math.random() * 10;
        if (progress >= 100) {
          progress = 100;
          clearInterval(progressInterval);
          this.mainWindow.webContents.send('model-download-progress', { modelId, progress: 100 });
          resolve();
        } else {
          this.mainWindow.webContents.send('model-download-progress', { modelId, progress: Math.round(progress) });
        }
      }, 500);
    });
  }

  handleChatRequest(data) {
    // Handle chat requests with local models
    // This would integrate with the local inference engine
    this.mainWindow.webContents.send('chat-request', data);
  }

  sendInstalledModels() {
    if (this.webSocket && this.isConnected) {
      this.webSocket.send(JSON.stringify({
        type: 'installed_models',
        data: { models: this.installedModels }
      }));
    }
  }
}

// Create desktop app instance
const desktopApp = new NeuroLMDesktop();

// App event handlers
app.whenReady().then(() => {
  desktopApp.createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      desktopApp.createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// IPC handlers
ipcMain.handle('connect-to-server', async (event, serverUrl) => {
  if (serverUrl) {
    desktopApp.serverUrl = serverUrl;
    store.set('serverUrl', serverUrl);
  }
  
  try {
    await desktopApp.connectToServer();
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('get-installed-models', () => {
  return desktopApp.installedModels;
});

ipcMain.handle('get-hardware-info', () => {
  return store.get('hardwareInfo', {});
});

ipcMain.handle('open-external', async (event, url) => {
  shell.openExternal(url);
});

ipcMain.handle('show-save-dialog', async () => {
  const result = await dialog.showSaveDialog(desktopApp.mainWindow, {
    filters: [
      { name: 'Text Files', extensions: ['txt'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  });
  return result;
});

// Model management IPC handlers
ipcMain.handle('get-all-models', () => {
  return desktopApp.modelManager.getAllModels();
});

ipcMain.handle('download-model', async (event, modelId) => {
  return new Promise((resolve, reject) => {
    desktopApp.modelManager.downloadModel(modelId, (progress) => {
      desktopApp.mainWindow.webContents.send('model-download-progress', progress);
    }).then(resolve).catch(reject);
  });
});

ipcMain.handle('run-local-model', async (event, modelId, prompt, options) => {
  try {
    const response = await desktopApp.modelManager.runModel(modelId, prompt, options);
    return { success: true, response };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('get-offline-mode', () => {
  return desktopApp.isOfflineMode;
});

ipcMain.handle('set-offline-mode', (event, enabled) => {
  desktopApp.isOfflineMode = enabled;
  store.set('offlineMode', enabled);
  return enabled;
});

  createApplicationMenu() {
    const template = [
      {
        label: 'File',
        submenu: [
          {
            label: 'New Chat',
            accelerator: 'CmdOrCtrl+N',
            click: () => {
              this.mainWindow.webContents.send('new-chat');
            }
          },
          {
            label: 'Open Chat History',
            accelerator: 'CmdOrCtrl+O',
            click: () => {
              this.mainWindow.webContents.send('open-history');
            }
          },
          { type: 'separator' },
          {
            label: 'Exit',
            accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
            click: () => {
              app.quit();
            }
          }
        ]
      },
      {
        label: 'Models',
        submenu: [
          {
            label: 'Manage Models',
            click: () => {
              this.mainWindow.webContents.send('open-model-manager');
            }
          },
          {
            label: 'Download New Model',
            click: () => {
              this.mainWindow.webContents.send('download-model-dialog');
            }
          },
          { type: 'separator' },
          {
            label: 'Offline Mode',
            type: 'checkbox',
            checked: this.isOfflineMode,
            click: (menuItem) => {
              this.isOfflineMode = menuItem.checked;
              store.set('offlineMode', this.isOfflineMode);
              this.mainWindow.webContents.send('offline-mode-changed', this.isOfflineMode);
            }
          }
        ]
      },
      {
        label: 'View',
        submenu: [
          { role: 'reload' },
          { role: 'forceReload' },
          { role: 'toggleDevTools' },
          { type: 'separator' },
          { role: 'resetZoom' },
          { role: 'zoomIn' },
          { role: 'zoomOut' },
          { type: 'separator' },
          { role: 'togglefullscreen' }
        ]
      },
      {
        label: 'Window',
        submenu: [
          { role: 'minimize' },
          { role: 'close' }
        ]
      },
      {
        label: 'Help',
        submenu: [
          {
            label: 'About NeuroLM Desktop',
            click: () => {
              dialog.showMessageBox(this.mainWindow, {
                type: 'info',
                title: 'About NeuroLM Desktop',
                message: 'NeuroLM Desktop v1.0.0',
                detail: 'Personal AI Assistant with Local Model Support\n\nRun powerful AI models directly on your computer for privacy and offline access.'
              });
            }
          },
          {
            label: 'Learn More',
            click: () => {
              shell.openExternal('https://neurolm.repl.co');
            }
          }
        ]
      }
    ];

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
  }

  async initializeLocalModels() {
    try {
      this.mainWindow.webContents.send('status-update', { 
        message: 'Initializing AI models...', 
        type: 'info' 
      });

      const success = await this.modelManager.initializeOllama();
      
      if (success) {
        const models = this.modelManager.getAllModels();
        this.mainWindow.webContents.send('models-loaded', models);
        this.mainWindow.webContents.send('status-update', { 
          message: 'AI models ready', 
          type: 'success' 
        });
      } else {
        this.mainWindow.webContents.send('status-update', { 
          message: 'Warning: Some models may not be available', 
          type: 'warning' 
        });
      }
    } catch (error) {
      console.error('Error initializing models:', error);
      this.mainWindow.webContents.send('status-update', { 
        message: 'Error loading AI models', 
        type: 'error' 
      });
    }
  }
}