from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError

import os

from database import XRAY_INSTANCE, SessionLocal
from loki_logger import LOGGER
from schemas import XrayError
from crud import users

import schemas


load_dotenv('../.env')

async def process():
    inactivated_users = []
    activated_users = []
    blocked_users = []

    async with SessionLocal() as session:
        try:
            usersList, _ = await users.get_users(session)

            now = datetime.now().replace(microsecond=0)
            reset_traffic_period = float(os.getenv("RESET_TRAFFIC_PERIOD_SECONDS"))

            for user in usersList:
                user_data = schemas.UpdateUser(
                    traffic=user.traffic,
                    limit=user.limit,
                    is_active=user.is_active,
                    is_blocked=user.is_blocked,
                    reset_traffic_date=user.reset_traffic_date
                )

                is_need_to_reset = user_data.reset_traffic_date + timedelta(seconds=reset_traffic_period) <= now

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
                    user_data.is_active == True
                ):
                    user_data.is_active = False

                # reset traffic after "reset traffic date" + "reset traffic period"
                if is_need_to_reset:
                    if (
                        user_data.is_active == False and
                        user_data.is_blocked == False
                    ):
                        user_data.is_active = True

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
                    user_data.is_active == True and
                    user_data.is_blocked == True
                ):
                    blocked_users.append(user.email)
                    user_data.is_active = False

                # activate previously unblocked user
                if (
                    user_data.is_active == False and
                    user_data.is_blocked == False and
                    is_traffic_overage == False
                ):
                    user_data.is_active = True

                # remove user
                if (
                    user_data.is_active == False and
                    user.is_active == True
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
                        inactivated_users.append(user.email)

                # add user
                elif (
                    user_data.is_active == True and
                    user.is_active == False
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
                        activated_users.append(user.email)

                await users.update_user(session, user.inbound_tag, user.email, user_data)

        except SQLAlchemyError as e:
            await session.rollback()

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
            await session.rollback()

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

        finally:
            await session.close()

        LOGGER.info(
            'PROCESSING RESULT',
            extra={
                'tags': {
                    'inactivated_users': ', '.join(inactivated_users),
                    'activated_users': ', '.join(activated_users),
                    'blocked_users': ', '.join(blocked_users)
                }
            }
        )
