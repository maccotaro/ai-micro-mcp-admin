# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **MCP (Model Context Protocol) Admin Service** that provides intelligent chat functionality for knowledge bases. It implements MCP server capabilities with JWT authentication, vector search, and knowledge base summarization.

## Key Features

- **MCP Server Implementation**: Tool-based interface for knowledge base operations
- **Vector Search**: Semantic search using embeddings and PGVector
- **Knowledge Base Summary**: Generate overviews and statistics
- **JWT Authentication**: Secure access control
- **Concurrent Request Support**: Optimized for multiple simultaneous requests

## Technology Stack

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
│   │   └── auth.py              # JWT authentication
│   ├── services/
│   │   ├── mcp_server.py        # MCP server implementation
│   │   ├── vector_search.py     # Vector search service (async)
│   │   └── kb_summary.py        # Knowledge base summary service
│   └── routers/
│       └── mcp.py               # MCP endpoints
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── CLAUDE.md                    # This file
└── .env
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `OLLAMA_BASE_URL` | Ollama API URL | `http://host.docker.internal:11434` |
| `EMBEDDING_MODEL` | Embedding model name | `embeddinggemma:300m` |
| `JWT_SECRET_KEY` | JWT signing key | - |
| `JWT_ALGORITHM` | JWT algorithm | `RS256` |
| `JWKS_URL` | JWKS endpoint URL | `http://host.docker.internal:8002/.well-known/jwks.json` |

## Commands

### Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload
```

### Docker Commands

```bash
# Start the service with Docker Compose
cd ai-micro-mcp-admin && docker compose up -d

# View logs
docker compose logs -f ai-micro-mcp-admin

# Restart after code changes
docker compose restart

# Stop service
docker compose down
```

## MCP Tools

### 1. search_documents

Search for specific information in knowledge base documents.

**Parameters**:
- `query` (string, required): The search query
- `knowledge_base_id` (string, required): Knowledge base UUID
- `threshold` (number, optional): Similarity threshold (0.0-1.0, default: 0.6)
- `max_results` (integer, optional): Maximum results (default: 10, max: 50)

**Use Cases**:
- Specific topic searches (e.g., "アルムナイについて")
- Technical details or procedures
- Concrete information queries

### 2. get_knowledge_base_summary

Get an overview and statistics of the entire knowledge base.

**Parameters**:
- `knowledge_base_id` (string, required): Knowledge base UUID

**Use Cases**:
- Knowledge base overview ("このナレッジベースについて")
- Overall structure ("全体の構成")
- Statistics ("統計情報")

## Architecture

### Service Communication Flow

```
Frontend (ai-micro-front-admin)
        ↓
API Admin (ai-micro-api-admin)
        ↓
MCP Admin (ai-micro-mcp-admin) ← This service
        ↓
[Vector Search | KB Summary]
        ↓
PostgreSQL (admindb + pgvector)
```

### Concurrent Request Handling

The service is optimized for multiple simultaneous requests with the following features:

#### 1. Async Vector Search (2025-10-23)
- **Implementation**: `asyncio.to_thread()` wraps blocking LangChain operations
- **Benefit**: Non-blocking execution prevents request queuing
- **File**: `app/services/vector_search.py:52-58`

```python
# Blocking operations run in separate thread pool
results = await asyncio.to_thread(
    self.vector_store.similarity_search_with_score,
    query, k=top_k, filter=filter_condition
)
```

#### 2. Database Connection Management
- **Connection Pool**: 20 base connections + 30 overflow (total: 50)
- **Timeout**: 30 seconds for connection acquisition
- **Recycle**: Connections recycled after 1 hour
- **Leak Prevention**: Automatic connection close in `finally` blocks
- **File**: `app/core/database.py:9-17`, `app/services/kb_summary.py:58-60`

```python
# Connection pool configuration
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,          # Health check
    pool_size=20,                # Base pool size
    max_overflow=30,             # Overflow connections
    pool_recycle=3600,           # Recycle after 1 hour
    pool_timeout=30              # Acquisition timeout
)
```

#### 3. Stateless Service Design
- Singleton pattern for service instances (thread-safe)
- No shared mutable state between requests
- Each request uses independent database sessions

### Performance Characteristics

| Load Level | Expected Behavior | Notes |
|------------|-------------------|-------|
| **Low** (1-2 req/s) | ✅ Optimal performance | <100ms response time |
| **Medium** (5-10 req/s) | ✅ Good performance | ~200-500ms response time |
| **High** (20+ req/s) | ✅ Stable performance | Improved from previous blocking design |

**Previous Issues (Before 2025-10-23)**:
- ❌ Blocking vector search causing request queuing
- ❌ Connection leaks under high load
- ❌ Limited connection pool (10+20=30 total)

**Current Status (After 2025-10-23)**:
- ✅ Non-blocking async operations
- ✅ Proper connection lifecycle management
- ✅ Expanded connection pool (20+50=50 total)

## Authentication

All endpoints (except `/health` and `/`) require JWT authentication:

1. **Token Validation**: JWT Bearer token in `Authorization` header
2. **JWKS Verification**: Public key fetched from auth service
3. **Role Check**: User must have appropriate permissions
4. **Knowledge Base Access**: Verified against user's accessible knowledge bases

## Integration with Other Services

### API Admin Service
- **Client**: `app/services/mcp_chat_service.py` in ai-micro-api-admin
- **Endpoint**: `/mcp/chat` (POST)
- **Flow**: Receives chat requests and forwards to MCP tools

### Authentication Service
- **JWKS Endpoint**: Provides public keys for JWT verification
- **URL**: `http://host.docker.internal:8002/.well-known/jwks.json`

