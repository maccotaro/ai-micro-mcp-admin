# ai-micro-mcp-admin Code Style Guidelines

## Python Standards
- Python 3.11+を使用
- 型ヒントを必ず使用
- async/awaitをI/O操作に優先使用

## File Size Limit
- **500行以下/ファイル**（ドキュメントを除く）

## Directory Structure
```
app/
├── main.py                  # FastAPIアプリケーション
├── core/
│   ├── config.py            # 設定管理
│   ├── database.py          # データベース接続プール
│   └── auth.py              # JWT認証
├── services/
│   ├── mcp_server.py        # MCPサーバー実装
│   ├── vector_search.py     # ベクトル検索（async）
│   └── kb_summary.py        # ナレッジベース要約
└── routers/
    └── mcp.py               # MCPエンドポイント
```

## Async Patterns
```python
# I/O操作はasyncio.to_threadでラップ
results = await asyncio.to_thread(
    blocking_function,
    arg1, arg2
)
```

## Database Connection Management
```python
# 必ずfinallyブロックで接続を閉じる
try:
    session = SessionLocal()
    # 処理
finally:
    session.close()
```

## Error Handling
- 包括的なロギング
- 詳細なエラーメッセージ
- 適切なHTTPステータスコード

## MCP Tool Implementation
1. `_create_tools_list()`でスキーマ定義
2. ハンドラメソッドを実装
3. `call_tool()`デコレータで登録
4. テスト追加
5. ドキュメント更新

## Import Order
1. 標準ライブラリ
2. サードパーティ（fastapi, sqlalchemy等）
3. ローカルモジュール
4. 型定義
