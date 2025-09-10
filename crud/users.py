import secrets
import uuid

from sqlalchemy import desc
from sqlalchemy.orm import Session
from typing import List, Tuple

import models, schemas


def get_users(
        session: Session,
        inbound_tag: str = None,
        email: str = None
) -> Tuple[List[models.User], int]:
    query = session.query(models.User)

    if inbound_tag:
        query = query.filter(models.User.inbound_tag == inbound_tag)

    if email:
        query = query.filter(models.User.email == email)

    query.order_by(desc(models.User.inbound_tag))

    total = query.count()

    return (
        query.all(),
        total
    )

def create_user(
        session: Session,
        inbound_tag: str,
        user_data: schemas.CreateUser
) -> (models.User | None):
    uuid_str = None
    password = None

    if user_data.limit < 0:
        user_data.limit = 0

    if user_data.type in (schemas.NodeTypeEnum.VMess, schemas.NodeTypeEnum.VLess):
        uuid_str = str(uuid.uuid4())
    else:
        if user_data.cipher_type == schemas.CipherType.ss2022_blake3_aes_128_gcm:
            password = secrets.token_urlsafe(64)[0:24]
        elif user_data.cipher_type == schemas.CipherType.ss2022_blake3_aes_256_gcm:
            password = secrets.token_urlsafe(64)[0:44]
        else:
            password = secrets.token_urlsafe(64)[0:22]

    if user_data.cipher_type in (
        schemas.CipherType.ss2022_blake3_aes_128_gcm,
        schemas.CipherType.ss2022_blake3_aes_256_gcm,
        schemas.CipherType.ss2022_blake3_chacha20_poly1305
    ):
        user_data.cipher_type = None

    user = models.User(
        inbound_tag=inbound_tag,
        email=user_data.email,
        level=user_data.level,
        type=user_data.type,
        password=password,
        cipher_type=user_data.cipher_type,
        uuid=uuid_str,
        flow=user_data.flow,
        limit=user_data.limit
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return user

def update_user(
        session: Session,
        inbound_tag: str,
        email: str,
        user_data: schemas.UpdateUser
) -> (models.User | None):
    usersList, total = get_users(session, inbound_tag, email)
    
    if total != 1:
        return False

    user = usersList[0]

    for key, value in user_data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)

    session.commit()
    session.refresh(user)

    return user

def delete_user(
        session: Session,
        inbound_tag: str,
        email: str
) -> bool:
    usersList, total = get_users(session, inbound_tag, email)
    
    if total != 1:
        return False

    session.delete(usersList[0])
    session.commit()

    return True