### PostgreSQL
- **Database**: admindb
- **Tables**: knowledge_bases, collections, documents
- **Extension**: pgvector for embeddings
- **Connection**: Via connection pool with optimized settings

## Development Guidelines

### Code Quality Standards
- **File Size Limit**: 500 lines per file (excluding docs)
- **Type Hints**: Use Python type annotations
- **Error Handling**: Comprehensive logging and error messages
- **Async/Await**: Prefer async for I/O operations

### Adding New MCP Tools

1. Define tool schema in `app/services/mcp_server.py:_create_tools_list()`
2. Implement handler method (e.g., `_my_new_tool()`)
3. Register in `call_tool()` decorator
4. Add integration tests
5. Update this documentation

### Testing

```bash
# Health check
curl http://localhost:8004/health

# MCP chat (requires JWT)
curl -X POST http://localhost:8004/mcp/chat \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "アルムナイについて教えて",
    "knowledge_base_id": "9fba1ff9-3159-4417-a5d1-cf6a079c3a1b"
  }'
```

## Recent Updates

### 2025-10-23: Concurrent Request Optimization

**Problem**: Service could not handle multiple simultaneous requests efficiently due to:
- Blocking vector search operations
- Connection pool exhaustion
- Missing connection lifecycle management

**Solution**:
1. ✅ Async vector search with `asyncio.to_thread()`
2. ✅ Expanded connection pool (20+30)
3. ✅ Added connection timeouts and recycling
4. ✅ Fixed connection leak in KB summary service

**Files Modified**:
- `app/services/vector_search.py` (+1 import, +4 lines for async)
- `app/services/kb_summary.py` (+3 lines for finally block)
- `app/core/database.py` (+3 config parameters)

**Testing Results**:
- ✅ Health check: Passed
- ✅ Meta query ("このナレッジベースについて"): Passed
- ✅ Search query ("アルムナイについて"): Passed

### 2025-10-22: Initial MCP Integration

**Implementation**:
- Created MCP server with two tools (search_documents, get_knowledge_base_summary)
- Integrated with ai-micro-api-admin via HTTP endpoint
- Delegated query intent detection to LLM
- Removed 200+ lines of frontend intent logic

## Troubleshooting

### High Response Times

**Symptoms**: Requests taking >5 seconds
**Possible Causes**:
1. Database connection pool exhausted
2. Ollama service slow/unavailable
3. Large result sets without pagination

**Solutions**:
```bash
# Check connection pool usage
docker exec ai-micro-mcp-admin python -c "
from app.core.database import engine
print(f'Pool size: {engine.pool.size()}')
print(f'Checked out: {engine.pool.checkedout()}')
"

# Check Ollama availability
curl http://localhost:11434/api/tags

# Check database response time
docker exec postgres psql -U postgres -d admindb -c "SELECT COUNT(*) FROM documents;"
```

### Connection Pool Errors

**Symptoms**: "QueuePool limit exceeded"
**Solution**: Increase pool size or reduce connection leak

```python
# Temporary increase (app/core/database.py)
pool_size=30,
max_overflow=50
```

### Vector Search Errors

**Symptoms**: "No results found" or timeout
**Possible Causes**:
1. Missing embeddings in database
2. Ollama service down
3. Incorrect knowledge_base_id filter

**Solutions**:
```sql
-- Check if chunks have embeddings
SELECT COUNT(*) FROM langchain_pg_embedding
WHERE cmetadata->>'knowledge_base_id' = 'YOUR_KB_ID';

-- Check embedding dimensions
SELECT COUNT(*), LENGTH(embedding::text)
FROM langchain_pg_embedding
GROUP BY LENGTH(embedding::text);
```

## Related Documentation

- [Root CLAUDE.md](../CLAUDE.md) - System-wide architecture
- [API Admin CLAUDE.md](../ai-micro-api-admin/CLAUDE.md) - MCP client integration
- [ai-micro-docs/](../ai-micro-docs/) - Detailed API documentation
