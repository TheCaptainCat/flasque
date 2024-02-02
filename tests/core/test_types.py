# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
from typing import Any, ForwardRef, Generic, NotRequired, TypedDict, TypeVar

import pytest

from bolinette.core.exceptions import TypingError
from bolinette.core.testing import Mock
from bolinette.core.types import Type, TypeVarLookup
from bolinette.core.types.checker import (
    DefaultTypeChecker,
    ProtocolTypeChecker,
    TypeChecker,
    TypedDictChecker,
    type_checker,
)


def test_simple_type() -> None:
    class _T:
        pass

    t = Type(_T)

    assert t.cls is _T
    assert t.vars == ()
    assert str(t) == "test_simple_type.<locals>._T"
    assert repr(t) == "<Type test_simple_type.<locals>._T>"
    assert hash(t) == hash((_T, ()))
    assert t == Type(_T)


def test_generic_type() -> None:
    class _T[T]:
        pass

    T = TypeVar("T")
    t = Type(_T[T], raise_on_typevar=False)

    assert t.cls is _T
    assert t.vars == (T,)
    assert str(t) == "test_generic_type.<locals>._T[~T]"
    assert repr(t) == "<Type test_generic_type.<locals>._T[~T]>"
    assert hash(t) == hash((_T, (T,)))
    assert t == Type(_T[T], raise_on_typevar=False)


def test_missing_generic_param_is_any() -> None:
    class _T[T]:
        pass

    t = Type(_T)

    assert t.cls is _T
    assert t.vars == (Any,)


def test_specified_generic_type() -> None:
    class _P:
        pass

    class _T[T]:
        pass

    t = Type(_T[_P])

    assert t.cls is _T
    assert t.vars == (_P,)
    assert str(t) == "test_specified_generic_type.<locals>._T[test_specified_generic_type.<locals>._P]"
    assert hash(t) == hash((_T, (_P,)))


def test_fail_forward_ref() -> None:
    class _T[T]:
        pass

    class _P:
        pass

    with pytest.raises(TypingError) as info:
        Type(_T["_P"])

    assert info.value.message == "Type test_fail_forward_ref.<locals>._T, Generic parameter '_P' cannot be a string"


def test_forward_ref() -> None:
    class _T[T]:
        pass

    class _P:
        pass

    t = Type(_T["_P"], raise_on_string=False)

    assert t.vars == (ForwardRef("_P"),)
    assert str(t) == "test_forward_ref.<locals>._T['_P']"


def test_fail_typevar() -> None:
    class _T[T]:
        pass

    T = TypeVar("T")
    with pytest.raises(TypingError) as info:
        Type(_T[T], raise_on_typevar=True)

    assert info.value.message == "Type test_fail_typevar.<locals>._T, Generic parameter ~T cannot be a TypeVar"


def test_typevar_lookup() -> None:
    T = TypeVar("T")

    class _T(Generic[T]):
        pass

    class _K(Generic[T]):
        pass

    class _P:
        pass

    t = Type(_T[T], lookup=TypeVarLookup(Type(_K[_P])))

    assert t.vars == (_P,)


def test_fail_typevar_not_found_in_lookup() -> None:
    class _T[T]:
        pass

    class _K[K]:
        pass

    class _P:
        pass

    T = TypeVar("T")
    with pytest.raises(TypingError) as info:
        Type(_T[T], lookup=TypeVarLookup(Type(_K[_P])))

    assert (
        info.value.message
        == "Type test_fail_typevar_not_found_in_lookup.<locals>._T, TypeVar ~T could not be found in lookup"
    )


def test_typevar_not_found_in_lookup() -> None:
    class _T[T]:
        pass

    class _K[K]:
        pass

    class _P:
        pass

    T = TypeVar("T")
    k = Type(_K[_P])
    t = Type(_T[T], lookup=TypeVarLookup(k), raise_on_typevar=False)

    assert t.vars == (T,)


def test_lookup() -> None:
    T = TypeVar("T")

    class _T(Generic[T]):
        pass

    class _P:
        pass

    t = Type(_T[_P], raise_on_typevar=False)
    lookup = TypeVarLookup(t)

    assert not lookup.empty
    assert [*lookup] == [(T, _P)]
    assert lookup[T] is _P


def test_empty_lookup() -> None:
    class _T:
        pass

    t = Type(_T)
    lookup = TypeVarLookup(t)

    assert lookup.empty
    assert [*lookup] == []


def test_fail_lookup_key_not_found() -> None:
    K = TypeVar("K")

    class _T[T]:
        pass

    class _P:
        pass

    t = Type(_T[_P], raise_on_typevar=False)
    lookup = TypeVarLookup(t)

    with pytest.raises(KeyError):
        lookup[K]


def test_nullable_type() -> None:
    t = Type(None | int)

    assert t.cls is int
    assert not t.is_union
    assert t.nullable


def test_union() -> None:
    t = Type(str | int)

    assert t.cls is str
    assert t.is_union
    assert t.union == (Type(int),)
    assert not t.nullable


def test_nullable_union() -> None:
    t = Type(str | None | int)

    assert t.cls is str
    assert t.is_union
    assert t.union == (Type(int),)
    assert t.nullable


def test_typed_dict() -> None:
    class TestDict(TypedDict, total=False):
        name: str
        description: NotRequired[str]

    t_int = Type(int)
    assert t_int.total

    t_dict = Type(TestDict)
    assert t_dict.cls is TestDict
    assert not t_dict.total

    annotations = t_dict.annotations()
    assert set(annotations.keys()) == {"name", "description"}
    assert annotations["name"].required
    assert not annotations["description"].required


def _setup_type_checkers(mock: Mock):
    mock.injection.add(TypeChecker, "singleton")
    type_checker(priority=-800, cache=mock.injection.cache)(ProtocolTypeChecker)
    type_checker(priority=-900, cache=mock.injection.cache)(TypedDictChecker)
    type_checker(priority=-1000, cache=mock.injection.cache)(DefaultTypeChecker)


def test_type_checker() -> None:
    mock = Mock()
    _setup_type_checkers(mock)

    checker = mock.injection.require(TypeChecker)

    assert checker.instanceof(1, int)
    assert not checker.instanceof(1, str)


def test_typed_dict_type_checker() -> None:
    mock = Mock()
    _setup_type_checkers(mock)

    checker = mock.injection.require(TypeChecker)

    class TestDict(TypedDict):
        name: str
        age: int

    assert checker.instanceof({"name": "Bob", "age": 42}, TestDict)
    assert not checker.instanceof({"name": "Bob"}, TestDict)
    assert not checker.instanceof({"name": 42}, TestDict)
    assert not checker.instanceof("Bob", TestDict)
