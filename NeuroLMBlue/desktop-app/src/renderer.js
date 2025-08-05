// NeuroLM Desktop Renderer Process
class NeuroLMRenderer {
    constructor() {
        this.currentTab = 'models';
        this.isConnected = false;
        this.hardwareInfo = {};
        this.installedModels = [];
        this.availableModels = [];
        this.downloadProgress = new Map();
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        this.setupElectronListeners();
        await this.loadHardwareInfo();
        await this.loadInstalledModels();
        this.loadAvailableModels();
        this.attemptConnection();
    }

    setupEventListeners() {
        // Tab navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const tab = e.currentTarget.dataset.tab;
                this.switchTab(tab);
            });
        });

        // Settings
        document.getElementById('connectBtn').addEventListener('click', () => {
            this.connectToServer();
        });

        document.getElementById('openWebApp').addEventListener('click', () => {
            const serverUrl = document.getElementById('serverUrl').value;
            const webUrl = serverUrl.replace('ws://', 'http://').replace('wss://', 'https://');
            window.electronAPI.openExternal(webUrl);
        });

        // Chat
        document.getElementById('sendBtn').addEventListener('click', () => {
            this.sendMessage();
        });

        document.getElementById('chatInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }

    setupElectronListeners() {
        // Connection status
        window.electronAPI.onConnectionStatus((event, data) => {
            this.updateConnectionStatus(data.connected);
        });

        // Hardware detection
        window.electronAPI.onHardwareDetected((event, hardware) => {
            this.hardwareInfo = hardware;
            this.updateHardwareDisplay();
            this.updateModelCompatibility();
        });

        // Model download events
        window.electronAPI.onModelDownloadStart((event, data) => {
            this.showDownloadModal(data.modelId, data.config);
        });

        window.electronAPI.onModelDownloadProgress((event, data) => {
            this.updateDownloadProgress(data.modelId, data.progress);
        });

        window.electronAPI.onModelDownloadComplete((event, data) => {
            this.hideDownloadModal();
            this.loadInstalledModels();
            this.showNotification('Model installed successfully!', 'success');
        });

        window.electronAPI.onModelDownloadError((event, data) => {
            this.hideDownloadModal();
            this.showNotification(`Failed to install model: ${data.error}`, 'error');
        });
    }

    switchTab(tabName) {
        // Update nav items
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}Tab`).classList.add('active');

        this.currentTab = tabName;
    }

    async connectToServer() {
        const serverUrl = document.getElementById('serverUrl').value;
        const connectBtn = document.getElementById('connectBtn');
        
        connectBtn.textContent = 'Connecting...';
        connectBtn.disabled = true;

        try {
            const result = await window.electronAPI.connectToServer(serverUrl);
            if (result.success) {
                this.updateConnectionStatus(true);
                this.showNotification('Connected to server successfully!', 'success');
            } else {
                this.showNotification(`Connection failed: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`Connection failed: ${error.message}`, 'error');
        } finally {
            connectBtn.textContent = 'Connect';
            connectBtn.disabled = false;
        }
    }

    async attemptConnection() {
        try {
            await this.connectToServer();
        } catch (error) {
            console.log('Initial connection failed, will retry manually');
        }
    }

    updateConnectionStatus(connected) {
        this.isConnected = connected;
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');

        if (connected) {
            statusDot.className = 'status-dot online';
            statusText.textContent = 'Connected';
        } else {
            statusDot.className = 'status-dot offline';
            statusText.textContent = 'Disconnected';
        }
    }

    async loadHardwareInfo() {
        try {
            this.hardwareInfo = await window.electronAPI.getHardwareInfo();
            this.updateHardwareDisplay();
        } catch (error) {
            console.error('Failed to load hardware info:', error);
        }
    }

    updateHardwareDisplay() {
        const ramInfo = document.getElementById('ramInfo');
        const cpuInfo = document.getElementById('cpuInfo');
        const gpuInfo = document.getElementById('gpuInfo');

        if (this.hardwareInfo.totalMemory) {
            ramInfo.textContent = `${this.hardwareInfo.totalMemory}GB`;
        }
        
        if (this.hardwareInfo.cpus) {
            cpuInfo.textContent = `${this.hardwareInfo.cpus} cores`;
        }
        
        if (this.hardwareInfo.gpu) {
            gpuInfo.textContent = this.hardwareInfo.gpu.length > 25 
                ? this.hardwareInfo.gpu.substring(0, 25) + '...'
                : this.hardwareInfo.gpu;
        }
    }

    async loadInstalledModels() {
        try {
            this.installedModels = await window.electronAPI.getInstalledModels();
            this.updateInstalledModelsDisplay();
            this.updateChatModelSelector();
        } catch (error) {
            console.error('Failed to load installed models:', error);
        }
    }

    loadAvailableModels() {
        // Personal AI Models from the configuration
        this.availableModels = [
            {
                id: 'devstral_small',
                name: 'Code Agent Pro',
                description: 'Autonomous coding agent with multi-file editing capabilities',
                size: '15GB',
                parameters: '24B',
                hardware_req: 'HEAVY',
                specialties: ['Multi-file editing', 'Codebase exploration', 'Bug fixing'],
                ram_required: 32,
                gpu_recommended: true
            },
            {
                id: 'deepseek_r1_8b',
                name: 'Reasoning Master',
                description: 'Advanced reasoning and problem-solving capabilities',
                size: '8GB',
                parameters: '8B',
                hardware_req: 'MEDIUM',
                specialties: ['Logic puzzles', 'Mathematical reasoning', 'Analysis'],
                ram_required: 16,
                gpu_recommended: false
            },
            {
                id: 'qwen_coder_32b',
                name: 'Code Specialist',
                description: 'Expert code generation and debugging',
                size: '20GB',
                parameters: '32B',
                hardware_req: 'EXTREME',
                specialties: ['Code generation', 'Architecture design', 'Debugging'],
                ram_required: 64,
                gpu_recommended: true
            },
            {
                id: 'llama_3_2_3b',
                name: 'Fast Assistant',
                description: 'Quick responses and general assistance',
                size: '6GB',
                parameters: '3B',
                hardware_req: 'LIGHT',
                specialties: ['Quick responses', 'General questions', 'Light coding'],
                ram_required: 8,
                gpu_recommended: false
            },
            {
                id: 'mixtral_8x7b',
                name: 'Creative Writer',
                description: 'Creative writing and content generation',
                size: '45GB',
                parameters: '8x7B',
                hardware_req: 'EXTREME',
                specialties: ['Story writing', 'Content creation', 'Marketing'],
                ram_required: 64,
                gpu_recommended: true
            },
            {
                id: 'phi_3_medium',
                name: 'Research Assistant',
                description: 'Research and analysis capabilities',
                size: '12GB',
                parameters: '14B',
                hardware_req: 'HEAVY',
                specialties: ['Research', 'Analysis', 'Data processing'],
                ram_required: 24,
                gpu_recommended: true
            }
        ];

        this.updateAvailableModelsDisplay();
    }

    updateAvailableModelsDisplay() {
        const container = document.getElementById('availableModels');
        container.innerHTML = '';

        this.availableModels.forEach(model => {
            const isInstalled = this.installedModels.some(installed => installed.id === model.id);
            const compatibility = this.checkModelCompatibility(model);
            
            const modelCard = document.createElement('div');
            modelCard.className = 'model-card';
            modelCard.innerHTML = `
                <div class="model-header">
                    <div class="model-title">${model.name}</div>
                    <div class="model-size">${model.size}</div>
                </div>
                <div class="model-description">${model.description}</div>
                <div class="model-specs">
                    <span class="spec-tag">${model.parameters} params</span>
                    <span class="spec-tag">${model.hardware_req.toLowerCase()}</span>
                    ${model.specialties.slice(0, 2).map(spec => 
                        `<span class="spec-tag">${spec}</span>`
                    ).join('')}
                </div>
                <div class="compatibility-indicator ${compatibility.class}">
                    <span>${compatibility.icon}</span>
                    <span>${compatibility.text}</span>
                </div>
                <div class="model-actions">
                    <button class="btn btn-primary" ${isInstalled || !compatibility.canInstall ? 'disabled' : ''} 
                            onclick="renderer.installModel('${model.id}')">
                        ${isInstalled ? 'Installed' : 'Download for Desktop'}
                    </button>
                    ${!isInstalled ? `
                        <button class="btn btn-secondary" onclick="renderer.learnMore('${model.id}')">
                            Learn More
                        </button>
                    ` : ''}
                </div>
            `;
            
            container.appendChild(modelCard);
        });
    }

    updateInstalledModelsDisplay() {
        const container = document.getElementById('installedModels');
        
        if (this.installedModels.length === 0) {
            container.innerHTML = `
                <div class="no-models-message">
                    No models installed yet. Choose a model above to get started.
                </div>
            `;
            return;
        }

        container.innerHTML = '';
        this.installedModels.forEach(model => {
            const modelConfig = this.availableModels.find(m => m.id === model.id);
            if (!modelConfig) return;

            const modelCard = document.createElement('div');
            modelCard.className = 'model-card';
            modelCard.innerHTML = `
                <div class="model-header">
                    <div class="model-title">${modelConfig.name}</div>
                    <div class="model-size">${modelConfig.size}</div>
                </div>
                <div class="model-description">${modelConfig.description}</div>
                <div class="model-specs">
                    <span class="spec-tag">Installed</span>
                    <span class="spec-tag">${new Date(model.installedAt).toLocaleDateString()}</span>
                </div>
                <div class="model-actions">
                    <button class="btn btn-primary" onclick="renderer.startChat('${model.id}')">
                        Start Chat
                    </button>
                    <button class="btn btn-secondary" onclick="renderer.uninstallModel('${model.id}')">
                        Uninstall
                    </button>
                </div>
            `;
            
            container.appendChild(modelCard);
        });
    }

    updateChatModelSelector() {
        const selector = document.getElementById('modelSelector');
        const chatInput = document.getElementById('chatInput');
        const sendBtn = document.getElementById('sendBtn');
        
        selector.innerHTML = '<option value="">Select a model to chat with</option>';
        
        this.installedModels.forEach(model => {
            const modelConfig = this.availableModels.find(m => m.id === model.id);
            if (modelConfig) {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = modelConfig.name;
                selector.appendChild(option);
            }
        });

        // Enable/disable chat based on model selection
        selector.addEventListener('change', (e) => {
            const hasModel = e.target.value !== '';
            chatInput.disabled = !hasModel;
            sendBtn.disabled = !hasModel;
            
            if (hasModel) {
                chatInput.placeholder = 'Type your message here...';
            } else {
                chatInput.placeholder = 'Select a model first...';
            }
        });
    }

    checkModelCompatibility(model) {
        if (!this.hardwareInfo.totalMemory) {
            return {
                class: 'warning',
                icon: '⚠️',
                text: 'Hardware detection in progress...',
                canInstall: false
            };
        }

        const hasEnoughRAM = this.hardwareInfo.totalMemory >= model.ram_required;
        
        if (!hasEnoughRAM) {
            return {
                class: 'incompatible',
                icon: '❌',
                text: `Requires ${model.ram_required}GB RAM (you have ${this.hardwareInfo.totalMemory}GB)`,
                canInstall: false
            };
        }

        if (model.gpu_recommended && !this.hardwareInfo.gpu.includes('GPU')) {
            return {
                class: 'warning',
                icon: '⚠️',
                text: 'GPU recommended for optimal performance',
                canInstall: true
            };
        }

        return {
            class: 'compatible',
            icon: '✅',
            text: 'Compatible with your system',
            canInstall: true
        };
    }

    updateModelCompatibility() {
        this.updateAvailableModelsDisplay();
    }

    async installModel(modelId) {
        const model = this.availableModels.find(m => m.id === modelId);
        if (!model) return;

        if (!this.isConnected) {
            this.showNotification('Please connect to server first', 'error');
            return;
        }

        const compatibility = this.checkModelCompatibility(model);
        if (!compatibility.canInstall) {
            this.showNotification('Model is not compatible with your system', 'error');
            return;
        }

        // This would trigger the desktop app to start downloading
        // The actual implementation would send a message to the main process
        console.log(`Installing model: ${modelId}`);
        this.showNotification(`Starting installation of ${model.name}...`, 'info');
    }

    learnMore(modelId) {
        const model = this.availableModels.find(m => m.id === modelId);
        if (!model) return;

        // Show detailed information about the model
        alert(`${model.name}\n\n${model.description}\n\nSpecialties:\n${model.specialties.join(', ')}\n\nRequirements:\n- RAM: ${model.ram_required}GB\n- GPU: ${model.gpu_recommended ? 'Recommended' : 'Optional'}`);
    }

    startChat(modelId) {
        this.switchTab('chat');
        const selector = document.getElementById('modelSelector');
        selector.value = modelId;
        selector.dispatchEvent(new Event('change'));
    }

    uninstallModel(modelId) {
        if (confirm('Are you sure you want to uninstall this model?')) {
            // Implementation would remove model files and update the list
            this.showNotification('Model uninstall feature coming soon', 'info');
        }
    }

    sendMessage() {
        const input = document.getElementById('chatInput');
        const message = input.value.trim();
        const selectedModel = document.getElementById('modelSelector').value;
        
        if (!message || !selectedModel) return;

        // Add message to chat
        this.addChatMessage('user', message);
        input.value = '';

        // Simulate AI response (replace with actual local model inference)
        setTimeout(() => {
            this.addChatMessage('assistant', 'This is a simulated response from the local AI model. The actual implementation would use the installed model to generate responses.');
        }, 1000);
    }

    addChatMessage(role, content) {
        const messagesContainer = document.getElementById('chatMessages');
        const welcomeMessage = messagesContainer.querySelector('.welcome-message');
        
        if (welcomeMessage) {
            welcomeMessage.remove();
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${role}`;
        messageDiv.innerHTML = `
            <div class="message-content">${content}</div>
            <div class="message-time">${new Date().toLocaleTimeString()}</div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    showDownloadModal(modelId, config) {
        const modal = document.getElementById('downloadModal');
        const modelName = document.getElementById('downloadModelName');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        const downloadStatus = document.getElementById('downloadStatus');

        const model = this.availableModels.find(m => m.id === modelId);
        modelName.textContent = model ? model.name : modelId;
        
        progressFill.style.width = '0%';
        progressText.textContent = '0%';
        downloadStatus.textContent = 'Preparing download...';
        
        modal.classList.add('active');
    }

    updateDownloadProgress(modelId, progress) {
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        const downloadStatus = document.getElementById('downloadStatus');

        progressFill.style.width = `${progress}%`;
        progressText.textContent = `${progress}%`;
        
        if (progress < 100) {
            downloadStatus.textContent = `Downloading model files... ${progress}%`;
        } else {
            downloadStatus.textContent = 'Installing model...';
        }
    }

    hideDownloadModal() {
        const modal = document.getElementById('downloadModal');
        modal.classList.remove('active');
    }

    showNotification(message, type = 'info') {
        // Simple notification system (can be enhanced with a proper notification library)
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'error' ? '#ff4444' : type === 'success' ? '#00ff88' : '#00d4ff'};
            color: white;
            padding: 12px 20px;
            border-radius: 6px;
            z-index: 10000;
            font-size: 14px;
            max-width: 300px;
            word-wrap: break-word;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// Initialize the renderer when the DOM is loaded
const renderer = new NeuroLMRenderer();