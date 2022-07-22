import pytest

from bolinette.core import Cache, Injection, InjectionStrategy
from bolinette.core.inject import InjectionContext
from bolinette.core.exceptions import (
    AnnotationMissingInjectionError,
    InstanceExistsInjectionError,
    InvalidArgCountInjectionError,
    NoLiteralMatchInjectionError,
    NoPositionalParameterInjectionError,
    TooManyLiteralMatchInjectionError,
    TypeNotRegisteredInjectionError,
    TypeRegisteredInjectionError,
)


class InjectableClassB:
    def __init__(self) -> None:
        pass

    def func(self) -> str:
        return "b"


class InjectableClassC:
    def __init__(self) -> None:
        pass

    def func(self) -> str:
        return "c"


class InjectableClassD:
    def __init__(self, c: InjectableClassC) -> None:
        self.c = c

    def func(self) -> str:
        return "d"


class InjectableClassA:
    def __init__(self, b: InjectableClassB, d_param: "InjectableClassD") -> None:
        self.b = b
        self.d_attr = d_param

    def func(self) -> str:
        return "a"


def test_add_type_twice() -> None:
    inject = Injection(Cache(), InjectionContext())

    inject.add(InjectableClassA, InjectionStrategy.Singleton, None, None)
    with pytest.raises(TypeRegisteredInjectionError) as info:
        inject.add(InjectableClassA, InjectionStrategy.Singleton, None, None)

    assert f"Type {InjectableClassA} is already a registered type" in info.value.message


def test_instanciate_type_twice() -> None:
    inject = Injection(Cache(), InjectionContext())

    inject.add(InjectableClassB, InjectionStrategy.Singleton, None, None)
    inject._instanciate(InjectableClassB)
    with pytest.raises(InstanceExistsInjectionError) as info:
        inject._instanciate(InjectableClassB)

    assert f"Type {InjectableClassB} has already been instanciated" in info.value.message


def test_class_injection() -> None:
    cache = Cache()
    cache.add_type(InjectableClassA, InjectionStrategy.Singleton, None, None)
    cache.add_type(InjectableClassB, InjectionStrategy.Singleton, None, None)
    cache.add_type(InjectableClassC, InjectionStrategy.Singleton, None, None)
    cache.add_type(InjectableClassD, InjectionStrategy.Singleton, None, None)

    inject = Injection(cache, InjectionContext())
    a = inject.require(InjectableClassA)

    assert a.func() == "a"
    assert a.b.func() == "b"
    assert a.d_attr.func() == "d"
    assert a.d_attr.c.func() == "c"


def test_inject_call_sync() -> None:
    def _test_func(a: InjectableClassA):
        assert a.func() == "a"
        assert a.b.func() == "b"
        assert a.d_attr.func() == "d"
        assert a.d_attr.c.func() == "c"

    cache = Cache()
    cache.add_type(InjectableClassA, InjectionStrategy.Singleton, None, None)
    cache.add_type(InjectableClassB, InjectionStrategy.Singleton, None, None)
    cache.add_type(InjectableClassC, InjectionStrategy.Singleton, None, None)
    cache.add_type(InjectableClassD, InjectionStrategy.Singleton, None, None)

    inject = Injection(cache, InjectionContext())

    inject.call(_test_func)


async def test_inject_call_async() -> None:
    async def _test_func(b: InjectableClassB):
        assert b.func() == "b"

    cache = Cache()
    cache.add_type(InjectableClassB, InjectionStrategy.Singleton, None, None)

    inject = Injection(cache, InjectionContext())

    await inject.call(_test_func)


async def test_fail_injection() -> None:
    cache = Cache()
    cache.add_type(InjectableClassB, InjectionStrategy.Singleton, None, None)

    inject = Injection(cache, InjectionContext())
    with pytest.raises(TypeNotRegisteredInjectionError) as info:
        inject.require(InjectableClassC)

    assert (
        f"Type {InjectableClassC} is not a registered type in the injection system"
        in info.value.message
    )


async def test_fail_subinjection() -> None:
    cache = Cache()
    cache.add_type(InjectableClassD, InjectionStrategy.Singleton, None, None)

    inject = Injection(cache, InjectionContext())
    with pytest.raises(TypeNotRegisteredInjectionError) as info:
        inject.require(InjectableClassD)

    assert (
        f"Type {InjectableClassC} is not a registered type in the injection system"
        in info.value.message
    )


def test_fail_call_injection() -> None:
    def _test_func(b: InjectableClassC):
        assert b.func() == "b"

    cache = Cache()

    inject = Injection(cache, InjectionContext())
    with pytest.raises(TypeNotRegisteredInjectionError) as info:
        inject.call(_test_func)

    assert (
        f"Type {InjectableClassC} is not a registered type in the injection system"
        in info.value.message
    )


def test_require_twice() -> None:
    cache = Cache()
    cache.add_type(InjectableClassB, InjectionStrategy.Singleton, None, None)

    inject = Injection(cache, InjectionContext())
    b1 = inject.require(InjectableClassB)
    b2 = inject.require(InjectableClassB)

    assert b1 is b2


