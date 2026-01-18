# Task Completion Checklist for ai-micro-mcp-admin

## Before Completing a Task

### 1. Code Quality
- [ ] File does not exceed 500 lines
- [ ] Type hints added to all functions
- [ ] Error handling with proper cleanup
- [ ] Async patterns used for I/O operations

### 2. Testing
```bash
# Health check
curl http://localhost:8004/health

# Test MCP functionality (requires valid JWT)
curl -X POST http://localhost:8004/mcp/chat \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "knowledge_base_id": "test-kb-id"}'
```

### 3. Docker Verification
```bash
# Restart service after changes
docker compose restart

# Check logs for errors
docker compose logs -f ai-micro-mcp-admin

# Verify container is running
docker ps | grep mcp-admin
```

### 4. Documentation
- [ ] Update CLAUDE.md if architecture changed
- [ ] Update comments if behavior changed
- [ ] Add docstrings for new functions

### 5. Integration
- [ ] Verify integration with ai-micro-api-admin
- [ ] Check JWT authentication works
- [ ] Verify PostgreSQL connection

## After Task Completion

1. Run health check to confirm service is stable
2. Test any modified endpoints
3. Check container logs for errors
4. Update relevant documentation
