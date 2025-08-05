# NeuroLM - Advanced AI Memory System

An enterprise-grade intelligent AI chat system that combines the power of large language models with persistent memory capabilities. NeuroLM leverages a production-ready dual-datastore architecture featuring PostgreSQL as the primary storage with Neo4j for graph relationships, synchronized via an outbox pattern for reliability. The platform provides advanced features including hybrid search, per-user API keys, tiered memory retrieval, comprehensive health monitoring, and cross-platform desktop applications with local AI model support.

## ✨ Key Features

### Core AI Capabilities
- **🧠 Intelligent Memory**: Production-ready dual-datastore architecture with 4-tier retrieval (recent → conversation → topic → global)
- **🔧 Dynamic Tool Creation**: AI can generate custom functions on-demand using DevStral model with safe sandboxed execution
- **🌐 Multi-Model Access**: Connect to 300+ AI models through OpenRouter integration with per-user API keys
- **🔍 Real-Time Web Search**: Live web search integration for current information via `:online` suffix
- **📈 Quality Learning**: System learns from interactions to improve response quality over time with feedback integration

### Advanced Memory System
- **🎯 Hybrid Search**: Combines vector embeddings (OpenAI text-embedding-3-small) with BM25 full-text search
- **⚡ Tiered Retrieval**: Intelligent 4-tier memory access with conversation-scoped search and quality-boosted results
- **🔄 Dual-Datastore Sync**: PostgreSQL primary storage synchronized with Neo4j graph relationships via outbox pattern
- **📊 Context Awareness**: Semantic search with conversation history and topic-based memory organization

### Desktop & Cross-Platform
- **🖥️ Desktop Applications**: Cross-platform Electron apps with local AI model support (Windows, macOS, Linux)
- **🤖 Local AI Models**: 6 specialized models including Code Agent Pro (Devstral), Reasoning Master (DeepSeek R1), Creative Writer (Mixtral 8x7B)
- **📱 Progressive Web App**: Mobile PWA with offline capabilities and responsive design
- **🔌 Hardware Detection**: Automatic system analysis with model recommendations based on available resources

### Enterprise Security
- **🔐 Secrets Vault**: Enterprise-grade encrypted credential management with AES-256 encryption and PBKDF2 key derivation
- **🛡️ Multi-Tenant Security**: Row-level security (RLS) with complete user data isolation and role-based access control
- **📋 audit Logging**: Comprehensive access tracking and security monitoring with encrypted storage
- **🔒 Safe Execution**: Sandboxed environment for AI-generated code with proper isolation

### Data Management
- **📁 File Processing**: Upload and analyze documents with AI integration and vector embeddings
- **🗂️ Conversation Organization**: Topic-based conversation management with advanced filtering and slash commands
- **📊 Health Monitoring**: Comprehensive database observability with /health/db and /health/graph endpoints
- **🔄 Reliable Sync**: Outbox worker pattern ensures data consistency with at-least-once processing semantics

## 🚀 Getting Started

### Prerequisites

- **Runtime**: Python 3.11+ with FastAPI and Uvicorn
- **Databases**: PostgreSQL 13+ with pgvector extension, Neo4j 5.0+ (Community Edition)
- **Node.js**: 18+ for desktop application builds (optional)
- **API Access**:
  - OpenRouter account for AI models access (300+ models)
  - OpenAI account for text embeddings generation

### Quick Setup

1. **Clone and Install**
   ```bash
   git clone <repository-url>
   cd neurolm
   # Python dependencies installed automatically on Replit
   # Or manually: pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```env
   # Database Connections (automatically configured on Replit)
   DATABASE_URL=postgresql://user:pass@localhost/neurolm
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password
   
   # Core API Keys (store securely in Replit Secrets or secrets manager)
   OPENROUTER_API_KEY=your_openrouter_key
   OPENAI_API_KEY=your_openai_key
   SECRET_KEY=your_secret_key
   ```

3. **Initialize Databases**
   ```bash
   # Database migrations are applied automatically on startup
   # Health check: GET /health/db and /health/graph
   ```

4. **Launch Application**
   ```bash
   python main.py  # FastAPI server with outbox worker
   # Or use configured Replit workflow: "FastAPI Server"
   ```

5. **Access Applications**
   - **Web Interface**: `http://localhost:5000`
   - **Mobile PWA**: `http://localhost:5000/mobile`
   - **Secrets Vault**: `http://localhost:5000/secrets`
   - **Personal Models**: `http://localhost:5000/personal-models`
   - **Desktop Apps**: Download from `/desktop-app-download.html`

