# Author: Yiannis Charalambous


from enum import Enum
from typing import Optional, final
from typing_extensions import override
from zlib import adler32

from clang.cindex import Cursor, SourceLocation, SourceRange
import clang.cindex as cindex


class Declaration(object):
    def __init__(
        self, name: str, type_name: str, cursor: Optional[Cursor] = None
    ) -> None:
        self.name: str = name
        self.type_name: str = type_name
        self.cursor: Optional[Cursor] = cursor

    @classmethod
    def from_cursor(cls, cursor: Cursor) -> "Declaration":
        """Constructs a declaration from a Cursor."""
        node_type: cindex.Type = cursor.type
        return Declaration(
            name=cursor.spelling,
            type_name=node_type.get_canonical().spelling,
            cursor=cursor,
        )

    @override
    def __str__(self) -> str:
        return self.name + ":" + self.type_name

    @property
    def extent(self) -> SourceRange:
        return self.get_extent()

    @property
    def location(self) -> SourceLocation:
        return self.get_location()

    @final
    def get_location(self) -> SourceLocation:
        assert self.cursor
        return self.cursor.location

    @final
    def get_extent(self) -> SourceRange:
        assert self.cursor
        return self.cursor.extent

    @override
    def __eq__(self, __value: object) -> bool:
        """The values are compared with all other values."""
        if not isinstance(__value, Declaration):
            return False

        # Dont compare the cursor...
        attributes_1 = self.__dict__.copy()
        del attributes_1["cursor"]
        attributes_2 = __value.__dict__.copy()
        del attributes_2["cursor"]

        compare_1 = tuple(sorted(attributes_1.items()))
        compare_2 = tuple(sorted(attributes_2.items()))

        return compare_1 == compare_2

    def _get_attr_hashes(self, attributes: dict) -> int:
        assert id(attributes) != id(
            self.__dict__
        ), "attributes needs to be a copy of __dict__"
        del attributes["cursor"]
        return hash(tuple(sorted(attributes.items())))

    @override
    def __hash__(self):
        return self._get_attr_hashes(self.__dict__.copy())

    def is_pointer_type(self) -> bool:
        """Checks if the type name is a pointer type."""
        return self.type_name.endswith(("*", "[]"))


class FunctionDeclaration(Declaration):
    def __init__(
        self,
        name: str,
        type_name: str,
        args: list[Declaration],
        cursor: Optional[Cursor] = None,
    ) -> None:
        super().__init__(name, type_name, cursor=cursor)
        self.args: list[Declaration] = args

    def returns_pointer(self) -> bool:
        # Call the super method, because it checks the type_name which
        # for function declarations is the return type.
        return super().is_pointer_type()

    @override
    def is_pointer_type(self) -> bool:
        "Functions cannot be pointers."
        return False

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
    def __eq__(self, __value: object) -> bool:
        return isinstance(__value, FunctionDeclaration) and super().__eq__(__value)

    @override
    def _get_attr_hashes(self, attributes: dict) -> int:
        # Dont sort args since order matters
        args_hash = hash(tuple(self.args))
        del attributes["args"]
        return super()._get_attr_hashes(attributes) + args_hash

    @override
    def __hash__(self):
        return self._get_attr_hashes(self.__dict__.copy())

    @override
    def __str__(self) -> str:
        arg: list[str] = [f"{arg.name}: {arg.type_name}" for arg in self.args]
        args: str = ", ".join(arg)
        return f"{self.name}({args})"


