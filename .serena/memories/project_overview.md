# ai-micro-mcp-admin - Project Overview

## Purpose
MCP (Model Context Protocol) Admin Service that provides intelligent chat functionality for knowledge bases. Implements MCP server capabilities with JWT authentication, vector search, and knowledge base summarization.

## Tech Stack
- **Framework**: FastAPI
- **Language**: Python 3.11+
- **MCP**: Model Context Protocol SDK
- **Embeddings**: Ollama (embeddinggemma:300m)
- **Vector Store**: PGVector (PostgreSQL + pgvector extension)
- **Database**: PostgreSQL via SQLAlchemy
- **Container**: Docker

## Project Structure
```
ai-micro-mcp-admin/
├── app/
│   ├── main.py                  # FastAPI application
│   ├── core/
│   │   ├── config.py            # Configuration settings
│   │   ├── database.py          # Database connection pool
│   │   ├── auth.py              # JWT authentication
│   │   └── permissions.py       # Permission handling
│   ├── dependencies/
│   │   └── auth.py              # Auth dependencies
│   ├── services/
│   │   ├── mcp_server.py        # MCP server implementation
│   │   ├── vector_search.py     # Vector search service (async)
│   │   └── kb_summary.py        # Knowledge base summary service
│   └── routers/
│       └── mcp.py               # MCP endpoints
├── Dockerfile
├── docker-compose.yml           # NVIDIA GPU version
├── docker-compose.mac.yml       # M3 Mac (CPU) version
├── requirements.txt
└── CLAUDE.md
```

## Key Features
- MCP Server with two tools: search_documents, get_knowledge_base_summary
- Async vector search with `asyncio.to_thread()`
- Connection pool optimization (20 base + 30 overflow)
- JWT authentication via JWKS

## Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `OLLAMA_BASE_URL`: Ollama API URL
- `EMBEDDING_MODEL`: Embedding model name
- `JWT_SECRET_KEY`: JWT signing key
- `JWKS_URL`: JWKS endpoint URL