6. **Desktop Application** (Optional)
   ```bash
   cd desktop-app
   npm install
   npm run build  # Build for current platform
   # Or use: python desktop_app_builder.py
   ```

## 🏗️ System Architecture

### Core Components

**Frontend Layer:**
- **Web Interface**: Custom HTML/CSS with vanilla JavaScript and real-time streaming
- **Mobile PWA**: Progressive Web App with offline capabilities and responsive design
- **Desktop Applications**: Cross-platform Electron apps with local AI model support (.tar.gz installers)
- **UI Features**: Dark theme, markdown rendering, file upload, model selection, toggle for web data access

**Backend Layer:**
- **API Server**: FastAPI application with session-based authentication and comprehensive health monitoring
- **Memory System**: Production-ready dual-datastore architecture with PostgreSQL primary + Neo4j graph relationships
- **AI Gateway**: OpenRouter integration with per-user API keys supporting 300+ models and web search via `:online` suffix
- **Tool System**: Dynamic function generation using DevStral model with safe sandboxed execution environment
- **Synchronization**: Outbox worker pattern ensuring reliable data consistency between datastores

**Data Layer:**
- **Primary Database**: PostgreSQL with pgvector extension, BM25 full-text search, IVFFlat indexing, and row-level security (RLS)
- **Graph Database**: Neo4j for conversation memory and context relationships, synchronized via outbox pattern
- **Vector Embeddings**: OpenAI text-embedding-3-small for semantic search with hybrid retrieval capabilities
- **Secrets Vault**: Enterprise-grade encrypted credential management with AES-256 encryption and PBKDF2 key derivation

### How It Works

1. **User Interaction**: Natural conversation through web interface, mobile PWA, or desktop application
2. **Memory Retrieval**: 4-tier intelligent search (recent → conversation → topic → global) with hybrid vector + BM25 search
3. **AI Processing**: Multi-model access via OpenRouter with per-user API keys and optional web search integration
4. **Response Delivery**: Real-time streaming with markdown rendering and conversation context preservation
5. **Data Synchronization**: Outbox worker ensures reliable dual-datastore sync with at-least-once processing semantics
6. **Quality Enhancement**: Background evaluation and user feedback integration for continuous improvement
7. **Memory Persistence**: Automatic conversation storage with topic organization and slash command support

## 💫 Unique Capabilities

### Intelligent Features

- **4-Tier Memory Architecture**: Production-ready retrieval with recent → conversation → topic → global fallback
- **Hybrid Search Technology**: Combines vector embeddings with BM25 full-text search for optimal context retrieval  
- **Dynamic Tool Creation**: AI generates custom functions on-demand using DevStral model with safe sandboxed execution
- **Quality-Boosted Search**: Enhanced memory retrieval with conversation-first scoping and intelligent filtering
- **Adaptive Context Management**: Smart conversation history with topic-based organization and slash command support

### Enterprise Security

- **Multi-Tenant Architecture**: Row-level security (RLS) with complete user data isolation and role-based access control
- **Enterprise Secrets Vault**: AES-256 encryption with PBKDF2 key derivation and comprehensive audit logging
- **Sandboxed Code Execution**: AI-generated code runs in isolated environment with proper security boundaries
- **Database-Persistent Sessions**: Secure authentication system with automatic cleanup and session management
- **Health Monitoring**: Comprehensive database observability with /health/db and /health/graph endpoints

### Cross-Platform Experience

- **Local AI Models**: 6 specialized models including Code Agent Pro (Devstral 15GB), Reasoning Master (DeepSeek R1 8GB), Creative Writer (Mixtral 8x7B 45GB)
- **Hardware Detection**: Automatic system analysis with model recommendations based on available resources (RAM, GPU, storage)
- **Offline Capabilities**: Desktop applications work without internet once models are downloaded
- **Multiple Interfaces**: Web, mobile PWA, and desktop applications with consistent experience across platforms
- **Real-Time Data Access**: Web search integration for current information via `:online` suffix in prompts

## 🆕 Recent Updates (August 2025)

