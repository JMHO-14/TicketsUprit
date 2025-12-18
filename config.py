from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Configuración de Base de Datos
    # Lee estas variables directamente de tu archivo .env
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: str = "5432"  # Valor por defecto si no está en .env
    
    # Configuración de Seguridad (JWT)
    SECRET_KEY: str = "clave_secreta_por_defecto_cambiar_en_prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 días

    # Configuración de la App
    DEBUG: bool = True
    APP_NAME: str = "SisoAI"

    class Config:
        env_file = ".env"
        # Esto es importante: ignora variables extra en el .env que no usemos
        extra = "ignore" 
        # Sensible a mayúsculas/minúsculas para coincidir con tus variables
        case_sensitive = True

    @property
    def DATABASE_URL(self) -> str:
        """Construye la URL de conexión automáticamente"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

# Instancia única de configuración para importar en otros archivos
settings = Settings()