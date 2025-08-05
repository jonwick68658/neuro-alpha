# NeuroLM - Advanced AI Memory System

### Overview
NeuroLM is an enterprise-grade intelligent AI chat system that combines large language models with persistent memory capabilities. It leverages a production-ready dual-datastore architecture featuring PostgreSQL as the primary storage with Neo4j for graph relationships, synchronized via an outbox pattern for reliability. The system provides advanced features including hybrid search (vector + BM25), per-user API keys, tiered memory retrieval, and comprehensive health monitoring. The project has evolved from a personal AI system to a scalable business intelligence platform with multi-tenant support, enterprise security, and automated synchronization between datastores.

### Recent Changes (August 2025)
- **Database Architecture Upgrade**: Implemented dual-datastore with PostgreSQL primary + Neo4j graph, synchronized via outbox pattern
- **Applied All Migrations**: 7 PostgreSQL migrations (extensions, schema, search, vectors, security, roles, outbox) and 4 Neo4j migrations (constraints, indexes, model, feedback)
- **Database Health Monitoring**: Added /health/db and /health/graph endpoints for comprehensive database observability
- **Outbox Worker Integration**: Reliable dual-datastore synchronization with at-least-once processing semantics
- **Fixed Neo4j Synchronization (Aug 2025)**: Resolved root cause where outbox events weren't being generated during memory storage. Implemented automatic outbox event creation within database transactions for memory storage, conversation creation, and feedback updates. Backfilled 261 historical events (194 memories, 31 conversations, 36 feedback records). Neo4j sync now working with 195 messages, 43 conversations, and 37 feedback relationships synchronized.
- **Fixed Sidebar Toggle Issue (Aug 2025)**: Resolved sidebar not opening/closing on desktop. Issue was desktop layout used permanent grid columns while toggle only worked in mobile view. Implemented proper desktop toggle with grid-template-columns transitions and transform animations for all screen sizes.
- **Memory System Assessment (Aug 2025)**: User confirmed current hybrid intelligent memory system is performing well with its 4-tier retrieval approach (recent context → conversation-scoped → topic-scoped → global fallback), intelligent filtering, and conversation-first scoping strategy.
- **Codebase Cleanup (Aug 2025)**: Removed unused migration and utility files: `migrate.py` (migrations complete), `password_reset_service.py` (auth system upgraded), `migrate_existing_memories.py` (one-time migration), `backfill_outbox_events.py` (backfill complete), and `temporal_summerizer` (unused feature). Kept personal model training components for future development.
- **Slash Commands Restored (Aug 2025)**: Restored complete slash command functionality that was accidentally removed during recent architectural changes. Added back `handle_slash_command` function supporting: `/files`, `/view [filename]`, `/delete [filename]`, `/search [term]`, `/download [filename]`, and `/topics` commands for file management and conversation organization.

### User Preferences
Preferred communication style: Simple, everyday language.

### System Architecture
The application is built on a FastAPI-based microservice architecture.

**Frontend Layer:**
-   **Web Interface**: Custom HTML/CSS with vanilla JavaScript.
-   **Mobile PWA**: Progressive Web App with offline capabilities.
-   **Real-time Communication**: Direct HTTP API calls with streaming.
-   **UI Components**: Responsive chat interface with markdown rendering, file upload, model selection, and a toggle button for real-time web data access. Desktop applications are provided as `.tar.gz` installers with Electron runtime.
-   **Design**: Dark theme for code blocks with language indicators, floating input bubble, topic-based conversation filtering.

**Backend Layer:**
-   **API Server**: FastAPI application with session-based authentication and comprehensive health monitoring.
-   **Memory System**: Production-ready dual-datastore architecture with PostgreSQL primary storage and Neo4j graph relationships. Features hybrid search (vector + BM25), tiered retrieval, quality-boosted search, and reliable outbox synchronization.
-   **Model Integration**: OpenRouter API integration with per-user API keys, supporting multiple AI providers, web search capability via `:online` suffix, and dynamic model listing.
-   **File Management**: PostgreSQL-based file storage with vector embeddings and full-text search capabilities.
-   **Security**: Enterprise-grade secrets management with AES-256 encryption, PBKDF2 key derivation, role-based access control (RLS), and multi-tenant support.
-   **Synchronization**: Outbox worker pattern ensuring reliable data consistency between PostgreSQL and Neo4j with at-least-once processing semantics.
-   **Tooling**: Automated tool creation system using DevStral model and a safe, sandboxed execution environment for AI-generated functions.

**Data Layer:**
-   **Primary Database**: PostgreSQL with pgvector extension for vector embeddings, full-text search (BM25), IVFFlat indexing, and row-level security (RLS).
-   **Graph Database**: Neo4j for conversation memory and context relationships, synchronized via outbox pattern.
-   **Vector Embeddings**: OpenAI `text-embedding-3-small` for semantic search with hybrid retrieval capabilities.
-   **Session Storage**: Database-persistent sessions with automatic cleanup and role-based access control.
-   **Migration System**: Automated database migrations with safety gates, plan/apply modes, and production confirmation requirements.
-   **Synchronization**: Outbox table pattern ensuring reliable data consistency between PostgreSQL and Neo4j datastores.

### External Dependencies
-   **Neo4j Database**: Graph database for memory storage.
-   **PostgreSQL**: Relational database for user data and files.
-   **OpenRouter API**: AI model access and management.
-   **OpenAI API**: Text embeddings generation.
-   **OpenRouter models**: DeepSeek-R1-Distill, Mistral Devstral, mistralai/mistral-small-3.2-24b-instruct, etc.