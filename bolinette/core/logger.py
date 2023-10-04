import sys
from datetime import datetime
from typing import Generic, Protocol, TypeVar

from bolinette.core import Cache, GenericMeta, meta
from bolinette.core.injection import init_method

T_Contra = TypeVar("T_Contra", contravariant=True)
T = TypeVar("T")


class SupportsWrite(Protocol[T_Contra]):
    def write(self, __s: T_Contra) -> object:
        pass


class ConsoleColorCode:
    Reset = "\x1b[0m"
    Bright = "\x1b[1m"
    Dim = "\x1b[2m"
    Underscore = "\x1b[4m"
    Blink = "\x1b[5m"
    Reverse = "\x1b[7m"
    Hidden = "\x1b[8m"

    FgBlack = "\x1b[30m"
    FgRed = "\x1b[31m"
    FgGreen = "\x1b[32m"
    FgYellow = "\x1b[33m"
    FgBlue = "\x1b[34m"
    FgMagenta = "\x1b[35m"
    FgCyan = "\x1b[36m"
    FgWhite = "\x1b[37m"

    BgBlack = "\x1b[40m"
    BgRed = "\x1b[41m"
    BgGreen = "\x1b[42m"
    BgYellow = "\x1b[43m"
    BgBlue = "\x1b[44m"
    BgMagenta = "\x1b[45m"
    BgCyan = "\x1b[46m"
    BgWhite = "\x1b[47m"


class Logger(Generic[T]):
    def __init__(self, cache: Cache | None = None) -> None:
        self._cache = cache or Cache()
        self._package = "<Logger>"

    @init_method
    def _init(self) -> None:
        if gen_meta := meta.get(self, GenericMeta, default=None):
            if len(gen_meta):
                self._package = gen_meta[0].__name__

    def _log(
            self,
            prefix: str,
            text: str,
            color: str | None = None,
            file: SupportsWrite[str] | None = None,
    ):
        strings: list[str] = [f"{datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')}",
                              f"{ConsoleColorCode.Bright}{color}{prefix}{ConsoleColorCode.Reset}",
                              f"[{ConsoleColorCode.FgGreen}{self._package}{ConsoleColorCode.Reset}]", text]
        print(*strings, file=file)

    def warning(self, *values: str, sep: str | None = None) -> None:
        self._log("WARN", (sep or " ").join(values), color=ConsoleColorCode.FgYellow)

    def info(self, *values: str, sep: str | None = None) -> None:
        self._log("INFO", (sep or " ").join(values), color=ConsoleColorCode.FgGreen)

    def debug(self, *values: str, sep: str | None = None) -> None:
        if self._cache.debug:
            self._log(
                "DEBUG",
                (sep or " ").join(values),
                color=ConsoleColorCode.FgBlue,
            )

    def error(self, *values: str, sep: str | None = None) -> None:
        self._log(
            "ERROR",
            (sep or " ").join(values),
            color=ConsoleColorCode.FgRed,
            file=sys.stderr,
        )
