# ai-micro-mcp-admin Project Overview

## Purpose
MCP（Model Context Protocol）管理サービス。ナレッジベース向けのインテリジェントチャット機能を提供。MCPサーバー機能、JWT認証、ベクトル検索、ナレッジベース要約を実装。

## Technology Stack
- **Framework**: FastAPI
- **Language**: Python 3.11+
- **MCP**: Model Context Protocol SDK
- **Embeddings**: Ollama (embeddinggemma:300m)
- **Vector Store**: PGVector (PostgreSQL + pgvector拡張)
- **Database**: PostgreSQL (SQLAlchemy)
- **Container**: Docker

## Architecture
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

## MCP Tools

### 1. search_documents
ナレッジベース内のドキュメントをセマンティック検索。

**Parameters**:
- `query`: 検索クエリ
- `knowledge_base_id`: ナレッジベースUUID
- `threshold`: 類似度閾値 (0.0-1.0, default: 0.6)
- `max_results`: 最大結果数 (default: 10, max: 50)

### 2. get_knowledge_base_summary
ナレッジベース全体の概要と統計情報を取得。

**Parameters**:
- `knowledge_base_id`: ナレッジベースUUID

## Key Features
- **Concurrent Request Support**: asyncio.to_threadによる非同期処理
- **Connection Pool**: 20 base + 30 overflow = 50 connections
- **JWT Authentication**: RS256アルゴリズム、JWKS検証

## Port Configuration
- **Service Port**: 8004
- **Health Check**: `/health`

## Backend Dependencies
- PostgreSQL (admindb): pgvector拡張
- Ollama: embeddinggemma:300mモデル
- Auth Service: JWKS公開鍵取得

## Multiplatform Support
- **WSL2 + NVIDIA GPU**: `docker compose up -d`
- **M3 Mac (CPU)**: `docker compose -f docker-compose.mac.yml up -d`
