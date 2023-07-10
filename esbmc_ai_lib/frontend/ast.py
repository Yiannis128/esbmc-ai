# Author: Yiannis Charalambous

from os.path import dirname, join as path_join
from typing import Optional

import clang.native
import clang.cindex as cindex
from clang.cindex import Config

from .ast_decl import *

# Connect the Python API of Clang to the libclang.so file bundled in the libclang PyPI package.
Config.library_file = path_join(
    dirname(clang.native.__file__),
    "libclang.so",
)


class ClangAST(object):
    file_path: str
    source_code: str
    index: cindex.Index
    tu: cindex.TranslationUnit
    root: cindex.Cursor

    declarations: list[Declaration] = []
    preprocessing_directives: list[PreProcessingDirective] = []

    def __init__(
        self,
        file_path: str,
        source_code: Optional[str] = None,
    ) -> None:
        super().__init__()

        self.index = cindex.Index.create()
        self.init_ast(file_path, source_code)

    def init_ast(self, file_path: str, source_code: Optional[str] = None) -> None:
        if file_path == "":
            raise ValueError("file_path provided cannot be empty string...")

        self.file_path = file_path

        if source_code is None:
            # Load from file
            self.tu = self.index.parse(path=self.file_path)
        else:
            self.source_code = source_code
            # Load from string
            self.tu = self.index.parse(
                path=self.file_path,
                unsaved_files=[(self.file_path, source_code)],
            )
        self.root = self.tu.cursor

    def get_references(self, declaration: Declaration) -> list["Declaration"]:
        """Finds all references to a specific declaration."""
        refs: list = []

        def traverse_children(node: Cursor) -> None:
            if node.referenced and node.referenced == declaration.cursor:
                refs.append(declaration.from_cursor(node))

            for child in node.get_children():
                traverse_children(child)

        for child in self.root.get_children():
            traverse_children(child)

        return refs

    def rename_declaration(self, declaration: Declaration, new_name: str) -> str:
        """Renames the declaration along with any references to it."""

        refs: list[Declaration] = self.get_references(declaration)

        extents: list[SourceRange] = [ref.get_extent() for ref in refs]

        # Rename each ref and update all other refs.
        delta: int = len(new_name) - len(declaration.name)
        size_offset: int = 0
        for extent in extents:
            start_offset: int = extent.start.offset + size_offset
            end_offset: int = extent.end.offset + size_offset
            # Get the reference
            ref: str = self.source_code[start_offset:end_offset]
            # Replace it
            ref = ref.replace(declaration.name, new_name, 1)
            # Place replacement in source code
            self.source_code = (
                self.source_code[:start_offset] + ref + self.source_code[end_offset:]
            )
            # Add delta offset so next references are offset by the change in character.
            size_offset += delta

        # TODO: Consider an update method for all other Declarations to be kept valid when renaming occurs.
        # TODO A method to check for this is for each element:
        # 1. Does it have the same name & type_name
        # 2. Is it in the same location (after offsets have been calculated from the rename)

        return self.source_code

    def get_source_code(self, declaration: Declaration) -> str:
        if declaration.cursor is None:
            raise ValueError("")
        node: cindex.Cursor = declaration.cursor
        loc: cindex.SourceRange = node.extent
        start: cindex.SourceLocation = loc.start
        end: cindex.SourceLocation = loc.end
        return self.source_code[start.offset : end.offset]

    def get_fn_decl(self) -> list[FunctionDeclaration]:
        """Get function declaration list."""
        functions: list[FunctionDeclaration] = []
        node: cindex.Cursor
        for node in self.root.get_children():
            kind: cindex.CursorKind = node.kind
            # StorageClass.NONE indicates that the declaration is inside the file.
            if (
                kind.is_declaration()
                and node.storage_class == cindex.StorageClass.NONE
                and kind == cindex.CursorKind.FUNCTION_DECL
            ):
                functions.append(FunctionDeclaration.from_cursor(node))

        self.declarations.extend(functions)
        return functions

    def get_type_decl(self) -> list[TypeDeclaration]:
        typedefs: list[TypeDeclaration] = []
        node: cindex.Cursor
        for node in self.root.get_children():
            kind: cindex.CursorKind = node.kind
            if (
                kind.is_declaration()
                # NOTE StorageClass.INVALID for some reason is what works here instead of NONE.
                # This may be a bug that's fixed in future versions of libclang.
                and node.storage_class == cindex.StorageClass.INVALID
                and (
                    kind == cindex.CursorKind.STRUCT_DECL
                    or kind == cindex.CursorKind.UNION_DECL
                    or kind == cindex.CursorKind.ENUM_DECL
                    or kind == cindex.CursorKind.TYPEDEF_DECL
                )
            ):
                typedefs.append(TypeDeclaration.from_cursor(node))

        self.declarations.extend(typedefs)
        return typedefs

    def get_variable_decl(self) -> list[Declaration]:
        variables: list[Declaration] = []
        node: cindex.Cursor
        for node in self.root.get_children():
            kind: cindex.CursorKind = node.kind
            if (
                kind.is_declaration()
                and node.storage_class == cindex.StorageClass.NONE
                and kind == cindex.CursorKind.VAR_DECL
            ):
                variables.append(Declaration.from_cursor(node))

        self.declarations.extend(variables)
        return variables

    def get_include_directives(self) -> list[InclusionDirective]:
        includes: list[InclusionDirective] = []
        include: cindex.FileInclusion
        for include in self.tu.get_includes():
            if include.depth == 1:
                includes.append(InclusionDirective(path=str(include.include)))

        self.preprocessing_directives.extend(includes)
        return includes

    def get_all_decl(self) -> list[Declaration]:
        """Returns all local declarations."""
        declarations: list[Declaration] = []
        declarations.extend(self.get_fn_decl())
        declarations.extend(self.get_type_decl())
        declarations.extend(self.get_variable_decl())
        # TODO add more...
        return declarations
