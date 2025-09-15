from enum import Enum
from typing import Generic, List
from annotated_types import T
from pydantic import BaseModel, Field
from datetime import datetime


class XrayError:
    def __init__(self, message: str) -> None:
        self.message = message


class NodeTypeEnum(Enum):
    Shadowsocks = "shadowsocks"
    Shadowsocks_2022 = "shadowsocks_2022"
    VMess = "vmess"
    VLess = "vless"
    Trojan = "trojan"
    Socks = "socks"


class CipherType(Enum):
    unknown = 0,
    aes_128_gcm = 5,
    aes_256_gcm = 6,
    chacha20_poly1305 = 7,
    chacha20_ietf_poly1305 = 7,
    xchacha20_poly1305 = 8,
    xchacha20_ietf_poly1305 = 8,
    none = 9,
    ss2022_blake3_aes_128_gcm = 0,
    ss2022_blake3_aes_256_gcm = 0,
    ss2022_blake3_chacha20_poly1305 = 0


class CreateUser(BaseModel):
    email: str = Field(min_length=3, max_length=128)
    level: int | None = Field(default=0)
    type: NodeTypeEnum | None = Field(default=NodeTypeEnum.VLess)
    cipher_type: CipherType | None = Field(default=CipherType.unknown)
    flow: str | None = Field(default='xtls-rprx-vision', max_length=32)
    limit: int | None = Field(default=0)


class ReadUser(BaseModel):
    id: int
    inbound_tag: str
    email: str
    level: int | None
    type: NodeTypeEnum
    password: str | None
    cipher_type: CipherType | None
    uuid: str | None
    flow: str
    traffic: int
    limit: int
    active: bool
    blocked: bool
    created_date: datetime
    reset_traffic_date: datetime


class ReadUsers(BaseModel, Generic[T]):
    users: List[T]
    total: int


class UpdateUser(BaseModel):
    traffic: int | None = Field(default=None)
    limit: int | None = Field(default=None)
    active: bool | None = Field(default=None)
    blocked: bool | None = Field(default=None)
    reset_traffic_date: datetime | None = Field(default=None)


class Inbound(BaseModel):
    inbound_tag: str
    download_traffic: int
    upload_traffic: int


class ReadStats(BaseModel, Generic[T]):
    inbounds: List[T]


class Error(BaseModel):
    message: str
    code: int
