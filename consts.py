from enum import Enum

from xray_rpc.proxy.shadowsocks.config_pb2 import (
    NONE,
    UNKNOWN,
    AES_128_GCM,
    AES_256_GCM,
    CHACHA20_POLY1305,
    XCHACHA20_POLY1305,
)


class NodeTypeEnum(Enum):
    Shadowsocks = "shadowsocks"
    ShadowsocksR = "shadowsocksr"
    VMess = "vmess"
    VLess = "vless"
    Trojan = "trojan"


class ErrorEnum:
    EmailExistsError = 1
    InboundTagNotFound = 2
    UplinkNotFound = 3
    DownlinkNotFound = 4
    XrayError = 5


CIPHER_TYPE_DICT = {
    "none": NONE,
    "unknown": UNKNOWN,
    "aes-128-gcm": AES_128_GCM,
    "aes-256-gcm": AES_256_GCM,
    "chacha20-poly1305": CHACHA20_POLY1305,
    "xchacha20-poly1305": XCHACHA20_POLY1305,
}


class XrayError:
    def __init__(self, code: ErrorEnum, message: str) -> None:
        self.code = code
        self.message = message
