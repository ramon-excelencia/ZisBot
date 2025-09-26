from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import update, delete, func
from pydantic import BaseModel
from app.config.database import Base

# Type variables para genéricos
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Repositorio base con operaciones CRUD async"""
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """Crear un nuevo registro"""
        obj_in_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]:
        """Obtener un registro por ID"""
        result = await db.execute(select(self.model).filter(self.model.id == id))
        return result.scalar_one_or_none()
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Obtener múltiples registros con paginación y filtros"""
        query = select(self.model)
        
        # Aplicar filtros si existen
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.filter(getattr(self.model, key) == value)
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_count(
        self, 
        db: AsyncSession, 
        *, 
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Contar registros con filtros opcionales"""
        query = select(func.count(self.model.id))
        
        # Aplicar filtros si existen
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.filter(getattr(self.model, key) == value)
        
        result = await db.execute(query)
        return result.scalar()
    
    async def update(
        self, 
        db: AsyncSession, 
        *, 
        db_obj: ModelType, 
        obj_in: UpdateSchemaType
    ) -> ModelType:
        """Actualizar un registro existente"""
        obj_data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, 'model_dump') else obj_in.dict(exclude_unset=True)
        
        for field, value in obj_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def delete(self, db: AsyncSession, *, id: int) -> Optional[ModelType]:
        """Eliminar un registro por ID"""
        db_obj = await self.get(db, id)
        if db_obj:
            await db.delete(db_obj)
            await db.commit()
        return db_obj
    
    async def get_by_field(
        self, 
        db: AsyncSession, 
        *, 
        field: str, 
        value: Any
    ) -> Optional[ModelType]:
        """Obtener un registro por un campo específico"""
        if not hasattr(self.model, field):
            return None
        
        query = select(self.model).filter(getattr(self.model, field) == value)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_multi_by_field(
        self, 
        db: AsyncSession, 
        *, 
        field: str, 
        value: Any,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Obtener múltiples registros por un campo específico"""
        if not hasattr(self.model, field):
            return []
        
        query = select(self.model).filter(getattr(self.model, field) == value).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def exists(self, db: AsyncSession, *, id: int) -> bool:
        """Verificar si existe un registro por ID"""
        query = select(func.count(self.model.id)).filter(self.model.id == id)
        result = await db.execute(query)
        count = result.scalar()
        return count > 0
    
    async def bulk_create(
        self, 
        db: AsyncSession, 
        *, 
        objs_in: List[CreateSchemaType]
    ) -> List[ModelType]:
        """Crear múltiples registros en lote"""
        db_objs = []
        for obj_in in objs_in:
            obj_in_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
            db_obj = self.model(**obj_in_data)
            db_objs.append(db_obj)
        
        db.add_all(db_objs)
        await db.commit()
        
        # Refresh all objects
        for db_obj in db_objs:
            await db.refresh(db_obj)
        
        return db_objs


# Repositorios específicos con métodos personalizados
class ClinicaRepository(BaseRepository):
    """Repositorio específico para Clínica"""
    
    async def get_by_whatsapp_did(self, db: AsyncSession, *, did_whatsapp: str) -> Optional[ModelType]:
        """Obtener clínica por DID de WhatsApp"""
        return await self.get_by_field(db, field="did_whatsapp", value=did_whatsapp)
    
    async def get_active_clinics(self, db: AsyncSession) -> List[ModelType]:
        """Obtener solo clínicas activas"""
        return await self.get_multi_by_field(db, field="activa", value=True)


class PacienteRepository(BaseRepository):
    """Repositorio específico para Paciente"""
    
    async def get_by_dni(self, db: AsyncSession, *, dni: str) -> Optional[ModelType]:
        """Obtener paciente por DNI y clínica"""
        query = select(self.model).filter(
            self.model.dni == dni,            
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_telefono(self, db: AsyncSession, *, telefono: str) -> Optional[ModelType]:
        """Obtener paciente por teléfono"""
        query = select(self.model).filter(
            self.model.telefono == telefono,            
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()


class TurnoRepository(BaseRepository):
    """Repositorio específico para Turno"""
    
    async def get_by_fecha_profesional(
        self, 
        db: AsyncSession, 
        *, 
        id_profesional: int, 
        fecha_inicio: str,
        fecha_fin: str
    ) -> List[ModelType]:
        """Obtener turnos por profesional en un rango de fechas"""
        query = select(self.model).filter(
            self.model.id_profesional == id_profesional,
            self.model.fecha_hora >= fecha_inicio,
            self.model.fecha_hora <= fecha_fin
        ).order_by(self.model.fecha_hora)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_by_paciente(
        self, 
        db: AsyncSession, 
        *, 
        id_paciente: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Obtener turnos por paciente"""
        return await self.get_multi_by_field(
            db, 
            field="id_paciente", 
            value=id_paciente,
            skip=skip,
            limit=limit
        )