### Database Architecture Overhaul
- **Dual-Datastore Implementation**: Migrated from single Neo4j to PostgreSQL primary + Neo4j graph relationships
- **Outbox Pattern Synchronization**: Implemented reliable data consistency with at-least-once processing semantics
- **Applied All Migrations**: 7 PostgreSQL migrations and 4 Neo4j migrations successfully applied
- **Health Monitoring**: Added comprehensive database observability with `/health/db` and `/health/graph` endpoints

### Memory System Enhancements
- **Fixed Neo4j Synchronization**: Resolved root cause where outbox events weren't being generated during memory storage
- **Backfilled Historical Data**: Successfully synchronized 261 historical events (194 memories, 31 conversations, 36 feedback records)
- **4-Tier Retrieval Confirmed**: User-validated memory system performing optimally with intelligent filtering and conversation-first scoping

### UI/UX Improvements
- **Fixed Sidebar Toggle**: Resolved desktop sidebar not opening/closing with proper grid-template-columns transitions
- **Restored Slash Commands**: Complete slash command functionality for file management and conversation organization
- **Cross-Platform Desktop**: Enhanced Electron applications with local AI model support and hardware detection

### System Maintenance
- **Codebase Cleanup**: Removed unused migration and utility files while preserving personal model training components
- **Enhanced Security**: Improved multi-tenant architecture with row-level security and comprehensive audit logging
- **Performance Optimization**: Hybrid search with vector + BM25 combination for optimal context retrieval

## 🔮 Future Development

**Expanding AI capabilities through continuous development.**

We're actively working on enhancing NeuroLM with additional features and capabilities to provide an even more powerful AI assistant experience.

### Planned Features

- **🤖 Enhanced AI Integration**: Expand support for more AI models and providers
- **🧠 Advanced Memory**: Improved context understanding and retrieval capabilities
- **🔧 Extended Tool Support**: More sophisticated function generation and execution
- **📊 Analytics Dashboard**: Enhanced usage tracking and performance insights
- **🌐 Multi-Modal Support**: Integration of text, voice, and vision capabilities
- **⚡ Real-Time Features**: Live collaboration and instant synchronization
- **🛡️ Enterprise Features**: Advanced security and deployment options

### Contributing

We welcome contributions from the developer community. The project is open source and available for enhancement and customization.

*"Building the future of AI-powered conversation and assistance."*

## 📱 Usage Guide

### Getting Started

1. **Create Account**: Register and log in to your personal AI assistant
2. **Configure API Keys**: Visit `/secrets` to securely store your OpenRouter and OpenAI keys
3. **Choose Model**: Select from 300+ AI models including GPT-4, Claude, Gemini, and many others
4. **Start Chatting**: Begin conversations - everything is automatically saved and learned from
5. **Enable Web Search**: Use 🌐 button for real-time information access

### Advanced Features

- **Topic Organization**: Categorize conversations for better retrieval
- **File Upload**: Drag and drop documents for AI analysis
- **Tool Requests**: Ask for custom functions: "Create a tool to analyze CSV data"
- **Feedback Training**: Use feedback buttons to improve future responses
- **Mobile PWA**: Install as mobile app for offline access
- **Secrets Management**: Secure API key storage with encryption and rotation
- **Personal Models**: Train custom AI models from your conversation data
- **Model Analytics**: Track usage patterns and performance metrics

## 🔧 Development

### Project Structure

```
neurolm/
├── main.py                           # FastAPI server and API endpoints
├── hybrid_intelligent_memory.py     # 4-tier intelligent memory system  
├── hybrid_background_riai.py        # Background learning service
├── outbox_worker.py                 # Dual-datastore synchronization
├── tool_generator.py                # Dynamic tool creation (DevStral)
├── tool_executor.py                 # Secure sandboxed execution
├── model_services.py                # Multi-model AI integration
├── secrets_vault.py                 # Enterprise secrets management
├── personal_model_manager.py        # Custom model training
├── training_scheduler.py            # Automated training pipeline
├── desktop_app_connector.py         # Desktop application integration
├── desktop_app_builder.py           # Cross-platform app builder
├── migrations/                      # Database migrations
│   ├── pg/                         # PostgreSQL migrations (7 applied)
│   └── neo4j/                      # Neo4j migrations (4 applied)
├── desktop-app/                     # Electron desktop application
│   ├── src/main.js                 # Main Electron process
│   ├── src/renderer.js             # UI logic and interactions
│   ├── src/preload.js              # Context bridge for IPC
│   └── package.json                # Electron build configuration
├── chat.html                       # Desktop web interface
├── mobile.html                     # Mobile PWA interface
├── secrets_manager.html            # Secrets management interface
├── personal_models_dashboard.html  # Personal models interface
├── desktop-app-download.html       # Desktop app distribution page
└── manifest.json                   # PWA manifest
```

