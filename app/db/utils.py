import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


@asynccontextmanager
async def transaction(db: AsyncSession) -> AsyncGenerator[None, None]:
    """if select was called before than implicit transaction has already started"""
    if not db.in_transaction():
        async with db.begin():
            logger.debug("explicit transaction begin")
            yield
        logger.debug("explicit transaction commit")
    else:
        logger.debug("already in transaction")
        yield
        if db.in_transaction():
            await db.commit()
            logger.debug("implicit transaction commit")