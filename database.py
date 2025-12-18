from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

# 1. Crear el motor de conexión
# pool_pre_ping=True ayuda a reconectar si la BD cierra la conexión por inactividad
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# 2. Crear la fábrica de sesiones
# IMPORTANTE: expire_on_commit=False evita el error "Instance is not bound to a Session"
# Esto permite seguir usando los objetos (leer sus IDs) después de hacer db.commit()
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine, 
    expire_on_commit=False 
)

# 3. DEFINIR LA BASE ÚNICA
Base = declarative_base()

# 4. Función para obtener sesión (Dependency Injection)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()