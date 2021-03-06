import asyncio

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import event
from sqlalchemy.engine import Transaction
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.db.base import engine
from app.db.middleware import session_context_var
from app.main import app


@pytest.fixture(scope="session")
def event_loop(request):
    """Redefined event loop fixture with bigger scope"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db():
    # https://docs.sqlalchemy.org/en/14/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False, future=True)
    await connection.begin_nested()

    @event.listens_for(session.sync_session, "after_transaction_end")
    def end_savepoint(session: Session, transaction: Transaction) -> None:
        """async events are not implemented yet, recreates savepoints to avoid final commits"""
        # https://github.com/sqlalchemy/sqlalchemy/issues/5811#issuecomment-756269881
        if connection.closed:
            return
        if not connection.in_nested_transaction():
            connection.sync_connection.begin_nested()

    yield session

    if session.in_transaction():
        await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
def db_context(db: AsyncSession):
    token = session_context_var.set(db)
    yield
    session_context_var.reset(token)


@pytest_asyncio.fixture
async def client(db_context):
    async with AsyncClient(
        app=app,
        base_url="http://test",
    ) as client:
        yield client
