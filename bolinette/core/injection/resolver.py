import logging
from collections.abc import Callable
from typing import Any, Protocol

from bolinette.core import Cache, CoreSection, __user_cache__, injection, meta
from bolinette.core.injection.context import InjectionContext
from bolinette.core.logging import ColorFormatter, Logger
from bolinette.core.types import Type
from bolinette.core.utils import OrderedSet


class ArgResolverOptions:
    def __init__(
        self,
        injection: "injection.Injection",
        t: Type[Any],
        context: InjectionContext | None,
        circular_guard: OrderedSet[Any],
        additional_resolvers: "list[ArgumentResolver]",
    ) -> None:
        self.injection = injection
        self.t = t
        self.context = context
        self.circular_guard = circular_guard
        self.additional_resolvers = additional_resolvers


class ArgumentResolver(Protocol):
    def supports(self, options: ArgResolverOptions) -> bool: ...

    def resolve(self, options: ArgResolverOptions) -> Any: ...


class ArgResolverMeta:
    def __init__(self, priority: int, scoped: bool) -> None:
        self.priority = priority
        self.scoped = scoped


def injection_arg_resolver[ArgResolverT: ArgumentResolver](
    *,
    priority: int = 0,
    scoped: bool = False,
    cache: Cache | None = None,
) -> Callable[[type[ArgResolverT]], type[ArgResolverT]]:
    def decorator(cls: type[ArgResolverT]) -> type[ArgResolverT]:
        (cache or __user_cache__).add(ArgumentResolver, cls)
        meta.set(cls, ArgResolverMeta(priority, scoped))
        return cls

    return decorator


class LoggerArgResolver:
    def __init__(self, core_config: CoreSection) -> None:
        self.config = core_config

    def supports(self, options: ArgResolverOptions) -> bool:
        return options.t.cls is Logger

    def resolve(self, options: ArgResolverOptions) -> logging.Logger:
        logger = logging.getLogger(f"__blnt_logger__.{options.t}")
        if not logger.hasHandlers():
            print(self.config.logging)
            handler = logging.StreamHandler()
            handler.setFormatter(ColorFormatter(options.t.vars[0].__qualname__))
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
        return logger
