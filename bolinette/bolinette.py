from typing import Callable

from bolinette import (
    Environment,
    Injection,
    Logger,
    __core_cache__,
    __user_cache__,
    core_ext,
    meta,
    require,
    Extension,
)
from bolinette.command import Parser
from bolinette.utils import FileUtils, PathUtils


class Bolinette:
    def __init__(
        self,
        *,
        profile: str | None = None,
        inject: Injection | None = None,
        load_defaults: bool = True,
        extensions: list[Extension] | None = None,
    ) -> None:
        if extensions is None:
            extensions = []
        if load_defaults and core_ext not in extensions:
            extensions = [core_ext, *extensions]

        extensions = Extension.sort_extensions(extensions)
        cache = Extension.merge_caches(extensions)
        cache |= __user_cache__

        self._inject = inject or Injection(cache)
        meta.set(self, self._inject)

        self._logger = self._inject.require(Logger[Bolinette])
        self._paths = self._inject.require(PathUtils)
        self._files = self._inject.require(FileUtils)

        self._profile = (
            profile
            or self._files.read_profile(self._paths.env_path())
            or self._set_default_profile()
        )

        self._inject.add(Bolinette, "singleton", instance=self)
        self._inject.add(
            Environment,
            "singleton",
            args=[self._profile],
            instanciate=True,
        )
        self._inject._hook_proxies(self)

    @property
    def injection(self) -> Injection:
        return self._inject

    def _set_default_profile(self) -> str:
        self._logger.warning(
            "No profile set, defaulting to 'development'.",
            "Be sure to set the current profile in a .profile file in the env folder",
        )
        return "development"

    async def startup(self) -> None:
        pass

    @require(Parser)
    def _parser(self):
        pass

    async def exec_cmd_args(self):
        await self._parser.run()


def main_func(func: Callable[[], Bolinette]) -> Callable[[], Bolinette]:
    setattr(func, "__blnt__", "__blnt_main__")
    return func
