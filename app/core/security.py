from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from app.core.config import settings
from typing import Optional

security = HTTPBearer()

def verify_jwt(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM], 
            options={"verify_exp": False} # The API gateway handles expiration, but we can verify it if needed
        )
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def get_current_user(payload: dict = Depends(verify_jwt)):
    role = payload.get("role", "")
    modules = payload.get("modules", [])
    
    if role != "SuperAdmin" and "personal-finances" not in modules:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return payload

def get_tenant_id(payload: dict = Depends(get_current_user)) -> Optional[str]:
    tenant_id = payload.get("tenantId")
    if not tenant_id and payload.get("role") != "SuperAdmin":
        raise HTTPException(status_code=400, detail="Tenant ID is required for regular users")
    return tenant_id
