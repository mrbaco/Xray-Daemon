from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, status

import os, pytz

from database import XRAY_INSTANCE, get_session
from loki_logger import LOGGER
from schemas import XrayError
from crud import users

import schemas


load_dotenv('../.env')

router = APIRouter(prefix='/v1/routine', tags=['Routine'])

@router.get('/', status_code=status.HTTP_204_NO_CONTENT)
async def run(
    session: Session = Depends(get_session)
):
    usersList, _ = users.get_users(session)
    now = datetime.now(pytz.timezone(os.getenv('TIMEZONE')))

    for user in usersList:
        user_data = schemas.UpdateUser(
            traffic=user.traffic,
            limit=user.limit,
            active=user.active,
            blocked=user.blocked,
            reset_traffic_date=user.reset_traffic_date
        )

        # update traffic
        download_traffic = await XRAY_INSTANCE.get_user_download_traffic(user.email)
        upload_traffic = await XRAY_INSTANCE.get_user_upload_traffic(user.email)

        # block previously blocked user
        if (
            user_data.active == True and
            user_data.blocked == True
        ):
            user_data.active = False

            # compare traffic and limit then set inactive due traffic overage
            if not type(download_traffic) is XrayError and not type(upload_traffic) is XrayError:
                user_data.traffic = download_traffic + upload_traffic

                if (
                    user_data.limit != 0 and
                    user_data.traffic > user_data.limit and
                    user_data.active == True
                ):
                    user_data.active = False

            # remove user
            if user_data.active != user.active:
                result = await XRAY_INSTANCE.remove_user(user.inbound_tag, user.email)

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

            # move reset traffic date to now for blocked users cause not traffic overage
            if (
                user_data.active == False and 
                user_data.blocked == True
            ):
                user_data.reset_traffic_date = now - timedelta(seconds=float(os.getenv("RESET_TRAFFIC_PERIOD_SECONDS")))

            # reset traffic after reset period for traffic overage users
            if (
                user_data.active == False and
                user_data.blocked == False
            ):
                using_period = (now - user_data.reset_traffic_date).seconds

                if (
                    using_period >= float(os.getenv("RESET_TRAFFIC_PERIOD_SECONDS")) or
                    user_data.traffic <= user_data.limit
                ):
                    user_data.active = True
                    user_data.traffic = 0
                    user_data.reset_traffic_date = now

                    # restore user
                    add_user_result = await XRAY_INSTANCE.add_user(
                        inbound_tag=user.inbound_tag,
                        email=user.email,
                        level=user.level,
                        type=user.type,
                        password=user.password,
                        cipher_type=user.cipher_type,
                        uuid=user.uuid,
                        flow=user.flow,
                    )

                    # reset user traffic
                    reset_dtraffic_result = await XRAY_INSTANCE.get_user_download_traffic(user.email, True)
                    reset_utraffic_result = await XRAY_INSTANCE.get_user_upload_traffic(user.email, True)

                    if type(add_user_result) is XrayError:
                        LOGGER.error(
                            'XRAY ERROR',
                            extra={
                                'tags': {
                                    'error_msg': add_user_result.message,
                                    'user.email': user.email
                                }
                            },
                            exc_info=True,
                        )

                    if type(reset_dtraffic_result) is XrayError:
                        LOGGER.error(
                            'XRAY ERROR',
                            extra={
                                'tags': {
                                    'error_msg': reset_dtraffic_result.message,
                                    'user.email': user.email
                                }
                            },
                            exc_info=True,
                        )

                    if type(reset_utraffic_result) is XrayError:
                        LOGGER.error(
                            'XRAY ERROR',
                            extra={
                                'tags': {
                                    'error_msg': reset_utraffic_result.message,
                                    'user.email': user.email
                                }
                            },
                            exc_info=True,
                        )

        if not users.update_user(session, user.inbound_tag, user.email, user_data):
            LOGGER.error(
                'UPDATE USER ERROR',
                extra={
                    'tags': {
                        'user.email': user.email
                    }
                },
                exc_info=True,
            )
