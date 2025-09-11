from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status

from schemas import XrayError
from database import XRAY_INSTANCE, get_session
from crud import users
from security import check_api_key

import schemas


router = APIRouter(prefix='/v1/users', tags=['Users'])

@router.post('/{inbound_tag}', status_code=status.HTTP_201_CREATED, response_model=schemas.ReadUser)
async def create_user(
    inbound_tag: str,
    user_data: schemas.CreateUser,
    session: Session = Depends(get_session),
    _ = Depends(check_api_key)
):
    user = users.create_user(session, inbound_tag, user_data)

    if not user:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, result.message)

    return user

@router.get('/{inbound_tag}', status_code=status.HTTP_200_OK, response_model=schemas.ReadUsers[schemas.ReadUser])
async def get_users(
    inbound_tag: str,
    session: Session = Depends(get_session),
    _ = Depends(check_api_key)
):
    usersList, _ = users.get_users(session, inbound_tag)

    return schemas.ReadUsers(
        users=usersList
    )

@router.get('/{inbound_tag}/{email}', status_code=status.HTTP_200_OK, response_model=schemas.ReadUser)
async def get_user(
    inbound_tag: str,
    email: str,
    session: Session = Depends(get_session),
    _ = Depends(check_api_key)
):
    usersList, total = users.get_users(session, inbound_tag, email)

    if total != 1:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    return usersList[0]

@router.delete('/{inbound_tag}/{email}', status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(
    inbound_tag: str,
    email: str,
    session: Session = Depends(get_session),
    _ = Depends(check_api_key)
):
    if not users.delete_user(session, inbound_tag, email):
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    result = await XRAY_INSTANCE.remove_user(inbound_tag, email)

    if type(result) is XrayError and "not found" not in result.message:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, result.message)

@router.patch('/{inbound_tag}/{email}', status_code=status.HTTP_204_NO_CONTENT)
async def update_user(
    inbound_tag: str,
    email: str,
    user_data: schemas.UpdateUser,
    session: Session = Depends(get_session),
    _ = Depends(check_api_key)
):
    if user_data.limit and user_data.limit < 0:
        user_data.limit = 0

    if not users.update_user(session, inbound_tag, email, user_data):
        raise HTTPException(status.HTTP_404_NOT_FOUND)
