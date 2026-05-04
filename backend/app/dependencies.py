"""
Dependencias de FastAPI para autenticación y autorización.
Inyectables via Depends() en los endpoints.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.auth import decode_access_token, UserStore

logger = logging.getLogger(__name__)

# ─── Esquema de seguridad Bearer ─────────────────────────────────────
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Extrae y valida el JWT del header Authorization.
    
    Returns:
        Dict con datos del usuario: username, role, nombre_completo
    
    Raises:
        HTTPException 401 si el token es inválido o expiró
    """
    token = credentials.credentials

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: Optional[str] = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: falta información de usuario",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verificar que el usuario todavía existe y está activo
    user_store = UserStore()
    user = user_store.get_user(username)
    if user is None or not user.get("activo", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o desactivado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "username": user["username"],
        "role": user["role"],
        "nombre_completo": user["nombre_completo"],
    }


class RoleChecker:
    """
    Dependency callable para verificar que el usuario tiene el rol requerido.
    
    Uso:
        @app.get("/endpoint", dependencies=[Depends(RoleChecker("gerente"))])
        async def mi_endpoint(...):
            ...
    
    O como dependencia directa:
        current_user: dict = Depends(RoleChecker("gerente"))
    """

    def __init__(self, required_role: str):
        self.required_role = required_role

    async def __call__(
        self,
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        if current_user["role"] != self.required_role:
            logger.warning(
                f"Acceso denegado: {current_user['username']} "
                f"(rol: {current_user['role']}) intentó acceder a recurso "
                f"que requiere rol: {self.required_role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere rol: {self.required_role}",
            )
        return current_user
