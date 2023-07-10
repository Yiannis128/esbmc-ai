# Author: Yiannis Charalambous


from typing import Optional
from typing_extensions import override

from clang.cindex import Cursor
import clang.cindex as cindex


class Declaration(object):
    name: str
    type_name: str
    cursor: Optional[Cursor]
    """Optional and not used in any checks, used to provide the underlying Cursor object that this
    Declaration represents."""

    def __init__(
        self, name: str, type_name: str, cursor: Optional[Cursor] = None
    ) -> None:
        self.name = name
        self.type_name = type_name
        self.cursor = cursor

    @classmethod
    def from_cursor(cls, cursor: Cursor) -> "Declaration":
        """Constructs a declaration from a Cursor."""
        return Declaration(
            name=cursor.spelling,
            type_name=cursor.type.spelling,
            cursor=cursor,
        )

    @override
    def __hash__(self) -> int:
        return self.name.__hash__() + self.type_name.__hash__()

    @override
    def __eq__(self, __value: object) -> bool:
        return (
            isinstance(__value, Declaration)
            and self.name == __value.name
            and self.type_name == __value.type_name
        )

    @override
    def __str__(self) -> str:
        return self.name + ":" + self.type_name

    def rename(self, new_name: str) -> None:
        """Renames the declaration along with any references to it. Requires cursor to be defined."""
        assert self.cursor
        # TODO: Consider an update method for all other Declarations to be kept valid when renaming occurs.
        # TODO A method to check for this is for each element:
        # 1. Does it have the same name & type_name
        # 2. Is it in the same location (after offsets have been calculated from the rename)

        refs: list[Declaration] = self.get_references()

        raise NotImplementedError()

    def get_references(self) -> list["Declaration"]:
        """Finds all references to a specific declaration."""
        assert self.cursor
        refs: list = []
        root: Cursor = self.cursor.translation_unit.cursor

        def traverse_children(node: Cursor) -> None:
            if node.referenced and node.referenced == self.cursor:
                refs.append(self.from_cursor(node))

            for child in node.get_children():
                traverse_children(child)

        for child in root.get_children():
            traverse_children(child)

        return refs


class FunctionDeclaration(Declaration):
    args: list[Declaration] = []

    def __init__(
        self,
        name: str,
        type_name: str,
        args: list[Declaration],
        cursor: Optional[Cursor] = None,
    ) -> None:
        super().__init__(name, type_name, cursor=cursor)
        self.args = args

    @override
    @classmethod
    def from_cursor(cls, cursor: Cursor) -> "FunctionDeclaration":
        return FunctionDeclaration(
            name=cursor.spelling,
            type_name=cursor.type.get_result().spelling,
            args=[Declaration.from_cursor(arg) for arg in cursor.get_arguments()],
            cursor=cursor,
        )

    @override
    def __hash__(self) -> int:
        hash_result: int = 0
        for arg in self.args:
            hash_result += arg.__hash__()
        return super().__hash__() + hash_result

    @override
    def __eq__(self, __value: object) -> bool:
        return (
            isinstance(__value, FunctionDeclaration)
            and self.args == __value.args
            and super().__eq__(__value)
        )

    @override
    def __str__(self) -> str:
        arg: list[str] = [f"{arg.name}: {arg.type_name}" for arg in self.args]
        args: str = ", ".join(arg)
        return f"{self.name}({args})"

    @override
    def rename(self, new_name: str) -> None:
        assert self.cursor is not None
        # 1. Get the locations where cursor is referenced.
        # self.cursor.
        # 2. In each location, change the name in the source code.
        # 3. Call ClangAST object again and read the new source code.
        return


class TypeDeclaration(Declaration):
    """Represents a type declaration. The following fields declare the type of declaration
    that this object is:
    * The type_name will be the typedef name assigned.
    * The name will be the struct/union name assigned.
    * The is_union shows if this is a union instead of a struct."""

    is_union: bool

    def __init__(
        self,
        name: str,
        type_name: str,
        elements: list[Declaration] = [],
        is_union: bool = False,
        cursor: Optional[Cursor] = None,
    ) -> None:
        super().__init__(name, type_name, cursor=cursor)

        self.elements = elements
        self.is_union = is_union

    @classmethod
    @override
    def from_cursor(cls, cursor: Cursor) -> "TypeDeclaration":
        elements: list[Declaration] = []
        # Get Elements
        element: Cursor
        for element in cursor.get_children():
            elements.append(Declaration.from_cursor(element))

        node_type: cindex.Type = cursor.type
        kind: cindex.CursorKind = cursor.kind
        return TypeDeclaration(
            name=node_type.get_canonical().spelling,
            type_name=node_type.get_typedef_name(),
            is_union=kind == cindex.CursorKind.UNION_DECL,
            cursor=cursor,
            elements=elements,
        )

    def is_typedef(self) -> bool:
        return len(self.type_name) > 0

    @override
    def __hash__(self) -> int:
        hash_result: int = 0
        for e in self.elements:
            hash_result += e.__hash__()
        return super().__hash__() + hash_result

    @override
    def __eq__(self, __value: object) -> bool:
        return (
            isinstance(__value, TypeDeclaration)
            and self.is_union == __value.is_union
            and super().__eq__(__value)
        )

    @override
    def __str__(self) -> str:
        elements: list[str] = [f"{e.name}: {e.type_name}" for e in self.elements]
        elements_string: str = ", ".join(elements)
        return (
            (f"typedef ({self.type_name}) " if self.is_typedef() else "")
            + self.name
            + (" {" + elements_string if len(elements_string) > 0 else " {")
            + "}"
        )


class PreProcessingDirective(object):
    """Base class for preprocessing directives."""

    # TODO If __eq__, __hash__, __str__ methods are added,
    # make sure to add super() calls to children.
    pass


class InclusionDirective(PreProcessingDirective):
    """Represents an inclusion directive."""

    path: str
    """Path to the inclusion directive.
    `#include <path>`"""

    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path

    @override
    def __hash__(self) -> int:
        return self.path.__hash__()

    @override
    def __eq__(self, __value: object) -> bool:
        return isinstance(__value, InclusionDirective) and self.path == __value.path

    @override
    def __str__(self) -> str:
        return f'#include "{self.path}"'
