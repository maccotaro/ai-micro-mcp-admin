"""JWT認証モジュール"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime

import httpx
from jose import jwt, jwk
from jose.exceptions import JWTError, ExpiredSignatureError
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

# JWKSキャッシュ（10分間有効）
_jwks_cache: Optional[Dict[str, Any]] = None
_jwks_cache_time: Optional[datetime] = None


async def get_jwks() -> Dict[str, Any]:
    """JWKS（公開鍵セット）を取得"""
    global _jwks_cache, _jwks_cache_time

    # キャッシュが有効か確認（10分間）
    if _jwks_cache and _jwks_cache_time:
        elapsed = (datetime.utcnow() - _jwks_cache_time).total_seconds()
        if elapsed < 600:  # 10分
            return _jwks_cache

    # JWKSを取得
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(settings.jwks_url)
            response.raise_for_status()
            jwks = response.json()

            # キャッシュ更新
            _jwks_cache = jwks
            _jwks_cache_time = datetime.utcnow()

            logger.info("JWKS fetched and cached")
            return jwks

    except Exception as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable"
        )


async def verify_token(token: str) -> Dict[str, Any]:
    """JWTトークンを検証してペイロードを返す"""

    try:
        # 1. トークンヘッダーからkidを取得
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing kid"
            )

        # 2. JWKSから公開鍵を取得
        jwks = await get_jwks()

        public_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                public_key = jwk.construct(key)
                break

        if not public_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: public key not found"
            )

        # 3. トークン検証・デコード
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer
        )

        logger.info(f"Token verified for user: {payload.get('sub')}")
        return payload

    except ExpiredSignatureError:
        logger.warning("Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token verification failed"
        )
