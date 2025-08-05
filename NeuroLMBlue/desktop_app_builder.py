#!/usr/bin/env python3
"""
Desktop App Builder - Creates downloadable installers for NeuroLM Desktop
Builds cross-platform Electron applications with embedded AI models
"""

import os
import sys
import json
import subprocess
import shutil
import zipfile
import platform
from pathlib import Path
from typing import Dict, List, Optional
import requests
from datetime import datetime

class DesktopAppBuilder:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.desktop_app_dir = self.project_root / "desktop-app"
        self.build_dir = self.project_root / "builds"
        self.assets_dir = self.project_root / "static"
        
        # Ensure build directory exists
        self.build_dir.mkdir(exist_ok=True)
        
        # App metadata
        self.app_info = {
            "name": "NeuroLM Desktop",
            "version": "1.0.0",
            "description": "Run AI models locally with NeuroLM",
            "author": "NeuroLM",
            "homepage": "https://neurolm.repl.co"
        }
        
        # Platform configurations
        self.platforms = {
            "win32": {
                "platform": "win32",
                "arch": "x64",
                "icon": "icon.ico",
                "installer": "nsis"
            },
            "darwin": {
                "platform": "darwin", 
                "arch": "x64",
                "icon": "icon.icns",
                "installer": "dmg"
            },
            "linux": {
                "platform": "linux",
                "arch": "x64", 
                "icon": "icon.png",
                "installer": "appimage"
            }
        }

    def setup_desktop_app_structure(self):
        """Ensure desktop app has proper structure"""
        print("Setting up desktop app structure...")
        
        # Create necessary directories
        dirs_to_create = [
            "src",
            "assets", 
            "models",
            "dist"
        ]
        
        for dir_name in dirs_to_create:
            (self.desktop_app_dir / dir_name).mkdir(exist_ok=True)
            
        # Copy icons from static directory
        if (self.assets_dir / "icon-brain.png").exists():
            shutil.copy2(
                self.assets_dir / "icon-brain.png",
                self.desktop_app_dir / "assets" / "icon.png"
            )
            
        print("✓ Desktop app structure ready")

    def create_package_json(self):
        """Create or update package.json for desktop app"""
        package_json = {
            "name": "neurolm-desktop",
            "version": self.app_info["version"],
            "description": self.app_info["description"],
            "main": "src/main.js",
            "scripts": {
                "start": "electron src/main.js --dev",
                "build": "electron-builder",
                "build-win": "electron-builder --win",
                "build-mac": "electron-builder --mac", 
                "build-linux": "electron-builder --linux",
                "dist": "npm run build",
                "pack": "electron-builder --dir"
            },
            "keywords": ["ai", "desktop", "electron", "neurolm"],
            "author": self.app_info["author"],
            "license": "MIT",
            "homepage": self.app_info["homepage"],
            "build": {
                "appId": "com.neurolm.desktop",
                "productName": "NeuroLM Desktop",
                "directories": {
                    "output": "dist",
                    "assets": "assets"
                },
                "files": [
                    "src/**/*",
                    "assets/**/*",
                    "models/**/*",
                    "package.json"
                ],
                "win": {
                    "target": "nsis",
                    "icon": "assets/icon.png"
                },
                "mac": {
                    "target": "dmg",
                    "icon": "assets/icon.png",
                    "category": "public.app-category.productivity"
                },
                "linux": {
                    "target": "AppImage",
                    "icon": "assets/icon.png",
                    "category": "Office"
                },
                "nsis": {
                    "oneClick": False,
                    "allowToChangeInstallationDirectory": True,
                    "createDesktopShortcut": True,
                    "createStartMenuShortcut": True
                }
            },
            "dependencies": {
                "ws": "^8.14.2",
                "electron-store": "^8.1.0",
                "node-fetch": "^3.3.2"
            },
            "devDependencies": {
                "electron": "^28.0.0",
                "electron-builder": "^24.6.4"
            }
        }
        
        # Write package.json
        package_path = self.desktop_app_dir / "package.json"
        with open(package_path, 'w') as f:
            json.dump(package_json, f, indent=2)
            
        print("✓ Package.json created")

    def create_desktop_interface(self):
        """Create the main desktop interface HTML"""
        html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NeuroLM Desktop</title>
    <style>
        :root {
            --primary-color: #4f46e5;
            --dark-bg: #000000;
            --card-bg: #2a2a2a;
            --light-text: #ffffff;
            --border-color: #404040;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--dark-bg);
            color: var(--light-text);
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .header {
            background: var(--card-bg);
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        .logo {
            width: 32px;
            height: 32px;
        }
        
        .main-content {
            flex: 1;
            display: flex;
            overflow: hidden;
        }
        
        .sidebar {
            width: 250px;
            background: var(--card-bg);
            border-right: 1px solid var(--border-color);
            padding: 1rem;
            overflow-y: auto;
        }
        
        .content-area {
            flex: 1;
            padding: 1rem;
            overflow-y: auto;
        }
        
        .model-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .model-card:hover {
            border-color: var(--primary-color);
            box-shadow: 0 2px 8px rgba(79, 70, 229, 0.2);
        }
        
        .model-card.installed {
            border-color: #10b981;
        }
        
        .model-name {
            font-weight: 600;
            margin-bottom: 0.5rem;
        }
        
        .model-description {
            font-size: 0.9rem;
            opacity: 0.8;
            margin-bottom: 0.5rem;
        }
        
        .model-status {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.2s;
        }
        
        .btn-primary {
            background: var(--primary-color);
            color: white;
        }
        
        .btn-success {
            background: #10b981;
            color: white;
        }
        
        .btn-secondary {
            background: var(--border-color);
            color: var(--light-text);
        }
        
        .progress-bar {
            width: 100%;
            height: 4px;
            background: var(--border-color);
            border-radius: 2px;
            overflow: hidden;
            margin: 0.5rem 0;
        }
        
        .progress-fill {
            height: 100%;
            background: var(--primary-color);
            transition: width 0.3s;
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #ef4444;
        }
        
        .status-dot.connected {
            background: #10b981;
        }
        
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="header">
        <img src="../assets/icon.png" alt="NeuroLM" class="logo">
        <h1>NeuroLM Desktop</h1>
        <div class="status-indicator">
            <div class="status-dot" id="connectionStatus"></div>
            <span id="connectionText">Connecting...</span>
        </div>
    </div>
    
    <div class="main-content">
        <div class="sidebar">
            <h3>Navigation</h3>
            <div class="nav-item" onclick="showPage('models')">Available Models</div>
            <div class="nav-item" onclick="showPage('installed')">Installed Models</div>
            <div class="nav-item" onclick="showPage('settings')">Settings</div>
        </div>
        
        <div class="content-area">
            <div id="models-page">
                <h2>Available AI Models</h2>
                <div id="models-list">
                    <!-- Models will be loaded here -->
                </div>
            </div>
            
            <div id="installed-page" class="hidden">
                <h2>Installed Models</h2>
                <div id="installed-list">
                    <!-- Installed models will be shown here -->
                </div>
            </div>
            
            <div id="settings-page" class="hidden">
                <h2>Settings</h2>
                <div class="settings-section">
                    <h3>Server Connection</h3>
                    <input type="text" id="serverUrl" placeholder="Server URL" value="http://localhost:5000">
                    <button class="btn btn-primary" onclick="connectToServer()">Connect</button>
                </div>
            </div>
        </div>
    </div>
    
    <script src="renderer.js"></script>
</body>
</html>'''
        
        # Write HTML file
        html_path = self.desktop_app_dir / "src" / "index.html"
        with open(html_path, 'w') as f:
            f.write(html_content)
            
        print("✓ Desktop interface created")

    def create_preload_script(self):
        """Create preload script for secure IPC"""
        preload_content = '''const { contextBridge, ipcRenderer } = require('electron');

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
});'''
        
        preload_path = self.desktop_app_dir / "src" / "preload.js" 
        with open(preload_path, 'w') as f:
            f.write(preload_content)
            
        print("✓ Preload script created")

    def build_installers(self, platforms: Optional[List[str]] = None):
        """Build installers for specified platforms"""
        if platforms is None:
            current_platform = platform.system().lower()
            if current_platform == "windows":
                platforms = ["win32"]
            elif current_platform == "darwin":
                platforms = ["darwin"]
            else:
                platforms = ["linux", "win32", "darwin"]
        
        print(f"Building installers for: {', '.join(platforms)}")
        
        # Change to desktop app directory
        original_cwd = os.getcwd()
        os.chdir(self.desktop_app_dir)
        
        try:
            # Install dependencies first
            print("Installing Node.js dependencies...")
            subprocess.run(["npm", "install"], check=True)
            
            # Build for each platform
            for platform_name in platforms:
                print(f"Building for {platform_name}...")
                
                build_commands = {
                    "win32": ["npm", "run", "build-win"],
                    "darwin": ["npm", "run", "build-mac"], 
                    "linux": ["npm", "run", "build-linux"]
                }
                
                if platform_name in build_commands:
                    try:
                        subprocess.run(build_commands[platform_name], check=True)
                        print(f"✓ {platform_name} build completed")
                    except subprocess.CalledProcessError as e:
                        print(f"✗ {platform_name} build failed: {e}")
                else:
                    print(f"✗ Unknown platform: {platform_name}")
                    
        except subprocess.CalledProcessError as e:
            print(f"Build failed: {e}")
            return False
        finally:
            os.chdir(original_cwd)
            
        return True

    def create_download_endpoints(self):
        """Generate download URLs for built installers"""
        downloads = {}
        dist_dir = self.desktop_app_dir / "dist"
        
        if dist_dir.exists():
            # Look for built files
            for item in dist_dir.iterdir():
                if item.is_file():
                    filename = item.name.lower()
                    if filename.endswith(('.exe', '.msi')):
                        downloads['windows'] = {
                            'filename': item.name,
                            'size': item.stat().st_size,
                            'url': f'/downloads/{item.name}'
                        }
                    elif filename.endswith(('.dmg', '.pkg')):
                        downloads['macos'] = {
                            'filename': item.name,
                            'size': item.stat().st_size,
                            'url': f'/downloads/{item.name}'
                        }
                    elif filename.endswith(('.appimage', '.deb', '.rpm')):
                        downloads['linux'] = {
                            'filename': item.name,
                            'size': item.stat().st_size,
                            'url': f'/downloads/{item.name}'
                        }
                        
        return downloads

    def run_build_process(self):
        """Execute complete build process"""
        print("🚀 Starting NeuroLM Desktop build process...")
        
        try:
            # Setup
            self.setup_desktop_app_structure()
            self.create_package_json()
            self.create_desktop_interface()
            self.create_preload_script()
            
            # Build
            if self.build_installers():
                downloads = self.create_download_endpoints()
                print("\n✅ Build process completed successfully!")
                
                if downloads:
                    print("\n📦 Available downloads:")
                    for platform, info in downloads.items():
                        size_mb = info['size'] / (1024 * 1024)
                        print(f"  {platform.capitalize()}: {info['filename']} ({size_mb:.1f}MB)")
                else:
                    print("\n⚠️  No installer files found. Check build output.")
                    
                return True
            else:
                print("\n❌ Build process failed!")
                return False
                
        except Exception as e:
            print(f"\n💥 Build process crashed: {e}")
            return False

if __name__ == "__main__":
    builder = DesktopAppBuilder()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        platforms = sys.argv[1].split(',')
        builder.build_installers(platforms)
    else:
        builder.run_build_process()