from enum import Enum

class NodeTypeEnum(Enum):
    Shadowsocks = "shadowsocks"
    Shadowsocks_2022 = "shadowsocks_2022"
    VMess = "vmess"
    VLess = "vless"
    Trojan = "trojan"
    Socks = "socks"


class ErrorEnum:
    EmailExistsError = 1
    InboundTagNotFound = 2
    UplinkNotFound = 3
    DownlinkNotFound = 4
    InboundTypeNotFound = 5
    XrayError = 6


CIPHER_TYPE = {
    "unknown": 0,
    "aes-128-gcm": 5,
    "aes-256-gcm": 6,
    "chacha20-poly1305": 7,
    "chacha20-ietf-poly1305": 7,
    "xchacha20-poly1305": 8,
    "xchacha20-ietf-poly1305": 8,
    "none": 9,
    "2022-blake3-aes-128-gcm": 0,
    "2022-blake3-aes-256-gcm": 0,
    "2022-blake3-chacha20-poly1305": 0,
}


class XrayError:
    def __init__(self, code: ErrorEnum, message: str) -> None:
        self.code = code
        self.message = message
