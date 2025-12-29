from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GetStatsRequest(_message.Message):
    __slots__ = ("name", "reset")
    NAME_FIELD_NUMBER: _ClassVar[int]
    RESET_FIELD_NUMBER: _ClassVar[int]
    name: str
    reset: bool
    def __init__(self, name: _Optional[str] = ..., reset: bool = ...) -> None: ...

class Stat(_message.Message):
    __slots__ = ("name", "value")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    name: str
    value: int
    def __init__(self, name: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...

class GetStatsResponse(_message.Message):
    __slots__ = ("stat",)
    STAT_FIELD_NUMBER: _ClassVar[int]
    stat: Stat
    def __init__(self, stat: _Optional[_Union[Stat, _Mapping]] = ...) -> None: ...

class QueryStatsRequest(_message.Message):
    __slots__ = ("pattern", "reset")
    PATTERN_FIELD_NUMBER: _ClassVar[int]
    RESET_FIELD_NUMBER: _ClassVar[int]
    pattern: str
    reset: bool
    def __init__(self, pattern: _Optional[str] = ..., reset: bool = ...) -> None: ...

class QueryStatsResponse(_message.Message):
    __slots__ = ("stat",)
    STAT_FIELD_NUMBER: _ClassVar[int]
    stat: _containers.RepeatedCompositeFieldContainer[Stat]
    def __init__(self, stat: _Optional[_Iterable[_Union[Stat, _Mapping]]] = ...) -> None: ...

class SysStatsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class SysStatsResponse(_message.Message):
    __slots__ = ("NumGoroutine", "NumGC", "Alloc", "TotalAlloc", "Sys", "Mallocs", "Frees", "LiveObjects", "PauseTotalNs", "Uptime")
    NUMGOROUTINE_FIELD_NUMBER: _ClassVar[int]
    NUMGC_FIELD_NUMBER: _ClassVar[int]
    ALLOC_FIELD_NUMBER: _ClassVar[int]
    TOTALALLOC_FIELD_NUMBER: _ClassVar[int]
    SYS_FIELD_NUMBER: _ClassVar[int]
    MALLOCS_FIELD_NUMBER: _ClassVar[int]
    FREES_FIELD_NUMBER: _ClassVar[int]
    LIVEOBJECTS_FIELD_NUMBER: _ClassVar[int]
    PAUSETOTALNS_FIELD_NUMBER: _ClassVar[int]
    UPTIME_FIELD_NUMBER: _ClassVar[int]
    NumGoroutine: int
    NumGC: int
    Alloc: int
    TotalAlloc: int
    Sys: int
    Mallocs: int
    Frees: int
    LiveObjects: int
    PauseTotalNs: int
    Uptime: int
    def __init__(self, NumGoroutine: _Optional[int] = ..., NumGC: _Optional[int] = ..., Alloc: _Optional[int] = ..., TotalAlloc: _Optional[int] = ..., Sys: _Optional[int] = ..., Mallocs: _Optional[int] = ..., Frees: _Optional[int] = ..., LiveObjects: _Optional[int] = ..., PauseTotalNs: _Optional[int] = ..., Uptime: _Optional[int] = ...) -> None: ...

class GetStatsOnlineIpListResponse(_message.Message):
    __slots__ = ("name", "ips")
    class IpsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...
    NAME_FIELD_NUMBER: _ClassVar[int]
    IPS_FIELD_NUMBER: _ClassVar[int]
    name: str
    ips: _containers.ScalarMap[str, int]
    def __init__(self, name: _Optional[str] = ..., ips: _Optional[_Mapping[str, int]] = ...) -> None: ...

class GetAllOnlineUsersRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetAllOnlineUsersResponse(_message.Message):
    __slots__ = ("users",)
    USERS_FIELD_NUMBER: _ClassVar[int]
    users: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, users: _Optional[_Iterable[str]] = ...) -> None: ...

class Config(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...
