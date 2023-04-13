from collections.abc import Iterator
from typing import Any, Callable, Generic, Protocol, TypeVar

from bolinette.exceptions import InitMappingError, MappingError
from bolinette.utils import AttributeUtils

SrcT = TypeVar("SrcT", bound=object)
SrcT_contra = TypeVar("SrcT_contra", bound=object, contravariant=True)
DestT = TypeVar("DestT", bound=object)
DestT_contra = TypeVar("DestT_contra", bound=object, contravariant=True)


class MappingStep(Protocol[SrcT_contra, DestT_contra]):
    def apply(self, src: SrcT_contra, dest: DestT_contra) -> None:
        pass


class ToDestMappingStep(MappingStep[SrcT_contra, DestT_contra], Protocol[SrcT_contra, DestT_contra]):
    dest_cls: type[Any]
    dest_attr: str


class IgnoreMappingStep(Generic[SrcT, DestT], ToDestMappingStep[SrcT, DestT]):
    def __init__(self, dest_cls: type[Any], dest_attr: str, hints: tuple[type[Any] | None]) -> None:
        self.dest_cls = dest_cls
        self.dest_attr = dest_attr
        if None in hints:
            self.default = None
        else:
            for hint in hints:
                if hint is None:
                    continue
                self.default = hint()
                break
            else:
                raise MappingError(
                    "Default value for attribute could not be determined",
                    cls=self.dest_cls,
                    attr=self.dest_attr,
                )

    def apply(self, src: SrcT, dest: DestT) -> None:
        setattr(dest, self.dest_attr, self.default)


class FromSrcMappingStep(Generic[SrcT, DestT], ToDestMappingStep[SrcT, DestT]):
    def __init__(
        self,
        src_cls: type[Any],
        src_attr: str,
        dest_cls: type[Any],
        dest_attr: str,
        func: Callable[[SrcT, DestT], None],
    ) -> None:
        self.src_cls = src_cls
        self.src_attr = src_attr
        self.dest_cls = dest_cls
        self.dest_attr = dest_attr
        self.func = func

    def apply(self, src: SrcT, dest: DestT) -> None:
        self.func(src, dest)


class FunctionMappingStep(Generic[SrcT, DestT], MappingStep[SrcT, DestT]):
    def __init__(self, func: Callable[[SrcT, DestT], None]) -> None:
        self.func = func

    def apply(self, src: SrcT, dest: DestT) -> None:
        self.func(src, dest)


class IncludeFromBase:
    def __init__(self, src_cls: type[Any], dest_cls: type[Any]) -> None:
        self.src_cls = src_cls
        self.dest_cls = dest_cls


class MappingSequence(Generic[SrcT, DestT]):
    def __init__(self, src: type[SrcT], dest: type[DestT]) -> None:
        self.src_cls, self.src_type_vars = AttributeUtils.get_generics(src)
        self.dest_cls, self.dest_type_vars = AttributeUtils.get_generics(dest)
        self.src_hints = AttributeUtils.get_all_annotations(self.src_cls)
        self.dest_hints = AttributeUtils.get_all_annotations(self.dest_cls)
        self.head: list[MappingStep[SrcT, DestT]] = []
        self.steps: dict[str, MappingStep[SrcT, DestT]] = {}
        self.tail: list[MappingStep[SrcT, DestT]] = []
        self.includes: list[IncludeFromBase] = []

    @staticmethod
    def get_hash(
        src_cls: type[Any],
        src_type_vars: tuple[Any, ...],
        dest_cls: type[Any],
        dest_type_vars: tuple[Any, ...],
    ) -> int:
        return hash((src_cls, src_type_vars, dest_cls, dest_type_vars))

    def __hash__(self) -> int:
        return MappingSequence.get_hash(self.src_cls, self.src_type_vars, self.dest_cls, self.dest_type_vars)

    def __len__(self) -> int:
        return len(self.head) + len(self.steps) + len(self.tail)

    def __iter__(self) -> Iterator[MappingStep[Any, Any]]:
        return (s for s in [*self.head, *self.steps.values(), *self.tail])

    def __contains__(self, key: str) -> bool:
        return key in self.steps

    def add_head_step(self, step: FunctionMappingStep[Any, Any]) -> None:
        self.head.append(step)

    def add_step(self, step: ToDestMappingStep) -> None:
        self.steps[step.dest_attr] = step

    def add_tail_step(self, step: FunctionMappingStep[Any, Any]) -> None:
        self.tail.append(step)

    def add_include(self, include: IncludeFromBase) -> None:
        self.includes.append(include)

    def complete(self, completed_sequences: "dict[int, MappingSequence]") -> None:
        defined_steps = self.steps

        incl_head: list[MappingStep] = []
        incl_tail: list[MappingStep] = []
        incl_steps: dict[str, MappingStep[SrcT, DestT]] = {}
        for included in self.includes:
            incl_src_cls, incl_src_type_vars = AttributeUtils.get_generics(included.src_cls)
            incl_dest_cls, incl_dest_type_vars = AttributeUtils.get_generics(included.dest_cls)
            incl_hash = MappingSequence.get_hash(incl_src_cls, incl_src_type_vars, incl_dest_cls, incl_dest_type_vars)
            if incl_hash not in completed_sequences:
                raise InitMappingError(
                    f"Mapping {self.src_cls} -> {self.dest_cls}: "
                    f"Could not find base mapping {incl_src_cls} -> {incl_dest_cls}. "
                    f"Make sure the mappings are declared in the right order."
                )
            incl_sequence = completed_sequences[incl_hash]
            incl_head = [*incl_head, *incl_sequence.head]
            incl_tail = [*incl_tail, *incl_sequence.tail]
            incl_steps |= incl_sequence.steps
        self.head = [*incl_head, *self.head]
        self.tail = [*incl_tail, *self.tail]

        all_steps: dict[str, MappingStep[SrcT, DestT]] = {}
        for dest_attr, dest_hint in self.dest_hints.items():
            if dest_attr in defined_steps:
                all_steps[dest_attr] = defined_steps[dest_attr]
                continue
            if dest_attr in incl_steps:
                all_steps[dest_attr] = incl_steps[dest_attr]
                continue
            if dest_attr not in self.src_hints:
                all_steps[dest_attr] = IgnoreMappingStep(self.dest_cls, dest_attr, dest_hint)
                continue

            def inner_scope(_attr: str) -> FunctionMappingStep[Any, Any]:
                return FunctionMappingStep(lambda s, d: setattr(d, _attr, getattr(s, _attr)))

            all_steps[dest_attr] = inner_scope(dest_attr)
        self.steps = all_steps
