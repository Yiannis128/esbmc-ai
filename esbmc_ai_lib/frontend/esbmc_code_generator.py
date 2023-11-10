# Author: Yiannis Charalambous

from typing import Callable, Optional, Literal

import clang.cindex as cindex

import esbmc_ai_lib.config as config

from .ast import ClangAST
from .ast_decl import Declaration, TypeDeclaration, FunctionDeclaration
from .c_types import is_primitive_type, get_base_type


"""Note about how `assign_to` and `init` work:
* `assign_to: Optional[str] = None`: By default the result will not be a statement,
but will generate a value. By assigning "", a statement will be returned. By assigning
a string name, a value will be assigned to that string name.
* `init: bool = False`: This does not matter, unless `assign_to != None` and has a value other
than "", will initialize the variable by appending the type information before the name."""


class ESBMCCodeGenerator(object):
    """Generates code using ClangAST for use in ESBMC scripts."""

    _primitives_base_defaults: dict[str, str] = {
        # Bool
        "bool": "__VERIFIER_nondet_bool()",
        # Decimals
        "float": "__VERIFIER_nondet_float()",
        "double": "__VERIFIER_nondet_double()",
        "long double": "__VERIFIER_nondet_double()",
        # Char
        "char": "__VERIFIER_nondet_char()",
        "signed char": "__VERIFIER_nondet_schar()",
        "unsigned char": "__VERIFIER_nondet_uchar()",
        # Int
        "int": "__VERIFIER_nondet_int()",
        "signed int": "__VERIFIER_nondet_int()",
        "unsigned int": "__VERIFIER_nondet_uint()",
        # Short
        "short": "__VERIFIER_nondet_short()",
        "signed short": "__VERIFIER_nondet_short()",
        "unsigned short": "__VERIFIER_nondet_ushort()",
        # Short (int)
        "short int": "__VERIFIER_nondet_short()",
        "signed short int": "__VERIFIER_nondet_short()",
        "unsigned short int": "__VERIFIER_nondet_ushort()",
        # Long
        "long": "__VERIFIER_nondet_long()",
        "signed long": "__VERIFIER_nondet_long()",
        "unsigned long": "__VERIFIER_nondet_ulong()",
        # Long (int)
        "long int": "__VERIFIER_nondet_long()",
        "signed long int": "__VERIFIER_nondet_long()",
        "unsigned long int": "__VERIFIER_nondet_ulong()",
        # Long Long
        "long long": "__VERIFIER_nondet_long()",
        "signed long long": "__VERIFIER_nondet_long()",
        "unsigned long long": "__VERIFIER_nondet_ulong()",
        # Long Long (int)
        "long long int": "__VERIFIER_nondet_long()",
        "signed long long int": "__VERIFIER_nondet_long()",
        "unsigned long long int": "__VERIFIER_nondet_ulong()",
    }
    """Assign the following values for each primitive data type."""

    ast: ClangAST

    def __init__(self, ast: ClangAST) -> None:
        self.ast = ast

    def statement_primitive_construct(
        self,
        d: Declaration,
        assign_to: Optional[str] = None,
        init: bool = False,
    ) -> str:
        """Returns the primitive construction of a variable/value. Will be
        __VERIFIER_nondet_X(). The list of available ESBMC functions is taken
        from https://github.com/esbmc/esbmc/blob/master/src/clang-c-frontend/clang_c_language.cpp
        """

        base_type_name: str = get_base_type(d.type_name)
        base_value: str = ESBMCCodeGenerator._primitives_base_defaults[base_type_name]

        type_name: str = base_type_name
        value: str = base_value
        if d.is_pointer_type():
            # No difference if adding [] or *. Pointer means initialize continuous memory.
            type_name += "*"
            value = (
                f"({type_name})"
                + "{"
                + ",".join([base_value] * config.ocm_array_expansion)
                + "}"
            )

        if assign_to == None:
            return value
        else:
            if assign_to == "":
                return value + ";"
            else:
                return (type_name + " " if init else "") + f"{assign_to} = {value};"

    def statement_type_construct(
        self,
        d_type: TypeDeclaration,
        init_type: Literal["value", "ptr"],
        assign_to: Optional[str] = None,
        init: bool = False,
        primitive_assignment_fn: Optional[Callable[[Declaration], str]] = None,
        max_depth: int = 5,
        _current_depth: int = -1,
    ) -> str:
        """Constructs a statement that is represented by decleration d. Need ptr information
        since TypeDeclaration does not carry such info (Declaration) base type does."""
        assert d_type.cursor

        _current_depth += 1

        cmd: str

        # Check if primitive type and return nondet value.
        if len(list(d_type.cursor.get_children())) == 0:
            return self.statement_primitive_construct(d_type)

        if d_type.is_typedef():
            cmd = f"({d_type.type_name})" + "{"
            raise NotImplementedError("Typedefs not implemented...")
        else:
            if init_type == "value":
                cmd = f"({d_type.construct_type} {d_type.name})" + "{"
            elif init_type == "ptr":
                cmd = f"({d_type.construct_type} {d_type.name}*)" + "{"
            else:
                raise ValueError(f"init_type has an invalid value: {init_type}")

        # Loop through each element of the data type.
        elements: list[str] = []
        for element in d_type.elements:
            # Check if element is a primitive type. If not, it will need to be
            # further broken.
            if is_primitive_type(element):
                element_code: str
                # Call primitive assignment function if available in order to
                # assign a value. If not, then assign primitive using default
                # way.
                if primitive_assignment_fn != None:
                    element_code = primitive_assignment_fn(element)
                else:
                    element_code = self.statement_primitive_construct(element)
                elements.append(element_code)
            else:
                assert element.cursor
                # Need to convert element Declaration to TypeDeclaration

                type_declaration: Optional[
                    TypeDeclaration
                ] = self.ast._get_type_declaration_from_cursor(element.cursor)

                assert (
                    type_declaration != None
                ), f"Reference for type {element} could not be found"

                # Check if max depth is reached. If it has, then do not init pointer
                # elements.
                if _current_depth < max_depth or not element.is_pointer_type():
                    # Get decleration in AST
                    element_code: str = self.statement_type_construct(
                        d_type=type_declaration,
                        init_type="ptr" if element.is_pointer_type() else "value",
                        max_depth=max_depth,
                        _current_depth=_current_depth,
                        primitive_assignment_fn=primitive_assignment_fn,
                    )
                    elements.append(element_code)
                else:
                    elements.append("NULL")

        # Join the elements of the type initialization.
        cmd += ",".join(elements) + "}"

        # If this construction should be an assignment call.
        if assign_to != None:
            if assign_to == "":
                cmd = cmd + ";"
            elif d_type.type_name != "void":
                # Check if assignment variable should be initialized.
                if init:
                    assign_type: str = d_type.type_name
                    if d_type.type_name == "":
                        assign_type = f"{d_type.construct_type} {d_type.name}"

                    cmd = f"{assign_type} {assign_to} = {cmd};"
                else:
                    cmd = f"{assign_to} = {cmd};"

        return cmd

    def statement_function_call(
        self,
        fn: FunctionDeclaration,
        params: Optional[list[str]] = None,
        assign_to: Optional[str] = None,
        init: bool = False,
    ) -> str:
        """Calls a function fn, returns to result."""

        assert fn.cursor

        cmd: str = fn.name + "("

        # Parameter generation
        if params != None:
            # Given parameters
            cmd += ", ".join(params) + ")"
        else:
            # Walk through arguments
            arg_cmds: list[str] = []
            for arg in fn.args:
                assert arg.cursor

                # Check if primitive type.
                if is_primitive_type(arg):
                    arg_cmds.append(self.statement_primitive_construct(arg))
                else:
                    # Current cursor kind is CursorKind.PARAM_DECL, need to
                    # get underlying type.
                    underlying_type: cindex.Type = arg.cursor.type.get_canonical()
                    underlying_cursor: cindex.Cursor = underlying_type.get_declaration()

                    arg_decl: Declaration = Declaration.from_cursor(underlying_cursor)

                    arg_type: Optional[
                        TypeDeclaration
                    ] = self.ast._get_type_declaration_from_cursor(underlying_cursor)

                    if arg_type is None:
                        raise ValueError(
                            "Statement function call: Could not find declaration for"
                            + arg.name
                            + " "
                            + arg.type_name
                        )
                    arg_cmds.append(
                        self.statement_type_construct(
                            d_type=arg_type,
                            init_type="ptr" if arg_decl.is_pointer_type() else "value",
                        )
                    )

            cmd += ", ".join(arg_cmds) + ")"

        # If this construction should be an assignment call.
        if assign_to != None:
            if assign_to == "":
                cmd = cmd + ";"
            elif fn.type_name != "void":
                if init:
                    assign_type: str = fn.type_name
                    cmd = f"{assign_type} {assign_to} = {cmd};"
                else:
                    cmd = f"{assign_to} = {cmd};"

        return cmd
