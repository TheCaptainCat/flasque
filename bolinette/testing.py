from collections.abc import Callable
from typing import Any, Generic, TypeVar, get_args, get_origin

from bolinette import Cache, meta
from bolinette.expressions import AttributeNode, ExpressionTree
from bolinette.injection import Injection
from bolinette.injection.context import InjectionContext

T = TypeVar("T")


class _MockedMeta(Generic[T]):
    def __init__(self, cls: type[T]) -> None:
        self.cls = cls
        self.dummy = False
        self._attrs: dict[str, Any] = {}

    def _get_dummy(self, key: str) -> None | Callable[..., None]:
        if hasattr(self.cls, key) and callable(getattr(self.cls, key)):
            return lambda *args, **kwargs: None
        return None

    def __contains__(self, key: str) -> bool:
        return key in self._attrs or self.dummy

    def __getitem__(self, key: str) -> Any:
        if key not in self._attrs and self.dummy:
            return self._get_dummy(key)
        return self._attrs[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._attrs[key] = value


class _MockWrapper(Generic[T]):
    def __init__(
        self,
        cls: type[T],
    ) -> None:
        self._cls = self._setup_mocked_cls(cls)
        self.instance = self._cls()

    @staticmethod
    def _get_mocked_attr(_cls: type[T], instance: T, name: str) -> Any:
        if name == "__class__":
            return _cls
        _meta = meta.get(type(instance), _MockedMeta)
        if name in _meta:
            return _meta[name]
        raise KeyError(f"'{name}' attribute has not been mocked in {_cls}")

    @staticmethod
    def _setup_mocked_cls(_cls: type[T]) -> type[T]:
        _t = type(f"{_cls.__name__}__Mocked", (_cls,), {})  # type: ignore
        setattr(_t, "__init__", lambda _: None)
        setattr(_t, "__repr__", lambda _: f"<Mocked[{_cls.__name__}]>")
        setattr(
            _t,
            "__getattribute__",
            lambda i, n: _MockWrapper._get_mocked_attr(_cls, i, n),
        )
        meta.set(_t, _MockedMeta(_cls))
        return _t  # type: ignore

    def setup(self, func: Callable[[T], Any], value: Any) -> "_MockWrapper[T]":
        expr: AttributeNode = func(ExpressionTree.new())  # type: ignore
        name = ExpressionTree.get_attribute_name(expr)
        _meta = meta.get(self._cls, _MockedMeta)
        _meta[name] = value
        return self

    def dummy(self, value: bool = True) -> "_MockWrapper[T]":
        _meta = meta.get(self._cls, _MockedMeta)
        _meta.dummy = value
        return self


class Mock:
    def __init__(self, *, inject: Injection | None = None, cache: Cache | None = None) -> None:
        self._inject = inject or Injection(cache or Cache(), InjectionContext())
        self._mocked: dict[type[Any], _MockWrapper[Any]] = {}

    @staticmethod
    def _get_generic_params(
        _cls: type[T],
    ) -> tuple[type[T], tuple[Any, ...]]:
        if origin := get_origin(_cls):
            params: tuple[Any, ...] = ()
            for arg in get_args(_cls):
                params = (*params, arg)
            return origin, params
        return _cls, ()

    def mock(self, cls: type[T], *, match_all: bool = False) -> _MockWrapper[T]:
        origin, _ = self._get_generic_params(cls)
        if origin in self._mocked:
            mocked = self._mocked[origin]
        else:
            mocked = _MockWrapper(origin)
            self._mocked[origin] = mocked
            self._inject.add(cls, "singleton", instance=mocked.instance, match_all=match_all)
        return mocked

    @property
    def injection(self) -> Injection:
        return self._inject
