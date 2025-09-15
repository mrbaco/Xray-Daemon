from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, status

from schemas import XrayError
from crud.users import get_users
from database import XRAY_INSTANCE, get_session
from security import check_api_key

import schemas


router = APIRouter(prefix='/v1/stats', tags=['Stats'])

@router.get('/', status_code=status.HTTP_200_OK, response_model=schemas.ReadStats[schemas.Inbound])
async def get_stats(
    session: AsyncSession = Depends(get_session),
    _ = Depends(check_api_key)
):
    result = []
    inbound_tags = []

    usersList, _ = await get_users(session)

    for user in usersList:
        if user.inbound_tag not in inbound_tags:
            inbound_tags.append(user.inbound_tag)

    for inbound_tag in inbound_tags:
        download_traffic = await XRAY_INSTANCE.get_inbound_download_traffic(inbound_tag)
        upload_traffic = await XRAY_INSTANCE.get_inbound_upload_traffic(inbound_tag)

        if type(download_traffic) is XrayError:
            download_traffic = None

        if type(upload_traffic) is XrayError:
            upload_traffic = None

        result.append(schemas.Inbound(
            inbound_tag=inbound_tag,
            download_traffic=download_traffic,
            upload_traffic=upload_traffic
        ))

    return schemas.ReadStats(
        inbounds=result
    )
