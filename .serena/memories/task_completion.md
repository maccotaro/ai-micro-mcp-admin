# ai-micro-mcp-admin Task Completion Checklist

## Before Completing Any Task

### 1. Code Quality
- [ ] 型ヒントが適切に使用されている
- [ ] ファイルサイズが500行以下
- [ ] 適切なエラーハンドリング
- [ ] ログ出力が適切

### 2. Async Patterns
- [ ] I/O操作はasyncio.to_threadでラップ
- [ ] ブロッキング操作がない
- [ ] 適切なawait使用

### 3. Database
- [ ] コネクションが適切にクローズされる
- [ ] finallyブロックでの接続解放
- [ ] プール設定が適切

### 4. MCP Tools
- [ ] スキーマ定義が正確
- [ ] ハンドラーの実装
- [ ] call_toolへの登録
- [ ] エラーハンドリング

### 5. Authentication
- [ ] JWT検証が適切
- [ ] 権限チェック
- [ ] JWKS検証

### 6. Testing
- [ ] ヘルスチェックが動作
- [ ] MCPツールのテスト
- [ ] エラーケースの確認

### 7. Performance
- [ ] コネクションプール使用状況確認
- [ ] レスポンス時間確認
- [ ] 同時リクエスト対応

## After Task Completion
- [ ] ヘルスチェック確認
- [ ] MCPチャットテスト
- [ ] コネクションプール状態確認
- [ ] Dockerビルド確認
- [ ] ドキュメント更新（CLAUDE.md）