def test_no_literal_match() -> None:
    class _Value:
        pass

    class _TestClass:
        def __init__(self, value: "_Value") -> None:
            pass

    cache = Cache()
    cache.add_type(_TestClass, InjectionStrategy.Singleton, None, None)

    inject = Injection(cache, InjectionContext())
    with pytest.raises(NoLiteralMatchInjectionError) as info:
        inject.require(_TestClass)

    assert (
        f"Callable {_TestClass} Parameter 'value': "
        f"literal '{_Value.__name__}' does not match any registered type"
        in info.value.message
    )


def test_too_many_literal_matches() -> None:
    class _Value:
        pass

    class _1_Value:
        pass

    class _2_Value:
        pass

    class _TestClass:
        def __init__(self, _: "_Value") -> None:
            pass

    cache = Cache()
    cache.add_type(_TestClass, InjectionStrategy.Singleton, None, None)
    cache.add_type(_1_Value, InjectionStrategy.Singleton, None, None)
    cache.add_type(_2_Value, InjectionStrategy.Singleton, None, None)

    inject = Injection(cache, InjectionContext())
    with pytest.raises(TooManyLiteralMatchInjectionError) as info:
        inject.require(_TestClass)

    assert (
        f"Callable {_TestClass} Parameter '_': "
        f"literal '{_Value.__name__}' matches with 2 registered types, use a more explicit name"
        in info.value.message
    )


def test_no_annotation() -> None:
    class _TestClass:
        def __init__(self, _1, _2) -> None:
            pass

    cache = Cache()
    cache.add_type(_TestClass, InjectionStrategy.Singleton, None, None)

    inject = Injection(cache, InjectionContext())
    with pytest.raises(AnnotationMissingInjectionError) as info:
        inject.require(_TestClass)

    assert f"Callable {_TestClass} Parameter '_1' requires a type annotation" in info.value.message


def test_use_init_func() -> None:
    class _TestClass:
        def __init__(self) -> None:
            self.value: str | None = None
            self.cls_name: str | None = None

    def _test_func(t: _TestClass, b: InjectableClassB):
        t.value = b.func()
        t.cls_name = type(t).__name__

    class _ChildClass1(_TestClass):
        pass

    class _ChildClass2(_TestClass):
        pass

    cache = Cache()
    cache.add_type(InjectableClassB, InjectionStrategy.Singleton, None, None)

    inject = Injection(cache, InjectionContext())
    inject.add(_ChildClass1, InjectionStrategy.Singleton, _test_func, None)
    inject.add(_ChildClass2, InjectionStrategy.Singleton, _test_func, None)

    t1 = inject.require(_ChildClass1)
    t2 = inject.require(_ChildClass2)

    assert t1.value == "b"
    assert t2.value == "b"
    assert t1.cls_name == _ChildClass1.__name__
    assert t2.cls_name == _ChildClass2.__name__


def test_arg_resolve_fail_wilcard() -> None:
    def _test_func(a, *args):
        pass

    inject = Injection(Cache(), InjectionContext())

    with pytest.raises(NoPositionalParameterInjectionError) as info:
        inject.call(_test_func, kwargs={"a": "a", "b": "b"})

    assert (
        f"Callable {_test_func}: positional only parameters and positional wildcards are not allowed"
        in info.value.message
    )


def test_arg_resolve_fail_positional_only() -> None:
    def _test_func(a, /, b):
        pass

    inject = Injection(Cache(), InjectionContext())

    with pytest.raises(NoPositionalParameterInjectionError) as info:
        inject.call(_test_func, kwargs={"a": "a", "b": "b"})

    assert (
        f"Callable {_test_func}: positional only parameters and positional wildcards are not allowed"
        in info.value.message
    )


def test_arg_resolve_fail_too_many_args() -> None:
    def _test_func(a, b) -> None:
        pass

    inject = Injection(Cache(), InjectionContext())

    with pytest.raises(InvalidArgCountInjectionError) as info:
        inject.call(_test_func, args=["a", "b", "c"])

    assert (
        f"Callable {_test_func}: expected 2 arguments, 3 given"
        in info.value.message
    )


def test_arg_resolve() -> None:
    def _test_func(a, b, c: InjectableClassC, d="d", **kwargs) -> None:
        assert a == "a"
        assert b == "b"
        assert c.func() == "c"
        assert d == "d"
        assert kwargs == {"e": "e", "f": "f"}

    cache = Cache()
    cache.add_type(InjectableClassC, InjectionStrategy.Singleton, None, None)

    inject = Injection(cache, InjectionContext())
    inject.call(_test_func, args=["a"], kwargs={"b": "b", "e": "e", "f": "f"})


def test_two_injection() -> None:
    class _C1:
        pass

    class _C2:
        def __init__(self, c1: _C1) -> None:
            self.c1 = c1

    class _C3:
        def __init__(self, c1: _C1) -> None:
            self.c1 = c1

    cache = Cache()
    cache.add_type(_C1, InjectionStrategy.Singleton, None, None)
    cache.add_type(_C2, InjectionStrategy.Singleton, None, None)
    cache.add_type(_C3, InjectionStrategy.Singleton, None, None)

    inject = Injection(cache, InjectionContext())
    c2 = inject.require(_C2)
    c3 = inject.require(_C3)

    assert c2.c1 is c3.c1
