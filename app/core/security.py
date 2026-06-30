import json
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from app.core.config import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)
security = HTTPBearer()

# .NET claim names
ROLE_CLAIMS = [
    "role",
    "http://schemas.microsoft.com/ws/2008/06/identity/claims/role",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/role",
]

def verify_jwt(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM], 
            options={"verify_exp": False, "verify_aud": False}
        )
        return payload
    except jwt.PyJWTError as e:
        logger.error(f"JWT verification failed{e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def _get_role(payload: dict) -> str:
    for claim in ROLE_CLAIMS:
        value = payload.get(claim)
        if value:
            return value
    return ""

def _get_modules(payload: dict) -> list:
    modules_raw = payload.get("modules", [])
    if isinstance(modules_raw, str):
        try:
            return json.loads(modules_raw)
        except (json.JSONDecodeError, TypeError):
            return []
    return modules_raw

def get_current_user(payload: dict = Depends(verify_jwt)):
    role = _get_role(payload)
    modules = _get_modules(payload)
    
    if role != "SuperAdmin" and "personal-finances" not in modules:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return payload

def get_tenant_id(payload: dict = Depends(get_current_user)) -> Optional[str]:
    role = _get_role(payload)
    tenant_id = payload.get("tenantId")
    
    if not tenant_id and role != "SuperAdmin":
        raise HTTPException(status_code=400, detail="Tenant ID is required for regular users")
    return tenant_id
