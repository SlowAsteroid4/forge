"""BaseRepository genérico para SQLAlchemy 2.0."""

from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from forge.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)
PK = TypeVar("PK")


class BaseRepository(Generic[ModelT, PK]):
    """CRUD genérico parametrizado por tipo de modelo y tipo de PK.

    Los repos concretos heredan y pasan model_class en __init__.
    Las mutaciones usan flush() — el commit es responsabilidad del llamador (service).
    """

    def __init__(self, session: Session, model_class: type[ModelT]) -> None:
        self._session = session
        self._model_class = model_class

    def get(self, pk: Any) -> ModelT | None:
        """Retorna la entidad por PK o None si no existe."""
        return self._session.get(self._model_class, pk)

    def list_all(self, limit: int = 100, offset: int = 0) -> list[ModelT]:
        """Lista todas las entidades con paginación básica."""
        stmt = select(self._model_class).limit(limit).offset(offset)
        return list(self._session.scalars(stmt))

    def create(self, entity: ModelT) -> ModelT:
        """Persiste una nueva entidad y retorna el objeto actualizado."""
        self._session.add(entity)
        self._session.flush()
        self._session.refresh(entity)
        return entity

    def update(self, entity: ModelT) -> ModelT:
        """Persiste cambios sobre una entidad ya cargada en sesión."""
        self._session.flush()
        self._session.refresh(entity)
        return entity

    def delete(self, entity: ModelT) -> None:
        """Elimina una entidad de la base de datos."""
        self._session.delete(entity)
        self._session.flush()

    def count(self) -> int:
        """Retorna el total de filas en la tabla."""
        stmt = select(func.count()).select_from(self._model_class)
        return self._session.scalar(stmt) or 0
