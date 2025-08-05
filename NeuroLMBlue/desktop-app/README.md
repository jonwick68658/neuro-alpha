# NeuroLM Desktop

Personal AI Models that run locally on your computer.

## Features

- **Run AI Models Locally**: Download and run powerful AI models directly on your hardware
- **Complete Privacy**: Your conversations never leave your computer
- **Works Offline**: Once models are downloaded, no internet connection required
- **Multiple Specialized Models**: Choose from 6 different AI models for coding, reasoning, creativity, and more
- **Hardware Detection**: Automatic system analysis with model recommendations
- **Easy Model Management**: Simple interface to download, install, and switch between models

## Available Models

1. **Code Agent Pro (Devstral)** - 15GB - Autonomous coding with multi-file editing
2. **Reasoning Master (DeepSeek R1)** - 8GB - Advanced logical reasoning and problem solving
3. **Code Specialist (Qwen Coder)** - 20GB - Expert code generation and debugging
4. **Fast Assistant (Llama 3.2)** - 6GB - Quick responses for general tasks
5. **Creative Writer (Mixtral 8x7B)** - 45GB - Creative writing and content generation
6. **Research Assistant (Phi-3)** - 12GB - Research and data analysis

## System Requirements

- **RAM**: 8GB minimum (16GB+ recommended)
- **Storage**: 50GB+ free space for models
- **GPU**: Optional but recommended for faster inference
- **OS**: Windows 10+, macOS 11+, or Linux

## Development

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
npm install
```

### Development Mode

```bash
npm run dev
```

### Build for Distribution

```bash
# Build for current platform
npm run build

# Build for specific platforms
npm run build-win    # Windows
npm run build-mac    # macOS
npm run build-linux  # Linux
```

### Project Structure

- `src/main.js` - Main Electron process
- `src/renderer.js` - Renderer process logic
- `src/preload.js` - Context bridge for secure IPC
- `src/index.html` - Main UI
- `src/styles.css` - Application styling
- `assets/` - Icons and images

## Connection to NeuroLM Server

The desktop app connects to your NeuroLM web instance via WebSocket to:

1. Receive model download requests from the web interface
2. Report local model status and capabilities  
3. Handle chat requests that route to local models
4. Synchronize usage analytics and preferences

## Architecture

```
NeuroLM Web App
       ↓ WebSocket
NeuroLM Desktop App
       ↓ Local API calls
AI Models (Ollama/VLLM)
       ↓ Direct inference  
Local Hardware (CPU/GPU)
```

The desktop app acts as a bridge between the web interface and local AI model inference engines, providing a seamless experience while keeping all processing on your local hardware.