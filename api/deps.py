from fastapi import Depends, Header, HTTPException, status

from common.config import get_settings
from common.database import get_db


def require_api_key(x_api_key: str = Header(default="")):
    if x_api_key != get_settings().api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return x_api_key


DBSession = Depends(get_db)
APIKey = Depends(require_api_key)
