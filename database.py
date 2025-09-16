from typing import AsyncGenerator
from sqlalchemy import Connection, inspect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

import os

from schemas import XrayError
from crud.users import get_users

from loki_logger import LOGGER
import models
from xray import Xray


load_dotenv('.env')

DATABASE_URL = os.getenv('DATABASE_CONNECTION_STRING')
if not DATABASE_URL:
    raise ValueError('DATABASE_CONNECTION_STRING не задан в .env')

XRAY_INSTANCE = Xray(
	os.getenv("GRPC_URL"),
	int(os.getenv("GRPC_PORT"))
)

async_engine = create_async_engine(DATABASE_URL)

SessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session

        except SQLAlchemyError as e:
            await session.rollback()
            raise e

        finally:
            await session.close()

async def import_database():
    async with async_engine.connect() as conn:
        def create_database(sync_conn: Connection):
            if not inspect(sync_conn).has_table('users'):
                models.Base.metadata.create_all(bind=sync_conn)

            sync_conn.close()

        await conn.run_sync(lambda sync_conn: create_database(sync_conn))

    session = SessionLocal()

    try:
        usersList, total = await get_users(session)

        if total > 0:
            for user in usersList:
                if user.active == True:
                    result = await XRAY_INSTANCE.add_user(
                        inbound_tag=user.inbound_tag,
                        email=user.email,
                        level=user.level,
                        type=user.type,
                        password=user.password,
                        cipher_type=user.cipher_type,
                        uuid=user.uuid,
                        flow=user.flow,
                    )

                    if type(result) is XrayError:
                        LOGGER.error(
                            'XRAY ERROR',
                            extra={
                                'tags': {
                                    'error_msg': result.message,
                                    'user.email': user.email
                                }
                            },
                            exc_info=True,
                        )

    except SQLAlchemyError as e:
        await session.rollback()
        raise e

    finally:
        await session.close()
