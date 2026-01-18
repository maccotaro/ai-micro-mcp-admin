"""データベース接続"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import settings

# データベースエンジン（並行処理最適化）
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,          # 接続の健全性チェック
    pool_size=20,                # 基本プールサイズ（同時リクエスト対応）
    max_overflow=30,             # オーバーフロー接続数
    pool_recycle=3600,           # 接続リサイクル（1時間）
    pool_timeout=30,             # 接続取得タイムアウト（30秒）
    echo_pool=False              # プールデバッグログは無効
)

# セッションファクトリー
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """データベースセッションを取得"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
