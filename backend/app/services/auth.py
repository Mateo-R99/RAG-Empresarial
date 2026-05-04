"""
Servicio de autenticación con JWT y almacenamiento de usuarios en JSON.
Manejo de tokens, hashing de contraseñas y gestión de usuarios.
"""

import json
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

logger = logging.getLogger(__name__)

# ─── Ruta del archivo de usuarios ────────────────────────────────────
USERS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "users.json")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash bcrypt."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def hash_password(password: str) -> str:
    """Genera el hash bcrypt de una contraseña."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


class UserStore:
    """Almacén de usuarios basado en archivo JSON."""

    def __init__(self, filepath: str = USERS_FILE):
        self.filepath = filepath
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Crea el archivo de usuarios con datos iniciales si no existe."""
        if not os.path.exists(self.filepath):
            initial_users = {
                "empleado1": {
                    "username": "empleado1",
                    "nombre_completo": "Empleado Demo",
                    "role": "empleado",
                    "hashed_password": hash_password("emp123"),
                    "activo": True,
                },
                "gerente1": {
                    "username": "gerente1",
                    "nombre_completo": "Gerente Demo",
                    "role": "gerente",
                    "hashed_password": hash_password("ger123"),
                    "activo": True,
                },
            }
            os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(initial_users, f, indent=2, ensure_ascii=False)
            logger.info(f"Archivo de usuarios creado en {self.filepath}")

    def _load_users(self) -> dict:
        """Carga todos los usuarios desde el archivo JSON."""
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error cargando usuarios: {e}")
            return {}

    def get_user(self, username: str) -> Optional[dict]:
        """Obtiene un usuario por su nombre de usuario."""
        users = self._load_users()
        return users.get(username)

    def authenticate(self, username: str, password: str) -> Optional[dict]:
        """Autentica un usuario verificando credenciales."""
        user = self.get_user(username)
        if not user:
            logger.warning(f"Intento de login con usuario inexistente: {username}")
            return None

        if not user.get("activo", True):
            logger.warning(f"Intento de login con usuario desactivado: {username}")
            return None

        if not verify_password(password, user["hashed_password"]):
            logger.warning(f"Contraseña incorrecta para usuario: {username}")
            return None

        logger.info(f"Login exitoso: {username} (rol: {user['role']})")
        return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crea un token JWT con los datos proporcionados."""
    settings = get_settings()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    """Decodifica y valida un token JWT."""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        logger.warning(f"Token JWT inválido: {e}")
        return None
