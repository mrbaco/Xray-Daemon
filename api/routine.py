from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
from fastapi import APIRouter, BackgroundTasks, Depends, status

import os

from database import XRAY_INSTANCE, SessionLocal
from loki_logger import LOGGER
from schemas import XrayError
from crud import users
from security import check_api_key

import schemas


load_dotenv('../.env')

router = APIRouter(prefix='/v1/routine', tags=['Routine'])

async def process():
    session = SessionLocal()

    try:
        usersList, _ = users.get_users(session)

        now = datetime.now().replace(microsecond=0)
        reset_traffic_period = float(os.getenv("RESET_TRAFFIC_PERIOD_SECONDS"))

        for user in usersList:
            user_data = schemas.UpdateUser(
                traffic=user.traffic,
                limit=user.limit,
                active=user.active,
                blocked=user.blocked,
                reset_traffic_date=user.reset_traffic_date
            )

            is_need_to_reset = user_data.reset_traffic_date + timedelta(seconds=reset_traffic_period) <= now

            # get user traffic info
            download_traffic = await XRAY_INSTANCE.get_user_download_traffic(user.email, is_need_to_reset)
            upload_traffic = await XRAY_INSTANCE.get_user_upload_traffic(user.email, is_need_to_reset)

            if is_need_to_reset == False:
                user_data.traffic = (
                    download_traffic if not type(download_traffic) is XrayError else 0 +
                    upload_traffic if not type(upload_traffic) is XrayError else 0
                )

            # compare traffic and limit then set inactive due traffic overage
            is_traffic_overage = (
                user_data.limit != 0 and
                user_data.traffic > user_data.limit
            )

            if (
                is_traffic_overage == True and
                user_data.active == True
            ):
                is_traffic_overage = True
                user_data.active = False

            # reset traffic after "reset traffic date" + "reset traffic period"
            if is_need_to_reset:
                if (
                    user_data.active == False and
                    user_data.blocked == False
                ):
                    user_data.active = True

                user_data.traffic = 0
                user_data.reset_traffic_date = now

                if (
                    type(is_need_to_reset) is XrayError or
                    type(upload_traffic) is XrayError
                ):
                    error_msg = []

                    error_msg.append(is_need_to_reset.message if type(is_need_to_reset) is XrayError else '')
                    error_msg.append(upload_traffic.message if type(upload_traffic) is XrayError else '')

                    LOGGER.error(
                        'RESET TRAFFIC ERROR',
                        extra={
                            'tags': {
                                'error_msg': '\n'.join(error_msg),
                                'email': user.email
                            }
                        },
                        exc_info=True,
                    )

            # inactivate previously blocked user
            if (
                user_data.active == True and
                user_data.blocked == True
            ):
                user_data.active = False

            # activate previously unblocked user
            if (
                user_data.active == False and
                user_data.blocked == False and
                is_traffic_overage == False
            ):
                user_data.active = True

            # remove user
            if (
                user_data.active == False and
                user.active == True
            ):
                result = await XRAY_INSTANCE.remove_user(user.inbound_tag, user.email)

                if type(result) is XrayError:
                    LOGGER.error(
                        'REMOVE USER ERROR',
                        extra={
                            'tags': {
                                'error_msg': result.message,
                                'email': user.email
                            }
                        },
                            exc_info=True,
                    )
                else:
                    LOGGER.info(
                        'INACTIVATE USER',
                        extra={
                            'tags': {
                                'email': user.email
                            }
                        }
                    )

            # add user
            elif (
                user_data.active == True and
                user.active == False
            ):
                user_data.traffic = 0
                user_data.reset_traffic_date = now

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
                        'ADD USER ERROR',
                        extra={
                            'tags': {
                                'error_msg': result.message,
                                'email': user.email
                            }
                        },
                        exc_info=True,
                    )
                else:
                    LOGGER.info(
                        'ACTIVATE USER',
                        extra={
                            'tags': {
                                'email': user.email
                            }
                        }
                    )

            if not users.update_user(session, user.inbound_tag, user.email, user_data):
                LOGGER.error(
                    'UPDATE USER ERROR',
                    extra={
                        'tags': {
                            'email': user.email
                        }
                    },
                    exc_info=True,
                )

    except SQLAlchemyError as e:
        session.rollback()

        LOGGER.error(
            'PROCESSING ERROR (SQL)',
            extra={
                'tags': {
                    'error_type': type(e).__name__,
                    'error_msg': str(e)
                }
            },
            exc_info=True,
        )

    except Exception as e:
        LOGGER.error(
            'PROCESSING ERROR',
            extra={
                'tags': {
                    'error_type': type(e).__name__,
                    'error_msg': str(e)
                }
            },
            exc_info=True,
        )

    session.close()

@router.post('/', status_code=status.HTTP_202_ACCEPTED)
async def run(
    background_tasks: BackgroundTasks,
    _ = Depends(check_api_key)
):
    background_tasks.add_task(process)