### Key Technologies

- **Dual-Datastore Architecture**: PostgreSQL primary storage with Neo4j graph relationships synchronized via outbox pattern
- **Hybrid Search**: Vector embeddings (OpenAI text-embedding-3-small) combined with BM25 full-text search
- **Cross-Platform**: FastAPI backend, vanilla JavaScript frontend, Electron desktop apps with local AI models
- **Enterprise Security**: Row-level security (RLS), AES-256 encryption, PBKDF2 key derivation, comprehensive audit logging
- **Multi-Model AI**: OpenRouter integration supporting 300+ models with per-user API keys and web search capabilities
- **Progressive Web App**: Mobile PWA with offline capabilities and responsive design

## 📊 Performance Metrics

- **Memory Retrieval**: Sub-100ms semantic search across thousands of memories
- **Response Time**: Instant user responses with background learning
- **Intelligence Growth**: Measurable improvement in response quality over time
- **Tool Creation**: Custom functions generated in seconds
- **Multi-Platform**: Consistent experience across desktop and mobile

## 🌟 What Makes NeuroLM Different

Unlike traditional AI assistants that provide static responses, NeuroLM offers a dynamic experience:

- **Traditional AI**: Static responses, no memory, limited context
- **NeuroLM**: Persistent memory, context-aware, continuously learning

Every conversation builds context. Every tool request expands capabilities. Every feedback improves future interactions.

## 🚀 Deployment

### Cloud Deployment

Optimized for cloud deployment:
1. Fork repository
2. Configure API keys in environment variables or use the built-in `/secrets` manager
3. Deploy automatically to production with PostgreSQL and Neo4j integration

### Enterprise Deployment

- **Horizontal Scaling**: Stateless architecture for cloud deployment
- **Security**: All credentials externalized to environment variables
- **Monitoring**: Comprehensive logging and error handling
- **Database**: Compatible with managed PostgreSQL and Neo4j Aura

## 📈 Version History

- **August 2025**: **DUAL-DATASTORE ARCHITECTURE** - PostgreSQL primary + Neo4j graph with outbox synchronization
- **August 2025**: **MEMORY SYSTEM OVERHAUL** - 4-tier retrieval with hybrid search and Neo4j sync fixes
- **August 2025**: **DESKTOP APPLICATIONS** - Cross-platform Electron apps with local AI model support
- **August 2025**: **UI/UX ENHANCEMENTS** - Fixed sidebar toggle, restored slash commands, enhanced responsive design
- **July 2025**: **ENTERPRISE SECRETS MANAGER** - Professional interface with AES-256 encryption and audit logging
- **July 2025**: **PERSONAL AI MODELS** - Custom model training with desktop integration and hardware detection
- **July 2025**: **INTELLIGENT MEMORY** - Advanced conversation storage with semantic search and context retrieval
- **June 2025**: **MULTI-MODEL ACCESS** - OpenRouter integration with 300+ AI models and real-time web search

## 🤝 Community

- **Documentation**: Comprehensive guides in project documentation
- **Issues**: Bug reports and feature requests via GitHub
- **API Access**: Get keys at [openrouter.ai](https://openrouter.ai)
- **Enterprise**: Contact us for custom deployment and licensing

## 🔬 The Technology

NeuroLM implements advanced techniques in artificial intelligence:

**Intelligent Learning System**

The platform uses sophisticated algorithms to learn from user interactions and feedback, continuously improving response quality and context understanding. The system combines multiple AI models with persistent memory to create a truly adaptive AI assistant.

## 📄 License

MIT License - Open source with commercial use permitted.

---

**NeuroLM: Where artificial intelligence becomes truly intelligent.**

*Built with FastAPI, dual-datastore architecture (PostgreSQL + Neo4j), hybrid intelligent memory systems, cross-platform Electron apps, and OpenRouter AI*

🔗 **Open source platform for advanced AI-powered conversations and assistance**
