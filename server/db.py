from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from server.config import get_settings

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            f"sqlite:///{settings.db_path}",
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(_engine, "connect")
        def _set_pragmas(dbapi_conn, _record):
            # isolation_level=None desliga o BEGIN implícito do pysqlite;
            # o controle transacional fica todo com o evento "begin" abaixo.
            dbapi_conn.isolation_level = None
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        @event.listens_for(_engine, "begin")
        def _begin_immediate(conn):
            # Write-lock no início da transação: claims concorrentes serializam
            # sem janela de corrida nem erro de upgrade de lock.
            conn.exec_driver_sql("BEGIN IMMEDIATE")

    return _engine


def reset_engine() -> None:
    """Descarta o engine em cache (usado nos testes para trocar de banco)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def init_db() -> None:
    import server.models  # noqa: F401  garante que as tabelas estão registradas

    SQLModel.metadata.create_all(get_engine())


def get_session():
    with Session(get_engine()) as session:
        yield session
