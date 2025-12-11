# Code Style and Conventions for ai-micro-mcp-admin

## File Size Limits
- **Maximum lines per file**: 500 lines (including comments and blank lines)
- Automatically refactor if approaching 500 lines

## Python Code Style

### Type Hints
- Use Python type annotations for all functions
- Example:
```python
def search_documents(query: str, kb_id: str, threshold: float = 0.6) -> List[Dict]:
    ...
```

### Async/Await
- Prefer async for I/O operations
- Wrap blocking operations with `asyncio.to_thread()`
```python
results = await asyncio.to_thread(
    self.vector_store.similarity_search_with_score,
    query, k=top_k, filter=filter_condition
)
```

### Error Handling
- Comprehensive logging and error messages
- Use try/except with proper cleanup in finally blocks

### Naming Conventions
- Classes: PascalCase (e.g., `VectorSearchService`)
- Functions/Methods: snake_case (e.g., `search_documents`)
- Constants: UPPER_SNAKE_CASE (e.g., `DATABASE_URL`)
- Private methods: _leading_underscore (e.g., `_create_tools_list`)

### Docstrings
- Use docstrings for public functions and classes
- Keep comments minimal where code is self-explanatory

## Adding New MCP Tools

1. Define tool schema in `app/services/mcp_server.py:_create_tools_list()`
2. Implement handler method (e.g., `_my_new_tool()`)
3. Register in `call_tool()` decorator
4. Add integration tests
5. Update CLAUDE.md documentation

## Database Patterns
- Use connection pool with proper lifecycle management
- Always close connections in `finally` blocks
- Singleton pattern for service instances
