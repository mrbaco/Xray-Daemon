from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
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

engine = create_engine(DATABASE_URL)

if not inspect(engine).has_table('users'):
    models.Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(bind=engine)

def get_session():
    session = SessionLocal()

    try:
        yield session
    except SQLAlchemyError as e:
        session.rollback()
        raise e
    finally:
        session.close()

async def import_database():
    session = SessionLocal()

    try:
        usersList, total = get_users(session)

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
                                    'error_type': type(e).__name__,
                                    'error_msg': str(e),
                                    'user.email': user.email
                                }
                            },
                            exc_info=True,
                        )

    except SQLAlchemyError as e:
        session.rollback()
        raise e
    finally:
        session.close()
