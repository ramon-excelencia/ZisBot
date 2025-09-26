import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

# Cargar las variables de entorno
load_dotenv()

# Configuración de la base de datos
DATABASE_PG_URL = os.getenv("DATABASE_PG_URL")
# Motor async para PostgreSQL
engine = create_async_engine(
    DATABASE_PG_URL,
    echo=True,  # Para debug, cambiar a False en producción
    future=True
)

# Factory para sesiones async
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base para los modelos
class Base(DeclarativeBase):
    pass

# Dependencia para obtener sesión de DB
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Función para crear todas las tablas
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Función para cerrar conexiones
async def close_db():
    await engine.dispose()