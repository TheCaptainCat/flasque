from functools import cache

import pytest
from bolinette.core import Cache, injectable, init_func, InjectionStrategy
from bolinette.core.exceptions import InitError


def test_empty_cache() -> None:
    cache = Cache()

    assert len(cache.types) == 0
    assert len(cache.init_funcs) == 0


def test_add_type() -> None:
    class _TestClass:
        pass

    cache = Cache()
    cache.add_type(_TestClass, InjectionStrategy.Singleton, None, None)

    assert len(cache.types) == 1
    assert cache.has_type(_TestClass)


def test_get_of_type() -> None:
    class _ParentClass:
        pass

    class _ChildClass1(_ParentClass):
        pass

    class _ChildClass2(_ParentClass):
        pass

    cache = Cache()
    cache.add_type(_ChildClass1, InjectionStrategy.Singleton, None, None)
    cache.add_type(_ChildClass2, InjectionStrategy.Singleton, None, None)

    assert len(cache.of_type(_ParentClass)) == 2


def test_add_init_func() -> None:
    def _test_func():
        pass

    cache = Cache()
    cache.add_init_func(_test_func)

    assert len(cache.init_funcs) == 1


def test_injectable_decorator() -> None:
    cache = Cache()

    @injectable(cache=cache)
    class _TestClass:
        pass

    assert len(cache.types) == 1
    assert cache.has_type(_TestClass)


def test_injectable_decorator_fail() -> None:
    def _test_func():
        pass

    cache = Cache()
    with pytest.raises(InitError) as info:
        injectable(cache=cache)(_test_func)

    assert (
        f"'{_test_func}' must be a class to be decorated by @{injectable.__name__}"
        in info.value.message
    )


def test_init_func_decorator() -> None:
    cache = Cache()

    @init_func(cache=cache)
    async def _test_func():
        pass

    assert len(cache.init_funcs) == 1


def test_init_func_decorator_fail() -> None:
    class _TestClass:
        pass

    cache = Cache()
    with pytest.raises(InitError) as info:
        init_func(cache=cache)(_TestClass)

    assert (
        f"'{_TestClass}' must be an async function to be an init function"
        in info.value.message
    )


def test_no_type_fail() -> None:
    class _TestClass:
        pass

    cache = Cache()

    with pytest.raises(KeyError):
        cache.get_type(_TestClass)