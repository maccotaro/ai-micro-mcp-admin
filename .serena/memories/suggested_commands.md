# ai-micro-mcp-admin Suggested Commands

## Development
```bash
# 依存関係インストール
pip install -r requirements.txt

# 開発サーバー起動
uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload
```

## Docker Operations

### WSL2 + NVIDIA GPU (デフォルト)
```bash
cd ai-micro-mcp-admin && docker compose up -d
```

### M3 Mac (CPU)
```bash
cd ai-micro-mcp-admin && docker compose -f docker-compose.mac.yml up -d
```

### 共通コマンド
```bash
# ログ確認
docker compose logs -f ai-micro-mcp-admin

# コンテナ再起動
docker compose restart

# 停止
docker compose down
```

## Testing
```bash
# ヘルスチェック
curl http://localhost:8004/health

# MCPチャット（JWT必須）
curl -X POST http://localhost:8004/mcp/chat \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "アルムナイについて教えて",
    "knowledge_base_id": "9fba1ff9-3159-4417-a5d1-cf6a079c3a1b"
  }'
```

## Troubleshooting
```bash
# コネクションプール確認
docker exec ai-micro-mcp-admin python -c "
from app.core.database import engine
print(f'Pool size: {engine.pool.size()}')
print(f'Checked out: {engine.pool.checkedout()}')
"

# Ollama確認
curl http://localhost:11434/api/tags

# データベース応答時間確認
docker exec postgres psql -U postgres -d admindb -c "SELECT COUNT(*) FROM documents;"

# チャンク確認
docker exec postgres psql -U postgres -d admindb -c "
SELECT COUNT(*) FROM langchain_pg_embedding
WHERE cmetadata->>'knowledge_base_id' = 'YOUR_KB_ID';
"
```

## Environment
- **Service URL**: http://localhost:8004
- **Ollama**: http://localhost:11434
- **Auth JWKS**: http://localhost:8002/.well-known/jwks.json
