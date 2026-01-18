# Suggested Commands for ai-micro-mcp-admin

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload
```

## Docker Commands

```bash
# Start service (WSL2 + NVIDIA GPU)
docker compose up -d

# Start service (M3 Mac / CPU)
docker compose -f docker-compose.mac.yml up -d

# View logs
docker compose logs -f ai-micro-mcp-admin

# Restart after code changes
docker compose restart

# Stop service
docker compose down

# Rebuild image
docker compose build
```

## Testing

```bash
# Health check
curl http://localhost:8004/health

# MCP chat (requires JWT)
curl -X POST http://localhost:8004/mcp/chat \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "アルムナイについて教えて",
    "knowledge_base_id": "YOUR_KB_ID"
  }'
```

## Troubleshooting

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

## System Utilities (Linux)
- `git`: Version control
- `ls`: List directory contents
- `cd`: Change directory
- `grep`: Pattern matching
- `find`: File search
- `cat`: View file contents
- `docker`: Container management
