"""
Database configuration for SQLite + SQLModel.
"""

from sqlmodel import SQLModel, create_engine, Session
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Ruta por defecto para la base de datos
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "plan.db"


class Database:
    """
    Maneja la conexión a SQLite y las sesiones.

    Usage:
        db = Database()
        db.create_tables()

        with db.get_session() as session:
            plan = session.get(Plan, 1)
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Inicializa la conexión a la base de datos.

        Args:
            db_path: Ruta al archivo SQLite. Si es None, usa el default.
        """
        if db_path is None:
            db_path = DEFAULT_DB_PATH

        # Asegurar que el directorio existe
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,  # Cambiar a True para debug de SQL
            connect_args={"check_same_thread": False},  # Necesario para SQLite
        )

        logger.info(f"Database initialized at: {db_path}")

    def create_tables(self) -> None:
        """
        Crea todas las tablas definidas en los modelos SQLModel.

        Importa todos los modelos primero para que SQLModel los conozca.
        """
        # Importar modelos para que SQLModel los registre
        from models.db import global_data, plan_data, trazabilidad, survey  # noqa
        # Sprint 1 new models are in plan_data — already imported above

        SQLModel.metadata.create_all(self.engine)
        logger.info("All tables created successfully")

    def get_session(self) -> Session:
        """
        Retorna una nueva sesión de base de datos.

        Returns:
            Session de SQLModel

        Note:
            Usar con context manager:
            with db.get_session() as session:
                ...
        """
        return Session(self.engine)

    def drop_tables(self) -> None:
        """
        Elimina todas las tablas. (Solo para desarrollo/testing)
        """
        SQLModel.metadata.drop_all(self.engine)
        logger.warning("All tables dropped")


# Singleton instance
_db_instance: Optional[Database] = None


def get_database() -> Database:
    """
    Factory function que retorna una instancia singleton de Database.

    Returns:
        Database instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