class TypeDeclaration(Declaration):
    """Represents a type declaration. The following fields declare the type of declaration
    that this object is:
    * The type_name will be the typedef name assigned.
    * The name will be the struct/union name assigned."""

    class ConstructTypes(Enum):
        STRUCT = 0
        UNION = 1
        ENUM = 2

        @override
        def __str__(self) -> str:
            if self == TypeDeclaration.ConstructTypes.STRUCT:
                return "struct"
            elif self == TypeDeclaration.ConstructTypes.UNION:
                return "union"
            elif self == TypeDeclaration.ConstructTypes.ENUM:
                return "enum"
            else:
                return super().__str__()

    def __init__(
        self,
        name: str,
        type_name: str,
        construct_type: ConstructTypes,
        elements: list[Declaration] = [],
        cursor: Optional[Cursor] = None,
    ) -> None:
        super().__init__(name, type_name, cursor=cursor)

        self.elements = elements
        self.construct_type: TypeDeclaration.ConstructTypes = construct_type

    @classmethod
    @override
    def from_cursor(cls, cursor: Cursor) -> "TypeDeclaration":
        node_type: cindex.Type = cursor.type
        type_name: str = node_type.get_typedef_name()

        name: str = TypeDeclaration._parse_name_from_construct_cursor(cursor)

        # Get the definition if it's a TYPE_REF.
        kind: cindex.CursorKind = cursor.kind
        if kind == cindex.CursorKind.TYPE_REF:
            def_cursor: cindex.Cursor = cursor.get_definition()
            kind = def_cursor.kind
            name = def_cursor.spelling
            type_name = ""

        construct_type: TypeDeclaration.ConstructTypes
        if kind == cindex.CursorKind.STRUCT_DECL:
            construct_type = TypeDeclaration.ConstructTypes.STRUCT
        elif kind == cindex.CursorKind.UNION_DECL:
            construct_type = TypeDeclaration.ConstructTypes.UNION
        elif kind == cindex.CursorKind.ENUM_DECL:
            construct_type = TypeDeclaration.ConstructTypes.ENUM
        else:
            raise ValueError(f'Unkown type construct (tag): "{kind}" "{name}"')

        # Get Elements
        elements: list[Declaration] = []
        element: Cursor
        for element in cursor.get_children():
            elements.append(Declaration.from_cursor(element.get_definition()))

        return TypeDeclaration(
            name=name,
            type_name=type_name,
            construct_type=construct_type,
            elements=elements,
            cursor=cursor,
        )

    @classmethod
    def _parse_name_from_construct_cursor(cls, cursor: cindex.Cursor) -> str:
        """Parses the tokens of a construct (struct/enum/union) to extract the
        struct name. The cursor needs to be pointing to that struct. If the
        name returned is empty, then there is no name associated with this struct."""
        for token in cursor.get_tokens():
            if token.kind == cindex.TokenKind.IDENTIFIER:
                return str(token.spelling)
            elif token.kind == cindex.TokenKind.PUNCTUATION:
                # TokenKind.PUNCTUATION is the opening brace, if that is
                # encountered, then the struct doesn't have an identifier.
                return ""
        return ""

    def is_typedef(self) -> bool:
        """If the type has a typedef, the name will be the name of the original
        construct."""
        return len(self.type_name) > 0

    @override
    def is_pointer_type(self) -> bool:
        """Type declarations cannot be pointers."""
        return False

    @override
    def __eq__(self, __value: object) -> bool:
        return isinstance(__value, TypeDeclaration) and super().__eq__(__value)

    @override
    def _get_attr_hashes(self, attributes: dict) -> int:
        elements_hash = hash(tuple(self.elements))
        del attributes["elements"]
        return super()._get_attr_hashes(attributes) + elements_hash

    @override
    def __hash__(self):
        return self._get_attr_hashes(self.__dict__.copy())

    @override
    def __str__(self) -> str:
        construct_type_str: str
        if self.construct_type == TypeDeclaration.ConstructTypes.STRUCT:
            construct_type_str = "struct"
        elif self.construct_type == TypeDeclaration.ConstructTypes.UNION:
            construct_type_str = "union"
        elif self.construct_type == TypeDeclaration.ConstructTypes.ENUM:
            construct_type_str = "enum"
        else:
            raise ValueError(
                "No construct type found for type "
                f"{self.name} ({self.type_name}): {self.construct_type}"
            )

        elements: list[str] = [f"{e.name}: {e.type_name}" for e in self.elements]
        elements_string: str = ", ".join(elements)
        return (
            (f"typedef ({self.type_name}) " if self.is_typedef() else "")
            + f"{construct_type_str} {self.name}"
            + (" {" + elements_string if len(elements_string) > 0 else " {")
            + "}"
        )


class TypedefDeclaration(Declaration):
    """Typedef declarations define the following fields as such:
    * `name`: Name of the typedef.
    * `type_name`: Always blank.
    * `underlying_type`: The underlying TypeDeclaration that the Typedef
    encompasses.

    In the case of anonymous structs (etc.), the type_name will be blank."""

    def __init__(
        self,
        name: str,
        type_name: str,
        underlying_type: TypeDeclaration,
        cursor: Optional[Cursor] = None,
    ) -> None:
        super().__init__(name, type_name, cursor)

        self.underlying_type: TypeDeclaration = underlying_type

    @classmethod
    @override
    def from_cursor(cls, cursor: Cursor) -> "TypedefDeclaration":
        kind: cindex.CursorKind = cursor.kind
        if kind != cindex.CursorKind.TYPEDEF_DECL:
            raise ValueError(
                f"cursor kind is not a TYPEDEF_DECL: {cursor.spelling} {cursor.kind}"
            )

        underlying_type: cindex.Type = cursor.underlying_typedef_type
        decl_cursor: cindex.Cursor = underlying_type.get_declaration()
        underlying_type_decl = TypeDeclaration.from_cursor(decl_cursor)

        return TypedefDeclaration(
            name=cursor.spelling,
            type_name="",
            underlying_type=underlying_type_decl,
            cursor=cursor,
        )

    @override
    def __eq__(self, __value: object) -> bool:
        return isinstance(__value, TypedefDeclaration) and super().__eq__(__value)

    @override
    def __hash__(self):
        return self._get_attr_hashes(self.__dict__.copy())

    @override
    def __str__(self) -> str:
        return f"typedef ({self.name}) {self.underlying_type}"

    @override
    def is_pointer_type(self) -> bool:
        """Typedef declarations are a type declaration so they don't have pointers."""
        return False


class PreProcessingDirective(object):
    """Base class for preprocessing directives."""

    # TODO If __eq__, __hash__, __str__ methods are added,
    # make sure to add super() calls to children.
    pass


class InclusionDirective(PreProcessingDirective):
    """Represents an inclusion directive."""

    def __init__(self, path: str) -> None:
        super().__init__()
        self.path: str = path
        """Path to the inclusion directive.
        `#include <path>`"""

    @override
    def __hash__(self) -> int:
        return adler32(bytes(self.path, "utf-8"))

    @override
    def __eq__(self, __value: object) -> bool:
        return isinstance(__value, InclusionDirective) and self.path == __value.path

    @override
    def __str__(self) -> str:
        return f'#include "{self.path}"'
