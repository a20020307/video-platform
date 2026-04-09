from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# These are initialised in main.py lifespan before any request arrives.
engine = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str, echo: bool = False) -> None:
    global engine, async_session_factory
    engine = create_async_engine(database_url, echo=echo, pool_pre_ping=True)
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def create_tables() -> None:
    """Create all tables that don't exist yet (dev/test convenience)."""
    # Import models so they register with Base.metadata
    from app.models import user, video, upload_session  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
